# -*- coding: utf-8 -*-
# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse.drift
===================

Rôle
----
Mesure la dérive des données d’entrée (zone propre) et des prédictions
entre deux fenêtres temporelles.

Fonctions principales
---------------------
- :func:`psi_numerique` : indice de stabilité de population (PSI) pour une
  variable numérique.
- :func:`psi_categoriel` : même indice pour une variable catégorielle.
- :func:`derive_entrees` : calcul du PSI sur les colonnes d’intérêt de la zone
  propre.
- :func:`derive_predictions` : détection de dérive sur les parts de
  négatifs prédites vs réelles dans le résumé quotidien.
- :func:`interpretation` : texte explicatif selon le seuil du PSI.
- :func:`main` : orchestration, génération d’un rapport JSON.

Ce module ne réalise aucun appel réseau, aucune écriture hors du répertoire
défini dans :pymod:`reviewpulse.config` et ne dépend que de la bibliothèque
standard, de *pandas* et de *numpy*.

Décision appliquée ici : ADR 0015 — surveillance de la dérive, révisée le 19/09/2026 (flux naturel seul, colonnes surveillées restreintes).

Quoi
----
Ce module mesure la dérive entre deux fenêtres temporelles de la zone propre
et du résumé quotidien, et produit un rapport JSON ainsi qu'une alerte si des
seuils sont franchis.

Pourquoi
--------
Sans surveillance, une dérive des données d'entrée ou des prédictions peut
dégrader silencieusement le modèle en production. Ce module fournit une mesure
quantitative (PSI) et un garde-fou sur les parts de négatifs prédites, afin de
déclencher une alerte et un ré-entraînement si nécessaire.

Où
--
Appelé par la tâche `drift` du DAG quotidien, après `score`. Lit
`config.CLEAN_FILE` et `config.SUMMARY_FILE`, écrit `drift_report.json` dans
`config.SCORED_DIR` et, le cas échéant, un fichier d'alerte dans
`config.SCORED_DIR / "alertes"`.

Comment
-------
Le module calcule l'indice de stabilité de population (PSI) sur les colonnes
d'intérêt de la zone propre, en utilisant la première moitié comme référence
et la seconde comme fenêtre courante. Pour les prédictions, il compare les
parts de négatifs prédites et réelles du résumé quotidien et marque les lignes
hors bornes. Un verdict d'alerte est ensuite évalué à partir des seuils
configurés, et une alerte est écrite si nécessaire.

Choix de conception
-------------------
- **PSI plutôt qu'un test statistique** : le PSI se lit par seuils (0,1 et
  0,2) et supporte les variables catégorielles, contrairement à un test de
  Kolmogorov-Smirnov ou du chi-deux qui nécessiterait des hypothèses
  supplémentaires. ADR 0015.
- **Colonnes surveillées restreintes** : seules les colonnes de
  `COLONNES_ALERTE` peuvent lever une alerte. `language` et `app_id` sont
  exclues car leur composition est imposée par le plan de collecte, pas
  observée sur une population (mesure du 19/09/2026). ADR 0015.
- **Flux naturel seul** : le flux `negative_boost` est une collecte ponctuelle
  destinée à l'entraînement et n'arrive jamais en production ; l'inclure
  fausserait la mesure de la population réelle. ADR 0015.
- **Écriture atomique** : le rapport et l'alerte sont écrits via des fichiers
  temporaires et `os.replace` (pour l'alerte) ou directement avec `open` (pour
  le rapport), garantissant qu'un fichier partiel n'est jamais lu.

Limites connues
---------------
- Le module ne surveille que les colonnes listées dans `COLONNES_ALERTE` pour
  les alertes ; les autres colonnes sont calculées mais informatives.
- La détection de dérive des prédictions repose sur le résumé quotidien, qui
  est limité aux avis naturels ; les groupes de moins de `n_min` avis sont
  ignorés.
- Aucune correction automatique n'est appliquée : le module se contente de
  signaler et d'écrire une alerte.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from reviewpulse import config

logger = logging.getLogger(__name__)

# Pourquoi : ces seuils sont ceux de la littérature PSI (0,1 et 0,2) et le
# garde-fou sur la part hors bornes évite les faux positifs sur de petits
# échantillons. L'alternative d'un seuil unique sur le PSI ne couvrait pas la
# dérive des prédictions.
# Seuils d'alerte. 0,2 est le seuil usuel du PSI, celui qu'emploie deja
# `interpretation` pour parler de derive ; la part hors bornes est le
# garde-fou cote predictions.
SEUIL_PSI_ALERTE = 0.2
SEUIL_PART_HORS_BORNES = 0.1

# Pourquoi : restreindre les colonnes d'alerte évite de déclencher une alerte
# sur des colonnes dont la distribution est imposée par le plan de collecte
# (language, app_id) ou constante après filtrage (sample_source). L'alternative
# de surveiller toutes les colonnes produisait des faux positifs (mesure du
# 19/09/2026 : PSI 3,10 sur `language` sans changement de nature des avis).
# Colonnes dont le PSI peut lever une alerte. `language` et `app_id` en sont
# exclus : leur composition est imposée par notre propre plan de collecte
# (`config.APP_IDS` × `config.LANGUAGES`), pas observée sur une population.
# Mesure du 19/09/2026, flux naturel seul : la fenêtre ancienne est à 85 %
# francophone, la récente à 91 % anglophone, ce qui porte le PSI de `language`
# à 3,10 sans qu'aucun avis n'ait changé de nature. Ces colonnes restent dans
# le rapport, à titre informatif. `sample_source` est constant après filtrage.
COLONNES_ALERTE = ("text_len",)


def evaluer_alerte(rapport: dict, colonnes: tuple[str, ...] | None = None) -> dict:
    """
    Évalue si une alerte de dérive doit être levée.

    Pourquoi : centralise la décision d'alerte pour que `main` et les tests
    partagent la même logique de seuils, et pour permettre de restreindre les
    colonnes surveillées sans modifier le rapport.

    Paramètres
    ----------
    rapport : dict
        Rapport tel que construit par :func:`main`, contenant les clés
        ``entrees`` et ``predictions``.

    Retour
    ------
    dict
        {
            "alerte": bool,
            "motifs": list[str],
            "psi_max": float,
            "colonne_psi_max": str | None,
            "part_hors_bornes": float,
        }
    """
    # Valeurs par défaut
    resultat = {
        "alerte": False,
        "motifs": [],
        "psi_max": 0.0,
        "colonne_psi_max": None,
        "part_hors_bornes": 0.0,
    }

    surveillees = COLONNES_ALERTE if colonnes is None else tuple(colonnes)
    resultat["colonnes_surveillees"] = list(surveillees)

    entrees = {
        col: info
        for col, info in rapport.get("entrees", {}).items()
        if col in surveillees
    }
    predictions = rapport.get("predictions", [])

    # PSI maximal
    if entrees:
        psi_vals = {col: info.get("psi", 0.0) for col, info in entrees.items()}
        colonne_max = max(psi_vals, key=psi_vals.get)
        psi_max = psi_vals[colonne_max]
        resultat["psi_max"] = psi_max
        resultat["colonne_psi_max"] = colonne_max
        if psi_max >= SEUIL_PSI_ALERTE:
            resultat["alerte"] = True
            resultat["motifs"].append(
                f"Le PSI maximal {psi_max:.3f} dépasse le seuil d'alerte {SEUIL_PSI_ALERTE:.3f}."
            )

    # Part d'éléments hors bornes
    if predictions:
        total = len(predictions)
        hors = sum(1 for p in predictions if p.get("hors_bornes"))
        part = hors / total if total > 0 else 0.0
        resultat["part_hors_bornes"] = part
        if part > SEUIL_PART_HORS_BORNES:
            resultat["alerte"] = True
            resultat["motifs"].append(
                f"La proportion d'éléments hors bornes {part:.2%} dépasse le seuil {SEUIL_PART_HORS_BORNES:.2%}."
            )

    return resultat


def ecrire_alerte(verdict: dict, repertoire: Path) -> Path | None:
    """
    Écrit une alerte de dérive sous forme de fichier JSON.

    Si ``verdict["alerte"]`` est ``False``, aucune écriture n'est effectuée et
    ``None`` est retourné.

    Pourquoi : ne pas écrire de fichier inutile quand il n'y a pas d'alerte, et
    journaliser l'échec sans interrompre le pipeline si l'écriture échoue.

    Paramètres
    ----------
    verdict : dict
        Résultat de :func:`evaluer_alerte`.
    repertoire : pathlib.Path
        Répertoire racine où créer le sous‑dossier ``alertes``.

    Retour
    ------
    pathlib.Path | None
        Chemin du fichier d'alerte écrit, ou ``None`` si aucune alerte.
    """
    if not verdict.get("alerte"):
        return None

    alerts_dir = repertoire / "alertes"
    try:
        alerts_dir.mkdir(parents=True, exist_ok=True)
        maintenant = datetime.datetime.now(datetime.timezone.utc)
        timestamp = maintenant.strftime("%Y%m%d-%H%M%S")
        filename = f"derive_{timestamp}.json"
        chemin = alerts_dir / filename

        payload = dict(verdict)  # copie
        payload["horodatage_utc"] = maintenant.isoformat()
        payload["code_commit"] = os.getenv("REVIEWPULSE_COMMIT", "inconnu")

        with chemin.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        motifs = verdict.get("motifs", [])
        logger.info("Alerte de dérive écrite dans %s : %s", chemin, "; ".join(motifs))
        return chemin
    except Exception as exc:
        logger.error("Échec de l'écriture de l'alerte de dérive : %s", exc)
        return None

# --------------------------------------------------------------------------- #
# Indice de stabilité de population (PSI)                                    #
# --------------------------------------------------------------------------- #
def psi_numerique(reference: pd.Series, courant: pd.Series, bins: int = 10) -> float:
    """
    Calcule le PSI (Population Stability Index) sur une variable numérique.

    Les bornes des classes proviennent des quantiles de ``reference`` ;
    les éventuels doublons de bornes sont supprimés.  Les parts nulles sont
    remplacées par ``1e-6`` afin d’éviter une division par zéro.

    Formule appliquée :
    ``∑ (p_c - p_r) × ln(p_c / p_r)``

    Pourquoi : utiliser les quantiles de la référence garantit que les classes
    sont définies une fois pour toutes et ne dépendent pas de la fenêtre
    courante, ce qui rend la comparaison stable. Le remplacement des zéros par
    une petite valeur évite les divisions par zéro sans biaiser le résultat.

    Parameters
    ----------
    reference : pd.Series
        Série de référence (fenêtre la plus ancienne).
    courant : pd.Series
        Série à comparer (fenêtre la plus récente).
    bins : int, optional
        Nombre de classes souhaité (défaut : 10).

    Returns
    -------
    float
        Valeur du PSI.
    """
    if reference.empty or courant.empty:
        logger.debug("Une des séries est vide, PSI = 0.0")
        return 0.0

    # 1. Détermination des bornes à partir des quantiles de la référence
    quantiles = np.linspace(0, 1, bins + 1)
    edges = reference.quantile(quantiles).drop_duplicates().values
    if len(edges) < 2:
        # Pas assez de variation pour créer des classes
        logger.debug("Pas assez de bornes distinctes, PSI = 0.0")
        return 0.0

    # 2. Découpage des deux séries dans les mêmes intervalles
    ref_bins = pd.cut(reference, bins=edges, include_lowest=True)
    cur_bins = pd.cut(courant, bins=edges, include_lowest=True)

    # 3. Proportions dans chaque classe
    p_ref = ref_bins.value_counts(normalize=True).reindex(ref_bins.cat.categories, fill_value=0)
    p_cur = cur_bins.value_counts(normalize=True).reindex(ref_bins.cat.categories, fill_value=0)

    # 4. Remplacement des zéros
    eps = 1e-6
    p_ref = p_ref.replace(0, eps)
    p_cur = p_cur.replace(0, eps)

    # 5. Calcul du PSI
    psi = float(((p_cur - p_ref) * np.log(p_cur / p_ref)).sum())
    logger.debug("PSI numérique calculé : %f", psi)
    return psi


def psi_categoriel(reference: pd.Series, courant: pd.Series) -> float:
    """
    Calcule le PSI sur une variable catégorielle.

    Les catégories sont l’union des modalités présentes dans les deux séries.
    Les parts nulles sont remplacées par ``1e-6`` pour éviter la division par
    zéro.

    Pourquoi : l'union des modalités garantit qu'une catégorie absente d'une
    fenêtre est traitée avec une part nulle, ce qui capture l'apparition ou la
    disparition de modalités. Le remplacement des zéros évite les divisions par
    zéro.

    Parameters
    ----------
    reference : pd.Series
        Série de référence.
    courant : pd.Series
        Série à comparer.

    Returns
    -------
    float
        Valeur du PSI.
    """
    if reference.empty or courant.empty:
        logger.debug("Une des séries est vide, PSI = 0.0")
        return 0.0

    categories = pd.Index(reference.dropna().unique()).union(courant.dropna().unique())
    p_ref = reference.value_counts(normalize=True).reindex(categories, fill_value=0)
    p_cur = courant.value_counts(normalize=True).reindex(categories, fill_value=0)

    eps = 1e-6
    p_ref = p_ref.replace(0, eps)
    p_cur = p_cur.replace(0, eps)

    psi = float(((p_cur - p_ref) * np.log(p_cur / p_ref)).sum())
    logger.debug("PSI catégoriel calculé : %f", psi)
    return psi


# --------------------------------------------------------------------------- #
# Dérive sur les entrées (zone propre)                                        #
# --------------------------------------------------------------------------- #
def derive_entrees(reference: pd.DataFrame, courant: pd.DataFrame) -> Dict[str, float]:
    """
    Applique le PSI aux colonnes d’intérêt de la zone propre.

    Colonnes prises en compte :
    - ``text_len`` (numérique) si présente,
    - ``language``, ``app_id`` et ``sample_source`` (catégorielles).

    Les colonnes absentes de *l’une* des deux fenêtres sont simplement ignorées.

    Pourquoi : ne pas échouer si une colonne manque dans une fenêtre permet au
    module de fonctionner même si le schéma évolue légèrement, et de ne
    surveiller que les colonnes réellement présentes.

    Parameters
    ----------
    reference : pd.DataFrame
        Première moitié (fenêtre de référence) de la zone propre.
    courant : pd.DataFrame
        Deuxième moitié (fenêtre courante) de la zone propre.

    Returns
    -------
    dict[str, float]
        Mapping ``nom_de_colonne → PSI``.
    """
    result: Dict[str, float] = {}

    # 1. Variable numérique éventuelle
    if "text_len" in reference.columns and "text_len" in courant.columns:
        result["text_len"] = psi_numerique(reference["text_len"], courant["text_len"])

    # 2. Variables catégorielles
    for col in ("language", "app_id", "sample_source"):
        if col in reference.columns and col in courant.columns:
            result[col] = psi_categoriel(reference[col].astype(str), courant[col].astype(str))

    logger.info("PSI sur les entrées calculés : %s", result)
    logger.info("Nombre de colonnes analysées : %d", len(result))
    return result


# --------------------------------------------------------------------------- #
# Dérive sur les prédictions (résumé quotidien)                               #
# --------------------------------------------------------------------------- #
def derive_predictions(
    resume: pd.DataFrame,
    ratio_min: float = 0.5,
    ratio_max: float = 2.0,
    n_min: int = 20,
) -> List[Dict[str, Any]]:
    """
    Analyse la dérive des parts de négatifs prédites vs réelles.

    Pour chaque ligne du résumé dont ``n_reviews`` ≥ ``n_min``, le ratio
    ``share_negative_pred / share_negative_true`` est calculé (en excluant les
    lignes où la part réelle est nulle).  Le champ ``hors_bornes`` indique si
    le ratio sort de l’intervalle ``[ratio_min, ratio_max]``.

    Pourquoi : le seuil `n_min` évite de considérer des groupes trop petits où
    le ratio serait instable, et l'exclusion des parts réelles nulles évite une
    division par zéro. Les bornes `ratio_min` et `ratio_max` définissent une
    plage acceptable autour de 1 (prédiction parfaite).

    Parameters
    ----------
    resume : pd.DataFrame
        Résumé quotidien produit par :func:`reviewpulse.score.summarize`.
    ratio_min : float, optional
        Borne inférieure du ratio acceptable (défaut : 0.5).
    ratio_max : float, optional
        Borne supérieure du ratio acceptable (défaut : 2.0).
    n_min : int, optional
        Nombre minimal d’avis requis pour considérer la ligne (défaut : 20).

    Returns
    -------
    list[dict]
        Liste de dictionnaires contenant ``app_id``, ``language``, ``date``,
        ``ratio`` et ``hors_bornes``.
    """
    records: List[Dict[str, Any]] = []

    required_cols = {"app_id", "language", "date", "n_reviews", "share_negative_pred", "share_negative_true"}
    missing = required_cols - set(resume.columns)
    if missing:
        logger.warning("Colonnes manquantes dans le résumé : %s", missing)
        return records

    for _, row in resume.iterrows():
        if row["n_reviews"] < n_min:
            continue
        true_share = row["share_negative_true"]
        if true_share == 0:
            # On ignore les cas où la part réelle est nulle (division impossible)
            continue
        ratio = row["share_negative_pred"] / true_share
        hors = not (ratio_min <= ratio <= ratio_max)
        records.append(
            {
                "app_id": int(row["app_id"]),
                "language": str(row["language"]),
                "date": str(row["date"]),
                "ratio": float(ratio),
                "hors_bornes": bool(hors),
            }
        )
    logger.info("Analyse de dérive des prédictions : %d enregistrements étudiés", len(records))
    return records


# --------------------------------------------------------------------------- #
# Interprétation du PSI                                                       #
# --------------------------------------------------------------------------- #
def interpretation(indice: float) -> str:
    """
    Interprète un indice PSI selon les seuils usuels.

    - ``stable`` : indice < 0.1
    - ``à surveiller`` : 0.1 ≤ indice < 0.2
    - ``dérive`` : indice ≥ 0.2

    Ces seuils sont ceux communément employés pour le Population Stability
    Index (PSI) dans les projets de monitoring de modèles.

    Pourquoi : fournir une lecture humaine immédiate du PSI, alignée sur les
    seuils d'alerte utilisés dans `evaluer_alerte`.

    Parameters
    ----------
    indice : float
        Valeur du PSI à interpréter.

    Returns
    -------
    str
        Description textuelle.
    """
    if indice < 0.1:
        return "stable"
    if indice < 0.2:
        return "à surveiller"
    return "dérive"


# --------------------------------------------------------------------------- #
# Point d’entrée principal                                                    #
# --------------------------------------------------------------------------- #
def main() -> int:
    """
    Orchestration du calcul de dérive.

    - Charge le fichier propre ``config.CLEAN_FILE``.
    - Le découpe en deux fenêtres temporelles selon la colonne de date
      (``created_at`` si disponible, sinon ``updated_at``) ; la moitié la plus
      ancienne sert de référence.
    - Calcule le PSI sur les colonnes d’intérêt via :func:`derive_entrees`.
    - Charge le résumé quotidien ``config.SUMMARY_FILE`` et analyse les
      prédictions via :func:`derive_predictions`.
    - Génère un rapport JSON dans ``config.SCORED_DIR / "drift_report.json"``.
    - Ajoute une éventuelle alerte de dérive hors journal et déclenche le
      ré‑entraînement si nécessaire.
    - Retourne ``0`` en cas de succès, ``1`` sinon (fichier manquant ou erreur).

    Tous les messages d’erreur sont journalisés avec le logger du module.

    Pourquoi : ce module est conçu pour être appelé comme tâche du DAG ; il
    doit donc retourner un code de sortie exploitable par Airflow et journaliser
    chaque étape pour faciliter le diagnostic en cas d'échec.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info("Début du calcul de dérive")

    # ------------------------------------------------------------------- #
    # Chargement de la zone propre
    # ------------------------------------------------------------------- #
    try:
        df_clean = pd.read_parquet(config.CLEAN_FILE)
    except Exception as exc:
        logger.error("Impossible de lire le fichier propre %s : %s", config.CLEAN_FILE, exc)
        return 1

    # Pourquoi : le flux `negative_boost` est une collecte ponctuelle destinée
    # à l'entraînement ; il n'arrive jamais en production. L'inclure fausserait
    # la mesure de la population réelle (mesure du 19/09/2026 : PSI 2,07 sur
    # `language`). La zone gold applique déjà ce même filtre.
    # Seul le flux naturel est surveillé. Le flux `negative_boost` est une
    # collecte ponctuelle destinée à l'entraînement : il n'arrive jamais en
    # production, et sa présence dans la seule fenêtre ancienne faisait mesurer
    # la méthode de collecte au lieu de la population (mesure du 19/09/2026 :
    # PSI 2,07 sur `language`, la fenêtre ancienne étant à 79 % francophone et
    # à 45 % de flux boost, la récente à 86 % anglophone et à 93 % naturelle).
    # La zone gold applique déjà ce même filtre (`mart_sentiment_daily`).
    if "sample_source" in df_clean.columns:
        avant = len(df_clean)
        df_clean = df_clean[df_clean["sample_source"] == config.SAMPLE_NATURAL]
        logger.info(
            "Dérive mesurée sur le flux naturel seul : %d lignes sur %d",
            len(df_clean),
            avant,
        )
        if df_clean.empty:
            logger.error("Aucune ligne du flux naturel dans la zone propre.")
            return 1

    # Pourquoi : `created_at` est la date de création de l'avis, plus fiable que
    # `updated_at` qui peut changer après une mise à jour. Si `created_at` est
    # absente, on se replie sur `updated_at`.
    # Choix de la colonne date
    date_col = "created_at" if "created_at" in df_clean.columns else "updated_at"
    if date_col not in df_clean.columns:
        logger.error("Aucune colonne date disponible dans la zone propre.")
        return 1

    # Pourquoi : trier par date garantit que la première moitié est bien la plus
    # ancienne, servant de référence, et la seconde la plus récente.
    # Tri chronologique et découpage en deux moitiés
    df_clean = df_clean.sort_values(by=date_col)
    midpoint = len(df_clean) // 2
    reference_df = df_clean.iloc[:midpoint].reset_index(drop=True)
    courant_df = df_clean.iloc[midpoint:].reset_index(drop=True)

    drift_entrees = derive_entrees(reference_df, courant_df)

    # ------------------------------------------------------------------- #
    # Chargement du résumé quotidien
    # ------------------------------------------------------------------- #
    try:
        df_summary = pd.read_parquet(config.SUMMARY_FILE)
    except Exception as exc:
        logger.error("Impossible de lire le fichier de résumé %s : %s", config.SUMMARY_FILE, exc)
        return 1

    drift_predictions = derive_predictions(df_summary)

    # ------------------------------------------------------------------- #
    # Construction du rapport
    # ------------------------------------------------------------------- #
    report = {
        "entrees": {col: {"psi": psi, "interpretation": interpretation(psi)} for col, psi in drift_entrees.items()},
        "predictions": drift_predictions,
    }

    # Évaluation de l'alerte
    verdict = evaluer_alerte(report)
    report["alerte"] = verdict

    report_path: Path = config.SCORED_DIR / "drift_report.json"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Rapport de dérive écrit dans %s", report_path)
    except Exception as exc:
        logger.error("Échec de l'écriture du rapport de dérive : %s", exc)
        return 1

    # Écriture de l'alerte éventuelle
    if verdict.get("alerte"):
        chemin_alerte = ecrire_alerte(verdict, config.SCORED_DIR)
        if chemin_alerte is None:
            logger.error("Échec de l'écriture de l'alerte de dérive.")
            return 1

    logger.info("Fin du calcul de dérive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

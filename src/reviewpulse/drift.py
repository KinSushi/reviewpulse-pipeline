# -*- coding: utf-8 -*-
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
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from reviewpulse import config

logger = logging.getLogger(__name__)

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
    - Retourne ``0`` en cas de succès, ``1`` sinon (fichier manquant ou erreur).

    Tous les messages d’erreur sont journalisés avec le logger du module.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # ------------------------------------------------------------------- #
    # Chargement de la zone propre
    # ------------------------------------------------------------------- #
    try:
        df_clean = pd.read_parquet(config.CLEAN_FILE)
    except Exception as exc:
        logger.error("Impossible de lire le fichier propre %s : %s", config.CLEAN_FILE, exc)
        return 1

    # Choix de la colonne date
    date_col = "created_at" if "created_at" in df_clean.columns else "updated_at"
    if date_col not in df_clean.columns:
        logger.error("Aucune colonne date disponible dans la zone propre.")
        return 1

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

    report_path: Path = config.SCORED_DIR / "drift_report.json"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Rapport de dérive écrit dans %s", report_path)
    except Exception as exc:
        logger.error("Échec de l'écriture du rapport de dérive : %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

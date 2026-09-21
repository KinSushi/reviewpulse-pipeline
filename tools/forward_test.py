"""tools.forward_test
===================

Ce script exécute, en conditions réelles, un jeu complet de contrôles de santé
sur la stack ReviewPulse :

* API FastAPI
* Tableau de bord Streamlit
* Serveur MLflow
* Données brutes, nettoyées et scorées

Chaque contrôle est implémenté sous forme de fonction retournant un tuple
``(nom, statut, détail)`` où *statut* vaut ``"PASS"`` ou ``"FAIL"``.
Les exceptions sont capturées et converties en ``FAIL`` avec le message
d'erreur.

Le script accepte plusieurs arguments en ligne de commande afin de pouvoir
cibler des environnements de test différents.  Le rapport Markdown généré
contient :

* titre et date UTC
* identifiant du commit Git (ou ``inconnu``)
* URLs testées
* tableau récapitulatif des contrôles
* nombre total de PASS / FAIL

Le code de sortie est ``0`` si tous les contrôles passent, sinon ``1``.

Quoi
----
Script de validation end-to-end de la stack ReviewPulse déployée.

Pourquoi
--------
Détecter les régressions en production avant qu'elles n'affectent les utilisateurs.
Éviter le défaut où un composant fonctionne isolément mais échoue en intégration
(constaté le 16/09/2026 : API santé OK mais prédictions incohérentes).

Ou
----
Appelé par : CI/CD (.github/workflows/pipeline.yml), opérateur manuel.
Lit : config.py, fichiers parquet (clean, scored), DuckDB gold, tables Iceberg.
Écrit : rapport Markdown dans docs/evidence/forward_test.md.

Comment
-------
1. Parse les arguments CLI pour les URLs et chemins.
2. Exécute A1 pour extraire la version du modèle champion.
3. Enchaîne 15 contrôles (A1-A4, D1, M1, F1-F10) avec décorateur _handle.
4. Chaque contrôle retourne (nom, statut, détail) ou FAIL sur exception.
5. Génère un rapport Markdown récapitulatif avec date, commit, URLs, résultats.
6. Retourne 0 si tous PASS, 1 sinon.

Choix de conception
-------------------
- Décorateur _handle : centralise la capture d'exception pour éviter la duplication
  de code try/except dans chaque contrôle. Alternative écartée : bloc try/except
  dans chaque fonction (trop verbeux, risque d'oubli).
- Tuple (nom, statut, détail) : structure simple, sérialisable, lisible dans le rapport.
  Alternative écartée : classe dataclass (surcharge inutile pour ce cas).
- Rapport Markdown : format lisible par humain et versionnable dans Git.
  Alternative écartée : JSON (moins lisible pour revue manuelle).
- Code de sortie 0/1 : convention Unix standard pour l'orchestration CI/CD.
- Pas de modification de la logique existante : ce fichier est un outil de validation,
  pas un composant de production. ADR 0011 (orchestration), ADR 0008 (promotion champion).

Limites connues
---------------
- Ne teste pas les performances (latence, débit).
- Ne valide pas la cohérence sémantique des prédictions (seulement le format).
- Dépend de la disponibilité des services externes (API, dashboard, MLflow).
- Le contrôle F4 nécessite un minimum de 20 avis négatifs par groupe (app_id, language).
- Ne remplace pas les tests unitaires (reverse_tests.py) ni les contrôles qualité (expectations.py).
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import requests
import duckdb

from reviewpulse import config, quality
from reviewpulse.decision import LABEL_NEGATIVE
# Fonctions de lecture du lakehouse
from reviewpulse.lakehouse import read_table, table_history

# --------------------------------------------------------------------------- #
# Configuration du logger
# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
# Types utilitaires
# --------------------------------------------------------------------------- #
ControlResult = Tuple[str, str, str]  # (nom, statut, détail)


# --------------------------------------------------------------------------- #
# Fonctions de contrôle
# --------------------------------------------------------------------------- #
def _handle(func):
    """Décorateur qui transforme toute exception en résultat FAIL.

    Pourquoi : éviter la duplication de code try/except dans chaque contrôle.
    Alternative écartée : bloc try/except dans chaque fonction (trop verbeux).

    Args:
        func: Fonction de contrôle à décorer.

    Returns:
        Fonction wrapper retournant ControlResult.

    Raises:
        Aucune exception propagée : toutes capturées et converties en FAIL.
    """
    def wrapper(*args, **kwargs) -> ControlResult:
        name = func.__name__.upper()
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover – safety net
            logger.debug("Exception dans %s : %s", name, exc, exc_info=True)
            return (name, "FAIL", str(exc))
    return wrapper


@_handle
def A1(api_url: str) -> ControlResult:
    """Vérifie la santé de l'API et la validité des métadonnées du modèle.

    Pourquoi : s'assurer que l'API est accessible et que le modèle est configuré.
    Le seuil (0,1) pour decision_threshold vient de la convention de décision.

    Args:
        api_url: URL de base de l'API ReviewPulse.

    Returns:
        ControlResult avec model_version et decision_threshold en détail.

    Raises:
        RuntimeError: Si le statut HTTP n'est pas 200.
        ValueError: Si model_version est vide ou decision_threshold hors (0,1).
    """
    resp = requests.get(f"{api_url.rstrip('/')}/health", timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    data = resp.json()
    mv = data.get("model_version")
    dt = data.get("decision_threshold")
    if not mv:
        raise ValueError("model_version vide")
    if not isinstance(dt, (int, float)) or not (0 < dt < 1):
        raise ValueError(f"decision_threshold hors intervalle (0,1) : {dt}")
    return ("A1", "PASS", f"model_version={mv}, decision_threshold={dt}")


@_handle
def A2(api_url: str) -> ControlResult:
    """Valide les prédictions sur 4 textes de référence (2 négatifs, 2 positifs).

    Pourquoi : vérifier que le modèle classe correctement des cas connus.
    Les textes sont en anglais et français pour tester le multilingue.

    Args:
        api_url: URL de base de l'API ReviewPulse.

    Returns:
        ControlResult avec les labels prédits en détail.

    Raises:
        RuntimeError: Si le statut HTTP n'est pas 200.
        ValueError: Si la réponse n'a pas 4 prédictions.
        AssertionError: Si les labels ne correspondent pas aux attendus.
    """
    texts = [
        "The game crashes on launch after the last patch, I want a refund.",
        "Le jeu plante sans arrêt depuis la mise à jour, injouable.",
        "Masterpiece, I loved every minute of this game.",
        "Chef-d’œuvre absolu, je recommande à tout le monde."
    ]
    resp = requests.post(
        f"{api_url.rstrip('/')}/predict",
        json={"texts": texts},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    payload = resp.json()
    preds = payload.get("predictions")
    if not isinstance(preds, list) or len(preds) != 4:
        raise ValueError("Réponse inattendue")
    # extraction des libellés
    labels = [p.get("label") for p in preds]
    expected = ["negative", "negative", "positive", "positive"]
    if labels != expected:
        raise AssertionError(f"Labels {labels} ≠ {expected}")
    return ("A2", "PASS", f"labels={labels}")


@_handle
def A3(api_url: str) -> ControlResult:
    """Valide le rejet d'une requête avec une liste de textes vide.

    Pourquoi : s'assurer que l'API refuse les entrées invalides (fail-closed).
    Le code 422 est la convention HTTP pour les données non valides.

    Args:
        api_url: URL de base de l'API ReviewPulse.

    Returns:
        ControlResult confirmant la réception du 422.

    Raises:
        RuntimeError: Si le statut HTTP n'est pas 422.
    """
    resp = requests.post(
        f"{api_url.rstrip('/')}/predict",
        json={"texts": []},
        timeout=10,
    )
    if resp.status_code != 422:
        raise RuntimeError(f"Statut {resp.status_code} (attendu 422)")
    return ("A3", "PASS", "reçu 422 comme attendu")


@_handle
def A4(api_url: str) -> ControlResult:
    """Valide l'endpoint /insights avec un app_id de la configuration.

    Pourquoi : vérifier que les insights sont accessibles et retournent des données.
    Utilise le premier APP_IDS de config pour la démo rejouable.

    Args:
        api_url: URL de base de l'API ReviewPulse.

    Returns:
        ControlResult avec le nombre d'éléments retournés.

    Raises:
        RuntimeError: Si APP_IDS est vide ou statut HTTP non 200.
        ValueError: Si la réponse n'est pas une liste.
    """
    if not config.APP_IDS:
        raise RuntimeError("APP_IDS vide dans la configuration")
    app_id = config.APP_IDS[0]
    resp = requests.get(
        f"{api_url.rstrip('/')}/insights",
        params={"app_id": app_id, "days": 7},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError("Réponse n'est pas une liste")
    return ("A4", "PASS", f"{len(data)} éléments")


@_handle
def D1(dashboard_url: str) -> ControlResult:
    """Vérifie la santé du tableau de bord Streamlit.

    Pourquoi : s'assurer que le dashboard est accessible aux utilisateurs.
    L'endpoint /_stcore/health est l'endpoint de santé natif de Streamlit.

    Args:
        dashboard_url: URL de base du tableau de bord Streamlit.

    Returns:
        ControlResult confirmant l'accès OK.

    Raises:
        RuntimeError: Si le statut HTTP n'est pas 200.
    """
    resp = requests.get(f"{dashboard_url.rstrip('/')}/_stcore/health", timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    return ("D1", "PASS", "OK")


@_handle
def M1(mlflow_url: str, expected_version: str) -> ControlResult:
    """Vérifie que l'alias champion dans MLflow correspond à la version d'A1.

    Pourquoi : garantir la cohérence entre l'API et le registre de modèles.
    L'alias champion est le mécanisme de promotion (ADR 0008).

    Args:
        mlflow_url: URL de base du serveur MLflow.
        expected_version: Version attendue du modèle champion (issue de A1).

    Returns:
        ControlResult confirmant que champion=servi.

    Raises:
        RuntimeError: Si le statut HTTP n'est pas 200.
        ValueError: Si le format de model_version est inattendu.
        AssertionError: Si la version servie diffère de l'attendue.
    """
    endpoint = (
        f"{mlflow_url.rstrip('/')}"
        f"/api/2.0/mlflow/registered-models/alias"
        f"?name={config.MODEL_NAME}&alias={config.ALIAS_CHAMPION}"
    )
    resp = requests.get(endpoint, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    info = resp.json()
    mv_info = info.get("model_version")
    if not isinstance(mv_info, dict):
        raise ValueError("Format inattendu de model_version")
    version = mv_info.get("version")
    if version != expected_version:
        raise AssertionError(f"Version {version} ≠ {expected_version}")
    return ("M1", "PASS", f"champion={expected_version} servi={version}")


@_handle
def F1(data_dir: Path) -> ControlResult:
    """Vérifie l'idempotence des fichiers raw : chaque flux a autant de lignes que d'ids distincts.

    Pourquoi : détecter les doublons dans la zone brute (ADR 0002).
    Le flux est déduit du chemin (sample=negative_boost ou natural).

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult avec le détail par flux (lignes / ids distincts).

    Raises:
        FileNotFoundError: Si le répertoire raw est absent.
        RuntimeError: Si aucun fichier .jsonl n'est trouvé.
        AssertionError: Si le nombre de lignes diffère du nombre d'ids distincts.
    """
    raw_dir = data_dir / "raw"
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"{raw_dir} absent")
    files = list(raw_dir.rglob("*.jsonl"))
    if not files:
        raise RuntimeError("Aucun fichier .jsonl trouvé")
    # Accumulation des ids par flux
    ids_by_flux = {"natural": [], "negative_boost": []}
    for file_path in files:
        flux = "negative_boost" if "sample=negative_boost" in str(file_path) else "natural"
        with file_path.open("r", encoding="utf-8") as f:
            ids = [json.loads(line).get("recommendationid") for line in f if line.strip()]
            ids_by_flux[flux].extend(ids)
    # Vérification de l'unicité globale par flux
    details = []
    for flux, ids in ids_by_flux.items():
        distinct = set(ids)
        if len(ids) != len(distinct):
            raise AssertionError(
                f"Flux {flux}: {len(ids)} lignes vs {len(distinct)} ids distincts"
            )
        details.append(f"{flux}: {len(ids)} lignes / {len(distinct)} ids")
    detail_str = " ; ".join(details)
    return ("F1", "PASS", detail_str)


@_handle
def F2(data_dir: Path) -> ControlResult:
    """Vérifie la qualité du parquet clean via quality.check_clean.

    Pourquoi : s'assurer que la zone propre passe les contrôles qualité (ADR 0005).
    check_clean renvoie [] si tout est valide, sinon la liste des erreurs.

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult confirmant aucune erreur.

    Raises:
        AssertionError: Si check_clean retourne des erreurs.
    """
    clean_path = data_dir / "clean" / "reviews.parquet"
    df = pd.read_parquet(clean_path)
    errors = quality.check_clean(df)
    if errors:
        raise AssertionError(f"Erreurs qualité : {errors}")
    return ("F2", "PASS", "aucune erreur")


@_handle
def F3(data_dir: Path) -> ControlResult:
    """Vérifie l'absence de colonnes interdites dans clean et scored.

    Pourquoi : garantir la confidentialité (ADR 0004 - pseudonymisation).
    Les colonnes interdites sont définies dans config.FORBIDDEN_CLEAN_COLUMNS.

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult confirmant aucune colonne interdite.

    Raises:
        AssertionError: Si des colonnes interdites sont détectées.
    """
    forbidden = set(config.FORBIDDEN_CLEAN_COLUMNS)
    for sub in ["clean", "scored"]:
        path = data_dir / sub / ("reviews.parquet" if sub == "clean" else "reviews_scored.parquet")
        df = pd.read_parquet(path)
        present = forbidden.intersection(df.columns)
        if present:
            raise AssertionError(f"{sub}: colonnes interdites {sorted(present)}")
    return ("F3", "PASS", "aucune colonne interdite détectée")


@_handle
def F4(data_dir: Path, ratio_min: float, ratio_max: float) -> ControlResult:
    """Vérifie la cohérence métier sur les lignes natural (ratio prédit/réel).

    Pourquoi : détecter une dérive du modèle ou un biais de collecte.
    Le ratio doit être entre ratio_min et ratio_max (défaut 0,5 à 2,0).
    Seuls les groupes avec >= 20 avis négatifs réels sont contrôlés.

    Args:
        data_dir: Répertoire racine des données.
        ratio_min: Ratio minimal acceptable.
        ratio_max: Ratio maximal acceptable.

    Returns:
        ControlResult avec les ratios par groupe (app_id/language).

    Raises:
        RuntimeError: Si aucune ligne natural n'est présente.
        AssertionError: Si un ratio est hors bornes.
    """
    scored_path = data_dir / "scored" / "reviews_scored.parquet"
    df = pd.read_parquet(scored_path)
    natural = df[df["sample_source"] == config.SAMPLE_NATURAL]
    if natural.empty:
        raise RuntimeError("Aucune ligne natural")
    groups = natural.groupby(["app_id", "language"])
    details = []
    for (app_id, lang), grp in groups:
        real_neg_count = (grp["label"] == LABEL_NEGATIVE).sum()
        if real_neg_count < 20:
            continue
        real_neg = real_neg_count / grp.shape[0]
        pred_neg = (grp["pred_label"] == LABEL_NEGATIVE).mean()
        ratio = pred_neg / real_neg if real_neg else float("inf")
        if not (ratio_min <= ratio <= ratio_max):
            raise AssertionError(
                f"app_id={app_id}, lang={lang}, ratio={ratio:.3f} hors [{ratio_min},{ratio_max}]"
            )
        details.append(f"{app_id}/{lang}={ratio:.3f}")
    return ("F4", "PASS", ", ".join(details))


@_handle
def F5(data_dir: Path) -> ControlResult:
    """Vérifie que daily_summary agrège uniquement les avis naturels.

    Pourquoi : le flux negative_boost est une collecte ponctuelle, pas en production.
    Le total n_reviews du résumé doit égaler le nombre de lignes natural.

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult avec le total n_reviews.

    Raises:
        AssertionError: Si les totaux ne correspondent pas.
    """
    scored_path = data_dir / "scored" / "reviews_scored.parquet"
    summary_path = data_dir / "scored" / "daily_summary.parquet"
    scored = pd.read_parquet(scored_path)
    natural_cnt = scored[scored["sample_source"] == config.SAMPLE_NATURAL].shape[0]
    summary = pd.read_parquet(summary_path)
    total_reviews = summary["n_reviews"].sum()
    if total_reviews != natural_cnt:
        raise AssertionError(
            f"n_reviews total {total_reviews} ≠ lignes natural {natural_cnt}"
        )
    return ("F5", "PASS", f"n_reviews={total_reviews}")


@_handle
def F6(data_dir: Path, champion_version: str) -> ControlResult:
    """Vérifie que toutes les lignes scorées portent la version du champion.

    Pourquoi : garantir la traçabilité des prédictions (ADR 0010).
    Toute ligne avec une version différente indique un problème de scoring.

    Args:
        data_dir: Répertoire racine des données.
        champion_version: Version du modèle champion attendue.

    Returns:
        ControlResult confirmant que toutes les lignes ont la bonne version.

    Raises:
        AssertionError: Si des lignes ont une version différente.
    """
    scored_path = data_dir / "scored" / "reviews_scored.parquet"
    df = pd.read_parquet(scored_path)
    mismatches = df[df["model_version"] != champion_version]
    if not mismatches.empty:
        raise AssertionError(f"{len(mismatches)} lignes avec version différente")
    return ("F6", "PASS", f"toutes version={champion_version}")


# --------------------------------------------------------------------------- #
# Génération du rapport
# --------------------------------------------------------------------------- #
@_handle
def F9(data_dir: Path) -> ControlResult:
    """Vérifie que la base DuckDB gold existe et que mart_sentiment_daily a des lignes.

    Pourquoi : s'assurer que la couche gold est construite et peuplée.
    La table main.mart_sentiment_daily est le point d'entrée pour les analystes.

    Args:
        data_dir: Répertoire racine des données (non utilisé ici, config.GOLD_DB).

    Returns:
        ControlResult avec le nombre de lignes dans la table.

    Raises:
        FileNotFoundError: Si le fichier DuckDB est absent.
        AssertionError: Si la table est vide.
    """
    if not config.GOLD_DB.is_file():
        raise FileNotFoundError(f"{config.GOLD_DB} absent")
    con = duckdb.connect(str(config.GOLD_DB), read_only=True)
    try:
        result = con.execute(
            "SELECT COUNT(*) FROM main.mart_sentiment_daily"
        ).fetchone()
        count = result[0] if result else 0
        if count < 1:
            raise AssertionError(
                "Table main.mart_sentiment_daily vide (0 lignes)"
            )
    finally:
        con.close()
    return ("F9", "PASS", f"{count} lignes")


@_handle
def F10(data_dir: Path) -> ControlResult:
    """Vérifie la cohérence entre le parquet scored et la table fct_review_predictions.

    Pourquoi : garantir que l'ETL vers DuckDB préserve toutes les lignes.
    Compare le total et le nombre de lignes naturelles entre les deux sources.

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult avec les comptes totaux et naturels.

    Raises:
        FileNotFoundError: Si le fichier DuckDB est absent.
        AssertionError: Si les comptes diffèrent entre parquet et DuckDB.
    """
    # Chemins
    scored_path = data_dir / "scored" / "reviews_scored.parquet"

    # Chargement du parquet scored
    df_parquet = pd.read_parquet(scored_path)
    parquet_total = len(df_parquet)
    parquet_natural = df_parquet[df_parquet["sample_source"] == config.SAMPLE_NATURAL].shape[0]

    # Comptage dans la table DuckDB
    if not config.GOLD_DB.is_file():
        raise FileNotFoundError(f"{config.GOLD_DB} absent")
    con = duckdb.connect(str(config.GOLD_DB), read_only=True)
    try:
        result_total = con.execute(
            "SELECT COUNT(*) FROM main.fct_review_predictions"
        ).fetchone()
        duck_total = result_total[0] if result_total else 0

        result_natural = con.execute(
            f"SELECT COUNT(*) FROM main.fct_review_predictions WHERE sample_source = '{config.SAMPLE_NATURAL}'"
        ).fetchone()
        duck_natural = result_natural[0] if result_natural else 0
    finally:
        con.close()

    # Vérifications
    if duck_total != parquet_total or duck_natural != parquet_natural:
        raise AssertionError(
            f"Différence de lignes : total duckdb={duck_total} parquet={parquet_total} ; "
            f"naturelles duckdb={duck_natural} parquet={parquet_natural}"
        )

    return ("F10", "PASS", f"{duck_total} lignes au total, dont {duck_natural} naturelles")


def _git_commit_short() -> str:
    """Retourne le hash court du commit Git, ou la variable d'env REVIEWPULSE_COMMIT,
    ou 'inconnu' en cas d'échec.

    Pourquoi : tracer la version exacte du code testé dans le rapport.
    La variable d'environnement permet de forcer un commit en CI/CD.

    Returns:
        Hash court du commit, ou 'inconnu'.
    """
    env_commit = os.getenv("REVIEWPULSE_COMMIT")
    if env_commit:
        return env_commit
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "inconnu"
    except Exception:
        return "inconnu"


@_handle
def F7(data_dir: Path) -> ControlResult:
    """Vérifie que la table Iceberg silver.reviews est lisible et a le même nombre de lignes que le parquet clean.

    Pourquoi : garantir la cohérence entre la zone clean (pandas) et silver (Iceberg).
    Utilise lakehouse.read_table pour lire la table Iceberg sans Spark.

    Args:
        data_dir: Répertoire racine des données.

    Returns:
        ControlResult confirmant l'égalité des comptes de lignes.

    Raises:
        AssertionError: Si les nombres de lignes diffèrent.
    """
    # Lecture du parquet « zone propre »
    clean_path = data_dir / "clean" / "reviews.parquet"
    df_clean = pd.read_parquet(clean_path)
    clean_rows = len(df_clean)

    # Lecture de la table Iceberg
    iceberg_table = read_table(config.SILVER_REVIEWS_TABLE)
    iceberg_rows = iceberg_table.num_rows

    if iceberg_rows != clean_rows:
        raise AssertionError(
            f"Nombre de lignes Iceberg ({iceberg_rows}) ≠ parquet clean ({clean_rows})"
        )
    return ("F7", "PASS", f"{iceberg_rows} lignes = {clean_rows} lignes")


@_handle
def F8(data_dir: Path) -> ControlResult:
    """Vérifie que l'historique de la table Iceberg silver.reviews contient au moins un instantané.

    Pourquoi : garantir que la table Iceberg a été écrite avec snapshot (ADR 0014).
    Un historique vide indiquerait une écriture directe sans gestion de version.

    Args:
        data_dir: Répertoire racine des données (non utilisé ici).

    Returns:
        ControlResult avec le nombre d'instantanés et l'id du dernier.

    Raises:
        AssertionError: Si l'historique est vide.
    """
    history = table_history(config.SILVER_REVIEWS_TABLE)
    if not history:
        raise AssertionError("Aucun instantané trouvé dans l'historique de la table Iceberg")
    latest = history[-1]
    return (
        "F8",
        "PASS",
        f"{len(history)} instantané(s), dernier id={latest['snapshot_id']}",
    )


def _write_report(
    report_path: Path,
    results: List[ControlResult],
    urls: dict,
) -> None:
    """Écrit le rapport Markdown.

    Pourquoi : produire un artefact lisible et versionnable pour la revue.
    Le format Markdown permet une lecture directe sur GitHub.

    Args:
        report_path: Chemin du fichier rapport à écrire.
        results: Liste des ControlResult de tous les contrôles.
        urls: Dictionnaire des URLs testées (API, Dashboard, MLflow, Data directory).
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    commit = _git_commit_short()
    total_pass = sum(1 for _, status, _ in results if status == "PASS")
    total_fail = len(results) - total_pass

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Rapport de tests forward\n")
        f.write(f"*Date UTC* : {now}\n")
        f.write(f"*Commit* : {commit}\n\n")
        f.write("## URLs testées\n")
        for key, url in urls.items():
            f.write(f"- **{key}** : `{url}`\n")
        f.write("\n## Résultats des contrôles\n")
        f.write("| Contrôle | Statut | Détail |\n")
        f.write("|----------|--------|--------|\n")
        for name, status, detail in results:
            f.write(f"| {name} | {status} | {detail} |\n")
        f.write("\n")
        f.write(f"**Total PASS** : {total_pass}\n\n")
        f.write(f"**Total FAIL** : {total_fail}\n")


# --------------------------------------------------------------------------- #
# Fonction principale
# --------------------------------------------------------------------------- #
def main() -> int:
    """Parse les arguments, exécute les contrôles et génère le rapport.

    Pourquoi : point d'entrée unique pour l'exécution en CLI ou CI/CD.
    Le code de retour (0/1) permet l'intégration dans les pipelines.

    Returns:
        0 si tous les contrôles passent, 1 sinon.
    """
    parser = argparse.ArgumentParser(
        description="Test en conditions réelles de la stack ReviewPulse"
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8000",
        help="URL de l'API ReviewPulse (défaut http://localhost:8000)",
    )
    parser.add_argument(
        "--dashboard",
        default="http://localhost:8501",
        help="URL du tableau de bord Streamlit (défaut http://localhost:8501)",
    )
    parser.add_argument(
        "--mlflow",
        default="http://localhost:5000",
        help="URL du serveur MLflow (défaut http://localhost:5000)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Répertoire des données (défaut config.DATA_DIR)",
    )
    parser.add_argument(
        "--report",
        default="docs/evidence/forward_test.md",
        help="Chemin du rapport Markdown (défaut docs/evidence/forward_test.md)",
    )
    parser.add_argument(
        "--ratio-min",
        type=float,
        default=0.5,
        help="Ratio minimal pour le contrôle F4 (défaut 0.5)",
    )
    parser.add_argument(
        "--ratio-max",
        type=float,
        default=2.0,
        help="Ratio maximal pour le contrôle F4 (défaut 2.0)",
    )

    args = parser.parse_args()

    # Résolution du répertoire de données
    data_dir = Path(args.data_dir) if args.data_dir else config.DATA_DIR

    # Exécution du premier contrôle A1 pour récupérer la version du modèle
    a1_name, a1_status, a1_detail = A1(args.api)
    model_version = None
    if a1_status == "PASS":
        # le détail contient "model_version=..."
        try:
            model_version = a1_detail.split("model_version=")[1].split(",")[0]
        except Exception:
            logger.warning("Impossible d'extraire model_version depuis A1")
    else:
        logger.error("A1 a échoué : %s", a1_detail)

    # Liste ordonnée des contrôles
    controls: List[ControlResult] = [
        (a1_name, a1_status, a1_detail),
        A2(args.api),
        A3(args.api),
        A4(args.api),
        D1(args.dashboard),
        M1(args.mlflow, model_version or ""),
        F1(data_dir),
        F2(data_dir),
        F3(data_dir),
        F4(data_dir, args.ratio_min, args.ratio_max),
        F5(data_dir),
        F6(data_dir, model_version or ""),
        F7(data_dir),
        F8(data_dir),
        F9(data_dir),
        F10(data_dir),
    ]

    # Génération du rapport
    urls = {
        "API": args.api,
        "Dashboard": args.dashboard,
        "MLflow": args.mlflow,
        "Data directory": str(data_dir),
    }
    report_path = Path(args.report)
    _write_report(report_path, controls, urls)

    # Retour du code de sortie
    overall_pass = all(status == "PASS" for _, status, _ in controls)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

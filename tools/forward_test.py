"""tools.forward_test
===================

Ce script exécute, en conditions réelles, un jeu complet de contrôles de santé
sur la stack ReviewPulse :

* API FastAPI
* Tableau de bord Streamlit
* Serveur MLflow
* Données brutes, nettoyées et scorées

Chaque contrôle est implémenté sous forme de fonction retournant un tuple
``(nom, statut, détail)`` où *statut* vaut ``"PASS"`` ou ``"FAIL"``.
Les exceptions sont capturées et converties en ``FAIL`` avec le message
d’erreur.

Le script accepte plusieurs arguments en ligne de commande afin de pouvoir
cibler des environnements de test différents.  Le rapport Markdown généré
contient :

* titre et date UTC
* identifiant du commit Git (ou ``inconnu``)
* URLs testées
* tableau récapitulatif des contrôles
* nombre total de PASS / FAIL

Le code de sortie est ``0`` si tous les contrôles passent, sinon ``1``.
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

from reviewpulse import config, quality
from reviewpulse.decision import LABEL_NEGATIVE

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
    """Décorateur qui transforme toute exception en résultat FAIL."""
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
    """GET {api}/health → 200, model_version non vide, decision_threshold ∈ (0,1)."""
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
    """POST {api}/predict avec 4 textes → labels attendus négatif, négatif, positif, positif."""
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
    """POST {api}/predict avec [] → 422."""
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
    """GET {api}/insights?app_id=<premier>&days=7 → 200 et liste non vide."""
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
    """GET {dashboard}/_stcore/health → 200."""
    resp = requests.get(f"{dashboard_url.rstrip('/')}/_stcore/health", timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Statut {resp.status_code}")
    return ("D1", "PASS", "OK")


@_handle
def M1(mlflow_url: str, expected_version: str) -> ControlResult:
    """GET alias champion → version égale à model_version d'A1."""
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
    """Idempotence des fichiers raw : chaque flux a autant de lignes que d'ids distincts."""
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
    """Qualité du parquet clean → check_clean renvoie []"""
    clean_path = data_dir / "clean" / "reviews.parquet"
    df = pd.read_parquet(clean_path)
    errors = quality.check_clean(df)
    if errors:
        raise AssertionError(f"Erreurs qualité : {errors}")
    return ("F2", "PASS", "aucune erreur")


@_handle
def F3(data_dir: Path) -> ControlResult:
    """Confidentialité : aucune colonne interdite dans clean et scored."""
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
    """Cohérence métier sur les lignes natural."""
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
    """Résumé daily_summary agrège uniquement les avis naturels."""
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
    """Toutes les lignes scorées portent la version du champion."""
    scored_path = data_dir / "scored" / "reviews_scored.parquet"
    df = pd.read_parquet(scored_path)
    mismatches = df[df["model_version"] != champion_version]
    if not mismatches.empty:
        raise AssertionError(f"{len(mismatches)} lignes avec version différente")
    return ("F6", "PASS", f"toutes version={champion_version}")


# --------------------------------------------------------------------------- #
# Génération du rapport
# --------------------------------------------------------------------------- #
def _git_commit_short() -> str:
    """Retourne le hash court du commit Git, ou la variable d'env REVIEWPULSE_COMMIT,
    ou 'inconnu' en cas d'échec."""
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


def _write_report(
    report_path: Path,
    results: List[ControlResult],
    urls: dict,
) -> None:
    """Écrit le rapport Markdown."""
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
    """Parse les arguments, exécute les contrôles et génère le rapport."""
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

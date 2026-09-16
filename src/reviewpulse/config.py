"""Configuration du projet ReviewPulse.

Ce module centralise toutes les constantes et paramètres d'environnement
utilisés par l'application. Les valeurs sont lues depuis les variables
d'environnement au moment de l'import et peuvent être remplacées dans les
tests via ``monkeypatch`` sur les attributs du module.
"""

import os
from pathlib import Path

# Répertoire de données racine (peut être redéfini via la variable d'environnement)
DATA_DIR = Path(os.getenv("REVIEWPULSE_DATA_DIR", "data"))

# Sous‑répertoires
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
SCORED_DIR = DATA_DIR / "scored"
STATE_DIR = DATA_DIR / "state"

# Répertoire des artefacts MLflow (défini pour éviter ./mlruns)
ARTIFACT_DIR = DATA_DIR / "mlartifacts"

# Fichiers dérivés
CLEAN_FILE = CLEAN_DIR / "reviews.parquet"
SCORED_FILE = SCORED_DIR / "reviews_scored.parquet"
SUMMARY_FILE = SCORED_DIR / "daily_summary.parquet"

# Identifiants d'applications Steam
APP_IDS = [
    int(x)
    for x in os.getenv("REVIEWPULSE_APP_IDS", "1903340,1086940,2622380").split(",")
    if x
]

# Langues supportées
LANGUAGES = ["english", "french"]

# URL de l'API Steam
STEAM_URL = "https://store.steampowered.com/appreviews/{app_id}"

# Pagination et limites HTTP
PAGE_SIZE = 100
MAX_PAGES = int(os.getenv("REVIEWPULSE_MAX_PAGES", "20"))
HTTP_TIMEOUT_S = 20
HTTP_MAX_RETRIES = 4

# Configuration MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///data/mlflow.db")
MLFLOW_EXPERIMENT = "reviewpulse"

# Modèle et alias
MODEL_NAME = "reviewpulse-sentiment"
ALIAS_CHAMPION = "champion"
ALIAS_CHALLENGER = "challenger"

# Paramètres de la version v2 (flux complémentaire d'avis négatifs)
SAMPLE_NATURAL = "natural"
SAMPLE_NEGATIVE_BOOST = "negative_boost"
SAMPLE_SOURCES = [SAMPLE_NATURAL, SAMPLE_NEGATIVE_BOOST]
BOOST_MAX_PAGES = int(os.getenv("REVIEWPULSE_BOOST_MAX_PAGES", "5"))
THRESHOLD_GRID = [round(0.30 + 0.025 * i, 3) for i in range(21)]  # 0.30 à 0.80
DEFAULT_DECISION_THRESHOLD = 0.5

# Autres paramètres
RAW_RETENTION_DAYS = 30
F1_MACRO_MIN = 0.75  # seuil mesuré le 16/09/2026, voir docs/01_charte.md
RANDOM_STATE = 42
FORBIDDEN_CLEAN_COLUMNS = ["steamid", "personaname", "profile_url", "avatar"]

# Colonnes attendues après nettoyage et leurs types pandas
CLEAN_COLUMNS = {
    "review_id": "string",
    "app_id": "int64",
    "language": "string",
    "review_text": "string",
    "label": "int64",
    "created_at": "datetime64[ns, UTC]",
    "updated_at": "datetime64[ns, UTC]",
    "votes_up": "int64",
    "weighted_vote_score": "float64",
    "playtime_at_review_min": "int64",
    "author_pseudo": "string",
    "text_len": "int64",
    "sample_source": "string",
}

def salt() -> bytes:
    """Renvoie le sel utilisé pour le hachage des identifiants d'auteur.

    Le sel est lu depuis la variable d'environnement ``REVIEWPULSE_SALT``.
    Une ``RuntimeError`` est levée si la variable est absente ou vide.

    Returns
    -------
    bytes
        Le sel encodé en UTF‑8.
    """
    value = os.getenv("REVIEWPULSE_SALT")
    if not value:
        raise RuntimeError("Variable d'environnement REVIEWPULSE_SALT manquante ou vide")
    return value.encode("utf-8")

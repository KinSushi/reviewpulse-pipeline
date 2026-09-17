"""reviewpulse.config
====================

Rôle
----
Source unique des paramètres du projet (chemins, identifiants d’applications, langues, seuils, schéma de la zone propre, sel).

Place dans la chaîne
--------------------
Importé par tous les modules ; les valeurs sont lues au moment de l’appel (`config.X`). Aucun module ne doit copier les constantes ; les tests peuvent rediriger les chemins via la fixture ``data_env`` (voir la carte des modules).

Fonctionnement
--------------
- Lecture des variables d’environnement au moment de l’import.
- Construction des chemins avec :class:`pathlib.Path`.
- Définition de listes d’identifiants d’applications, de langues et de sources d’échantillonnage.
- Définition de paramètres numériques (pages, timeout, seuils, etc.).
- Exposition de la fonction ``salt()`` qui lit ``REVIEWPULSE_SALT`` et lève ``RuntimeError`` si la variable est absente ou vide.

Choix de conception
--------------------
- Toutes les valeurs configurables proviennent d’une variable d’environnement (compatible avec exécution locale, Airflow et GitHub Actions) – conformément à la description du module dans la carte des modules.  
- ``salt()`` n’a aucune valeur par défaut (ADR 0004).  
- ``F1_MACRO_MIN = 0.75`` (ADR 0008).  
- ``THRESHOLD_GRID`` s’étend de 0.30 à 0.80 par pas de 0.025 (ADR 0007).

Preuves
-------
Aucune preuve supplémentaire n’est documentée dans la carte des modules pour ce module.

Tests associés
--------------
Tous les tests utilisent la fixture ``data_env`` pour rediriger les constantes de chemin et définir ``REVIEWPULSE_SALT``.
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

# Répertoire des artefacts MLflow
ARTIFACT_DIR = DATA_DIR / "mlartifacts"
# Répertoire des rapports Great Expectations (voir expectations.py)
GX_DIR = DATA_DIR / "quality_reports" / "gx"

# --- Lakehouse — constantes spécifiques au stockage Iceberg et Spark ---
# Répertoire racine du lakehouse (Iceberg) ; créé à la volée par get_catalog()
LAKEHOUSE_DIR = DATA_DIR / "lakehouse"
# Namespace Iceberg dédié aux tables « silver » (données nettoyées et prédictions)
SILVER_NAMESPACE = "silver"
# Identifiant complet de la table Iceberg contenant les avis nettoyés
SILVER_REVIEWS_TABLE = "silver.reviews"
# Identifiant complet de la table Iceberg contenant les prédictions de sentiment
SILVER_PREDICTIONS_TABLE = "silver.predictions"
# Adresse du master Spark, configurable via l’environnement
SPARK_MASTER = os.getenv("REVIEWPULSE_SPARK_MASTER", "local[2]")
# Mémoire allouée au driver Spark, configurable via l’environnement
SPARK_DRIVER_MEMORY = os.getenv("REVIEWPULSE_SPARK_DRIVER_MEMORY", "2g")

# --- Gold — entrepôt DuckDB construit par dbt ---
GOLD_DIR = DATA_DIR / "gold"
GOLD_DB = GOLD_DIR / "reviewpulse.duckdb"
DBT_TARGET_DIR = GOLD_DIR / "dbt_target"  # artefacts dbt : manifest, catalogue, documentation
DBT_LOG_DIR = GOLD_DIR / "dbt_logs"
DBT_PROJECT_DIR = Path(
    os.getenv(
        "REVIEWPULSE_DBT_DIR",
        str(Path(__file__).resolve().parents[2] / "dbt")
    )
)  # la valeur par défaut vaut pour un dépôt cloné (installation éditable), les images Docker fixent la variable
DUCKDB_EXT_DIR = Path(
    os.getenv(
        "REVIEWPULSE_DUCKDB_EXT_DIR",
        str(DATA_DIR / "duckdb_extensions")
    )
)  # les images préinstallent l'extension iceberg dans ce répertoire pour fonctionner sans réseau

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
F1_MACRO_MIN = 0.75  # ADR 0008
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
    """Renvoie le sel utilisé pour le hachage des identifiants d’auteur.

    Le sel est lu depuis la variable d’environnement ``REVIEWPULSE_SALT``.
    Une ``RuntimeError`` est levée si la variable est absente ou vide.

    Returns
    -------
    bytes
        Le sel encodé en UTF‑8.

    Raises
    ------
    RuntimeError
        Si la variable d’environnement ``REVIEWPULSE_SALT`` n’est pas définie
        ou est vide.

    Pourquoi
    -------
    Le sel rend le pseudonyme non réversible par dictionnaire ; la donnée reste une donnée personnelle pseudonymisée (ADR 0004).
    """
    value = os.getenv("REVIEWPULSE_SALT")
    if not value:
        raise RuntimeError("Variable d'environnement REVIEWPULSE_SALT manquante ou vide")
    return value.encode("utf-8")

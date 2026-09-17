import hashlib
import random

import pytest
import pandas as pd
import numpy as np

from reviewpulse import config


@pytest.fixture
def data_env(tmp_path, monkeypatch):
    """
    Où : crée une arborescence de données temporaire sous ``tmp_path / "data"``.
    Quoi : ré‑initialise toutes les constantes de chemin du module
    ``reviewpulse.config`` pour qu’elles pointent vers ce répertoire temporaire,
    y compris les répertoires spécifiques à la couche *gold* et à Iceberg.
    Comment : crée les dossiers nécessaires, applique les patches via
    ``monkeypatch.setattr(..., raising=False)`` et définit la variable
    d’environnement ``REVIEWPULSE_SALT``.
    Pourquoi : les tests qui utilisent la couche Iceberg écrivent par défaut
    dans le lac réel ``./data/lakehouse`` lorsqu’``pytest`` est lancé depuis la
    racine du dépôt ; la redirection garantit l’isolation des tests et évite
    toute pollution de données réelles (constat du 17/09/2026).
    """
    # Arborescence principale
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    clean_dir = data_dir / "clean"
    scored_dir = data_dir / "scored"
    state_dir = data_dir / "state"

    # Répertoires additionnels liés à la couche gold / Iceberg
    lakehouse_dir = data_dir / "lakehouse"
    gx_dir = data_dir / "quality_reports" / "gx"
    gold_dir = data_dir / "gold"
    dbt_target_dir = gold_dir / "dbt_target"
    dbt_log_dir = gold_dir / "dbt_logs"

    # Création de tous les dossiers
    for p in (
        raw_dir,
        clean_dir,
        scored_dir,
        state_dir,
        lakehouse_dir,
        gx_dir,
        gold_dir,
        dbt_target_dir,
        dbt_log_dir,
    ):
        p.mkdir(parents=True, exist_ok=True)

    # Patch des chemins dans la configuration
    monkeypatch.setattr(config, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(config, "RAW_DIR", raw_dir, raising=False)
    monkeypatch.setattr(config, "CLEAN_DIR", clean_dir, raising=False)
    monkeypatch.setattr(config, "SCORED_DIR", scored_dir, raising=False)
    monkeypatch.setattr(config, "STATE_DIR", state_dir, raising=False)

    monkeypatch.setattr(config, "CLEAN_FILE", clean_dir / "reviews.parquet", raising=False)
    monkeypatch.setattr(config, "SCORED_FILE", scored_dir / "reviews_scored.parquet", raising=False)
    monkeypatch.setattr(config, "SUMMARY_FILE", scored_dir / "daily_summary.parquet", raising=False)

    # Répertoires spécifiques à la couche gold / Iceberg
    monkeypatch.setattr(config, "LAKEHOUSE_DIR", lakehouse_dir, raising=False)
    monkeypatch.setattr(config, "GX_DIR", gx_dir, raising=False)
    monkeypatch.setattr(config, "GOLD_DIR", gold_dir, raising=False)
    monkeypatch.setattr(config, "GOLD_DB", gold_dir / "reviewpulse.duckdb", raising=False)
    monkeypatch.setattr(config, "DBT_TARGET_DIR", dbt_target_dir, raising=False)
    monkeypatch.setattr(config, "DBT_LOG_DIR", dbt_log_dir, raising=False)

    # Ajout du répertoire d'artefacts ML (sans création du dossier)
    monkeypatch.setattr(config, "ARTIFACT_DIR", data_dir / "mlartifacts", raising=False)

    # MLflow tracking URI pointant vers un fichier SQLite temporaire
    mlflow_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", mlflow_uri, raising=False)

    # Variable d'environnement pour le sel
    monkeypatch.setenv("REVIEWPULSE_SALT", "test-salt")

    return data_dir


@pytest.fixture
def review_factory():
    """
    Retourne une fonction permettant de créer un dictionnaire représentant
    une revue telle qu'elle est renvoyée par l'API Steam.
    """

    def make_review(
        rid,
        voted_up=True,
        text="great game",
        steamid="7656119800000000",
        created=1_780_000_000,
        updated=None,
        playtime=120,
    ):
        if updated is None:
            updated = created
        return {
            "recommendationid": str(rid),
            "author": {
                "steamid": steamid,
                "personaname": f"User{rid}",
                "profile_url": f"https://steamcommunity.com/profiles/{steamid}",
                "avatar": "https://steamcdn-a.akamaihd.net/steamcommunity.com/public/images/avatars/aa/aa.jpg",
                "playtime_at_review": playtime,
            },
            "language": "english",
            "review": text,
            "timestamp_created": created,
            "timestamp_updated": updated,
            "voted_up": bool(voted_up),
            "votes_up": 0,
            "weighted_vote_score": "0.5",
        }

    # Vérification que la fonction correspond bien au contrat
    sample = make_review(1)
    required_keys = {
        "recommendationid",
        "author",
        "language",
        "review",
        "timestamp_created",
        "timestamp_updated",
        "voted_up",
        "votes_up",
        "weighted_vote_score",
    }
    assert callable(make_review), "review_factory doit renvoyer une fonction callable"
    assert isinstance(sample, dict), "make_review doit retourner un dict"
    assert required_keys.issubset(sample.keys()), "make_review manque des clés attendues"
    assert isinstance(sample["author"], dict) and "steamid" in sample["author"], "author doit contenir steamid"

    return make_review


class FakeResponse:
    """
    Réponse factice mimant l'interface de ``requests.Response`` utilisée dans les tests.
    """

    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """
    Session factice qui renvoie séquentiellement les réponses fournies dans ``pages``.
    Chaque appel à ``get`` enregistre les paramètres dans ``self.calls``.
    """

    def __init__(self, pages):
        self._pages = list(pages)  # copie pour itération
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if not self._pages:
            # aucune page restante → renvoie une réponse vide 200
            return FakeResponse(200, {})
        payload = self._pages.pop(0)
        return FakeResponse(200, payload)


@pytest.fixture
def fake_session_cls():
    """
    Fournit la classe ``FakeSession`` afin que les tests puissent l'instancier
    avec la liste de pages souhaitée.
    """
    return FakeSession


@pytest.fixture
def labelled_frame():
    """
    Retourne un ``pandas.DataFrame`` conforme à ``config.CLEAN_COLUMNS``.
    La moitié des lignes sont positives, l'autre moitié négatives,
    avec un texte généré à partir de listes de mots.
    """
    random.seed(0)
    np.random.seed(0)

    pos_words = [
        "great", "fun", "amazing", "love", "excellent",
        "awesome", "fantastic", "brilliant", "wonderful", "perfect"
    ]
    neg_words = [
        "crash", "bug", "refund", "boring", "broken",
        "terrible", "awful", "hate", "poor", "disappointing"
    ]

    rows = []
    n = 200
    half = n // 2
    for i in range(n):
        label = 1 if i < half else 0
        words = pos_words if label == 1 else neg_words
        text_len_words = random.randint(5, 15)
        text = " ".join(random.choices(words, k=text_len_words))
        author_pseudo = hashlib.sha256(f"{i}{random.getrandbits(256)}".encode()).hexdigest()
        row = {
            "review_id": f"rev{i}",
            "app_id": random.randint(1000000, 9999999),
            "language": random.choice(config.LANGUAGES),
            "review_text": text,
            "label": label,
            "created_at": pd.Timestamp("2023-01-01T00:00:00Z") + pd.Timedelta(seconds=i * 60),
            "updated_at": pd.Timestamp("2023-01-01T01:00:00Z") + pd.Timedelta(seconds=i * 60),
            "votes_up": random.randint(0, 100),
            "weighted_vote_score": round(random.uniform(0.0, 1.0), 3),
            "playtime_at_review_min": random.randint(0, 5000),
            "author_pseudo": author_pseudo,
            "text_len": len(text),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Ajout de la colonne sample_source conformément à l'évolution v2
    df["sample_source"] = "natural"

    # Cast aux types attendus
    for col, dtype in config.CLEAN_COLUMNS.items():
        if dtype == "string":
            df[col] = df[col].astype("string")
        elif dtype.startswith("datetime"):
            df[col] = pd.to_datetime(df[col], utc=True)
        else:
            df[col] = df[col].astype(dtype)

    return df

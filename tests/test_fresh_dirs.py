# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
from pathlib import Path

import pytest

from reviewpulse import config, ingest, transform, train


@pytest.fixture
def empty_env(tmp_path, monkeypatch):
    """
    Configure les chemins de configuration vers un répertoire « fresh » sous ``tmp_path``,
    sans créer les dossiers. Initialise également le sel et l'URI MLflow.
    """
    fresh_root = tmp_path / "fresh"
    # Chemins sous fresh (pas de création)
    monkeypatch.setattr(config, "DATA_DIR", fresh_root, raising=False)
    monkeypatch.setattr(config, "RAW_DIR", fresh_root / "raw", raising=False)
    monkeypatch.setattr(config, "CLEAN_DIR", fresh_root / "clean", raising=False)
    monkeypatch.setattr(config, "SCORED_DIR", fresh_root / "scored", raising=False)
    monkeypatch.setattr(config, "STATE_DIR", fresh_root / "state", raising=False)

    monkeypatch.setattr(config, "CLEAN_FILE", fresh_root / "clean" / "reviews.parquet", raising=False)
    monkeypatch.setattr(config, "SCORED_FILE", fresh_root / "scored" / "reviews_scored.parquet", raising=False)
    monkeypatch.setattr(config, "SUMMARY_FILE", fresh_root / "scored" / "daily_summary.parquet", raising=False)

    # Ajout de ARTIFACT_DIR
    monkeypatch.setattr(config, "ARTIFACT_DIR", fresh_root / "mlartifacts", raising=False)

    # MLflow URI pointant vers un fichier SQLite dans un répertoire inexistant
    mlflow_uri = f"sqlite:///{(fresh_root / 'ml' / 'mlflow.db').as_posix()}"
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", mlflow_uri, raising=False)

    # Sel d'environnement
    monkeypatch.setenv("REVIEWPULSE_SALT", "test-salt")
    return fresh_root


def test_ingest_app_fresh_dirs(empty_env, fake_session_cls, review_factory):
    """
    Vérifie qu'``ingest_app`` crée correctement le lot et le manifeste même si les
    répertoires n'existent pas au départ.
    """
    # Préparer deux avis factices
    rev1 = review_factory(1)
    rev2 = review_factory(2)
    pages = [
        {
            "success": 1,
            "cursor": "c1",
            "reviews": [rev1, rev2],
        },
        {
            "success": 1,
            "cursor": "c2",
            "reviews": [],
        },
    ]

    # Première ingestion : deux nouveaux avis
    session = fake_session_cls(pages.copy())
    new_count = ingest.ingest_app(
        app_id=1903340,
        language="english",
        session=session,
        raw_dir=config.RAW_DIR,
        state_dir=config.STATE_DIR,
    )
    assert new_count == 2

    # Le manifeste doit exister et contenir les deux IDs
    manifest_path = config.STATE_DIR / "seen_1903340_english.txt"
    assert manifest_path.is_file()
    manifest_ids = manifest_path.read_text(encoding="utf-8").splitlines()
    assert set(manifest_ids) == {rev1["recommendationid"], rev2["recommendationid"]}

    # Un seul fichier batch doit avoir été créé
    batch_files = list(Path(config.RAW_DIR).rglob("*.jsonl"))
    assert len(batch_files) == 1

    # Deuxième ingestion avec les mêmes pages : aucun nouvel avis
    session2 = fake_session_cls(pages.copy())
    new_count2 = ingest.ingest_app(
        app_id=1903340,
        language="english",
        session=session2,
        raw_dir=config.RAW_DIR,
        state_dir=config.STATE_DIR,
    )
    assert new_count2 == 0
    # Aucun nouveau fichier batch ne doit être ajouté
    batch_files_after = list(Path(config.RAW_DIR).rglob("*.jsonl"))
    assert len(batch_files_after) == 1


def test_write_clean_creates_missing_dir(empty_env, labelled_frame):
    """
    ``write_clean`` doit créer le répertoire cible lorsqu'il n'existe pas.
    """
    # Le répertoire clean n'existe pas encore
    assert not config.CLEAN_DIR.exists()
    # L'écriture doit réussir et créer le fichier parquet
    out_path = transform.write_clean(labelled_frame)
    assert out_path == config.CLEAN_FILE
    assert out_path.is_file()


def test_purge_raw_returns_zero_when_missing_dir(empty_env):
    """
    ``purge_raw`` doit retourner 0 lorsqu'aucune partition brute n'existe.
    """
    # Le répertoire raw n'existe pas
    assert not config.RAW_DIR.exists()
    removed = transform.purge_raw()
    assert removed == 0


def test_train_and_log_creates_mlflow_db_dir(empty_env, labelled_frame):
    """
    ``train_and_log`` doit créer le répertoire de la base SQLite MLflow
    même s'il n'existe pas au préalable.
    """
    # Le répertoire contenant le fichier SQLite n'existe pas
    mlflow_db_path = Path(config.MLFLOW_TRACKING_URI.replace("sqlite:///", "", 1))
    assert not mlflow_db_path.parent.exists()

    # L'entraînement doit réussir sans lever d'exception
    result = train.train_and_log(labelled_frame, tracking_uri=config.MLFLOW_TRACKING_URI)
    # Le dictionnaire de résultat doit contenir les métriques attendues
    assert isinstance(result, dict)
    assert "f1_macro" in result
    # Le répertoire doit maintenant exister
    assert mlflow_db_path.parent.is_dir()
    # Le fichier SQLite doit avoir été créé
    assert mlflow_db_path.is_file()

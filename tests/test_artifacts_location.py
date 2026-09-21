# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
import pathlib
from pathlib import Path

from fastapi.testclient import TestClient

from reviewpulse import api, config, score, train


def test_artifacts_location_and_model_prediction(
    data_env: pathlib.Path,
    labelled_frame,
    monkeypatch,
    tmp_path: pathlib.Path,
):
    # Répertoire de travail pour l'entraînement
    cwd_train = tmp_path / "cwd_train"
    cwd_train.mkdir()
    monkeypatch.chdir(cwd_train)

    # Entraînement et enregistrement du modèle
    train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
    )

    # Répertoire de travail pour le service (différent)
    cwd_serve = tmp_path / "cwd_serve"
    cwd_serve.mkdir()
    monkeypatch.chdir(cwd_serve)

    # Chargement du modèle champion
    model, _ = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)

    # Vérification de la forme de la prédiction
    proba = model.predict_proba(["great fun", "crash bug"])
    assert hasattr(proba, "shape")
    assert proba.shape == (2, 2)

    # Vérification de la présence d'au moins un artefact
    artifact_dir = pathlib.Path(config.ARTIFACT_DIR)
    assert artifact_dir.is_dir()
    files = list(artifact_dir.iterdir())
    assert files, "Le répertoire d'artefacts doit contenir au moins un fichier"


def test_health_endpoint_without_model(
    data_env: pathlib.Path,
    monkeypatch,
    tmp_path: pathlib.Path,
):
    # S'assurer que le cache du modèle est vidé avant le test
    api._load_model.cache_clear()

    client = TestClient(api.app)

    response = client.get("/health")
    assert response.status_code == 503

    # S'assurer que le cache du modèle est vidé après le test
    api._load_model.cache_clear()


def test_training_writes_nothing_in_cwd(
    data_env: pathlib.Path,
    labelled_frame,
    tmp_path: pathlib.Path,
    monkeypatch,
):
    # Crée un répertoire de travail vide
    cwd_vide = tmp_path / "cwd_vide"
    cwd_vide.mkdir()
    monkeypatch.chdir(cwd_vide)

    # Lance l'entraînement
    train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
    )

    # Vérifie qu'aucun fichier n'a été créé dans le répertoire courant
    # MLflow crée lui-même un dossier ./mlruns VIDE à l'ouverture d'une base SQLite (comportement de la bibliothèque, vérifié le 16/09/2026) ; le test garantit qu'aucun FICHIER n'est écrit dans le dossier courant.
    files = [p for p in Path('.').rglob('*') if p.is_file()]
    assert files == []

# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_dashboard.py

Tests d’intégration du tableau de bord Streamlit.

- Utilise les fixtures partagées ``data_env`` et ``labelled_frame`` définies dans
  ``tests/conftest.py``.
- Prépare les artefacts attendus par le tableau de bord :
  * Entraîne le modèle sur le ``labelled_frame`` puis le consigne dans le suivi
    MLflow (URI fourni par la fixture ``data_env``).
  * Charge le modèle champion, le score sur le même ``labelled_frame`` et écrit
    les fichiers ``config.SCORED_FILE`` et ``config.SUMMARY_FILE`` (création des
    dossiers parents si nécessaire).
- Vérifie trois comportements :
  1. L’exécution du tableau de bord ne lève aucune exception.
  2. La métrique « Part négative réelle » vaut exactement 50 % (le jeu de
     données est équilibré : 100 positifs / 100 négatifs).
  3. En l’absence des fichiers de scores, le tableau de bord affiche au moins
     un message d’information, d’avertissement ou d’erreur, sans lever
     d’exception.

Les commentaires sont en français et expliquent le *pourquoi* de chaque
étape. Aucun import inutilisé.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from reviewpulse import config, score, train


def _prepare_artifacts(labelled_frame):
    """
    Entraîne le modèle, le consigne dans le suivi MLflow, puis génère les
    fichiers de scores et de résumé attendus par le tableau de bord.
    """
    # Crée une copie du DataFrame avec des valeurs fixes pour garantir que le
    # tableau de bord filtre sur le premier jeu et la première langue.
    # Sans cette copie, la fixture attribue des ``app_id`` et ``language`` aléatoires,
    # ce qui conduit à un taux de 0.00 % au lieu de 50.00 % lors du filtrage.
    frame = labelled_frame.copy()
    frame["app_id"] = 1  # type int64, conservé
    frame["language"] = "english"  # type string, conservé

    # Entraînement et enregistrement du modèle champion
    train.train_and_log(frame, tracking_uri=config.MLFLOW_TRACKING_URI)

    # Chargement du modèle champion (alias « champion ») et version associée
    model, version = score.load_champion()

    # Scoring du même DataFrame (conforme à ``config.CLEAN_COLUMNS``)
    scored = score.score(frame, model, version)

    # Écriture atomique du DataFrame scoré
    config.SCORED_FILE.parent.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(config.SCORED_FILE)

    # Agrégation quotidienne puis écriture du résumé
    summary = score.summarize(scored)
    config.SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    summary.to_parquet(config.SUMMARY_FILE)


@pytest.fixture
def app_test():
    """
    Retourne une instance d'``AppTest`` pointant sur le script du tableau de bord.
    Le chemin est résolu dynamiquement afin de fonctionner quel que soit le
    répertoire de lancement des tests.
    """
    script_path = (
        Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
    )
    return AppTest.from_file(str(script_path), default_timeout=60)


def test_dashboard_runs_without_exception(data_env, labelled_frame, app_test):
    """
    Le tableau de bord doit s’exécuter sans lever d’exception lorsque les
    fichiers de scores existent.
    """
    _prepare_artifacts(labelled_frame)

    app_test.run()
    assert not app_test.exception, "Le tableau de bord a levé une exception"


def test_dashboard_metric_negative_share(data_env, labelled_frame, app_test):
    """
    La métrique « Part négative réelle » doit refléter le partage réel des
    labels : 50 % négatif sur un jeu de données équilibré.
    """
    _prepare_artifacts(labelled_frame)

    app_test.run()
    # ``AppTest.metric`` renvoie une liste d'objets avec les attributs ``label`` et ``value``.
    metric = next(
        m for m in app_test.metric if getattr(m, "label", None) == "Part négative réelle"
    )
    # La valeur affichée par Streamlit est une chaîne formatée en pourcentage.
    assert metric.value == "50.00%", "La part négative réelle n’est pas à 50 %"


def test_dashboard_missing_files_shows_message(data_env, labelled_frame, app_test):
    """
    En l’absence des fichiers de scores, le tableau de bord doit afficher au
    moins un message (info, warning ou error) et ne doit pas lever d’exception.
    """
    _prepare_artifacts(labelled_frame)

    # Suppression volontaire des artefacts pour simuler le premier lancement.
    config.SCORED_FILE.unlink(missing_ok=True)
    config.SUMMARY_FILE.unlink(missing_ok=True)

    app_test.run()
    assert not app_test.exception, "Le tableau de bord a levé une exception malgré l'absence de fichiers"

    # ``AppTest`` capture les messages via les attributs ``info``, ``warning`` et ``error``.
    messages = list(app_test.info) + list(app_test.warning) + list(app_test.error)
    assert messages, "Aucun message n’a été affiché alors que les fichiers étaient manquants"

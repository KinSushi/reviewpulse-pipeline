# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
import pytest
import pandas as pd
from reviewpulse import train, score, config


@pytest.fixture
def trained_first(data_env, labelled_frame):
    """Entraîne le modèle une première fois et retourne le dictionnaire de métriques."""
    result = train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
        register=True,
    )
    return result


def test_train_and_log_promotes_on_separable_data(
    data_env, labelled_frame, trained_first
):
    """Le premier entraînement sur un jeu séparable doit être promu."""
    metrics = trained_first
    # clés attendues
    expected_keys = {
        "f1_macro",
        "recall_negative",
        "precision_negative",
        "roc_auc",
        "run_id",
        "model_version",
        "promoted",
        "n_train",
        "n_test",
        "negative_share",
    }
    assert expected_keys.issubset(metrics.keys())
    # performance minimale
    assert metrics["f1_macro"] >= config.F1_MACRO_MIN
    # AUC de la classe négative meilleure que le hasard
    assert 0.5 < metrics["roc_auc"] <= 1.0
    # promotion attendue
    assert metrics["promoted"] is True
    # version du modèle doit être renseignée et être une chaîne
    assert metrics["model_version"] is not None
    assert isinstance(metrics["model_version"], str)


def test_second_training_not_promoted_new_version(
    data_env, labelled_frame, trained_first
):
    """Un second entraînement identique ne doit pas être promu mais créer une nouvelle version."""
    first_version = trained_first["model_version"]
    second_metrics = train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
        register=True,
    )
    # la deuxième exécution ne doit pas être promue
    assert second_metrics["promoted"] is False
    # une nouvelle version doit être créée
    assert second_metrics["model_version"] is not None
    assert second_metrics["model_version"] != first_version
    # le run_id doit être différent
    assert second_metrics["run_id"] != trained_first["run_id"]


def test_load_champion_returns_model_and_version(
    data_env, labelled_frame, trained_first
):
    """load_champion doit renvoyer le modèle champion et sa version."""
    # le premier entraînement a déjà promu le champion
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)
    assert model is not None
    assert isinstance(version, str)
    # la version doit correspondre à celle du premier entraînement promu
    assert version == trained_first["model_version"]


def test_score_adds_columns_and_values(
    data_env, labelled_frame, trained_first
):
    """score doit ajouter les colonnes attendues avec des valeurs cohérentes."""
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)
    scored = score.score(labelled_frame, model, version)

    # colonnes attendues
    for col in ["proba_negative", "pred_label", "model_version", "scored_at"]:
        assert col in scored.columns

    # valeurs dans les bornes attendues
    assert scored["proba_negative"].between(0.0, 1.0).all()
    assert scored["pred_label"].isin([0, 1]).all()
    assert (scored["model_version"] == version).all()
    # scored_at doit être de type datetime avec timezone UTC
    assert pd.api.types.is_datetime64tz_dtype(scored["scored_at"])


def test_summarize_returns_one_row_per_app_language_date(
    data_env, labelled_frame, trained_first
):
    """summarize doit produire une ligne par combinaison (app_id, language, date)."""
    model, version = score.load_champion(tracking_uri=config.MLFLOW_TRACKING_URI)
    scored = score.score(labelled_frame, model, version)
    summary = score.summarize(scored)

    # colonnes attendues
    expected_cols = {
        "app_id",
        "language",
        "date",
        "n_reviews",
        "share_negative_pred",
        "share_negative_true",
        "model_version",
    }
    assert expected_cols.issubset(summary.columns)

    # nombre de lignes = nombre de combinaisons uniques
    unique_combinations = (
        scored.assign(date=scored["created_at"].dt.date)
        .groupby(["app_id", "language", "date"])
        .size()
        .reset_index()
        .shape[0]
    )
    assert len(summary) == unique_combinations
    # chaque ligne doit contenir la même version que le modèle utilisé
    assert (summary["model_version"] == version).all()


def test_ecart_train_test_raisonnable(data_env, labelled_frame):
    """L'écart entre les scores d'entraînement et de test doit rester raisonnable."""
    result = train.train_and_log(
        labelled_frame,
        tracking_uri=config.MLFLOW_TRACKING_URI,
        register=True,
    )
    f1_train = result.get("f1_macro_train")
    f1_test = result.get("f1_macro")
    ecart = result.get("ecart_train_test")
    # vérification de la présence des métriques
    assert f1_train is not None, f"f1_macro_train manquant : {f1_train}"
    assert f1_test is not None, f"f1_macro manquant : {f1_test}"
    assert ecart is not None, f"ecart_train_test manquant : {ecart}"
    # l'écart doit être compris entre -0,05 et 0,35
    assert -0.05 <= ecart < 0.35, f"Écart inattendu (train={f1_train:.3f}, test={f1_test:.3f}) = {ecart:.3f}"

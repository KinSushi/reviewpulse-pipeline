# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_expectations_lake.py
Batterie de tests unitaires pour les attentes Great Expectations
définies dans ``reviewpulse.expectations_lake``.
"""

from __future__ import annotations

import pandas as pd

from reviewpulse import expectations_lake as el
from reviewpulse import config


def _df_mart_base() -> pd.DataFrame:
    """DataFrame de base conforme aux attentes du mart."""
    return pd.DataFrame(
        {
            "app_id": [123, 456],
            "game_name": ["Game A", "Game B"],
            "language": [config.LANGUAGES[0], config.LANGUAGES[0]],
            "review_date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
            "n_reviews": [10, 20],
            "n_pred_negative": [2, 5],
            "n_actual_negative": [1, 4],
            "share_pred_negative": [0.2, 0.25],
            "share_actual_negative": [0.1, 0.2],
            "model_version": ["v1", "v1"],
        }
    )


def test_mart_conforme_passe():
    """Le mart valide doit réussir la validation."""
    df = _df_mart_base()
    result = el.valider(df, el.attentes_gold_mart(), "gold_mart_test")
    assert result["success"], f"Validation attendue comme réussie, échouée : {result}"
    assert not result["echecs"], f"Pas d'échecs attendus, mais trouvé : {result['echecs']}"


def test_mart_part_hors_bornes_echoue():
    """Un share_pred_negative hors de [0,1] doit provoquer un échec."""
    df = _df_mart_base()
    df.loc[0, "share_pred_negative"] = 1.7
    result = el.valider(df, el.attentes_gold_mart(), "gold_mart_test")
    assert not result["success"], "La validation aurait dû échouer à cause d'une valeur hors bornes"
    assert any(
        f["column"] == "share_pred_negative" for f in result["echecs"]
    ), "L'échec doit mentionner la colonne share_pred_negative"


def test_mart_jour_sans_avis_echoue():
    """Un n_reviews égal à 0 doit provoquer un échec."""
    df = _df_mart_base()
    df.loc[1, "n_reviews"] = 0
    result = el.valider(df, el.attentes_gold_mart(), "gold_mart_test")
    assert not result["success"], "La validation aurait dû échouer pour n_reviews=0"
    assert any(
        f["column"] == "n_reviews" for f in result["echecs"]
    ), "L'échec doit mentionner la colonne n_reviews"


def _df_silver_reviews_base() -> pd.DataFrame:
    """DataFrame silver.reviews conforme."""
    return pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "label": [0, 1],
            "language": [config.LANGUAGES[0], config.LANGUAGES[1]],
            "sample_source": [config.SAMPLE_SOURCES[0], config.SAMPLE_SOURCES[1]],
            "text_len": [100, 150],
            "author_pseudo": [
                "a" * 64,  # 64 caractères hexadécimaux (valide)
                "b" * 64,
            ],
        }
    )


def test_silver_reviews_pseudo_invalide_echoue():
    """Un pseudo d'auteur invalide doit déclencher l'échec du regex."""
    df_valide = _df_silver_reviews_base()
    res_ok = el.valider(df_valide, el.attentes_silver_reviews(), "silver_reviews_ok")
    assert res_ok["success"], f"Le DataFrame valide a échoué : {res_ok}"

    df_invalid = df_valide.copy()
    df_invalid.at[0, "author_pseudo"] = "c" * 10  # longueur incorrecte
    res_err = el.valider(df_invalid, el.attentes_silver_reviews(), "silver_reviews_err")
    assert not res_err["success"], "La validation aurait dû échouer à cause d'un pseudo invalide"
    assert any(
        f["column"] == "author_pseudo" for f in res_err["echecs"]
    ), "L'échec doit mentionner la colonne author_pseudo"


def _df_silver_predictions_base() -> pd.DataFrame:
    """DataFrame silver.predictions conforme."""
    return pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "pred_label": [0, 1],
            "proba_negative": [0.3, 0.7],
            "decision_threshold": [0.5, 0.5],
            "model_version": ["v1", "v1"],
        }
    )


def test_silver_predictions_proba_hors_bornes_echoue():
    """Une probabilité négative >1 doit provoquer un échec."""
    df = _df_silver_predictions_base()
    df.loc[0, "proba_negative"] = 1.5
    result = el.valider(df, el.attentes_silver_predictions(), "silver_predictions_test")
    assert not result["success"], "La validation aurait dû échouer pour proba_negative hors bornes"
    assert any(
        f["column"] == "proba_negative" for f in result["echecs"]
    ), "L'échec doit mentionner la colonne proba_negative"


def _df_gold_faits_base() -> pd.DataFrame:
    """DataFrame gold.faits conforme."""
    return pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "pred_label": [0, 1],
            "proba_negative": [0.2, 0.8],
            "sample_source": [config.SAMPLE_SOURCES[0], config.SAMPLE_SOURCES[1]],
            "language": [config.LANGUAGES[0], config.LANGUAGES[1]],
        }
    )


def test_gold_faits_review_id_duplique_echoue():
    """Des review_id dupliqués doivent déclencher l'échec d'unicité."""
    df = _df_gold_faits_base()
    df.loc[1, "review_id"] = df.loc[0, "review_id"]  # duplication
    result = el.valider(df, el.attentes_gold_faits(), "gold_faits_test")
    assert not result["success"], "La validation aurait dû échouer à cause d'un review_id dupliqué"
    assert any(
        f["column"] == "review_id" for f in result["echecs"]
    ), "L'échec doit mentionner la colonne review_id"


def test_valider_rend_le_nom_de_suite_et_le_compte():
    """valider doit renvoyer le nom de la suite et un nombre d'attentes >0."""
    df = _df_mart_base()
    suite_name = "suite_test"
    result = el.valider(df, el.attentes_gold_mart(), suite_name)
    assert result["suite"] == suite_name, f"Nom de suite attendu '{suite_name}', obtenu '{result['suite']}'"
    assert result["evaluees"] > 0, f"Le nombre d'attentes évaluées doit être >0, obtenu {result['evaluees']}"
    assert isinstance(result["evaluees"], int), "evaluees doit être un entier"

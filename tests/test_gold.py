# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""tests/test_gold.py
====================

Quoi
----
Tests d’intégration du projet *gold* (dbt) qui transforme les tables
*silver* en tables de mart (ex. ``mart_sentiment_daily``) et génère le
catalogue ``catalog.json``.

Pourquoi
-------
- Vérifier que la couche *gold* reflète exactement les données *silver*,
  en excluant le flux ``negative_boost`` des indicateurs.
- S’assurer qu’aucune donnée personnelle (``review_text`` ou ``author_pseudo``)
  ne transite dans le mart.
- Garantir que le test de fraîcheur (toutes les revues doivent être
  scorées) bloque le build lorsqu’il y a des prédictions manquantes.
- Détecter toute dérive de schéma entre les tables *silver* et le modèle dbt.

Où
---
- Les tables *silver* sont écrites via :func:`reviewpulse.lakehouse.write_table`
  (Iceberg).
- Le build dbt est déclenché par :func:`reviewpulse.gold.main`.
- Les résultats sont lus dans la base DuckDB ``config.GOLD_DB``.

Comment
-------
- Un helper ``_write_silver`` crée les deux tables *silver* attendues.
- Chaque test utilise la fixture ``data_env`` (pré‑configuration des
  variables d’environnement et du répertoire de travail).
- Aucun sous‑processus n’est lancé ; l’API Python de dbt est utilisée
  directement.
"""

import datetime
import duckdb
import pandas as pd
import pyarrow as pa
import pytest

from reviewpulse import config, gold, lakehouse


pytestmark = pytest.mark.dbt


def _write_silver(n_predictions_missing: int = 0, drift: bool = False) -> None:
    """
    Écrit les tables *silver* utilisées par le pipeline dbt.

    Parameters
    ----------
    n_predictions_missing : int, default 0
        Nombre de lignes de la table ``predictions`` à omettre (simule des
        scores manquants).
    drift : bool, default False
        Si True, la table ``reviews`` est écrite sans la colonne ``text_len``
        (déclenche une dérive de schéma).
    """
    # ----------------------------------------------------------------------
    # Table SILVER_REVIEWS_TABLE
    # ----------------------------------------------------------------------
    reviews_data = {
        "review_id": ["r1", "r2", "r3", "r4", "r5"],
        "app_id": [1086940, 1086940, 1086940, 2622380, 2622380],
        "language": ["english", "english", "english", "french", "french"],
        "review_text": [
            "super jeu",
            "trop de bugs",
            "remboursé",
            "déçu",
            "correct",
        ],
        "label": [1, 0, 0, 0, 1],
        "created_at": pd.to_datetime(
            [
                "2026-09-01T10:00:00Z",
                "2026-09-01T23:30:00Z",
                "2026-09-01T12:00:00Z",
                "2026-09-02T08:00:00Z",
                "2026-09-02T09:00:00Z",
            ],
            utc=True,
        ),
        "updated_at": pd.to_datetime(
            [
                "2026-09-01T10:00:00Z",
                "2026-09-01T23:30:00Z",
                "2026-09-01T12:00:00Z",
                "2026-09-02T08:00:00Z",
                "2026-09-02T09:00:00Z",
            ],
            utc=True,
        ),
        "votes_up": [10, 5, 2, 7, 3],
        "weighted_vote_score": [0.8, 0.5, 0.2, 0.9, 0.1],
        "playtime_at_review_min": [120, 45, 30, 200, 15],
        "author_pseudo": ["alice", "bob", "charlie", "dave", "eve"],
        "text_len": [100, 80, 60, 110, 70],
        "sample_source": ["natural", "natural", "negative_boost", "natural", "negative_boost"],
    }
    reviews_df = pd.DataFrame(reviews_data)
    if drift:
        # Supprime la colonne ``text_len`` pour provoquer une dérive de schéma.
        reviews_df = reviews_df.drop(columns=["text_len"])
    reviews_table = pa.Table.from_pandas(reviews_df, preserve_index=False)
    lakehouse.write_table(config.SILVER_REVIEWS_TABLE, reviews_table)

    # ----------------------------------------------------------------------
    # Table SILVER_PREDICTIONS_TABLE
    # ----------------------------------------------------------------------
    predictions_data = {
        "review_id": ["r1", "r2", "r3", "r4", "r5"],
        "app_id": [1086940, 1086940, 1086940, 2622380, 2622380],
        "language": ["english", "english", "english", "french", "french"],
        "sample_source": ["natural", "natural", "negative_boost", "natural", "negative_boost"],
        "created_at": pd.to_datetime(
            [
                "2026-09-01T10:00:00Z",
                "2026-09-01T23:30:00Z",
                "2026-09-01T12:00:00Z",
                "2026-09-02T08:00:00Z",
                "2026-09-02T09:00:00Z",
            ],
            utc=True,
        ),
        "label": [1, 0, 0, 0, 1],
        # cohérent avec decision.py : négatif (0) si proba_negative >= 0.75
        "pred_label": [1, 0, 0, 1, 1],
        "proba_negative": [0.1, 0.9, 0.8, 0.2, 0.3],
        "decision_threshold": [0.75] * 5,
        "model_version": ["3"] * 5,
        "scored_at": pd.to_datetime(
            [
                "2026-09-01T11:00:00Z",
                "2026-09-01T23:45:00Z",
                "2026-09-01T12:30:00Z",
                "2026-09-02T08:30:00Z",
                "2026-09-02T09:30:00Z",
            ],
            utc=True,
        ),
    }
    predictions_df = pd.DataFrame(predictions_data)

    if n_predictions_missing:
        # Supprime les dernières lignes (les plus récentes) selon le paramètre.
        predictions_df = predictions_df.iloc[:-n_predictions_missing]

    predictions_table = pa.Table.from_pandas(predictions_df, preserve_index=False)
    lakehouse.write_table(config.SILVER_PREDICTIONS_TABLE, predictions_table)


def test_gold_build_and_mart(data_env):
    """
    Vérifie que le build dbt aboutit à un mart correct :

    - Le tableau ``mart_sentiment_daily`` contient exactement deux lignes,
      agrégées par ``app_id`` et ``review_date``.
    - Le flux ``negative_boost`` est exclu des indicateurs.
    - La table ``fct_review_predictions`` compte bien les 5 revues.
    - Le catalogue dbt (``catalog.json``) est généré.
    """
    _write_silver()
    assert gold.main() == 0

    # Lecture du mart généré
    # dbt-duckdb garde sa connexion ouverte dans ce processus : une ouverture en lecture seule
    # serait refusée (constat du 17/09/2026). En production, chaque exécution est un processus distinct.
    con = duckdb.connect(str(config.GOLD_DB))
    mart = con.execute(
        """
        SELECT
            app_id,
            review_date,
            n_reviews,
            n_pred_negative,
            n_actual_negative,
            share_pred_negative,
            game_name,
            model_version
        FROM mart_sentiment_daily
        ORDER BY app_id, review_date
        """
    ).fetchall()

    # Expected rows
    expected = [
        # Baldur's Gate 3, 01/09 : r1 et r2 (flux naturel) ; r3 (negative_boost) exclu.
        (1086940, datetime.date(2026, 9, 1), 2, 1, 1, 0.5, "Baldur's Gate 3", "3"),
        # Nightreign, 02/09 : r4 seul (r5 est du flux negative_boost) ; prédit positif, réellement négatif.
        (2622380, datetime.date(2026, 9, 2), 1, 0, 1, 0.0, "ELDEN RING NIGHTREIGN", "3"),
    ]
    assert mart == expected

    # Vérification du nombre de lignes de la vue fct_review_predictions
    n_pred = con.execute("SELECT COUNT(*) FROM fct_review_predictions").fetchone()[0]
    assert n_pred == 5

    # Le catalogue dbt doit exister
    assert (config.DBT_TARGET_DIR / "catalog.json").exists()


def test_gold_has_no_personal_data(data_env):
    """
    Aucun champ contenant des données personnelles ne doit être présent dans le
    mart (ex. ``review_text`` ou ``author_pseudo``).
    """
    _write_silver()
    assert gold.main() == 0

    # dbt-duckdb garde sa connexion ouverte dans ce processus : une ouverture en lecture seule
    # serait refusée (constat du 17/09/2026). En production, chaque exécution est un processus distinct.
    con = duckdb.connect(str(config.GOLD_DB))
    cols = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'mart_sentiment_daily'
        """
    ).fetchall()
    col_names = {c[0] for c in cols}
    assert "review_text" not in col_names
    assert "author_pseudo" not in col_names


def test_gold_fails_when_scoring_is_stale(data_env):
    """
    Si une ou plusieurs revues n’ont pas de prédiction associée, le test
    ``assert_every_review_is_scored`` échoue et le build dbt renvoie 1.
    """
    _write_silver(n_predictions_missing=1)
    assert gold.main() == 1


def test_gold_rejects_schema_drift(data_env):
    """
    Une dérive de schéma (ex. suppression de la colonne ``text_len``) doit faire
    échouer le build dbt.
    """
    _write_silver(drift=True)
    assert gold.main() == 1

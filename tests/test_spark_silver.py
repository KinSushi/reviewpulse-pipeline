import json
import pathlib
import sys

import pandas as pd
import pyarrow as pa
import pytest
from pandas.testing import assert_frame_equal

from reviewpulse import config, lakehouse, spark_silver, transform

pytestmark = pytest.mark.spark


@pytest.fixture(scope="module")
def spark():
    """Session Spark partagée pour les tests."""
    spark = spark_silver.build_spark()
    yield spark
    spark.stop()


def _write_jsonl(path: pathlib.Path, reviews: list[dict]) -> None:
    """Écrit une liste de revues au format JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rev in reviews:
            f.write(json.dumps(rev, ensure_ascii=False) + "\n")


def test_spark_vs_pandas(data_env, review_factory, spark):
    """
    Vérifie que la version Spark produit exactement le même DataFrame que la version pandas.
    Scénario :
    - texte BBCode à nettoyer,
    - texte vide après nettoyage,
    - avis négatif,
    - doublon dans le flux naturel (deux timestamps),
    - même review_id présent dans le flux naturel et le flux « negative_boost ».
    """
    # Création des avis
    make_review = review_factory

    # Flux naturel
    natural_reviews = [
        make_review(
            rid=100,
            voted_up=True,
            text="[b]Super[/b]   jeu",
            created=1_700_000_000,
            updated=1_700_000_010,
        ),
        make_review(
            rid=101,
            voted_up=True,
            text="[b] [/b]",
            created=1_700_000_020,
            updated=1_700_000_020,
        ),
        make_review(
            rid=102,
            voted_up=False,
            text="bad experience",
            created=1_700_000_030,
            updated=1_700_000_030,
        ),
        # doublon naturel – première version
        make_review(
            rid=103,
            voted_up=True,
            text="duplicate natural old",
            created=1_700_000_040,
            updated=1_700_000_045,
        ),
        # doublon naturel – version plus récente
        make_review(
            rid=103,
            voted_up=True,
            text="duplicate natural new",
            created=1_700_000_040,
            updated=1_700_000_050,
        ),
        # --- Cas réels ayant fait diverger Spark et pandas le 16/09/2026 ---
        # texte contenant une espace insécable
        make_review(
            rid=104,
            voted_up=True,
            text="Recommandé\u00A0!",
            created=1_700_000_060,
            updated=1_700_000_060,
        ),
        # texte contenant un séparateur de ligne (U+2028)
        make_review(
            rid=105,
            voted_up=True,
            text="Bon\u2028jeu",
            created=1_700_000_070,
            updated=1_700_000_070,
        ),
        # texte contenant des espaces idéographiques autour du texte (U+3000)
        make_review(
            rid=106,
            voted_up=True,
            text="\u3000Super\u3000",
            created=1_700_000_080,
            updated=1_700_000_080,
        ),
    ]

    # Flux « negative_boost »
    boost_reviews = [
        make_review(
            rid=103,
            voted_up=True,
            text="duplicate boost",
            created=1_700_000_040,
            updated=1_700_000_060,
        )
    ]

    # Chemins des fichiers JSONL
    natural_path = (
        config.RAW_DIR
        / "app_id=1"
        / "language=english"
        / "dt=2026-09-16"
        / "batch_a.jsonl"
    )
    boost_path = (
        config.RAW_DIR
        / "sample=negative_boost"
        / "app_id=1"
        / "language=english"
        / "dt=2026-09-16"
        / "batch_b.jsonl"
    )

    # Écriture des flux
    _write_jsonl(natural_path, natural_reviews)
    _write_jsonl(boost_path, boost_reviews)

    # DataFrames pandas (référence)
    salt = config.salt()
    pandas_df = transform.clean(transform.load_raw(), salt)

    # DataFrame Spark
    spark_df = spark_silver.build_silver(spark, salt=salt)

    # Comparaison (tri par review_id)
    pandas_sorted = pandas_df.sort_values("review_id").reset_index(drop=True)
    spark_sorted = spark_df.sort_values("review_id").reset_index(drop=True)

    assert_frame_equal(pandas_sorted, spark_sorted)


def test_lakehouse_write_and_history(data_env):
    """
    Écriture Iceberg, relecture, et vérification de l'historique.
    """
    # Table de base
    df = pd.DataFrame(
        {
            "text": pd.Series(["a", "b", "c"], dtype="string"),
            "value": pd.Series([1, 2, 3], dtype="int64"),
            "ts": pd.to_datetime(
                ["2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z", "2023-01-03T00:00:00Z"],
                utc=True,
            ),
        }
    )
    table = pa.Table.from_pandas(df, preserve_index=False)

    identifier = "silver.essai"

    # Première écriture
    lakehouse.write_table(identifier, table)

    # Lecture et vérification du nombre de lignes
    read_back = lakehouse.read_table(identifier).to_pandas()
    assert len(read_back) == len(df)

    # Deuxième écriture avec des valeurs différentes (value * 10)
    df_modified = df.copy()
    df_modified["value"] = df_modified["value"] * 10
    table_modified = pa.Table.from_pandas(df_modified, preserve_index=False)
    lakehouse.write_table(identifier, table_modified)

    # Historique : au moins deux snapshots
    history = lakehouse.table_history(identifier)
    assert len(history) >= 2

    # Lecture après deuxième écriture : doit correspondre à la dernière version
    latest = lakehouse.read_table(identifier).to_pandas()
    assert len(latest) == len(df_modified)

    # Iceberg renvoie les chaînes en type `large_string`; pandas les convertit en `object`.
    # Les valeurs sont identiques, on compare donc les listes de valeurs Python.
    assert latest.astype(object).values.tolist() == df_modified.astype(object).values.tolist()


def test_lakehouse_schema_mismatch(data_env):
    """
    Un changement de schéma doit lever ValueError.
    """
    # Schéma initial
    df_base = pd.DataFrame(
        {
            "text": pd.Series(["x", "y"], dtype="string"),
            "value": pd.Series([10, 20], dtype="int64"),
        }
    )
    base_table = pa.Table.from_pandas(df_base, preserve_index=False)

    identifier = "silver.essai_schema"

    # Écriture initiale
    lakehouse.write_table(identifier, base_table)

    # Schéma différent (colonne supplémentaire)
    df_mismatch = pd.DataFrame(
        {
            "text": pd.Series(["x", "y"], dtype="string"),
            "value": pd.Series([10, 20], dtype="int64"),
            "extra": pd.Series([1, 2], dtype="int64"),
        }
    )
    mismatch_table = pa.Table.from_pandas(df_mismatch, preserve_index=False)

    # Tentative d'écriture avec schéma différent → ValueError
    with pytest.raises(ValueError):
        lakehouse.write_table(identifier, mismatch_table)


def test_workers_use_current_interpreter(spark):
    """
    c'est l'interpréteur réellement utilisé par les workers Python (lu dans PYSPARK_PYTHON) ; dans Airflow il doit être celui du projet, sinon « No module named 'pandas' » (constaté les 16 et 17/09/2026)
    """
    assert spark.sparkContext.pythonExec == sys.executable

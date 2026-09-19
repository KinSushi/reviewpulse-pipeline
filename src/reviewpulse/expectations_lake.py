"""reviewpulse.expectations_lake
================================

Rôle
----
Définir et exécuter des attentes Great Expectations sur les zones *silver* (Iceberg)
et *gold* (DuckDB) qui ne sont pas couvertes par :pymod:`reviewpulse.expectations`.

Place dans la chaîne
--------------------
* **Après** :pymod:`reviewpulse.lakehouse` (lecture des tables Iceberg).
* **Avant** :pymod:`reviewpulse.quality` (validation bloquante du DAG).

Fonctionnement
--------------
1. Quatre constructeurs d’attentes retournent une liste d’objets
   ``gx.Expectation`` :
   - ``attentes_silver_reviews`` : attentes sur la table Iceberg
     ``silver.reviews``.
   - ``attentes_silver_predictions`` : attentes sur la table Iceberg
     ``silver.predictions``.
   - ``attentes_gold_faits`` : attentes sur la table DuckDB
     ``main.fct_review_predictions``.
   - ``attentes_gold_mart`` : attentes sur la table DuckDB
     ``main.mart_sentiment_daily``.
2. ``valider`` crée un contexte Great Expectations éphémère, ajoute les
   attentes, exécute la validation et renvoie un dictionnaire synthétique.
3. ``lire_silver`` lit une table Iceberg via :func:`reviewpulse.lakehouse.read_table`
   et renvoie un ``pandas.DataFrame``.
4. ``lire_gold`` lit une table DuckDB en mode lecture‑seule.
5. ``main`` expose une interface CLI avec l’option ``--zone`` (``silver``,
   ``gold`` ou ``toutes``).  Chaque suite d’attentes est exécutée, le résultat
   est journalisé et le processus renvoie ``1`` dès la première erreur afin
   d’interrompre le DAG.

Ce module ne modifie en aucun cas :pymod:`reviewpulse.expectations` ; il s’en
inspire pour garantir la même forme de sortie.

"""

from __future__ import annotations

import logging
import argparse
from typing import List, Dict, Any

import pandas as pd
import great_expectations as gx
from great_expectations.data_context import AbstractDataContext
from great_expectations.exceptions import DataContextError

import duckdb

from reviewpulse import config
from reviewpulse import lakehouse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constructeurs d’attentes
# --------------------------------------------------------------------------- #


def attentes_silver_reviews() -> List[gx.Expectation]:
    """Attentes sur la table Iceberg ``silver.reviews``."""
    exp: List[gx.Expectation] = []

    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(column="label", value_set=[0, 1])
    )

    # language dans config.LANGUAGES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )

    # sample_source dans config.SAMPLE_SOURCES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sample_source", value_set=config.SAMPLE_SOURCES
        )
    )

    # text_len >= 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="text_len", min_value=1
        )
    )

    # author_pseudo conforme à l’expression hex 64 caractères
    exp.append(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="author_pseudo", regex=r"^[0-9a-f]{64}$"
        )
    )

    return exp


def attentes_silver_predictions() -> List[gx.Expectation]:
    """Attentes sur la table Iceberg ``silver.predictions``."""
    exp: List[gx.Expectation] = []

    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # pred_label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="pred_label", value_set=[0, 1]
        )
    )

    # proba_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="proba_negative", min_value=0, max_value=1
        )
    )

    # decision_threshold entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="decision_threshold", min_value=0, max_value=1
        )
    )

    # model_version non nul
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="model_version"))

    return exp


def attentes_gold_faits() -> List[gx.Expectation]:
    """Attentes sur la table DuckDB ``main.fct_review_predictions``."""
    exp: List[gx.Expectation] = []

    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # pred_label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="pred_label", value_set=[0, 1]
        )
    )

    # proba_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="proba_negative", min_value=0, max_value=1
        )
    )

    # sample_source dans config.SAMPLE_SOURCES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sample_source", value_set=config.SAMPLE_SOURCES
        )
    )

    # language dans config.LANGUAGES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )

    return exp


def attentes_gold_mart() -> List[gx.Expectation]:
    """Attentes sur la table DuckDB ``main.mart_sentiment_daily``."""
    exp: List[gx.Expectation] = []

    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # n_reviews >= 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_reviews", min_value=1
        )
    )

    # share_pred_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="share_pred_negative", min_value=0, max_value=1
        )
    )

    # share_actual_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="share_actual_negative", min_value=0, max_value=1
        )
    )

    # n_pred_negative >= 0
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_pred_negative", min_value=0
        )
    )

    # n_actual_negative >= 0
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_actual_negative", min_value=0
        )
    )

    # language dans config.LANGUAGES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )

    return exp


# --------------------------------------------------------------------------- #
# Validation générique
# --------------------------------------------------------------------------- #


def _reset_context(context: AbstractDataContext) -> None:
    """Supprime la suite et la source si elles existent déjà."""
    try:
        context.validation_definitions.delete("tmp_suite")
    except DataContextError:
        pass
    try:
        context.suites.delete("tmp_suite")
    except DataContextError:
        pass
    try:
        context.data_sources.delete("reviewpulse")
    except DataContextError:
        pass


def valider(
    df: pd.DataFrame,
    attentes: List[gx.Expectation],
    nom_suite: str,
) -> Dict[str, Any]:
    """
    Exécute la suite d’attentes sur *df*.

    Retourne un dictionnaire contenant :

    - ``suite`` : nom de la suite,
    - ``success`` : bool,
    - ``evaluees`` : nombre total d’attentes évaluées,
    - ``echecs`` : liste de dicts ``{expectation, column, unexpected_count}``.
    """
    context = gx.get_context(mode="ephemeral")
    _reset_context(context)

    # Source pandas
    ds = context.data_sources.add_pandas("reviewpulse")

    # Asset et batch definition couvrant tout le DataFrame
    bd = (
        ds.add_dataframe_asset("temp_asset")
        .add_batch_definition_whole_dataframe("tout")
    )

    # Suite
    suite = context.suites.add(gx.ExpectationSuite(name=nom_suite))
    for exp in attentes:
        suite.add_expectation(exp)

    # Validation definition
    vd = context.validation_definitions.add(
        gx.ValidationDefinition(name=nom_suite, data=bd, suite=suite)
    )

    # Exécution
    result = vd.run(batch_parameters={"dataframe": df})

    # Synthèse
    failures: List[Dict[str, Any]] = []
    for r in result.results:
        if not r.success:
            failures.append(
                {
                    "expectation": r.expectation_config.type,
                    "column": r.expectation_config.kwargs.get("column"),
                    "unexpected_count": r.result.get("unexpected_count"),
                }
            )
    summary = {
        "suite": nom_suite,
        "success": result.success,
        "evaluees": len(result.results),
        "echecs": failures,
    }
    return summary


# --------------------------------------------------------------------------- #
# Lecture des zones
# --------------------------------------------------------------------------- #


def lire_silver(identifier: str) -> pd.DataFrame:
    """
    Lit une table Iceberg et renvoie son contenu sous forme de DataFrame pandas.
    """
    pa_table = lakehouse.read_table(identifier)
    return pa_table.to_pandas()


def lire_gold(table: str) -> pd.DataFrame:
    """
    Lit une table DuckDB (lecture‑seule) et renvoie un DataFrame pandas.
    """
    conn = duckdb.connect(str(config.GOLD_DB), read_only=True)
    try:
        df = conn.execute(f"SELECT * FROM {table}").df()
        return df
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Entrée en ligne de commande
# --------------------------------------------------------------------------- #


def main(argv: List[str] | None = None) -> int:
    """Point d’entrée : exécute les suites d’attentes demandées.

    *argv* permet l’appel depuis un orchestrateur, où ``sys.argv`` appartient au
    processus hôte et non à ce module ; sans lui, Airflow ferait échouer l’analyse
    des arguments. Laissé à ``None``, le comportement en ligne de commande est
    inchangé."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Validation Great Expectations sur les zones silver et gold"
    )
    parser.add_argument(
        "--zone",
        choices=["silver", "gold", "toutes"],
        default="toutes",
        help="Zone à valider (silver, gold ou toutes).",
    )
    args = parser.parse_args(argv)

    exit_code = 0
    suites_to_run: List[Dict[str, Any]] = []

    if args.zone in ("silver", "toutes"):
        suites_to_run.append(
            {
                "name": "silver_reviews",
                "read_fn": lambda: lire_silver(config.SILVER_REVIEWS_TABLE),
                "expectations": attentes_silver_reviews(),
            }
        )
        suites_to_run.append(
            {
                "name": "silver_predictions",
                "read_fn": lambda: lire_silver(config.SILVER_PREDICTIONS_TABLE),
                "expectations": attentes_silver_predictions(),
            }
        )

    if args.zone in ("gold", "toutes"):
        suites_to_run.append(
            {
                "name": "gold_faits",
                "read_fn": lambda: lire_gold("main.fct_review_predictions"),
                "expectations": attentes_gold_faits(),
            }
        )
        suites_to_run.append(
            {
                "name": "gold_mart",
                "read_fn": lambda: lire_gold("main.mart_sentiment_daily"),
                "expectations": attentes_gold_mart(),
            }
        )

    for suite in suites_to_run:
        suite_name: str = suite["name"]
        try:
            df = suite["read_fn"]()
        except Exception as exc:
            logger.error("Impossible de lire la source pour la suite %s : %s", suite_name, exc)
            return 1

        try:
            result = valider(df, suite["expectations"], suite_name)
        except Exception as exc:
            logger.error("Échec de la validation pour la suite %s : %s", suite_name, exc)
            return 1

        nb_echecs = len(result["echecs"])
        logger.info(
            "Suite %s – succès : %s – attentes évaluées : %d – échecs : %d",
            suite_name,
            result["success"],
            result["evaluees"],
            nb_echecs,
        )
        if not result["success"]:
            exit_code = 1
            for f in result["echecs"]:
                logger.debug(
                    "Échec – expectation: %s, column: %s, unexpected_count: %s",
                    f.get("expectation"),
                    f.get("column"),
                    f.get("unexpected_count"),
                )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

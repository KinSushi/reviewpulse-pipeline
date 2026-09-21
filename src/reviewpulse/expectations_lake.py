# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
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

Décision appliquée ici : ADR 0020 — porte de qualité étendue aux zones silver et gold.

Quoi
----
Ce module définit et exécute des attentes Great Expectations sur les zones silver (Iceberg) et gold (DuckDB) qui ne sont pas couvertes par :pymod:`reviewpulse.expectations`.

Pourquoi
--------
La porte de qualité existante (:pymod:`reviewpulse.expectations`) ne couvre que la zone propre (parquet). Les zones silver et gold, produites par :pymod:`reviewpulse.spark_silver` et :pymod:`reviewpulse.gold`, nécessitent leurs propres contrôles bloquants pour garantir la qualité des données avant leur utilisation par les analystes et le tableau de bord. ADR 0020.

Où
---
Appelé par la tâche `gx_lake` du DAG quotidien, après `gold`. Lit les tables Iceberg via :func:`reviewpulse.lakehouse.read_table` et les tables DuckDB via une connexion en lecture seule. N'écrit aucun fichier ; renvoie un code de sortie.

Comment
-------
Quatre constructeurs d'attentes retournent des listes d'objets `gx.Expectation`. `valider` crée un contexte Great Expectations éphémère, ajoute les attentes, exécute la validation et renvoie un dictionnaire synthétique. `lire_silver` et `lire_gold` lisent les données. `main` orchestre l'exécution selon la zone demandée et renvoie 1 dès qu'une suite échoue.

Choix de conception
-------------------
- Module distinct de `expectations.py` : la porte de qualité existante fonctionne et couvre la zone propre ; on n'a pas voulu refondre une porte de qualité à quelques jours de la soutenance. Alternative écartée : étendre `expectations.py` pour couvrir silver et gold, ce qui aurait risqué de casser la validation existante.
- `main` accepte une liste d'arguments (`argv`) : un module lancé par Airflow ne peut pas lire `sys.argv` car il appartient au processus hôte. Alternative écartée : utiliser `sys.argv` directement, ce qui aurait fait échouer l'analyse des arguments dans Airflow.
- Contexte éphémère pour la validation : pas de persistance nécessaire, les résultats sont journalisés et le code de sortie suffit pour le DAG. Alternative écartée : contexte « file » pour générer des Data Docs, mais cela alourdirait l'exécution sans besoin métier.

Limites connues
---------------
- Ne génère pas de rapport HTML (contrairement à `expectations.py`).
- Ne vérifie pas la cohérence entre les tables silver et gold (par exemple, jointure entre reviews et predictions).
- Les attentes sont définies statiquement ; toute évolution du schéma nécessite une modification du code.
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
    """Attentes sur la table Iceberg ``silver.reviews``.

    Pourquoi : garantir que la table silver des avis respecte les contraintes de qualité avant son utilisation dans la couche gold et le tableau de bord.

    Returns:
        List[gx.Expectation]: liste des attentes Great Expectations à appliquer.
    """
    exp: List[gx.Expectation] = []

    # Pourquoi : une table vide indique un échec en amont (ingest ou spark_silver) et doit bloquer le pipeline.
    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Pourquoi : review_id est la clé primaire ; un doublon indiquerait une corruption ou une erreur de dédoublonnage.
    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # Pourquoi : la convention de décision (ADR 0009) impose des étiquettes binaires 0/1.
    # label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(column="label", value_set=[0, 1])
    )

    # Pourquoi : seules les langues configurées sont attendues ; toute autre valeur indique une erreur de collecte.
    # language dans config.LANGUAGES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )

    # Pourquoi : sample_source doit provenir des flux définis dans la configuration.
    # sample_source dans config.SAMPLE_SOURCES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sample_source", value_set=config.SAMPLE_SOURCES
        )
    )

    # Pourquoi : un texte vide n'apporte aucune information et fausserait l'entraînement.
    # text_len >= 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="text_len", min_value=1
        )
    )

    # Pourquoi : le pseudonyme est un HMAC-SHA256 hexadécimal de 64 caractères (ADR 0004).
    # author_pseudo conforme à l’expression hex 64 caractères
    exp.append(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="author_pseudo", regex=r"^[0-9a-f]{64}$"
        )
    )

    return exp


def attentes_silver_predictions() -> List[gx.Expectation]:
    """Attentes sur la table Iceberg ``silver.predictions``.

    Pourquoi : garantir que les prédictions stockées dans la zone silver respectent les contraintes de qualité avant leur utilisation dans la couche gold.

    Returns:
        List[gx.Expectation]: liste des attentes Great Expectations à appliquer.
    """
    exp: List[gx.Expectation] = []

    # Pourquoi : une table vide indique un échec en amont (score) et doit bloquer le pipeline.
    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Pourquoi : review_id est la clé primaire ; un doublon indiquerait une corruption ou une erreur de jointure.
    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # Pourquoi : la convention de décision (ADR 0009) impose des étiquettes binaires 0/1.
    # pred_label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="pred_label", value_set=[0, 1]
        )
    )

    # Pourquoi : une probabilité doit être comprise entre 0 et 1.
    # proba_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="proba_negative", min_value=0, max_value=1
        )
    )

    # Pourquoi : le seuil de décision est une probabilité, donc borné entre 0 et 1.
    # decision_threshold entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="decision_threshold", min_value=0, max_value=1
        )
    )

    # Pourquoi : la version du modèle doit être renseignée pour la traçabilité.
    # model_version non nul
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="model_version"))

    return exp


def attentes_gold_faits() -> List[gx.Expectation]:
    """Attentes sur la table DuckDB ``main.fct_review_predictions``.

    Pourquoi : garantir que la table de faits gold respecte les contraintes de qualité avant son utilisation par les analystes.

    Returns:
        List[gx.Expectation]: liste des attentes Great Expectations à appliquer.
    """
    exp: List[gx.Expectation] = []

    # Pourquoi : une table vide indique un échec en amont (gold) et doit bloquer le pipeline.
    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Pourquoi : review_id est la clé primaire ; un doublon indiquerait une corruption ou une erreur de jointure.
    # review_id non nul et unique
    exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column="review_id"))
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # Pourquoi : la convention de décision (ADR 0009) impose des étiquettes binaires 0/1.
    # pred_label dans {0, 1}
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="pred_label", value_set=[0, 1]
        )
    )

    # Pourquoi : une probabilité doit être comprise entre 0 et 1.
    # proba_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="proba_negative", min_value=0, max_value=1
        )
    )

    # Pourquoi : sample_source doit provenir des flux définis dans la configuration.
    # sample_source dans config.SAMPLE_SOURCES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sample_source", value_set=config.SAMPLE_SOURCES
        )
    )

    # Pourquoi : seules les langues configurées sont attendues ; toute autre valeur indique une erreur de collecte.
    # language dans config.LANGUAGES
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )

    return exp


def attentes_gold_mart() -> List[gx.Expectation]:
    """Attentes sur la table DuckDB ``main.mart_sentiment_daily``.

    Pourquoi : garantir que la table agrégée gold respecte les contraintes de qualité avant son utilisation par le tableau de bord.

    Returns:
        List[gx.Expectation]: liste des attentes Great Expectations à appliquer.
    """
    exp: List[gx.Expectation] = []

    # Pourquoi : une table vide indique un échec en amont (gold) et doit bloquer le pipeline.
    # Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # Pourquoi : le nombre d'avis par groupe doit être au moins 1, sinon le groupe est vide.
    # n_reviews >= 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_reviews", min_value=1
        )
    )

    # Pourquoi : une part doit être comprise entre 0 et 1.
    # share_pred_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="share_pred_negative", min_value=0, max_value=1
        )
    )

    # Pourquoi : une part doit être comprise entre 0 et 1.
    # share_actual_negative entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="share_actual_negative", min_value=0, max_value=1
        )
    )

    # Pourquoi : un comptage ne peut pas être négatif.
    # n_pred_negative >= 0
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_pred_negative", min_value=0
        )
    )

    # Pourquoi : un comptage ne peut pas être négatif.
    # n_actual_negative >= 0
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_actual_negative", min_value=0
        )
    )

    # Pourquoi : seules les langues configurées sont attendues ; toute autre valeur indique une erreur de collecte.
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
    """Supprime la suite et la source si elles existent déjà.

    Pourquoi : le contexte éphémère peut conserver des définitions d'une exécution précédente ; on les supprime pour éviter les doublons.

    Args:
        context: le contexte Great Expectations à nettoyer.

    Returns:
        None
    """
    # Pourquoi : les suppressions peuvent échouer si l'élément n'existe pas ; on ignore ces erreurs.
    try:
        context.validation_definitions.delete("tmp_suite")
    except DataContextError as exc:
        logger.debug("Suppression de tmp_suite ignorée : %s", exc)
        pass
    try:
        context.suites.delete("tmp_suite")
    except DataContextError as exc:
        logger.debug("Suppression de tmp_suite ignorée : %s", exc)
        pass
    try:
        context.data_sources.delete("reviewpulse")
    except DataContextError as exc:
        logger.debug("Suppression de reviewpulse ignorée : %s", exc)
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

    Pourquoi : centraliser l'exécution Great Expectations pour toutes les suites, avec un format de sortie uniforme.

    Args:
        df: le DataFrame pandas à valider.
        attentes: la liste des attentes à appliquer.
        nom_suite: le nom de la suite, utilisé pour identifier les résultats.

    Returns:
        Dict[str, Any]: dictionnaire de synthèse avec les clés ``suite``, ``success``, ``evaluees``, ``echecs``.

    Raises:
        Aucune exception n'est levée ; les erreurs Great Expectations sont propagées.
    """
    # Pourquoi : contexte éphémère pour ne pas persister de fichiers et rester léger dans le DAG.
    context = gx.get_context(mode="ephemeral")
    _reset_context(context)

    # Pourquoi : source pandas pour valider un DataFrame en mémoire.
    ds = context.data_sources.add_pandas("reviewpulse")

    # Pourquoi : batch definition couvrant tout le DataFrame, sans partition.
    bd = (
        ds.add_dataframe_asset("temp_asset")
        .add_batch_definition_whole_dataframe("tout")
    )

    # Pourquoi : suite nommée pour identifier les résultats.
    suite = context.suites.add(gx.ExpectationSuite(name=nom_suite))
    for exp in attentes:
        suite.add_expectation(exp)

    # Pourquoi : validation definition lie la suite aux données.
    vd = context.validation_definitions.add(
        gx.ValidationDefinition(name=nom_suite, data=bd, suite=suite)
    )

    # Pourquoi : exécution avec le DataFrame passé en paramètre.
    result = vd.run(batch_parameters={"dataframe": df})

    # Pourquoi : extraire les échecs sous forme de dictionnaires pour la journalisation et le code de sortie.
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

    Pourquoi : fournir une interface uniforme pour lire les tables silver, en s'appuyant sur lakehouse.read_table.

    Args:
        identifier: l'identifiant de la table Iceberg (par exemple ``silver.reviews``).

    Returns:
        pd.DataFrame: le contenu de la table sous forme de DataFrame pandas.

    Raises:
        Toute exception levée par :func:`reviewpulse.lakehouse.read_table` ou par la conversion en pandas.
    """
    # Pourquoi : lakehouse.read_table renvoie une table Arrow ; conversion en pandas pour compatibilité avec Great Expectations.
    pa_table = lakehouse.read_table(identifier)
    return pa_table.to_pandas()


def lire_gold(table: str) -> pd.DataFrame:
    """
    Lit une table DuckDB (lecture‑seule) et renvoie un DataFrame pandas.

    Pourquoi : fournir une interface uniforme pour lire les tables gold, en garantissant la lecture seule.

    Args:
        table: le nom de la table DuckDB (par exemple ``main.fct_review_predictions``).

    Returns:
        pd.DataFrame: le contenu de la table sous forme de DataFrame pandas.

    Raises:
        Toute exception levée par duckdb.connect ou par l'exécution de la requête.
    """
    # Pourquoi : lecture seule pour ne pas modifier la base gold.
    conn = duckdb.connect(str(config.GOLD_DB), read_only=True)
    try:
        # Pourquoi : f-string pour nom de table, mais le nom provient de constantes internes, pas d'entrée utilisateur.
        df = conn.execute(f"SELECT * FROM {table}").df()
        return df
    finally:
        # Pourquoi : fermeture garantie même en cas d'erreur.
        conn.close()


# --------------------------------------------------------------------------- #
# Entrée en ligne de commande
# --------------------------------------------------------------------------- #


def main(argv: List[str] | None = None) -> int:
    """Point d’entrée : exécute les suites d’attentes demandées.

    *argv* permet l’appel depuis un orchestrateur, où ``sys.argv`` appartient au
    processus hôte et non à ce module ; sans lui, Airflow ferait échouer l’analyse
    des arguments. Laissé à ``None``, le comportement en ligne de commande est
    inchangé.

    Pourquoi : orchestrer l'exécution des suites selon la zone demandée et renvoyer un code de sortie pour le DAG.

    Args:
        argv: liste d'arguments de ligne de commande (par défaut ``None`` pour utiliser ``sys.argv``).

    Returns:
        int: 0 si toutes les suites passent, 1 si une lecture ou une validation échoue.
    """
    # Pourquoi : configuration du logging pour la sortie console du DAG.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Validation Great Expectations sur les zones silver et gold"
    )
    # Pourquoi : restreindre les zones pour éviter les fautes de frappe.
    parser.add_argument(
        "--zone",
        choices=["silver", "gold", "toutes"],
        default="toutes",
        help="Zone à valider (silver, gold ou toutes).",
    )
    args = parser.parse_args(argv)

    logger.info("Début de la validation des zones %s", args.zone)

    exit_code = 0
    suites_to_run: List[Dict[str, Any]] = []

    # Pourquoi : construire la liste des suites selon la zone demandée.
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

    logger.info("%d suites à exécuter", len(suites_to_run))

    # Pourquoi : exécuter chaque suite indépendamment et arrêter au premier échec.
    for suite in suites_to_run:
        suite_name: str = suite["name"]
        logger.info("Lecture de la source pour la suite %s", suite_name)
        # Pourquoi : capturer les erreurs de lecture pour journaliser et retourner 1.
        try:
            df = suite["read_fn"]()
        except Exception as exc:
            logger.exception("Impossible de lire la source pour la suite %s : %s", suite_name, exc)
            return 1

        logger.info("Validation de la suite %s", suite_name)
        # Pourquoi : capturer les erreurs de validation pour journaliser et retourner 1.
        try:
            result = valider(df, suite["expectations"], suite_name)
        except Exception as exc:
            logger.exception("Échec de la validation pour la suite %s : %s", suite_name, exc)
            return 1

        nb_echecs = len(result["echecs"])
        logger.info(
            "Suite %s – succès : %s – attentes évaluées : %d – échecs : %d",
            suite_name,
            result["success"],
            result["evaluees"],
            nb_echecs,
        )
        # Pourquoi : un échec de validation doit faire échouer le DAG.
        if not result["success"]:
            exit_code = 1
            for f in result["echecs"]:
                logger.debug(
                    "Échec – expectation: %s, column: %s, unexpected_count: %s",
                    f.get("expectation"),
                    f.get("column"),
                    f.get("unexpected_count"),
                )

    logger.info("Fin de la validation, code de sortie %d", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

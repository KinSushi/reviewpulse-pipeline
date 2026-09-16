"""reviewpulse.expectations
==========================

Rôle
----
Définir et exécuter une suite d’attentes (Great Expectations) sur la zone propre.
Cette suite vient **compléter** le contrôle bloquant de :pymod:`reviewpulse.quality`
en fournissant un rapport HTML (Data Docs) exploitable par des non‑développeurs.

Place dans la chaîne
--------------------
* **Après** : :pymod:`reviewpulse.transform.main` (qui écrit le parquet).
* **Avant** : :pymod:`reviewpulse.score.main` (le DAG quotidien invoque
  :func:`main` via la tâche ``gx_validate``).

Fonctionnement
--------------
1. ``build_expectations`` crée la liste d’objets Expectation dans l’ordre
   spécifié par le contrat.
2. ``validate`` construit (ou ré‑utilise) un contexte Great Expectations,
   crée ou récupère la suite nommée ``zone_propre``, y ajoute les attentes,
   exécute la validation sur le DataFrame fourni et renvoie un dictionnaire
   synthétique.
3. ``build_data_docs`` crée un contexte **file** (ou ré‑utilise le même
   répertoire), exécute la même suite et génère les Data Docs. Le chemin
   vers ``index.html`` est retourné.
4. ``main`` charge le parquet, lance la génération du rapport, journalise le
   chemin et le nombre d’échecs, puis renvoie le code de sortie attendu
   (0 = succès, 1 = échec).

Choix de conception
--------------------
* Contexte éphémère par défaut dans :func:`validate` afin de ne pas polluer le
  disque lors des appels unitaires.
* Contexte « file » dans :func:`build_data_docs` pour persister le rapport.
* La suite est créée une seule fois ; les appels subséquents récupèrent la
  suite existante afin d’éviter les duplications.
* Aucun import inutilisé – chaque symbole est employé dans le code.
* Les messages d’erreur sont normalisés dans le dictionnaire retourné, ce qui
  simplifie les assertions dans les tests.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple, List, Dict

import great_expectations as gx
import pandas as pd

from great_expectations.data_context import AbstractDataContext
from great_expectations.exceptions import DataContextError

from reviewpulse import config

# --------------------------------------------------------------------------- #
# Configuration du module
# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)

# Nom de la suite d’attentes
SUITE_NAME = "zone_propre"
# Nom de la source de données pandas
SOURCE_NAME = "reviewpulse"


def _reset(context: AbstractDataContext) -> None:
    """Supprime, dans l’ordre, la validation, la suite puis la source.

    Les erreurs éventuelles (absence d’objet) sont ignorées conformément
    aux spécifications de l’API Great Expectations 1.23.0.
    """
    # Validation definition
    try:
        context.validation_definitions.delete(SUITE_NAME)
    except DataContextError:
        pass

    # Suite
    try:
        context.suites.delete(SUITE_NAME)
    except DataContextError:
        pass

    # Source – la méthode delete ne lève pas d’erreur lorsqu’elle est absente
    context.data_sources.delete(SOURCE_NAME)


def _run(context: AbstractDataContext, df: pd.DataFrame):
    """Exécute la suite d’attentes sur *df* dans le *context* fourni.

    La fonction réinitialise le contexte, crée la source, la suite,
    ajoute les attentes, crée la validation et lance l’exécution.
    """
    _reset(context)

    # Source pandas
    ds = context.data_sources.add_pandas(SOURCE_NAME)

    # Asset et batch definition couvrant tout le DataFrame
    bd = (
        ds.add_dataframe_asset("clean_reviews")
        .add_batch_definition_whole_dataframe("tout")
    )

    # Suite d’attentes
    suite = context.suites.add(gx.ExpectationSuite(name=SUITE_NAME))
    for expectation in build_expectations():
        suite.add_expectation(expectation)

    # Validation definition
    vd = context.validation_definitions.add(
        gx.ValidationDefinition(name=SUITE_NAME, data=bd, suite=suite)
    )

    # Exécution
    return vd.run(batch_parameters={"dataframe": df})


def _summarize(result) -> Dict:
    """Construit le dictionnaire de synthèse attendu par le contrat."""
    failed: List[Dict] = []
    for r in result.results:
        if not r.success:
            failed.append(
                {
                    "expectation": r.expectation_config.type,
                    "column": r.expectation_config.kwargs.get("column"),
                    "unexpected_count": r.result.get("unexpected_count"),
                }
            )
    return {
        "success": result.success,
        "evaluated": len(result.results),
        "failed": failed,
    }


def build_expectations() -> List[gx.Expectation]:
    """Construit la liste d’attentes dans l’ordre indiqué par le contrat."""
    exp: List[gx.Expectation] = []

    # 1. Colonnes dans le bon ordre
    exp.append(
        gx.expectations.ExpectTableColumnsToMatchOrderedList(
            column_list=list(config.CLEAN_COLUMNS)
        )
    )

    # 2. Au moins une ligne
    exp.append(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1))

    # 3. Valeurs non nulles sur les colonnes essentielles
    for col in ("review_id", "review_text", "created_at", "author_pseudo"):
        exp.append(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # 4. Unicité de review_id
    exp.append(gx.expectations.ExpectColumnValuesToBeUnique(column="review_id"))

    # 5. Valeurs dans des ensembles autorisés
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(column="label", value_set=[0, 1])
    )
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="language", value_set=config.LANGUAGES
        )
    )
    exp.append(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sample_source", value_set=config.SAMPLE_SOURCES
        )
    )

    # 6. Longueur du texte >= 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="text_len", min_value=1
        )
    )

    # 7. Score pondéré entre 0 et 1
    exp.append(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="weighted_vote_score", min_value=0, max_value=1
        )
    )

    # 8. Votes et temps de jeu >= 0
    for col in ("votes_up", "playtime_at_review_min"):
        exp.append(
            gx.expectations.ExpectColumnValuesToBeBetween(column=col, min_value=0)
        )
    # 9. Pseudo auteur au format hex 64 caractères
    exp.append(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="author_pseudo", regex=r"^[0-9a-f]{64}$"
        )
    )

    return exp


def validate(df: pd.DataFrame, context: AbstractDataContext | None = None) -> Dict:
    """Exécute la suite d’attentes sur le DataFrame fourni.

    Un contexte éphémère est créé si *context* n’est pas fourni.
    """
    if context is None:
        context = gx.get_context(mode="ephemeral")
    result = _run(context, df)
    return _summarize(result)


def run_and_document(df: pd.DataFrame, project_dir: Path | None = None) -> Tuple[Dict, Path]:
    """Exécute la validation et génère les Data Docs.

    Retourne le dictionnaire de synthèse et le chemin absolu du fichier
    ``index.html`` du site généré.
    """
    root = Path(project_dir or config.GX_DIR)
    root.mkdir(parents=True, exist_ok=True)

    context = gx.get_context(mode="file", project_root_dir=str(root))
    result = _run(context, df)

    # Génération des Data Docs
    context.build_data_docs()

    # Recherche du fichier index.html du site local
    candidates = sorted(
        p for p in root.rglob("index.html") if "local_site" in str(p)
    )
    if not candidates:
        raise FileNotFoundError(
            f"Impossible de trouver le fichier index.html dans {root}"
        )
    index_path = candidates[0].resolve()
    return _summarize(result), index_path


def build_data_docs(df: pd.DataFrame, project_dir: Path | None = None) -> Path:
    """Génère les Data Docs et renvoie le chemin du fichier ``index.html``."""
    return run_and_document(df, project_dir)[1]


def main() -> int:
    """Point d’entrée du module : génère le rapport Great Expectations."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        df = pd.read_parquet(config.CLEAN_FILE)
    except Exception as exc:  # pragma: no cover – cas rare en production
        logger.error(
            "Impossible de lire le fichier nettoyé %s : %s", config.CLEAN_FILE, exc
        )
        return 1

    try:
        summary, report_path = run_and_document(df)
        logger.info("Rapport Great Expectations généré : %s", report_path)
    except Exception as exc:  # pragma: no cover
        logger.error("Échec de la génération du rapport Great Expectations : %s", exc)
        return 1

    if summary["success"]:
        logger.info("Toutes les attentes Great Expectations sont satisfaites.")
        return 0
    else:
        nb_failed = len(summary["failed"])
        logger.warning("Great Expectations : %d attente(s) en échec.", nb_failed)
        for f in summary["failed"]:
            logger.debug(
                "Échec – expectation: %s, column: %s, unexpected_count: %s",
                f.get("expectation"),
                f.get("column"),
                f.get("unexpected_count"),
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

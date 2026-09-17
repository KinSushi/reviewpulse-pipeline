"""reviewpulse.gold
===================

Où
----
Ce module se situe dans la couche *gold* du pipeline, exécuté après l’étape
``score`` dans le DAG quotidien. Il orchestre la construction de l’entrepôt
DuckDB via dbt (staging, schéma en étoile, indicateur quotidien, tests,
contrats, documentation).

Quoi
----
Il lit les emplacements actuels des métadonnées Iceberg des tables *silver*
(``silver.reviews`` et ``silver.predictions``), les transmet à dbt comme
variables, puis invoque dbt via son API Python afin de :

* créer les modèles dbt (staging, marts, etc.) ;
* exécuter les tests et les contrats ;
* générer la documentation et le lignage.

Comment
-------
1. ``silver_vars`` récupère les ``metadata_location`` des deux tables
   Iceberg via :func:`reviewpulse.lakehouse.get_catalog`.
2. ``_prepare_env`` crée les répertoires configurés (``config.GOLD_DIR`` et
   ``config.DUCKDB_EXT_DIR``) et définit les variables d’environnement
   ``REVIEWPULSE_GOLD_DB`` et ``REVIEWPULSE_DUCKDB_EXT_DIR``.
3. ``run_dbt`` prépare l’environnement, construit la ligne de commande dbt
   (project‑dir, profiles‑dir, target‑path, log‑path, ``--vars``) et l’exécute
   avec :class:`dbt.cli.main.dbtRunner`.
4. ``main`` orchestre le ``dbt build`` puis la génération de la documentation
   (``dbt docs generate``), journalise les statuts et renvoie un code de sortie
   compatible avec Airflow.

Pourquoi
-------
* dbt est enseigné dans le programme et constitue le standard de modélisation
  analytique.
* DuckDB peut lire les tables Iceberg sans serveur, ce qui simplifie le
  déploiement.
* Les tests et contrats dbt rendent la couche *gold* vérifiable et
  reproductible.
* Utiliser l’API Python évite de lancer un sous‑processus, ce qui rend le
  code de retour testable.

Preuves
-------
* ``tests/test_gold.py`` : mart attendu sur un jeu de 5 avis (flux
  ``negative_boost`` exclu), absence de données personnelles, échec si le
  score est périmé, échec si le schéma silver dérive.
"""

import collections
import json
import logging
import os

from dbt.cli.main import dbtRunner, dbtRunnerResult

from reviewpulse import config, lakehouse

log = logging.getLogger(__name__)


def silver_vars() -> dict[str, str]:
    """Retourne les variables dbt contenant les métadonnées Iceberg des tables *silver*.

    Returns
    -------
    dict[str, str]
        ``{
            "silver_reviews_metadata": <metadata_location>,
            "silver_predictions_metadata": <metadata_location>,
        }``

    Notes
    -----
    La fonction utilise le catalogue Iceberg de :mod:`reviewpulse.lakehouse`
    pour charger les tables configurées dans ``config.SILVER_REVIEWS_TABLE`` et
    ``config.SILVER_PREDICTIONS_TABLE`` puis extrait leur attribut
    ``metadata_location``.
    """
    catalog = lakehouse.get_catalog()
    reviews_table = catalog.load_table(config.SILVER_REVIEWS_TABLE)
    predictions_table = catalog.load_table(config.SILVER_PREDICTIONS_TABLE)

    return {
        "silver_reviews_metadata": str(reviews_table.metadata_location),
        "silver_predictions_metadata": str(predictions_table.metadata_location),
    }


def _prepare_env() -> None:
    """Prépare le répertoire et les variables d’environnement nécessaires à dbt.

    - Crée ``config.GOLD_DIR`` et ``config.DUCKDB_EXT_DIR`` (parents créés si
      besoin).
    - Définit ``REVIEWPULSE_GOLD_DB`` et ``REVIEWPULSE_DUCKDB_EXT_DIR`` avec les
      chemins absolus configurés.
    """
    config.GOLD_DIR.mkdir(parents=True, exist_ok=True)
    config.DUCKDB_EXT_DIR.mkdir(parents=True, exist_ok=True)

    os.environ["REVIEWPULSE_GOLD_DB"] = str(config.GOLD_DB)
    os.environ["REVIEWPULSE_DUCKDB_EXT_DIR"] = str(config.DUCKDB_EXT_DIR)


def run_dbt(*command: str) -> dbtRunnerResult:
    """Exécute une commande dbt via l’API Python.

    Parameters
    ----------
    *command : str
        Séquence de sous‑commandes dbt (ex. ``'build'`` ou ``'docs', 'generate'``).

    Returns
    -------
    dbtRunnerResult
        Objet résultat retourné par :class:`dbtRunner`.
    """
    _prepare_env()
    args = [
        *command,
        "--project-dir",
        str(config.DBT_PROJECT_DIR),
        "--profiles-dir",
        str(config.DBT_PROJECT_DIR),
        "--target-path",
        str(config.DBT_TARGET_DIR),
        "--log-path",
        str(config.DBT_LOG_DIR),
        "--vars",
        json.dumps(silver_vars()),
    ]

    runner = dbtRunner()
    result = runner.invoke(args)
    return result


def main() -> int:
    """Orchestration du pipeline *gold*.

    - Exécute ``dbt build`` et journalise le comptage des statuts.
    - En cas d’échec, journalise l’erreur et renvoie ``1``.
    - Génère la documentation avec ``dbt docs generate``.
    - Journalise le chemin du fichier DuckDB final.

    Retour
    ------
    int
        ``0`` si tout s’est bien passé, ``1`` sinon.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Étape 1 : dbt build
    res = run_dbt("build")
    if res.result is not None:
        counter: collections.Counter[str] = collections.Counter(
            str(r.status) for r in res.result
        )
        log.info("dbt build : %s", dict(counter))

    if not res.success:
        log.error("dbt build a échoué")
        if hasattr(res, "exception") and res.exception:
            log.error("Exception dbt : %s", res.exception)
        return 1

    # Étape 2 : génération de la documentation
    # documentation et lignage consultables par le jury (dbt docs serve --target-path),
    # écrits dans config.DBT_TARGET_DIR.
    docs = run_dbt("docs", "generate")
    if not docs.success:
        log.error("dbt docs generate a échoué")
        return 1

    log.info("Entrepôt DuckDB créé : %s", config.GOLD_DB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

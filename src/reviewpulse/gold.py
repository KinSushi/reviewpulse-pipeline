# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""reviewpulse.gold
===================

Où
----
Ce module se situe dans la couche *gold* du pipeline, exécuté après l'étape
``score`` dans le DAG quotidien. Il orchestre la construction de l'entrepôt
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
   ``config.DUCKDB_EXT_DIR``) et définit les variables d'environnement
   ``REVIEWPULSE_GOLD_DB`` et ``REVIEWPULSE_DUCKDB_EXT_DIR``.
3. ``run_dbt`` prépare l'environnement, construit la ligne de commande dbt
   (project‑dir, profiles‑dir, target‑path, log‑path, ``--vars``) et l'exécute
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
* Utiliser l'API Python évite de lancer un sous‑processus, ce qui rend le
  code de retour testable.

Preuves
-------
* ``tests/test_gold.py`` : mart attendu sur un jeu de 5 avis (flux
  ``negative_boost`` exclu), absence de données personnelles, échec si le
  score est périmé, échec si le schéma silver dérive.

Choix de conception
-------------------
* **API Python dbtRunner plutôt que sous-processus** : permet de capturer le
  résultat de manière testable et d'éviter la gestion manuelle des codes de
  sortie. Alternative écartée : ``subprocess.run`` avec parsing de stdout.
  ADR 0011 (orchestration).
* **Métadonnées Iceberg passées via --vars JSON** : dbt peut ainsi lire les
  tables silver sans configuration statique. Alternative écartée : variables
  d'environnement séparées (moins structuré pour dbt).
* **Création explicite des répertoires avant exécution** : garantit que dbt
  trouve ses cibles même en environnement vierge. Alternative écartée :
  laisser dbt créer les répertoires (échec possible si permissions insuffisantes).
* **Code de retour compatible Airflow** : ``0`` pour succès, ``1`` pour échec.
  Alternative écartée : lever une exception (Airflow préfère les codes de retour).

Limites connues
---------------
* Ne vérifie pas la présence effective des tables Iceberg avant d'appeler dbt
  (la validation a lieu dans dbt via les tests).
* Ne gère pas les échecs partiels de ``dbt build`` : si un modèle échoue, tout
  le pipeline s'arrête (comportement voulu pour la cohérence des données).
* La documentation dbt est générée même en cas de ``dbt build`` partiellement
  réussi (seul le succès complet est accepté).
* Ne purge pas les anciennes versions de l'entrepôt DuckDB (gestion manuelle).
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

    Rôle : fournir à dbt les emplacements des tables source pour lecture.

    Pourquoi : dbt nécessite les metadata_location pour accéder aux tables Iceberg
    sans configuration statique dans profiles.yml.

    Returns
    -------
    dict[str, str]
        ``{
            "silver_reviews_metadata": <metadata_location>,
            "silver_predictions_metadata": <metadata_location>,
        }``

    Raises
    ------
    Exception
        Si le catalogue Iceberg est inaccessible ou si les tables n'existent pas.

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

    # Pourquoi : journalisation en debug car appelé une fois par exécution du pipeline,
    # pas à chaque requête HTTP.
    log.debug(
        "Métadonnées Iceberg : reviews=%s, predictions=%s",
        reviews_table.metadata_location,
        predictions_table.metadata_location,
    )

    return {
        "silver_reviews_metadata": str(reviews_table.metadata_location),
        "silver_predictions_metadata": str(predictions_table.metadata_location),
    }


def _prepare_env() -> None:
    """Prépare le répertoire et les variables d'environnement nécessaires à dbt.

    Rôle : garantir que dbt trouve ses répertoires de travail et variables.

    Pourquoi : dbt échoue silencieusement si les répertoires cibles n'existent pas
    ou si les variables d'environnement ne sont pas définies.

    Raises
    ------
    OSError
        Si la création des répertoires échoue (permissions insuffisantes).

    - Crée ``config.GOLD_DIR`` et ``config.DUCKDB_EXT_DIR`` (parents créés si
      besoin).
    - Définit ``REVIEWPULSE_GOLD_DB`` et ``REVIEWPULSE_DUCKDB_EXT_DIR`` avec les
      chemins absolus configurés.
    """
    # Pourquoi : parents=True permet de créer la hiérarchie complète en un appel,
    # exist_ok=True évite l'échec si le répertoire existe déjà (idempotence).
    config.GOLD_DIR.mkdir(parents=True, exist_ok=True)
    config.DUCKDB_EXT_DIR.mkdir(parents=True, exist_ok=True)

    # Pourquoi : journalisation des répertoires créés pour tracer l'environnement.
    log.info(
        "Répertoires créés : GOLD_DIR=%s, DUCKDB_EXT_DIR=%s",
        config.GOLD_DIR,
        config.DUCKDB_EXT_DIR,
    )

    os.environ["REVIEWPULSE_GOLD_DB"] = str(config.GOLD_DB)
    os.environ["REVIEWPULSE_DUCKDB_EXT_DIR"] = str(config.DUCKDB_EXT_DIR)

    # Pourquoi : journalisation des variables d'environnement pour débogage.
    log.info(
        "Variables d'environnement définies : REVIEWPULSE_GOLD_DB=%s, REVIEWPULSE_DUCKDB_EXT_DIR=%s",
        config.GOLD_DB,
        config.DUCKDB_EXT_DIR,
    )


def run_dbt(*command: str) -> dbtRunnerResult:
    """Exécute une commande dbt via l'API Python.

    Rôle : invoquer dbt avec les paramètres configurés et les variables Iceberg.

    Pourquoi : l'API Python permet de capturer le résultat structuré et de tester
    les codes de retour sans parser la sortie texte.

    Parameters
    ----------
    *command : str
        Séquence de sous‑commandes dbt (ex. ``'build'`` ou ``'docs', 'generate'``).

    Returns
    -------
    dbtRunnerResult
        Objet résultat retourné par :class:`dbtRunner`.

    Raises
    ------
    Exception
        Si dbtRunner lève une exception durant l'exécution.
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

    # Pourquoi : journalisation de la commande complète pour tracer l'exécution.
    log.info("Commande dbt : %s", " ".join(command))

    runner = dbtRunner()
    result = runner.invoke(args)
    return result


def main() -> int:
    """Orchestration du pipeline *gold*.

    Rôle : exécuter dbt build puis générer la documentation, avec codes de retour
    compatibles Airflow.

    Pourquoi : garantir que la couche gold est construite et documentée avant
    l'analyse, et signaler les échecs à l'orchestrateur.

    Returns
    -------
    int
        ``0`` si tout s'est bien passé, ``1`` sinon.

    Raises
    ------
    Exception
        Si une erreur non capturée survient durant l'exécution.

    - Exécute ``dbt build`` et journalise le comptage des statuts.
    - En cas d'échec, journalise l'erreur et renvoie ``1``.
    - Génère la documentation avec ``dbt docs generate``.
    - Journalise le chemin du fichier DuckDB final.
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

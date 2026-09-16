"""Rôle
    Automatiser la chaîne de traitement ReviewPulse : quotidien : ingest → spark_silver → gx_validate → score ; hebdomadaire : train → score.

Place dans la chaîne
    Le DAG quotidien orchestre les quatre premières étapes de la chaîne ; le DAG hebdomadaire orchestre l’entraînement puis le scoring, qui alimentent le tableau de bord et l’API.

Fonctionnement
    - Deux DAGs sont définis : ``reviewpulse_daily`` (planifié ``0 6 * * *``) et ``reviewpulse_weekly_train`` (planifié ``0 7 * * 1``).
    - Chaque tâche est un ``ExternalPythonOperator`` qui exécute la fonction autonome ``_run_module`` dans l’interpréteur du projet ReviewPulse.
    - Les dépendances sont linéaires : ``ingest`` → ``spark_silver`` → ``gx_validate`` → ``score`` pour le quotidien, et ``train`` → ``score`` pour le hebdomadaire.
    - Le module ``reviewpulse.transform`` reste disponible en ligne de commande comme moteur de référence, mais n’est plus invoqué dans le DAG quotidien.

Choix de conception
    - Utilisation d’``ExternalPythonOperator`` afin d’isoler l’exécution du code métier dans un environnement Python distinct (voir ADR 0013). L’interpréteur du projet est fourni par la variable d’environnement ``REVIEWPULSE_PYTHON`` (défaut ``/opt/rp-venv/bin/python``) définie dans le Dockerfile.
    - Fonction autonome ``_run_module`` qui charge dynamiquement le module métier via ``importlib`` et lève ``RuntimeError`` si le code de retour n’est pas nul, garantissant une gestion d’erreur centralisée sans dépendre du module ``reviewpulse`` dans le processus Airflow.
    - Deux nouvelles tentatives à 5 minutes et aucun rattrapage, conformément à la décision d’orchestration. ADR 0011.
    - Limitation à une exécution simultanée (``max_active_runs=1``) pour chaque DAG : constaté le 16/09/2026 que la réactivation d’un DAG crée l’exécution planifiée de la dernière période, qui s’exécute en même temps qu’un déclenchement manuel ; deux exécutions parallèles écriraient les mêmes fichiers, d’où le besoin de ce verrou. ADR 0011.

Preuves
    - Trois exécutions réussies du DAG quotidien et une du DAG hebdomadaire dans Airflow le 16/09/2026 après alignement de l’uid. ADR 0011.

Tests associés
    Aucun test dédié n’est fourni dans le répertoire ``tests/`` pour ce module.
"""

import logging
import os

import pendulum
from airflow import DAG
from airflow.operators.python import ExternalPythonOperator

logger = logging.getLogger(__name__)

# Chemin de l’interpréteur du projet ReviewPulse
RP_PYTHON = os.environ.get("REVIEWPULSE_PYTHON", "/opt/rp-venv/bin/python")


def _run_module(module_name: str) -> None:
    """Charge dynamiquement *module_name* et exécute ``module.main()``.

    Le code de retour de ``module.main()`` doit être 0 ; sinon, une
    ``RuntimeError`` est levée.

    Args
        module_name: Nom complet du module à exécuter (ex. ``reviewpulse.ingest``).

    Raises
        RuntimeError: Si le code de retour n’est pas nul.
    """
    try:
        import importlib

        module = importlib.import_module(module_name)
        result = module.main()
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors de l'exécution de %s.main()", module_name)
        raise RuntimeError(str(exc)) from exc

    if result != 0:
        raise RuntimeError(f"{module_name}.main() a renvoyé {result}")


# ---------------------------------------------------------------------------
# DAG quotidien : ingestion → spark_silver → validation GX → scoring
# ---------------------------------------------------------------------------

default_args_daily = {
    "start_date": pendulum.datetime(2026, 9, 1, tz="UTC"),
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "tags": ["reviewpulse"],
}

with DAG(
    dag_id="reviewpulse_daily",
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args_daily,
) as dag_daily:

    ingest_task = ExternalPythonOperator(
        task_id="ingest",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.ingest"],
        expect_airflow=False,
    )

    spark_silver_task = ExternalPythonOperator(
        task_id="spark_silver",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.spark_silver"],
        expect_airflow=False,
    )

    gx_validate_task = ExternalPythonOperator(
        task_id="gx_validate",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.expectations"],
        expect_airflow=False,
    )

    score_task = ExternalPythonOperator(
        task_id="score",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.score"],
        expect_airflow=False,
    )

    ingest_task >> spark_silver_task >> gx_validate_task >> score_task

# ---------------------------------------------------------------------------
# DAG hebdomadaire : entraînement → scoring
# ---------------------------------------------------------------------------

default_args_weekly = {
    "start_date": pendulum.datetime(2026, 9, 1, tz="UTC"),
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "tags": ["reviewpulse"],
}

with DAG(
    dag_id="reviewpulse_weekly_train",
    schedule="0 7 * * 1",
    catchup=False,
    max_active_runs=1,
    default_args=default_args_weekly,
) as dag_weekly:

    train_task = ExternalPythonOperator(
        task_id="train",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.train"],
        expect_airflow=False,
    )

    score_task_weekly = ExternalPythonOperator(
        task_id="score",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.score"],
        expect_airflow=False,
    )

    train_task >> score_task_weekly

# Export des DAGs pour qu'Airflow les découvre
reviewpulse_daily = dag_daily
reviewpulse_weekly_train = dag_weekly

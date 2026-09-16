"""Orchestration des DAGs ReviewPulse.

Ce module définit deux DAGs Airflow :
- ``reviewpulse_daily`` : ingestion → transformation & contrôle → scoring.
- ``reviewpulse_weekly_train`` : entraînement du modèle → scoring.

Les tâches appellent les fonctions ``main()`` des modules correspondants.
Un code de retour non nul lève ``AirflowException`` pour signaler l’échec.
"""

import logging

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException

# Import des modules métier
from reviewpulse import ingest, transform, score, train

logger = logging.getLogger(__name__)

def _run_main(module):
    """Exécute ``module.main()`` et lève ``AirflowException`` si le code retour n'est pas 0."""
    try:
        result = module.main()
    except Exception as exc:  # pragma: no cover
        logger.exception("Erreur lors de l'exécution de %s.main()", module.__name__)
        raise AirflowException(str(exc)) from exc
    if result != 0:
        raise AirflowException(f"{module.__name__}.main() a retourné {result}")
    return result

# ---------------------------------------------------------------------------
# DAG quotidien : ingestion → transformation & contrôle → scoring
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
    default_args=default_args_daily,
) as dag_daily:

    ingest_task = PythonOperator(
        task_id="ingest",
        python_callable=_run_main,
        op_args=[ingest],
    )

    transform_task = PythonOperator(
        task_id="transform_and_check",
        python_callable=_run_main,
        op_args=[transform],
    )

    score_task = PythonOperator(
        task_id="score",
        python_callable=_run_main,
        op_args=[score],
    )

    ingest_task >> transform_task >> score_task

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
    default_args=default_args_weekly,
) as dag_weekly:

    train_task = PythonOperator(
        task_id="train",
        python_callable=_run_main,
        op_args=[train],
    )

    score_task_weekly = PythonOperator(
        task_id="score",
        python_callable=_run_main,
        op_args=[score],
    )

    train_task >> score_task_weekly

# Export des DAGs pour qu'Airflow les découvre
reviewpulse_daily = dag_daily
reviewpulse_weekly_train = dag_weekly

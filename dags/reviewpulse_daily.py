"""Rôle
    Automatiser la chaîne de traitement ReviewPulse : quotidien : ingest → transform_and_check → score ; hebdomadaire : train → score.

Place dans la chaîne
    Le DAG quotidien orchestre les trois premières étapes de la chaîne ; le DAG hebdomadaire orchestre l’entraînement puis le scoring, qui alimentent le tableau de bord et l’API.

Fonctionnement
    - Deux DAGs sont définis : ``reviewpulse_daily`` (planifié ``0 6 * * *``) et ``reviewpulse_weekly_train`` (planifié ``0 7 * * 1``).
    - Chaque tâche est un ``PythonOperator`` qui exécute la fonction interne ``_run_main`` avec le module métier correspondant (``ingest``, ``transform``, ``score`` ou ``train``).
    - Les dépendances sont linéaires : ``ingest`` → ``transform_and_check`` → ``score`` pour le quotidien, et ``train`` → ``score`` pour le hebdomadaire.
    - Les DAGs sont créés avec ``catchup=False`` et les mêmes ``default_args`` (retries = 2, retry_delay = 5 min, tags = ["reviewpulse"]).

Choix de conception
    - Utilisation d’une fonction interne ``_run_main`` pour appeler ``module.main()`` et lever ``AirflowException`` en cas de code de retour non nul, afin d’éviter la duplication de logique dans chaque ``PythonOperator``. ADR 0011.
    - Deux nouvelles tentatives à 5 minutes et aucun rattrapage, conformément à la décision d’orchestration. ADR 0011.
    - Limitation à une exécution simultanée (``max_active_runs=1``) pour chaque DAG : constaté le 16/09/2026 que la réactivation d’un DAG crée l’exécution planifiée de la dernière période, qui s’exécute en même temps qu’un déclenchement manuel ; deux exécutions parallèles écriraient les mêmes fichiers, d’où le besoin de ce verrou. ADR 0011.

Preuves
    - Trois exécutions réussies du DAG quotidien et une du DAG hebdomadaire dans Airflow le 16/09/2026 après alignement de l’uid. ADR 0011.

Tests associés
    Aucun test dédié n’est fourni dans le répertoire ``tests/`` pour ce module.
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
    """Exécute ``module.main()`` et lève ``AirflowException`` si le code retour n'est pas 0.

    Args
        module (module): Le module métier dont la fonction ``main`` doit être appelée.

    Returns
        int: Le code de retour de ``module.main()`` (0 si aucune exception n’est levée).

    Raises
        AirflowException: Si une exception est interceptée lors de l’appel ou si le code de retour n’est pas 0.

    Pourquoi
        Centraliser la logique d’appel et de gestion d’erreur afin d’éviter la duplication de code dans chaque ``PythonOperator``.
    """
    try:
        result = module.main()
    except Exception as exc:  # pragma: no cover
        # Journalise l’erreur avec le nom du module pour faciliter le débogage.
        logger.exception("Erreur lors de l'exécution de %s.main()", module.__name__)
        raise AirflowException(str(exc)) from exc
    if result != 0:
        # Un code de retour différent de 0 indique un échec métier.
        raise AirflowException(f"{module.__name__}.main() a retourné {result}")
    return result

# ---------------------------------------------------------------------------
# DAG quotidien : ingestion → transformation & contrôle → scoring
# ---------------------------------------------------------------------------

# Paramètres communs au DAG quotidien (date de départ, politique de retry, tags)
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
    max_active_runs=1,  # Limite à une exécution simultanée pour éviter les conflits de fichiers (voir ADR 0011)
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

    # Chaînage séquentiel des tâches
    ingest_task >> transform_task >> score_task

# ---------------------------------------------------------------------------
# DAG hebdomadaire : entraînement → scoring
# ---------------------------------------------------------------------------

# Paramètres communs au DAG hebdomadaire (identiques au quotidien pour la cohérence)
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
    max_active_runs=1,  # Limite à une exécution simultanée pour éviter les conflits de fichiers (voir ADR 0011)
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

    # L'entraînement doit précéder le scoring de la semaine
    train_task >> score_task_weekly

# Export des DAGs pour qu'Airflow les découvre
reviewpulse_daily = dag_daily
reviewpulse_weekly_train = dag_weekly

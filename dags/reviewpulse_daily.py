# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
"""Rôle
    Automatiser la chaîne de traitement ReviewPulse :
    quotidien : ingest → spark_silver → gx_validate → score → gold (dbt) ;
    hebdomadaire : train → score → gold (dbt).

Place dans la chaîne
    Le DAG quotidien enchaîne toute la chaîne jusqu'à la zone gold ; le DAG hebdomadaire réentraîne le modèle, rescore et reconstruit la zone gold. L'API et le tableau de bord lisent les fichiers Parquet produits par le score ; la zone gold (DuckDB) sert l'analyse et la documentation dbt.

Fonctionnement
    - Deux DAGs sont définis : ``reviewpulse_daily`` (planifié ``0 6 * * *``) et ``reviewpulse_weekly_train`` (planifié ``0 7 * * 1``).
    - Chaque tâche est un ``ExternalPythonOperator`` qui exécute la fonction autonome ``_run_module`` dans l’interpréteur du projet ReviewPulse.
    - Les dépendances sont linéaires : ``ingest`` → ``spark_silver`` → ``gx_validate`` → ``score`` → ``gold`` pour le quotidien,
      et ``train`` → ``score`` → ``gold`` pour le hebdomadaire.
    - Le module ``reviewpulse.transform`` reste disponible en ligne de commande comme moteur de référence,
      mais n’est plus invoqué dans les DAGs.

Choix de conception
    - Utilisation d’``ExternalPythonOperator`` afin d’isoler l’exécution du code métier dans un environnement Python distinct
      (voir ADR 0013). L’interpréteur du projet est fourni par la variable d’environnement ``REVIEWPULSE_PYTHON``
      (défaut ``/opt/rp-venv/bin/python``) définie dans le Dockerfile.
    - Fonction autonome ``_run_module`` qui charge dynamiquement le module métier via ``importlib`` et lève ``RuntimeError``
      si le code de retour n’est pas nul, garantissant une gestion d’erreur centralisée sans dépendre du module ``reviewpulse``
      dans le processus Airflow.
    - Deux nouvelles tentatives à 5 minutes et aucun rattrapage, conformément à la décision d’orchestration. ADR 0011.
    - Limitation à une exécution simultanée (``max_active_runs=1``) pour chaque DAG : constaté le 16/09/2026 que la réactivation d’un DAG crée
      l’exécution planifiée de la dernière période, qui s’exécute en même temps qu’un déclenchement manuel ; deux exécutions parallèles écriraient les mêmes fichiers,
      d’où le besoin de ce verrou. ADR 0011.
    - Ajout d’alertes simples : ``_alert_on_failure`` et ``_alert_on_sla_miss`` (voir ci‑dessous). En production ces fonctions appelleraient le canal de l’équipe
      (ex. Slack, email). Dans la démo le canal d’alerte est le journal d’Airflow.
    - La tâche ``gold`` s'exécute après ``score`` : le test dbt ``assert_every_review_is_scored`` exige une prédiction pour chaque avis de la zone silver ; placé avant le score, dbt échouerait après chaque reconstruction de la zone silver.

Preuves
    Trois exécutions réussies du DAG quotidien et une du DAG hebdomadaire le 16/09/2026 (ADR 0011).
    Exécution manuelle spark_v3 du 17/09/2026 : ingest, spark_silver, gx_validate et score en succès dans Airflow,
    après correction de l’interpréteur des workers Spark (voir ``spark_silver.build_spark``).

Tests associés
    Pas de test unitaire : Airflow n’est pas installé dans l’environnement du projet (ADR 0013).
    La preuve est l’exécution réelle dans le conteneur Airflow, consignée dans ``docs/evidence``.

Décision appliquée ici : ADR 0017 — Airflow sur PostgreSQL, pour que le planificateur survive à l'accès concurrent.

Pourquoi
    Automatiser la chaîne pour que les données restent fraîches sans intervention manuelle, et pour que le modèle soit réentraîné périodiquement. Le DAG quotidien garantit que la zone gold est reconstruite après chaque score, et le DAG hebdomadaire maintient le modèle à jour.

Limites connues
    Pas de test unitaire (Airflow absent de l'environnement du projet, ADR 0013). Les alertes écrivent dans le journal d'Airflow, pas dans un canal externe. Le court-circuit de dérive ne déclenche le réentraînement que si le rapport de drift est lisible et lève une alerte. La tâche gold dépend de score pour que le test dbt ``assert_every_review_is_scored`` passe.
"""

import json
import logging
import os
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.python import ExternalPythonOperator, ShortCircuitOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

logger = logging.getLogger(__name__)

# Chemin de l’interpréteur du projet ReviewPulse
# Pourquoi : ExternalPythonOperator exécute le code dans un interpréteur séparé ;
# cette variable permet de pointer l'environnement du projet sans modifier le code.
RP_PYTHON = os.environ.get("REVIEWPULSE_PYTHON", "/opt/rp-venv/bin/python")


def _run_module(module_name: str) -> None:
    """Charge dynamiquement *module_name* et exécute ``module.main()``.

    Pourquoi : isoler l'exécution du code métier dans un interpréteur distinct,
    sans dépendre du module ``reviewpulse`` dans le processus Airflow.

    Le code de retour de ``module.main()`` doit être 0 ; sinon, une
    ``RuntimeError`` est levée.

    Args
        module_name: Nom complet du module à exécuter (ex. ``reviewpulse.ingest``).

    Returns
        None

    Raises
        RuntimeError: Si le code de retour n’est pas nul.
    """
    import logging

    logging.getLogger(__name__).info("Début de l'exécution de %s.main()", module_name)

    try:
        import importlib

        module = importlib.import_module(module_name)
        result = module.main()
    except Exception as exc:  # pragma: no cover
        # `logger` du module n'existe pas ici : ExternalPythonOperator n'expédie que le
        # code de cette fonction dans un interpréteur séparé (constaté le 19/09/2026,
        # « NameError: name 'logger' is not defined » masquant l'erreur réelle).
        logging.getLogger(__name__).exception(
            "Erreur lors de l'exécution de %s.main()", module_name
        )
        raise RuntimeError(str(exc)) from exc

    logging.getLogger(__name__).info("Fin de l'exécution de %s.main(), code %s", module_name, result)

    if result != 0:
        raise RuntimeError(f"{module_name}.main() a renvoyé {result}")


def _run_module_avec_args(module_name: str, argv: list) -> None:
    """Comme ``_run_module``, mais transmet *argv* à ``module.main()``.

    Pourquoi : un module dont ``main`` analyse des arguments ne peut pas lire
    ``sys.argv`` ici — il appartient au processus lancé par Airflow, pas au module.

    Args
        module_name: Nom complet du module à exécuter.
        argv: Liste des arguments à transmettre à ``module.main()``.

    Returns
        None

    Raises
        RuntimeError: Si le code de retour n’est pas nul.
    """
    import logging

    logging.getLogger(__name__).info("Début de l'exécution de %s.main(%s)", module_name, argv)

    try:
        import importlib

        module = importlib.import_module(module_name)
        result = module.main(argv)
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).exception(
            "Erreur lors de l'exécution de %s.main(%s)", module_name, argv
        )
        raise RuntimeError(str(exc)) from exc

    logging.getLogger(__name__).info("Fin de l'exécution de %s.main(%s), code %s", module_name, argv, result)

    if result != 0:
        raise RuntimeError(f"{module_name}.main({argv}) a renvoyé {result}")


# ---------------------------------------------------------------------------
# Alertes (exécutées dans le processus Airflow, aucun import de reviewpulse)
# ---------------------------------------------------------------------------

def _alert_on_failure(context: dict) -> None:
    """Journalise en ERROR lorsqu’une tâche échoue.

    Pourquoi : callback Airflow ; le journal d'Airflow est le canal d'alerte de la démo.

    Args
        context: Dictionnaire de contexte fourni par Airflow.

    Returns
        None

    Raises
        Aucune
    """
    ti = context["task_instance"]
    logger.error(
        "ALERTE ReviewPulse : tâche %s en échec (exécution %s, tentative %s)",
        ti.task_id,
        context.get("run_id", "unknown"),
        ti.try_number,
    )


def _alert_on_sla_miss(
    dag,
    task_list,
    blocking_task_list,
    slas,
    blocking_tis,
) -> None:
    """Journalise en ERROR lorsqu’un SLA est dépassé.

    Pourquoi : callback SLA ; le journal d'Airflow est le canal d'alerte de la démo.

    Args
        dag: Objet DAG concerné.
        task_list: Liste des tâches en retard.
        blocking_task_list: Liste des tâches bloquantes.
        slas: Détails des SLA manqués.
        blocking_tis: Instances de tâches bloquantes.

    Returns
        None

    Raises
        Aucune
    """
    logger.error(
        "ALERTE ReviewPulse : SLA dépassé pour %s : %s",
        dag.dag_id,
        task_list,
    )


# ---------------------------------------------------------------------------
# DAG quotidien : ingestion → spark_silver → validation GX → scoring → gold (dbt)
# ---------------------------------------------------------------------------

default_args_daily = {
    "start_date": pendulum.datetime(2026, 9, 1, tz="UTC"),
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "on_failure_callback": _alert_on_failure,
    # L'exécution complète dure moins de 2 minutes en local (mesure du 17/09/2026) ;
    # au-delà d'une heure, quelque chose est bloqué.
    "sla": pendulum.duration(hours=1),
}

def _derive_exige_reentrainement() -> bool:
    """Lit le rapport de drift et renvoie True si une alerte est levée.

    Pourquoi : le court-circuit doit décider sans bloquer le DAG ; en cas d'erreur
    de lecture, on ne déclenche pas de réentraînement (fail-closed).

    La lecture utilise uniquement la bibliothèque standard car l’interpréteur
    Airflow ne possède pas les dépendances du projet (voir ADR 0013).

    Args
        Aucun

    Returns
        bool: True si une alerte de dérive est levée, False sinon.

    Raises
        Aucune (toutes les exceptions sont capturées)
    """
    data_dir = os.environ.get("REVIEWPULSE_DATA_DIR", "/data")
    report_file = Path(data_dir) / "scored" / "drift_report.json"
    import logging

    logging.getLogger(__name__).info("Lecture du rapport de dérive %s", report_file)

    try:
        with report_file.open("r") as f:
            rapport = json.load(f)
        alerte = rapport.get("alerte", {}).get("alerte", False)
        if alerte:
            motifs = rapport.get("alerte", {}).get("motifs", [])
            logging.getLogger(__name__).info("Alerte de dérive levée : %s", motifs)
        logging.getLogger(__name__).info("Décision de réentraînement : %s", bool(alerte))
        return bool(alerte)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Impossible de lire le rapport de dérive %s : %s", report_file, exc
        )
        return False


with DAG(
    dag_id="reviewpulse_daily",
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args_daily,
    tags=["reviewpulse"],
    sla_miss_callback=_alert_on_sla_miss,
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

    drift_task = ExternalPythonOperator(
        task_id="drift",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.drift"],
        expect_airflow=False,
    )

    gold_task = ExternalPythonOperator(
        task_id="gold",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.gold"],
        expect_airflow=False,
    )

    # Le court-circuit est place en derivation : la zone gold n'est jamais sautee.
    derive_gate = ShortCircuitOperator(
        task_id="derive_exige_reentrainement",
        python_callable=_derive_exige_reentrainement,
    )

    trigger_train = TriggerDagRunOperator(
        task_id="declencher_reentrainement",
        trigger_dag_id="reviewpulse_weekly_train",
        wait_for_completion=False,
        reset_dag_run=True,
    )

    # Porte de qualité sur les zones silver et gold, après la construction de la zone gold.
    gx_lake_task = ExternalPythonOperator(
        task_id="gx_lake",
        python=RP_PYTHON,
        python_callable=_run_module_avec_args,
        op_args=["reviewpulse.expectations_lake", ["--zone", "toutes"]],
        expect_airflow=False,
    )

    ingest_task >> spark_silver_task >> gx_validate_task >> score_task >> drift_task >> gold_task >> gx_lake_task
    drift_task >> derive_gate >> trigger_train

# ---------------------------------------------------------------------------
# DAG hebdomadaire : entraînement → scoring → gold (dbt)
# ---------------------------------------------------------------------------

default_args_weekly = {
    "start_date": pendulum.datetime(2026, 9, 1, tz="UTC"),
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
    "on_failure_callback": _alert_on_failure,
}

with DAG(
    dag_id="reviewpulse_weekly_train",
    schedule="0 7 * * 1",
    catchup=False,
    max_active_runs=1,
    default_args=default_args_weekly,
    tags=["reviewpulse"],
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

    gold_task_weekly = ExternalPythonOperator(
        task_id="gold",
        python=RP_PYTHON,
        python_callable=_run_module,
        op_args=["reviewpulse.gold"],
        expect_airflow=False,
    )

    train_task >> score_task_weekly >> gold_task_weekly

# Export des DAGs pour qu'Airflow les découvre
reviewpulse_daily = dag_daily
reviewpulse_weekly_train = dag_weekly

# Image Airflow de ReviewPulse.
#
# Deux environnements Python dans la même image, volontairement séparés :
#   - celui d'Airflow, laissé intact : Airflow 2.10 exige SQLAlchemy < 2.0 ;
#   - /opt/rp-venv pour le projet : MLflow 3, PyIceberg et dbt tirent SQLAlchemy 2.0 et protobuf 6.
# Installer le projet dans l'environnement d'Airflow remplaçait SQLAlchemy par la 2.0 (constaté
# par pip le 16/09/2026). Les tâches s'exécutent donc via ExternalPythonOperator (voir ADR 0013).
#
# Pourquoi « slim » : l'image complète embarque des fournisseurs (Google, Snowflake, Azure…)
# inutiles au projet et source de conflits supplémentaires.
FROM apache/airflow:slim-2.10.3-python3.11

# Java 17 : minimum exigé par PySpark 4 ; la base est Debian 12, sans Java 21 (vérifié le 16/09/2026).
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/rp-venv \
    && chown -R airflow:root /opt/rp-venv

USER airflow

COPY --chown=airflow:root pyproject.toml requirements.txt /opt/reviewpulse/
COPY --chown=airflow:root src/ /opt/reviewpulse/src/

# Le projet s'installe UNIQUEMENT dans /opt/rp-venv. La ligne « -e . » de requirements.txt
# vise la racine du dépôt : on la retire et on installe le paquet depuis /opt/reviewpulse.
# Les deux « pip check » garantissent que chaque environnement est cohérent.
RUN set -eux; \
    grep -v -e '^-e' /opt/reviewpulse/requirements.txt > /tmp/requirements-projet.txt; \
    /opt/rp-venv/bin/pip install --no-cache-dir --upgrade pip; \
    /opt/rp-venv/bin/pip install --no-cache-dir -r /tmp/requirements-projet.txt; \
    /opt/rp-venv/bin/pip install --no-cache-dir /opt/reviewpulse; \
    /opt/rp-venv/bin/pip check; \
    pip check

# Chemin de l'interpréteur du projet, lu par les DAG.
ENV REVIEWPULSE_PYTHON=/opt/rp-venv/bin/python

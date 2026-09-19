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
# ADR 0018 : empreinte relevee le 19/09/2026 ; voir docker/Dockerfile pour la raison.
FROM apache/airflow:slim-2.10.3-python3.11@sha256:18eaa3e186eb833925d534f55c67f7e4ba488dcc9d8098495de5485c778fb400

# Java 17 : minimum exigé par PySpark 4 ; la base est Debian 12, sans Java 21 (vérifié le 16/09/2026).
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/rp-venv \
    && mkdir -p /opt/duckdb_extensions \
    && chown -R airflow:root /opt/rp-venv /opt/duckdb_extensions

USER airflow

# L'image slim ne contient pas le pilote PostgreSQL (psycopg2). Le scheduler d'Airflow en a besoin pour se connecter à la base de données.
RUN pip install --no-cache-dir "psycopg2-binary==2.9.10"

# Le projet s'installe UNIQUEMENT dans /opt/rp-venv. La ligne « -e . » de requirements.txt
# vise la racine du dépôt : on la retire, les dépendances d'abord, le paquet ensuite.
# Ordre des couches : la couche des dépendances (environ 3 Go) ne doit pas dépendre du code,
# sinon chaque modification la reconstruit et remplit le cache (disque plein le 16/09/2026).
COPY --chown=airflow:root requirements.txt /opt/reviewpulse/
RUN set -eux; \
    grep -v -e '^-e' /opt/reviewpulse/requirements.txt > /tmp/requirements-projet.txt; \
    /opt/rp-venv/bin/pip install --no-cache-dir --upgrade pip; \
    /opt/rp-venv/bin/pip install --no-cache-dir -r /tmp/requirements-projet.txt

# Extension iceberg de DuckDB préinstallée : la tâche gold (dbt) fonctionne sans réseau.
RUN /opt/rp-venv/bin/python -c "import duckdb; c = duckdb.connect(); c.execute(\"SET extension_directory='/opt/duckdb_extensions'\"); c.execute('INSTALL iceberg')"

# Code du projet, installé sans dépendances. Les deux « pip check » garantissent que chaque
# environnement (Airflow, projet) reste cohérent.
COPY --chown=airflow:root pyproject.toml /opt/reviewpulse/
COPY --chown=airflow:root src/ /opt/reviewpulse/src/
COPY --chown=airflow:root dbt/ /opt/reviewpulse/dbt/
RUN set -eux; \
    /opt/rp-venv/bin/pip install --no-cache-dir --no-deps /opt/reviewpulse; \
    /opt/rp-venv/bin/pip check; \
    pip check

# Interpréteur du projet (lu par les DAG), projet dbt et extensions DuckDB de la couche gold.
ENV REVIEWPULSE_PYTHON=/opt/rp-venv/bin/python \
    REVIEWPULSE_DBT_DIR=/opt/reviewpulse/dbt \
    REVIEWPULSE_DUCKDB_EXT_DIR=/opt/duckdb_extensions

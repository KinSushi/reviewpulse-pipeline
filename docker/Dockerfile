# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
# ADR 0018 : image de base epinglee par empreinte : une etiquette peut changer de contenu,
# une empreinte non. Relevee le 19/09/2026 par `docker buildx imagetools inspect`.
FROM python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9

# Utilisateur non root « app » (uid 1000). Un nom est indispensable : Hadoop, utilisé par Spark,
# refuse de démarrer si l'uid courant n'a pas de nom (constaté le 16/09/2026).
# Java 21 : exigé par PySpark 4 pour le job spark_silver (Debian 13 le propose).
RUN useradd -m -u 1000 -s /bin/bash app \
    && apt-get update \
    && apt-get install -y --no-install-recommends openjdk-21-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Ordre des couches : dépendances d'abord, code ensuite.
# Pourquoi : la couche des dépendances pèse environ 3 Go (Spark, MLflow, dbt, Great Expectations).
# Quand le code était copié avant elle, chaque modification du code la reconstruisait et laissait
# une copie de plus dans le cache de construction : 24 Go de cache et disque plein le 16/09/2026.
# La ligne « -e . » de requirements.txt vise le code : elle est installée après la copie, sans dépendances.
COPY requirements.txt ./
RUN grep -v -e '^-e' requirements.txt > /tmp/requirements-deps.txt \
    && pip install --no-cache-dir -r /tmp/requirements-deps.txt

# Extension iceberg de DuckDB téléchargée à la construction : la couche gold (dbt) lit les tables
# Iceberg sans accès réseau à l'exécution.
RUN python -c "import duckdb; c = duckdb.connect(); c.execute(\"SET extension_directory='/opt/duckdb_extensions'\"); c.execute('INSTALL iceberg')"

# Code du projet : seule cette partie est reconstruite quand le code change.
COPY pyproject.toml ./
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY dbt/ ./dbt/
RUN pip install --no-cache-dir --no-deps -e . && pip check

# Variables d'environnement
ENV REVIEWPULSE_DATA_DIR=/data \
    REVIEWPULSE_DBT_DIR=/app/dbt \
    REVIEWPULSE_DUCKDB_EXT_DIR=/opt/duckdb_extensions \
    MLFLOW_TRACKING_URI=http://mlflow:5000 \
    PYTHONUNBUFFERED=1

# Ports exposés
EXPOSE 8000 8501

# L'utilisateur non-root doit pouvoir écrire ses données, et MLflow crée un dossier ./mlruns vide dans le dossier courant dès qu'il ouvre une base SQLite locale.
RUN mkdir -p /data && chown -R app:app /app /data

# Exécution de l'application
USER app
CMD ["uvicorn", "reviewpulse.api:app", "--host", "0.0.0.0", "--port", "8000"]

# L'API répond 503 tant qu'aucun modèle champion n'existe, ce qui marque le conteneur unhealthy de façon voulue.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request, sys; \
    sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

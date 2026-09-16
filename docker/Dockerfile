FROM python:3.11-slim

# Crée l'utilisateur non root
RUN useradd -m -s /bin/bash app

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de configuration et du code source
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
COPY dashboard/ ./dashboard/

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Variables d'environnement
ENV REVIEWPULSE_DATA_DIR=/app/data \
    MLFLOW_TRACKING_URI=http://mlflow:5000 \
    PYTHONUNBUFFERED=1

# Ports exposés
EXPOSE 8000 8501

# L'utilisateur non-root doit pouvoir écrire ses données, et MLflow crée un dossier ./mlruns vide dans le dossier courant dès qu'il ouvre une base SQLite locale.
RUN mkdir -p /app/data && chown -R app:app /app

# Exécution de l'application
USER app
CMD ["uvicorn", "reviewpulse.api:app", "--host", "0.0.0.0", "--port", "8000"]

# L'API répond 503 tant qu'aucun modèle champion n'existe, ce qui marque le conteneur unhealthy de façon voulue.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request, sys; \
    sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

## Aide (cible par défaut, liste toutes les cibles avec une courte description)
.PHONY: help install lint test ingest transform quality train score pipeline api dashboard up jobs airflow down reverse forward evidence gx spark gold drift

help:
	@echo "Cibles du Makefile :"
	@echo "  help      - Affiche cette aide (cible par défaut)"
	@echo "  install   - Installe les dépendances de développement"
	@echo "  lint      - Analyse le code avec ruff (src, tests, dags, dashboard, tools)"
	@echo "  test      - Exécute la suite de tests avec pytest"
	@echo "  ingest    - Lance l'ingestion des données brutes"
	@echo "  transform - Transforme les données brutes en données propres"
	@echo "  quality   - Effectue les contrôles de qualité des données"
	@echo "  gx        - Exécute la suite Great Expectations sur la zone propre et génère le rapport HTML sous data/quality_reports/gx"
	@echo "  spark     - Construit la zone silver avec PySpark et l'écrit en table Iceberg"
	@echo "  train     - Entraîne le modèle et l'enregistre dans MLflow"
	@echo "  score     - Calcule les scores avec le modèle champion"
	@echo "  gold      - Construit la zone gold (dbt + DuckDB : modèles, tests, contrats, documentation)"
	@echo "  pipeline  - Exécute ingest → spark → gx → train → score → gold"
	@echo "  api       - Démarre le serveur FastAPI en mode reload"
	@echo "  dashboard - Lance le tableau de bord Streamlit"
	@echo "  up        - Construit et démarre les services Docker (mlflow, api, dashboard)"
	@echo "  jobs      - Exécute le job pipeline dans Docker (profil jobs)"
	@echo "  airflow   - Démarre les services Airflow (profil airflow)"
	@echo "  down      - Arrête les services Docker (profils jobs et airflow)"
	@echo "  reverse   - Exécute les tests inverses et génère le rapport docs/evidence/reverse_tests.md"
	@echo "  forward   - Vérifie la stack déployée et génère le rapport docs/evidence/forward_test.md"
	@echo "  evidence  - Enchaîne test, reverse et forward pour produire les preuves complètes"

## Installation des dépendances de développement
install:
	pip install -r requirements-dev.txt

## Analyse du code (lint) incluant le répertoire tools
lint:
	ruff check src tests dags dashboard tools

## Exécution des tests unitaires
test:
	pytest -q

## Ingestion des données brutes
ingest:
	python -m reviewpulse.ingest

## Transformation des données brutes en données propres
transform:
	python -m reviewpulse.transform

## Contrôles de qualité des données
quality:
	python -m reviewpulse.quality

## Exécution de la suite Great Expectations
gx:
	python -m reviewpulse.expectations

## Construction de la zone silver avec PySpark et écriture en table Iceberg
spark:
	python -m reviewpulse.spark_silver

## Entraînement du modèle et enregistrement dans MLflow
train:
	python -m reviewpulse.train

## Calcul des scores avec le modèle champion
score:
	python -m reviewpulse.score

## Mesure de la dérive des entrées et des prédictions
drift:
	python -m reviewpulse.drift

## Construction de la zone gold : dbt build (modèles, tests, contrats) puis documentation
gold:
	python -m reviewpulse.gold

## Exécution complète du pipeline : ingest → spark → gx → train → score → gold
pipeline:
	$(MAKE) ingest
	$(MAKE) spark
	$(MAKE) gx
	$(MAKE) train
	$(MAKE) score
	$(MAKE) gold

## Démarrage du serveur FastAPI en mode reload
api:
	uvicorn reviewpulse.api:app --reload

## Lancement du tableau de bord Streamlit
dashboard:
	streamlit run dashboard/app.py

## Construction et démarrage des services Docker (mlflow, api, dashboard)
up:
	docker compose up -d --build mlflow api dashboard

## Exécution du job pipeline dans Docker (profil jobs)
jobs:
	docker compose --profile jobs run --rm pipeline

## Démarrage des services Airflow (profil airflow)
airflow:
	docker compose --profile airflow up -d --build airflow

## Arrêt des services Docker (profils jobs et airflow)
down:
	docker compose --profile jobs --profile airflow down

## Tests inverses : injection de défauts connus et vérification de leur détection
reverse:
	python tools/reverse_tests.py
	@echo "Rapport généré dans docs/evidence/reverse_tests.md"

## Vérification de la stack déployée : API, tableau de bord, MLflow, fichiers
forward:
	python tools/forward_test.py
	@echo "Rapport généré dans docs/evidence/forward_test.md"

## Chaîne de preuves : exécute test, reverse puis forward
evidence:
	$(MAKE) test
	$(MAKE) reverse
	$(MAKE) forward

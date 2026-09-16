## Help (default target, lists all commands)
.PHONY: help install lint test ingest transform quality train score pipeline api dashboard up jobs airflow down

help:
	@echo "Makefile targets:"
	@echo "  install   - Install development dependencies"
	@echo "  lint      - Run ruff linting on source and tests"
	@echo "  test      - Execute pytest suite"
	@echo "  ingest    - Run data ingestion"
	@echo "  transform - Run data transformation"
	@echo "  quality   - Run data quality checks"
	@echo "  train     - Train the model and log to MLflow"
	@echo "  score     - Score the dataset with the champion model"
	@echo "  pipeline  - Execute ingest → transform → train → score"
	@echo "  api       - Start FastAPI server (reload mode)"
	@echo "  dashboard - Launch Streamlit dashboard"
	@echo "  up        - Build and start Docker services (mlflow, api, dashboard)"
	@echo "  jobs      - Run pipeline job in Docker (profile jobs)"
	@echo "  airflow   - Start Airflow services (profile airflow)"
	@echo "  down      - Stop Docker services (profiles jobs and airflow)"

## Install development dependencies
install:
	pip install -r requirements-dev.txt

## Lint source code
lint:
	ruff check src tests dags dashboard

## Run tests
test:
	pytest -q

## Ingest raw data
ingest:
	python -m reviewpulse.ingest

## Transform raw data to clean data
transform:
	python -m reviewpulse.transform

## Run data quality checks
quality:
	python -m reviewpulse.quality

## Train model and log to MLflow
train:
	python -m reviewpulse.train

## Score data with the champion model
score:
	python -m reviewpulse.score

## Execute full pipeline: ingest → transform → train → score
pipeline:
	$(MAKE) ingest
	$(MAKE) transform
	$(MAKE) train
	$(MAKE) score

## Start FastAPI server with reload
api:
	uvicorn reviewpulse.api:app --reload

## Launch Streamlit dashboard
dashboard:
	streamlit run dashboard/app.py

## Build and start Docker services (mlflow, api, dashboard)
up:
	docker compose up -d --build mlflow api dashboard

## Run pipeline job in Docker (profile jobs)
jobs:
	docker compose --profile jobs run --rm pipeline

## Start Airflow services (profile airflow)
airflow:
	docker compose --profile airflow up -d --build airflow

## Stop Docker services (profiles jobs and airflow)
down:
	docker compose --profile jobs --profile airflow down

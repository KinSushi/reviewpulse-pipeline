# Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
## Aide (cible par défaut, liste toutes les cibles avec une courte description)
.PHONY: documentation portes journaux chiffres comparaison copyright convention prevol presentations help install lint test ingest transform quality train score pipeline api dashboard up jobs airflow down reverse forward evidence gx spark gold drift rollback snapshots diagrams sauvegarde-mlflow restaure-mlflow justifications briques campagne charge pipeline-gele

# Le hash du commit est transmis aux outils de preuve pour que les rapports soient traçables
REVIEWPULSE_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo inconnu)
export REVIEWPULSE_COMMIT

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
	@echo "  snapshots - Historique Iceberg (TABLE=...) ou restauration (SNAPSHOT=<id>)"
	@echo "  diagrams  - Rend les schemas Mermaid en SVG et PNG, echoue si l'un est invalide"
	@echo "  sauvegarde-mlflow / restaure-mlflow - Registre MLflow hors du volume Docker"
	@echo "  justifications - Verifie que chaque ADR est cite dans le code et dans les questions du jury"
	@echo "  briques   - Verifie que chaque exigence est classee et suivie"
	@echo "  documentation - Chaque document numerote cite par le README, aucun lien mort"
	@echo "  campagne  - Batterie puis tests inverses, sous garde de temps, journal date"
	@echo "  charge    - Essai de charge de l'API : debit, latence, taux d'erreur"
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

## Retour arrière du modèle en service
## ADR 0016 : le deploiement progressif passe par l'alias, et le retour arriere aussi.
rollback:
	python -m reviewpulse.rollback $(if $(VERSION),--vers $(VERSION),)

## Verifie que chaque decision d'architecture est justifiee la ou le jury la cherchera :
## dans le code, dans les questions-reponses, et sur les diapositives. Echoue s'il manque
## une citation ou si un renvoi pointe vers un ADR inexistant.
justifications:
	python tools/verifier_justifications.py

## Verifie que toute exigence en gras de 08_exigences_par_bloc.md est classee dans
## 18_briques_exigees.md, et que toute brique non presente porte un sujet vivant du
## registre. Ne : le 19/09/2026 une exigence dormait dans le depot sans etre vue.
briques:
	python tools/verifier_briques.py

## Verifie que chaque document numerote est cite par le README et qu aucun lien n est mort.
## Ne le 20/09/2026 : six documents manquaient a l appel, dont les trois que la consigne du
## Demo Day exige nommement -- rapport de donnees, guide de l API, runbook de deploiement.
documentation:
	sh tools/verifier_documentation.sh

## Non-regression des portes d'enrichissement : seize temoins, chaque tolerance avec le refus voisin
portes:
	sh tools/tester_portes.sh

## Aucun journal n'ecrit une donnee issue de personnes, un secret ou un jeu de donnees entier
journaux:
	sh tools/verifier_journaux.sh

## Les totaux ecrits dans les documents tournes vers le jury sont ceux du depot ; aucune case ouverte
chiffres:
	sh tools/verifier_chiffres.sh

## Banc de comparaison des familles de modeles, sur le protocole du projet (ADR 0030) ; XGBoost optionnel
## Appose la mention de droit d'auteur sur chaque fichier qui peut la porter (idempotent), puis la verifie
copyright:
	sh tools/copyright.sh apposer
	sh tools/copyright.sh verifier

## Aucune etiquette de classe ecrite en dur hors de decision.py (ADR 0009)
convention:
	sh tools/verifier_convention.sh

## Controle avant vol de la demonstration : pile levee, rechauffee et coherente ? A lancer 15 min avant de passer
prevol:
	sh tools/prevol_demo.sh

## Chaque presentation du depot s'ouvrira : XML bien forme, relations et diapositives coherentes
presentations:
	sh tools/verifier_presentations.sh

comparaison:
	python tools/comparaison_modeles.py --sortie docs/evidence/comparaison_modeles.md

## Campagne de preuves : compilation, batterie, tests inverses, chacune sous une garde
## de temps, journal date dans docs/evidence/. Ne le 19/09/2026 : une campagne a tourne
## 3 h 09 a 0,13 % de CPU sans que rien ne le montre.
campagne:
	sh tools/campagne_preuves.sh

## Essai de charge de l'API : repond a l'indicateur AIA 4 « conteneurs et orchestration
## sous charge ». Rend un code non nul si le taux d'erreur ou la latence p99 depassent
## les bornes. Exige que la stack tourne (make up).
CHARGE_URL ?= http://localhost:8000
charge:
	python tools/essai_charge.py --url $(CHARGE_URL) --concurrence $(or $(CONCURRENCE),10) --requetes $(or $(REQUETES),200)




## ADR 0018 — Sauvegarde du registre MLflow HORS du volume Docker.
## Pourquoi : le 16/09/2026, la suppression du volume `mlflow_data` a detruit le
## registre et ses artefacts ; le lac, lui, etait sur le disque et a survecu.
## SAUVEGARDE_DIR designe un repertoire de l'hote ; par defaut le lac du projet.
MLFLOW_VOLUME ?= reviewpulse_mlflow_data
SAUVEGARDE_DIR ?= $(shell pwd)/data/sauvegardes/mlflow
sauvegarde-mlflow:
	@mkdir -p "$(SAUVEGARDE_DIR)"
	@MSYS_NO_PATHCONV=1 docker run --rm -v $(MLFLOW_VOLUME):/mlflow:ro -v "$(SAUVEGARDE_DIR)":/sauvegarde alpine:3.20 	  sh -c 'tar czf /sauvegarde/mlflow_$$(date -u +%Y%m%d-%H%M%S).tar.gz -C /mlflow .'
	@ls -1 "$(SAUVEGARDE_DIR)" | tail -1 | sed 's/^/Sauvegarde ecrite : /'

## Restauration : make restaure-mlflow ARCHIVE=<nom.tar.gz> [VOLUME_CIBLE=<volume>]
## Par defaut la restauration vise un volume d'essai, jamais le registre en service :
## verifier une sauvegarde ne doit pas pouvoir detruire ce qui tourne.
VOLUME_CIBLE ?= reviewpulse_mlflow_essai
restaure-mlflow:
	@test -n "$(ARCHIVE)" || { echo "Indiquer ARCHIVE=<nom.tar.gz>"; exit 1; }
	@MSYS_NO_PATHCONV=1 docker run --rm -v $(VOLUME_CIBLE):/mlflow -v "$(SAUVEGARDE_DIR)":/sauvegarde:ro alpine:3.20 	  sh -c 'tar xzf /sauvegarde/$(ARCHIVE) -C /mlflow && ls -la /mlflow'
	@echo "Restaure dans le volume $(VOLUME_CIBLE)"

## Rend les schemas Mermaid en SVG et PNG, et echoue si l'un d'eux est invalide.
## L'outil vit dans une image ; rien n'est installe sur la machine.
DIAGRAMS_IMAGE ?= minlag/mermaid-cli:latest
diagrams:
	@for f in docs/diagrams/src/*.mmd; do 	  n=$$(basename $$f .mmd); 	  echo "  $$n"; 	  MSYS_NO_PATHCONV=1 docker run --rm -u 0 -v "$$(pwd)/docs/diagrams:/data" $(DIAGRAMS_IMAGE) -i /data/src/$$n.mmd -o /data/svg/$$n.svg >/dev/null 2>&1 || { echo "ECHEC sur $$n"; exit 1; }; 	  MSYS_NO_PATHCONV=1 docker run --rm -u 0 -v "$$(pwd)/docs/diagrams:/data" $(DIAGRAMS_IMAGE) -i /data/src/$$n.mmd -o /data/png/$$n.png >/dev/null 2>&1 || { echo "ECHEC sur $$n"; exit 1; }; 	done
	@echo "Schemas regeneres dans docs/diagrams/svg et docs/diagrams/png"

## Historique et restauration d'un instantane Iceberg : make snapshots TABLE=silver.reviews [SNAPSHOT=<id>]
TABLE ?= silver.reviews
snapshots:
	python -m reviewpulse.lakehouse --table $(TABLE) $(if $(SNAPSHOT),--restaurer $(SNAPSHOT),--historique)

## Cette cible rejoue la chaîne sans ingérer de nouvelles données, pour une démonstration reproductible
pipeline-gele:
	python -m reviewpulse.spark_silver
	python -m reviewpulse.expectations
	python -m reviewpulse.score
	python -m reviewpulse.drift
	python -m reviewpulse.gold

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
	$(MAKE) justifications
	$(MAKE) briques
	$(MAKE) test
	$(MAKE) reverse
	$(MAKE) forward

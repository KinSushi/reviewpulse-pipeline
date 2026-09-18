# Plan de monitoring — ReviewPulse

## 1. Ce que l'on surveille et pourquoi
| Décision servie | Risque de fausseté |
|-----------------|--------------------|
| **Sélection des avis négatifs à lire** (API / dashboard) | Si les données d’entrée ou le modèle dérivent, la part prédite de négatifs peut devenir incohérente avec la réalité métier (charte : ratio 0,79 – 1,21). |
| **Promotion du modèle** (DAG hebdomadaire) | Une promotion basée sur un F1 < 0,75 ou non supérieur au champion actuel violerait l’ADR 0008. |
| **Qualité des données** (zone brute → zone propre) | Un défaut bloquant (ex. colonne manquante, doublon) ferait passer des avis corrompus au modèle, dégradant les prédictions. |
| **Disponibilité du service** (API / Airflow) | Une indisponibilité empêche les équipes community & live-ops d’accéder aux insights en temps réel. |

## 2. Quatre familles de signaux

### 2.1 Fraîcheur et volume des données

| Signal | Source (fichier ou service réellement présent) | Fréquence | Seuil | État |
|--------|-----------------------------------------------|-----------|-------|------|
| Nombre d’avis bruts ingérés (raw) | `data/raw/…/*.jsonl` (`config.RAW_DIR`) | Quotidien (DAG quotidien) | seuil à fixer | à faire |
| Nombre d’avis nettoyés (clean) | `data/clean/reviews.parquet` (`config.CLEAN_FILE`) | Quotidien (post-transformation) | seuil à fixer | à faire |
| Nombre d’enregistrements dans la table Iceberg *silver* | Table Iceberg `silver.reviews` (lecture via `lakehouse.read_table`) | Quotidien (post-score) | seuil à fixer | à faire |

### 2.2 Qualité des données

| Signal | Source | Fréquence | Seuil | État |
|--------|--------|-----------|-------|------|
| Résultat du contrôle bloquant `quality.check_clean` | `src/reviewpulse/quality.py` | À chaque exécution du DAG quotidien | 0 échec | **en place** (tests unitaires, arrêt du DAG en cas d’échec) |
| Rapport Great Expectations | `src/reviewpulse/expectations.py` (suite `zone_propre`) | À chaque exécution du DAG quotidien | succès = `True` | **en place** (rapport HTML généré) |

### 2.3 Dérive

| Signal | Source | Fréquence | Seuil | État |
|--------|--------|-----------|-------|------|
| Distribution des longueurs de texte & proportion des langues | Fichiers de la zone brute (`config.RAW_DIR`) | Quotidien | seuil à fixer | à faire |
| Part négative prédite par jour / jeu / langue (`share_negative_pred`) | `config.SUMMARY_FILE` (produit par `score.summarize`) | Quotidien | 0,79 ≤ ratio ≤ 1,21 (charte) | à faire |
| Part négative réelle par jour / jeu / langue (`share_negative_true`) | `config.SUMMARY_FILE` (même source) | Quotidien | 0,79 ≤ ratio ≤ 1,21 | à faire |

### 2.4 Performance du modèle et santé du service

| Signal | Source | Fréquence | Seuil | État |
|--------|--------|-----------|-------|------|
| F1 macro du modèle champion | Métrique `f1_macro` enregistrée dans MLflow (run `train_and_log`) | Hebdomadaire (post-entraînement) | ≥ 0,75 (ADR 0008) | **en place** |
| Disponibilité de l’API (`/health`) | FastAPI (`src/reviewpulse/api.py`) | À chaque appel / monitoring continu | Code 200, `model_version` non vide, `decision_threshold` ∈ (0,1) | **en place** |
| Temps de réponse moyen de l’API | FastAPI (mesure via client externe) | Continu | seuil à fixer | à faire |
| Succès du DAG quotidien | Airflow (logs du DAG `reviewpulse_daily`) | Quotidien | 0 échec | **en place** (logs, retries) |
| Succès du DAG hebdomadaire | Airflow (`reviewpulse_weekly_train`) | Hebdomadaire | 0 échec | **en place** |

## 3. Réaction attendue

| Famille de signaux | Qui est prévenu | Action attendue | Automatisé aujourd’hui ? |
|--------------------|-----------------|-----------------|------------------------|
| Fraîcheur / volume | Data Engineer | Vérifier l’ingestion (API Steam, permissions, disque) | **non** (pas d’alerte automatisée) |
| Qualité des données (blocage) | Pipeline (Airflow) → Data Engineer | Le DAG s’arrête, l’opérateur Airflow reçoit une alerte (log) ; correction manuelle du fichier ou du script de transformation | **partiellement** (arrêt du DAG, mais pas de notification externe) |
| Qualité (Great Expectations) | Data Engineer | Consultation du Data Docs ; si échec, correction du pipeline | **non** (rapport généré mais pas d’alerte) |
| Dérive (ratio prédiction) | ML Owner / Data Lead | Analyse du drift, décision de ré-entraînement (déclenchement manuel du DAG hebdomadaire) | **non** (pas de déclencheur) |
| Dérive (distribution texte) | Data Engineer | Vérifier la source Steam, éventuel changement d’API | **non** |
| Performance du modèle (F1) | ML Owner | Si F1 < 0,75 → aucune promotion, investigation ; si > 0,75 mais ≤ champion → aucune promotion ; si > champion → promotion automatique (déjà implémentée) | **en place** (promotion automatique via ADR 0008) |
| Santé de l’API | Ops / SRE | Redémarrage du service, vérification du modèle chargé ; si indisponible > 5 min → escalade | **partiellement** (endpoint `/health` existe, mais pas d’alerte automatisée) |
| Temps de réponse API | Ops | Optimisation (profilage, scaling) | **non** |
| Échec du DAG quotidien/hebdomadaire | Ops (via Airflow) | Relancer la tâche, corriger la cause racine | **en place** (retries Airflow, logs) |

## 4. Réentraînement

* **DAG hebdomadaire existant** (`reviewpulse_weekly_train`) :
  - Exécute `reviewpulse.train` → crée une version MLflow, calcule les métriques, applique la **barrière de promotion** (ADR 0008).
  - Si la promotion a lieu, le modèle champion est mis à jour ; sinon le DAG se termine sans changement.

* **Barrière de promotion** :
  - `f1_macro ≥ config.F1_MACRO_MIN` (0,75) **et** `f1_macro > champion_f1` (strictement supérieur).
  - Implémentée dans `src/reviewpulse/train.py` et décrite dans `docs/adr/0008-promotion-champion.md`.

* **Ce qui manque pour un réentraînement déclenché par la dérive** :
  - Aucun composant ne surveille les ratios de dérive (section 2.3) et ne déclenche automatiquement le DAG.
  - Aucun job Airflow ou script externe n’interroge le résumé quotidien et ne compare le ratio aux bornes de la charte.

## 5. Ce qui reste à construire

| # | Élément à construire | Fichier / service d’accueil |
|---|----------------------|-----------------------------|
| 1 | Job de calcul quotidien de la fraîcheur et du volume (nombre d’avis raw / clean / silver) | `monitoring/freshness_job.py` (Airflow DAG ou cron) |
| 2 | Alerting automatisé (Slack / email) en cas d’anomalie de fraîcheur ou de qualité | `monitoring/alerting.py` (service dédié) |
| 3 | Tableau de bord de suivi des dérives (ratio prédiction, distribution texte) | `monitoring/drift_dashboard.py` (Streamlit ou Grafana) |
| 4 | Script de contrôle de dérive qui compare le ratio du résumé aux bornes de la charte et déclenche le DAG hebdomadaire | `monitoring/drift_trigger.py` (Airflow sensor ou GitHub Action) |
| 5 | Intégration du rapport Great Expectations dans le système de monitoring (extraction du statut, alerte si échec) | `monitoring/gx_monitor.py` |
| 6 | Métrique de latence et de disponibilité de l’API (prometheus exporter) | `monitoring/api_metrics.py` |
| 7 | Dashboard de santé du DAG (succès / échecs, durée) | `monitoring/dag_health_dashboard.py` |
| 8 | Documentation opérationnelle du processus de réponse aux alertes (run-book) | `docs/operational/runbook_monitoring.md` |

## 6. Limites du plan

* **Pas de surveillance de la conformité RGPD** (pseudonymisation, suppression des colonnes interdites) – la conformité est assurée par les contrôles existants mais aucune alerte n’est prévue en cas de régression.
* **Pas de suivi des ressources** (CPU, mémoire, stockage) – aucune métrique d’infrastructure n’est intégrée.
* **Pas de monitoring de l’équité** (biais langue, jeu) – les dérives de part négative sont observées, mais aucun indicateur de biais sociétal n’est prévu.
* **Pas de contrôle de la latence du pipeline Spark** – les temps d’exécution Spark ne sont pas mesurés ni alertés.

*Plan rédigé le 18/09/2026*

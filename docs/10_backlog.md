# Backlog — sprints jusqu'au Demo Day, puis par bloc

Priorisation : **P1** indispensable au Demo Day · **P2** fort gain pour un bloc · **P3** confort. État : ✅ fait · 🔄 en cours · ⬜ à faire · ⛔ bloqué.
Chaque ligne cite le critère qu'elle sert (voir `08_exigences_par_bloc.md`).

## Sprint 0 — 16/09 (fait)

| # | Tâche | Critère | État |
|---|---|---|---|
| S0-1 | Chaîne ingestion → zones → modèle → API → tableau de bord → Airflow → CI | Demo Day 1 à 5 | ✅ |
| S0-2 | Tests, tests inverses (13/13), test de stack (12/12) | AIA 3 C3.4, AIA 4 C4.1 | ✅ |
| S0-3 | Douze ADR, carte des modules, questions du jury | AIA 4 C4.8, AIA 3 C3.7 | ✅ |
| S0-4 | Great Expectations + Data Docs | Demo Day 3, AIA 3 C3.4 | ✅ |
| S0-5 | Exigences officielles par bloc | tous | ✅ |

## Sprint 1 — 17 et 18/09 : pile du programme

| # | Tâche | Critère | Prio | État |
|---|---|---|---|---|
| S1-1 | Passage à MLflow 3.16 / Streamlit 1.60 ; FastAPI 0.141.1 ; 54 tests verts | prérequis | P1 | ✅ |
| S1-2a | Images application et Airflow (slim, Java 17, `/opt/rp-venv`, `ExternalPythonOperator`), serveur MLflow v3.16.0 avec `--allowed-hosts` ; DAG réel 4/4 ; test de stack 12/12 | AIA 4 C4.1, AIA 2 ind. 5.2 | P1 | ✅ |
| S1-2b | CI : Java 17 et `JAVA_TOOL_OPTIONS` ajoutés aux deux jobs ; déclenchement corrigé (le workflow ne partait que sur `main`, jamais sur la branche de travail). **Écrit, non exécuté** : attend la mise en ligne du dépôt | AIA 4 ind. 1.1 | P1 | 🔄 |
| S1-3 | Job **PySpark** bronze → silver (nettoyage, dédoublonnage, pseudonymisation), équivalence stricte avec pandas | Demo Day 3, CDSD 1 C1.2, CDSD 2 C2.3 | P1 | ✅ |
| S1-4 | Tables **Iceberg** : silver avis et silver prédictions écrites en réel (8 241 lignes) ; lac sous `/data` partout | AIA 3 ind. 2.3, CDSD 1 C1.1 | P1 | ✅ |
| S1-4e | Message de journal corrigé (« historique de la table : N instantané(s) ») ✅ ; contrôles F7 (table `silver.reviews` lisible, lignes = zone propre) et F8 (au moins un instantané) exécutés le 18/09 : test de stack **14 contrôles sur 14** ✅ | AIA 3 C3.4 | P2 | 🔄 |
| S1-4b | DAG `spark_silver` exécuté dans Airflow : 4/4 le 17/09 (exécution `spark_v3`) après correction de `PYSPARK_PYTHON` | AIA 3 C3.3 | P1 | ✅ |
| S1-4c | Mutations M14 (`(?U)` des espaces Unicode), M15 (priorité de dédoublonnage `natural`/`negative_boost`) et M16 (conversion ns→us avant écriture Iceberg) ajoutées à `tests/reverse/mutations.json` (18/09) ; ancre unique et code muté syntaxiquement valide vérifiés. **Exécutées le 18/09 : 16 mutations sur 16 tuées**, témoin vert ; portée déclarée par mutation pour ramener la durée de plusieurs heures à 20 minutes | AIA 3 C3.4 | P1 | ✅ |
| S1-4d | `score.py` : documentation déjà complète (5 objets sur 5, contrôle AST du 18/09) ; carte des modules complétée pour `lakehouse.py`, `spark_silver.py`, `expectations.py` et `gold.py` ; docstring ajoutée à `_hash_steamid` (code identique hors documentation, vérifié par AST) | AIA 4 C4.8 | P1 | ✅ |
| S1-5 | **dbt-duckdb** : staging, étoile, mart quotidien, 43 tests et contrats verts sur données réelles, `docs generate` ; `gold.py` + 4 tests (62 au total) ; exposures à ajouter quand un consommateur lira la gold | Demo Day 3, AIA 3 ind. 7.1, AIA 1 ind. 3.1-3.2 | P1 | ✅ |
| S1-6 | DAG : ingest → spark_silver → gx → score → **gold** (dbt après le score : test de fraîcheur) ; retries ; alertes d'échec et de SLA (journal Airflow) — **écrit, pas encore exécuté** (disque plein) | AIA 3 C3.3, ind. 6.1 | P1 | 🔄 |
| S1-7 | ADR : pile du programme (MLflow 3, Spark, Iceberg, dbt/DuckDB, Airbyte absent) — couvert par l'ADR 0013 (pile et environnements) et l'ADR 0014 (Spark et Iceberg) | AIA 2 C2.3 | P1 | ✅ |

| S1-8 | **Hygiène disque** : Dockerfiles réordonnés (dépendances avant le code), image unique `reviewpulse-app`, `.dockerignore` ; disque de Docker Desktop à déplacer vers `D:\DockerDesktop` (Enzo ; au 18/09 il est revenu sur C:, backend Hyper-V, déplacement reporté le temps du passage icacls sur D:) ; lac sur `D:\ReviewPulse_work\data` ; puis reconstruction et DAG 5/5 | livraison | P1 | ⛔ Enzo |

## Sprint 2 — 19 et 20/09

| # | Tâche | Critère | Prio | État |
|---|---|---|---|---|
| S2-1 | Bloc 6 CDSD : dépôt bancaire public, tag, écart 142/178 tests, archive | CDSD 6 | P1 | ⬜ |
| S2-2 | **Kafka** KRaft + Schema Registry ; producteur Avro des nouveaux avis | AIA 3 C3.1, ind. 1.2 | P2 | ⬜ |
| S2-3 | Consommateur qui score et alerte ; **DLQ** ; démonstration de résilience (LAG) | AIA 3 ind. 4.2, AIA 4 C4.2 | P2 | ⬜ |

## Sprint 3 — 21 et 22/09

| # | Tâche | Critère | Prio | État |
|---|---|---|---|---|
| S3-1 | Great Expectations sur silver et gold ; porte de qualité | AIA 3 C3.4 | P1 | ⬜ |
| S3-2 | Plan de monitoring écrit (`docs/14_plan_monitoring.md`, 18/09) : signaux, seuils, réactions, huit éléments à construire nommés. module `drift.py` et `tests/test_drift.py` écrits le 18/09 (indice de stabilité de population, dérive des prédictions, rapport JSON) — **jamais exécutés**. Restent l'alerte, la tâche Airflow et le déclenchement du réentraînement | AIA 4 C4.4, ind. 3.2-3.3 | P1 | 🔄 |
| S3-3 | **Model Card** écrite (`docs/12_model_card.md`, 18/09) : chiffres contrôlés un à un contre le README, la charte et les ADR ; hyperparamètres vérifiés dans `train.py`. explicabilité : module `explain.py` et `tests/test_explain.py` écrits le 18/09 (termes globaux, contributions locales exactes, lot vectorisé) — **jamais exécutés**, la batterie demande Docker ; reste à les brancher sur le tableau de bord | AIA 4 C4.6, C4.8 | P1 | 🔄 |
| S3-4 | Déploiement progressif champion / challenger : ADR 0016 rédigé le 18/09 (part de trafic par `REVIEWPULSE_CHALLENGER_TRAFFIC`, tirage déterministe par hachage, réponse indiquant la version). **Proposé, non implémenté** | AIA 4 ind. 3.1 | P2 | 🔄 |
| S3-5 | CI : Java, Spark, dbt ; entraînement continu | AIA 4 ind. 1.1 | P1 | ⬜ |
| S3-6 | Recréer le dépôt GitHub propre ; secret ; workflow planifié vert | livraison | P1 | ⛔ Enzo |

## Sprint 4 — 23 et 24/09

| # | Tâche | Critère | Prio | État |
|---|---|---|---|---|
| S4-1 | **MinIO** (S3) pour bronze et Iceberg | CDSD 1, AIA 2 C2.5 | P2 | ⬜ |
| S4-2 | **Terraform** cible AWS (S3 KMS, IAM, secrets) + `validate`, `plan`, scan | AIA 2 C2.4, ind. 4.3 | P2 | ⬜ |
| S4-3 | FinOps et GreenOps : mesure CPU, mémoire, durée par tâche | AIA 3 ind. 6.2, AIA 4 C4.5 | P2 | ⬜ |
| S4-4 | Vidéo de la solution en production | AIA 4 livrable | P1 | ⬜ |
| S4-5 | Slides sur le gabarit Jedha (ou Telco), script de 10 min, questions | Demo Day J3 | P1 | ⬜ |
| S4-6 | Note d'orientation technologique écrite (`docs/13_note_orientation.md`, 18/09) : options essayées et mesurées, latence, sécurité, veille ; chiffres contrôlés contre les ADR. Reste à citer la bibliothèque KOS et les sources de veille externes | AIA 4 livrable | P1 | 🔄 |
| S4-7 | Gel : tag `v1.0-demoday` | livraison | P1 | ⬜ |

## Après le 25/09 — applications de la plateforme

| # | Bloc | Projet imposé | Réemploi | État |
|---|---|---|---|---|
| A-1 | CDSD 1 | Kayak | ingestion, S3, Spark, entrepôt, Terraform ; partir du notebook trouvé dans `AIA/Bloc 1/` | ⬜ |
| A-2 | CDSD 2 | **Tinder (Speed Dating)** : données dans `Downloads`, énoncé dans l'export Julie ; **aucun notebook existant** | EDA pandas ; tableaux de bord | ⬜ |
| A-3 | CDSD 2 | Steam (Big Data, Databricks → captures) | Spark | ⬜ |
| A-4 | CDSD 3 | Walmart, Conversion, Uber : RGPD, K-Fold, compléments Uber | — | ⬜ |
| A-5 | CDSD 4 | AT&T (écart spam / sentiment à trancher) | chaîne MLflow, API | ⬜ |
| A-6 | CDSD 5 | Getaround : **URL publique en direct** | Docker, MLflow, API, tableau de bord, déploiement | ⬜ |
| A-7 | AIA 1 | Spotify : dossier + présentation | pilote de gouvernance ReviewPulse | ⬜ |
| A-8 | AIA 2 + AIA 3 | Stripe + Fraud Detection : application « paiements » | PostgreSQL, CDC, Kafka, Airflow, MLflow, Terraform | ⬜ |
| A-9 | CDSD 6 | Final Project | dépôt bancaire | voir S2-1 |

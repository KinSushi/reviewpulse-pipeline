# Briques exigées — état mesuré, sujet ouvert quand elles manquent

**Date** : 19/09/2026.

Ce document existe parce qu'une exigence peut dormir dans `08_exigences_par_bloc.md` sans que
personne ne la voie. Le 19/09, j'ai affirmé qu'aucun énoncé n'exigeait de magasin de documents
alors que le cas Stripe du bloc AIA 2 en demande un depuis des jours. `make briques` rend cet
oubli impossible : **tout terme en gras de `08_exigences_par_bloc.md` doit figurer ici**, dans
le tableau ou dans la liste des termes non techniques, et toute brique qui n'est pas `présente`
doit porter un sujet ouvert du registre `16_registre_suivi.md`.

États : `présente` · `partielle` · `absente`.

**Limite connue du détecteur** : `verifier_briques.py` ne lit que les termes **en gras** de
`08_exigences_par_bloc.md`. Une exigence rédigée sans gras lui échappe — c'est ainsi que
« conteneurs et orchestration sous charge » avait été manquée, jusqu'à ce qu'Enzo pose la
question de Kubernetes le 19/09/2026. Les briques peuvent donc être ajoutées à la main :
le contrôle vérifie que tout terme en gras est classé, jamais l'inverse. Sujet R43.

## Briques techniques

| Brique | Exigée par | État | Preuve ou sujet |
|---|---|---|---|
| , NoSQL DocumentDB, pipeline | — | absente | R29 |
| AI Act | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | risque minimal consigné ; classification argumentée absente, R08 |
| API de paiements en temps réel | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R17 |
| Airflow | Bloc 3 — Pipelines de données pour l'IA | présente | `dags/reviewpulse_daily.py`, 9 tâches ; ADR 0011, 0017 |
| Analyse de sentiment | 2. CDSD — RNCP35288 | présente | c'est le cas métier ; ADR 0001 |
| CDC | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| CI/CD/CT | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | workflows écrits, jamais exécutés en ligne ; R01 |
| CPU/GPU | Bloc 2 — Infrastructure de données et de calcul | absente | R34 |
| Data Contracts | Bloc 1 — Gouvernance des données et des systèmes d'IA | partielle | contrats dbt ; au sens gouvernance, R08 |
| Dead Letter Queues | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| FinOps | Bloc 3 — Pipelines de données pour l'IA | absente | R34 |
| FinOps, GreenOps | Bloc 2 — Infrastructure de données et de calcul | absente | R34 |
| Great Expectations | 5. Déduction de conception : une plateforme, des applications | présente | zone propre, silver et gold ; ADR 0005, 0020 |
| IAM/RBAC | Bloc 2 — Infrastructure de données et de calcul | absente | R08 |
| IaC reproductible et idempotente | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| KPI | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| Kafka | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| Model Cards | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `12_model_card.md` |
| Notification | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | partielle | alerte de dérive en fichier daté ; canal externe absent, R11 |
| OLTP, OLAP et NoSQL | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R29 |
| PCI-DSS | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R08 |
| PaaS, IaaS ou serverless | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| PySpark | 5. Déduction de conception : une plateforme, des applications | présente | `spark_silver.py` ; ADR 0014 |
| RACI | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| RBAC/ABAC | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| RGPD | 2. CDSD — RNCP35288 | présente | base légale écrite, charte et Model Card |
| RGPD, AI Act, ISO | Bloc 1 — Gouvernance des données et des systèmes d'IA | partielle | RGPD et AI Act écrits ; ISO absente, R08 |
| Terraform | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| URL | 2. CDSD — RNCP35288 | absente | R17 |
| `terraform plan`, linters, scan de sécurité | Bloc 2 — Infrastructure de données et de calcul | partielle | `ruff` en CI ; Terraform absent, R17 |
| accessibilité et handicap | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| alertes de SLA | Bloc 3 — Pipelines de données pour l'IA | partielle | `_alert_on_sla_miss` écrit dans le journal Airflow ; canal externe absent, R11 |
| anonymisation ou pseudonymisation | Bloc 1 — Gouvernance des données et des systèmes d'IA | présente | HMAC-SHA256 salé ; ADR 0004 |
| architecture médaillon | Bloc 3 — Pipelines de données pour l'IA | présente | brute, propre, silver, scorée, gold ; `02_architecture.md` |
| auto-scaling | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| avec Spark | 2. CDSD — RNCP35288 | présente | `spark_silver.py` ; ADR 0014 |
| backlog en sprints | Bloc 3 | partielle | `10_backlog.md` et le registre ; aucun sprint, R36 |
| batch, streaming ou ELT | Bloc 3 — Pipelines de données pour l'IA | partielle | batch seul, aucun flux ; R17 |
| catalogue | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| chiffrement en transit | Bloc 3 — Pipelines de données pour l'IA | partielle | seule l'API Steam est en HTTPS ; R32 |
| cloud, on-premise ou hybride | Bloc 2 | partielle | arbitrage écrit (ADR 0012) ; cible cloud non réalisée, R17 |
| coffre à secrets | Bloc 3 — Pipelines de données pour l'IA | absente | R32 |
| dbt | 5. Déduction de conception : une plateforme, des applications | présente | 6 modèles, contrats `enforced`, tests ; ADR 0013, 0020 |
| du modèle et des données | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | registre MLflow et instantanés Iceberg ; ADR 0008, 0014, 0018 |
| déploiement progressif (A/B, Canary) | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R31 |
| détection de dérive | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `drift.py`, tâche `drift` du DAG ; ADR 0015 |
| en direct | 1. Règles communes | présente | démonstration en direct, `script_10_minutes.md` |
| explicabilité (SHAP, LIME, tracing) | Bloc 4 | partielle | contribution linéaire exacte (ADR 0019) ; aucun tracing, R37 |
| failover | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| garde-fous | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R33 |
| gestion des secrets | Bloc 2 — Infrastructure de données et de calcul | partielle | sel obligatoire hors du dépôt ; aucun coffre, R32 |
| lignage | Bloc 3 — Pipelines de données pour l'IA | présente | `dbt docs generate` ; ADR 0020 |
| note d'orientation technologique | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `13_note_orientation.md` |
| optimisation | Bloc 4 | partielle | `lru_cache` sur le champion ; aucune mesure de ressources, R34 |
| pilote | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | ReviewPulse pilote la gouvernance ; `17_gouvernance.md` |
| pilote réel | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | ReviewPulse pilote la gouvernance ; `17_gouvernance.md` |
| plan de monitoring | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `14_plan_monitoring.md` |
| plateforme | Contexte | partielle | ReviewPulse est la brique commune ; briques manquantes, R17 |
| rapport chaque matin | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | DAG quotidien à 6 h UTC ; ADR 0011 |
| retraitement de l'historique | Bloc 3 — Pipelines de données pour l'IA | présente | `make pipeline-gele` et instantanés Iceberg ; ADR 0018 |
| retries | Bloc 3 — Pipelines de données pour l'IA | présente | deux tentatives à 5 minutes ; ADR 0011 |
| réentraînement automatique | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `derive_exige_reentrainement` puis `declencher_reentrainement` ; ADR 0015 |
| sentiment | 5. Déduction de conception : une plateforme, des applications | présente | c'est le cas métier ; ADR 0001 |
| solutions innovantes testées | Bloc 4 | présente | quatre variantes mesurées et comparées ; ADR 0006 |
| tests de validation avant toute mise à jour | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | batterie, tests inverses, test de stack |
| validation croisée K-Fold | 2. CDSD — RNCP35288 | présente | 5 plis pour le seuil ; ADR 0007 |
| validation de schéma à chaque étape | Bloc 3 — Pipelines de données pour l'IA | présente | contrats dbt et suites Great Expectations ; ADR 0005, 0020 |
| vidéo | Bloc 2 — Infrastructure de données et de calcul | absente | R03 |
| vidéo exigée | 1. Règles communes | absente | R03 |
| SCD2 | AIA 2 — travaux de référence | absente | R35 |
| médaillon batch et streaming | AIA 2 — travaux de référence | partielle | médaillon en place, aucun flux ; R17 |
| notification e-mail | AIA 3 — travaux de référence | absente | R11 |
| démonstration de résilience | AIA 3 — travaux de référence | absente | R39 |
| conteneurs et orchestration sous charge | Bloc 4 — indicateur non mis en gras | absente | aucun essai de charge ; R42 |

## Termes non techniques

Titres de section, noms de projets, durées, numéros de bloc, fragments de phrase mis en
valeur : rien à construire, rien à décider. Un terme par ligne, recopié caractère pour
caractère depuis `08_exigences_par_bloc.md` — la typographie française y emploie des
espaces fines insécables qu'une recopie approximative fait échouer.

- `1`
- `1 à 5`
- `15 min`
- `2`
- `3`
- `4`
- `5`
- `6`
- `7 à 8 slides`
- `AIA`
- `AT&T`
- `AT&T (spam)`
- `Automatic Fraud Detection`
- `CDSD`
- `Constat`
- `Conséquence`
- `Contraintes qui en découlent :`
- `Déduction de conception`
- `Examen`
- `Final Project de la Lead`
- `Fraud Detection`
- `Getaround`
- `Imposés par bloc`
- `Indicateurs`
- `Kayak`
- `Livrables`
- `Situation`
- `Sources primaires, lues le 16/09/2026 :`
- `Spotify`
- `Spotify Data Governance`
- `Steam`
- `Stripe`
- `Stripe Business Case`
- `Tinder`
- `individuelle`
- `ou`
- `paiements`
- `plus`

# Briques exigées — état mesuré, sujet ouvert quand elles manquent

**Date** : 19/09/2026.

Ce document existe parce qu'une exigence peut dormir dans `08_exigences_par_bloc.md` sans que
personne ne la voie. Le 19/09, j'ai affirmé qu'aucun énoncé n'exigeait de magasin de documents
alors que le cas Stripe du bloc AIA 2 en demande un depuis des jours. `make briques` rend cet
oubli impossible : **tout terme exigé de `08_exigences_par_bloc.md` doit figurer ici**, dans
le tableau ou dans la liste des termes non techniques, et toute brique qui n'est pas `présente`
doit porter un sujet ouvert du registre `16_registre_suivi.md`.

États : `présente` · `partielle` · `absente`.

**Décompte au 19/09/2026, 20 h** : 135 briques techniques — **39 présentes**, **42 partielles**, **54 absentes** — et 42 termes non techniques. Chiffres relus dans le tableau ci-dessous, pas de mémoire.

**Ce que le détecteur lit, depuis le 19/09/2026** : deux sources. D'abord les termes **en gras**
de `08_exigences_par_bloc.md`. Ensuite, et c'est la correction du jour (R43), chaque ligne de la
forme `- **<étiquette>** : <contenu>` est découpée sur le point-virgule, et chaque segment devient
un terme à classer. Le référentiel écrit ses indicateurs en listes de ce type, souvent sans gras :
« conteneurs et orchestration sous charge » avait ainsi échappé au détecteur jusqu'à ce qu'Enzo
pose la question de Kubernetes. La seconde source a fait passer le vocabulaire surveillé de 111 à
**176 termes** et découvert **65 exigences jamais classées**, toutes traitées ci-dessous.

**Limite qui demeure** : une exigence rédigée en prose continue, hors gras et hors liste à
point-virgule, échappe encore. Les briques peuvent donc être ajoutées à la main :
le contrôle vérifie que tout terme en gras est classé, jamais l'inverse. Sujet R43.

## Briques techniques

| Brique | Exigée par | État | Preuve ou sujet |
|---|---|---|---|
| `terraform plan`, linters, scan de sécurité | Bloc 2 — Infrastructure de données et de calcul | partielle | `ruff` en CI ; Terraform absent, R17 |
| accessibilité et handicap | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| AI Act | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | risque minimal consigné ; classification argumentée absente, R08 |
| Airflow | Bloc 3 — Pipelines de données pour l'IA | présente | `dags/reviewpulse_daily.py`, 9 tâches ; ADR 0011, 0017 |
| alertes de SLA | Bloc 3 — Pipelines de données pour l'IA | partielle | `_alert_on_sla_miss` écrit dans le journal Airflow ; canal externe absent, R11 |
| allocation CPU et mémoire | Bloc AIA 2 — Infrastructure | absente | R17 |
| amélioration continue | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| Analyse de sentiment | 2. CDSD — RNCP35288 | présente | c'est le cas métier ; ADR 0001 |
| anonymisation ou pseudonymisation | Bloc 1 — Gouvernance des données et des systèmes d'IA | présente | HMAC-SHA256 salé ; ADR 0004 |
| API de paiements en temps réel | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R17 |
| arbitrage batch, streaming ou ELT selon la fraîcheur requise | Bloc CDSD 1 — Construction d'infrastructure de données | partielle | le lot quotidien est justifié dans `docs/02_architecture.md` ; le streaming reste absent, R17 |
| architecture médaillon | Bloc 3 — Pipelines de données pour l'IA | présente | brute, propre, silver, scorée, gold ; `02_architecture.md` |
| architecture médaillon (Bronze, Silver, Gold) | Bloc CDSD 1 — Construction d'infrastructure de données | présente | zones brute, propre, silver Iceberg et gold DuckDB ; `docs/02_architecture.md` |
| architectures logique et physique | Bloc AIA 2 — Infrastructure | absente | R17 |
| audits | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| auto-scaling | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| auto-scaling et failover | Bloc AIA 2 — Infrastructure | absente | R17 |
| avec Spark | 2. CDSD — RNCP35288 | présente | `spark_silver.py` ; ADR 0014 |
| backlog en sprints | Bloc 3 | partielle | `10_backlog.md` et le registre ; aucun sprint, R36 |
| batch, streaming ou ELT | Bloc 3 — Pipelines de données pour l'IA | partielle | batch seul, aucun flux ; R17 |
| besoins CPU/GPU justifiés | Bloc AIA 2 — Infrastructure | absente | R17 |
| cartographie des systèmes d'IA | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| catalogue | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| CDC | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| chiffrement en transit | Bloc 3 — Pipelines de données pour l'IA | partielle | seule l'API Steam est en HTTPS ; R32 |
| chiffrement et segmentation | Bloc AIA 2 — Infrastructure | absente | R32 |
| choix temps réel, lots ou edge | Bloc AIA 3 — Pipelines de données | partielle | le lot quotidien est justifié dans `docs/02_architecture.md` ; le temps réel reste absent, R17 |
| CI/CD/CT | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | workflows écrits, jamais exécutés en ligne ; R01 |
| CI/CD/CT sans intervention manuelle | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | `ci.yml` et `pipeline.yml` écrits ; jamais exécutés en ligne, R01 |
| cloud, on-premise ou hybride | Bloc 2 | partielle | arbitrage écrit (ADR 0012) ; cible cloud non réalisée, R17 |
| code de déploiement (Terraform…) sur GitHub | Bloc AIA 2 — Infrastructure | absente | R17 |
| code sur GitHub | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R01 |
| coffre à secrets | Bloc 3 — Pipelines de données pour l'IA | absente | R32 |
| conteneurs et orchestration sous charge | Bloc 4 — indicateur non mis en gras | présente | `make charge` : 300 requêtes, 10 en parallèle, 0 % d'erreur, 29,3 req/s, p99 925 ms ; `docs/evidence/essai_charge.md` |
| continuité | Bloc AIA 2 — Infrastructure | absente | R17 |
| contrats d'interface | Bloc AIA 2 — Infrastructure | absente | R17 |
| coordination | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| CPU/GPU | Bloc 2 — Infrastructure de données et de calcul | absente | R34 |
| Data Contracts | Bloc 1 — Gouvernance des données et des systèmes d'IA | partielle | contrats dbt ; au sens gouvernance, R08 |
| Data Lake et bases vectorielles | Bloc AIA 2 — Infrastructure | absente | R17 |
| Data Owners et Stewards | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| dbt | 5. Déduction de conception : une plateforme, des applications | présente | 6 modèles, contrats `enforced`, tests ; ADR 0013, 0020 |
| Dead Letter Queues | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| dimensionnement du stockage | Bloc AIA 2 — Infrastructure | absente | R17 |
| documentation accessible | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| documentation reprenable par un tiers | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `README.md` et `docs/11_reprise.md` |
| dossier d'architecture | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `docs/02_architecture.md` et dix schémas rendus par `make diagrams` |
| du modèle et des données | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | registre MLflow et instantanés Iceberg ; ADR 0008, 0014, 0018 |
| démonstration de résilience | AIA 3 — travaux de référence | absente | R39 |
| dépendances du DAG | Bloc AIA 3 — Pipelines de données | présente | chaînage explicite en fin de `dags/reviewpulse_daily.py` |
| déploiement progressif (A/B, Canary) | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R31 |
| détection de dérive | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `drift.py`, tâche `drift` du DAG ; ADR 0015 |
| détection de dérive avec alerte | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | `drift.py` et `ecrire_alerte` écrits et branchés ; exécution réelle du DAG à prouver, R11 |
| en direct | 1. Règles communes | présente | démonstration en direct, `script_10_minutes.md` |
| explicabilité (SHAP, LIME, tracing) | Bloc 4 | partielle | contribution linéaire exacte (ADR 0019) ; aucun tracing, R37 |
| failover | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| feature engineering | Bloc CDSD 3 — Machine learning | présente | vectorisation TF-IDF dans `src/reviewpulse/train.py` |
| FinOps | Bloc 3 — Pipelines de données pour l'IA | absente | R34 |
| FinOps des pipelines | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R34 |
| FinOps précis | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R34 |
| FinOps, GreenOps | Bloc 2 — Infrastructure de données et de calcul | absente | R34 |
| garde-fous | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R33 |
| garde-fous (biais, injections) | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R33 |
| gestion des incidents | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| gestion des secrets | Bloc 2 — Infrastructure de données et de calcul | partielle | sel obligatoire hors du dépôt ; aucun coffre, R32 |
| Great Expectations | 5. Déduction de conception : une plateforme, des applications | présente | zone propre, silver et gold ; ADR 0005, 0020 |
| IaC reproductible et idempotente | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| IAM/RBAC | Bloc 2 — Infrastructure de données et de calcul | absente | R08 |
| interopérabilité | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| journaux d'audit | Bloc AIA 2 — Infrastructure | absente | R32 |
| Kafka | Bloc 3 — Pipelines de données pour l'IA | absente | R17 |
| KPI | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| KPI de gouvernance | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| lignage | Bloc 3 — Pipelines de données pour l'IA | présente | `dbt docs generate` ; ADR 0020 |
| mises à jour sans interruption | Bloc AIA 2 — Infrastructure | absente | R17 |
| Model Cards | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `12_model_card.md` |
| modules et versioning | Bloc AIA 2 — Infrastructure | absente | R17 |
| monitoring | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `docs/14_plan_monitoring.md`, `drift.py`, tableau de bord |
| médaillon batch et streaming | AIA 2 — travaux de référence | partielle | médaillon en place, aucun flux ; R17 |
| NoSQL DocumentDB | Bloc AIA 2 — Infrastructure | absente | R29 |
| note d'orientation technologique | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `13_note_orientation.md` |
| Notification | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | partielle | alerte de dérive en fichier daté ; canal externe absent, R11 |
| notification e-mail | AIA 3 — travaux de référence | absente | R11 |
| OLTP, OLAP et NoSQL | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R29 |
| optimisation | Bloc 4 | partielle | `lru_cache` sur le champion ; aucune mesure de ressources, R34 |
| optimisation (cache, quantification, élagage) | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | `lru_cache` sur le chargement du champion ; quantification et élagage sans objet pour une régression logistique, à assumer par écrit, R34 |
| orchestration Airflow, sans lancement manuel | Bloc AIA 3 — Pipelines de données | présente | `dags/reviewpulse_daily.py`, neuf tâches enchaînées |
| PaaS, IaaS ou serverless | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| parties prenantes | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| PCI-DSS | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | absente | R08 |
| pilote | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | ReviewPulse pilote la gouvernance ; `17_gouvernance.md` |
| pilote réel | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | ReviewPulse pilote la gouvernance ; `17_gouvernance.md` |
| plan d'infrastructure (diagramme) | Bloc AIA 2 — Infrastructure | absente | R17 |
| plan de monitoring | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `14_plan_monitoring.md` |
| plan des pipelines | Bloc AIA 3 — Pipelines de données | présente | `docs/diagrams/src/*.mmd`, rendus par `make diagrams` |
| plateforme | Contexte | partielle | ReviewPulse est la brique commune ; briques manquantes, R17 |
| politique de sécurité | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| priorisation | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| privacy by design | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| PySpark | 5. Déduction de conception : une plateforme, des applications | présente | `spark_silver.py` ; ADR 0014 |
| RACI | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| rapport chaque matin | 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`) | présente | DAG quotidien à 6 h UTC ; ADR 0011 |
| RBAC/ABAC | Bloc 1 — Gouvernance des données et des systèmes d'IA | absente | R08 |
| reproductibilité test et prod | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | ADR 0018 : graine fixe, empreinte du jeu et commit dans chaque run MLflow |
| retraitement de l'historique | Bloc 3 — Pipelines de données pour l'IA | présente | `make pipeline-gele` et instantanés Iceberg ; ADR 0018 |
| retries | Bloc 3 — Pipelines de données pour l'IA | présente | deux tentatives à 5 minutes ; ADR 0011 |
| RGPD | 2. CDSD — RNCP35288 | présente | base légale écrite, charte et Model Card |
| RGPD, AI Act, ISO | Bloc 1 — Gouvernance des données et des systèmes d'IA | partielle | RGPD et AI Act écrits ; ISO absente, R08 |
| risques (sécurité, biais, confidentialité) | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| réentraînement automatique | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `derive_exige_reentrainement` puis `declencher_reentrainement` ; ADR 0015 |
| réentraînement automatique en cas de baisse | Bloc 4 — Industrialisation et déploiement de solutions d'IA | partielle | branche `derive_gate` vers `declencher_reentrainement` ; exécution réelle à prouver, R11 |
| SCD2 | AIA 2 — travaux de référence | absente | R35 |
| schéma des flux | Bloc AIA 3 — Pipelines de données | présente | `docs/diagrams/src/*.mmd`, rendus par `make diagrams` |
| sensibilisation | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| sentiment | 5. Déduction de conception : une plateforme, des applications | présente | c'est le cas métier ; ADR 0001 |
| solutions innovantes testées | Bloc 4 | présente | quatre variantes mesurées et comparées ; ADR 0006 |
| sources, flux et sensibilités | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| soutenabilité | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R34 |
| souveraineté | Bloc AIA 2 — Infrastructure | absente | R17 |
| supervision des équipes et cahier des charges | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| Terraform | Bloc 2 — Infrastructure de données et de calcul | absente | R17 |
| tests de validation avant toute mise à jour | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | batterie, tests inverses, test de stack |
| traçabilité | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| URL | 2. CDSD — RNCP35288 | absente | R17 |
| validation croisée K-Fold | 2. CDSD — RNCP35288 | présente | 5 plis pour le seuil ; ADR 0007 |
| validation de schéma à chaque étape | Bloc 3 — Pipelines de données pour l'IA | présente | contrats dbt et suites Great Expectations ; ADR 0005, 0020 |
| veille réglementaire et technologique | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| versioning du modèle et des données avec restauration | Bloc 4 — Industrialisation et déploiement de solutions d'IA | présente | `rollback.py` pour le modèle, `lakehouse.restore_snapshot` pour les données |
| vidéo | Bloc 2 — Infrastructure de données et de calcul | absente | R03 |
| vidéo de l'infrastructure en production | Bloc AIA 2 — Infrastructure | absente | R03 |
| vidéo de la solution en production | Bloc 4 — Industrialisation et déploiement de solutions d'IA | absente | R03 |
| vidéo du pipeline en production | Bloc AIA 3 — Pipelines de données | absente | R03 |
| vidéo exigée | 1. Règles communes | absente | R03 |
| éthique et biais | Bloc AIA 1 — Gouvernance | partielle | `docs/17_gouvernance.md` couvre la notion ; relecture ligne à ligne contre le code, R08 |
| évolutivité | Bloc AIA 2 — Infrastructure | absente | R17 |

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
- `5 min`
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
- `environ 15 h`
- `environ 20 h`
- `environ 30 h`
- `environ 30 h, « ML classique ou IA générative »`
- `Examen`
- `Final Project de la Lead`
- `Fraud Detection`
- `Getaround`
- `Imposés par bloc`
- `Indicateurs`
- `individuelle`
- `Kayak`
- `Livrables`
- `ou`
- `paiements`
- `plus`
- `Situation`
- `Sources primaires, lues le 16/09/2026 :`
- `Spotify`
- `Spotify Data Governance`
- `Steam`
- `Stripe`
- `Stripe Business Case`
- `Tinder`

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

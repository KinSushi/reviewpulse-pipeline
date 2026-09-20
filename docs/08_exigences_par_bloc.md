# Exigences officielles, bloc par bloc — et ce que la plateforme doit fournir

**Sources primaires, lues le 16/09/2026 :**
- Référentiel CDSD RNCP35288 (PDF, `Dossier-Jedha/02-certification/`) ;
- Référentiel AIA « Architecte en Intelligence Artificielle », version renouvelée (PDF, 20 pages, même dossier) ;
- Pages Julie `certifications/rncp35288` et `certifications/rncp41993` ;
- Énoncé du Final Project Lead v2 (`00_sources/`).

Les formulations entre guillemets sont reprises des sources. Tout le reste est une déduction de conception, signalée comme telle.

---

## 1. Règles communes

| | CDSD (RNCP35288) | AIA (RNCP41993, ex-38777) |
|---|---|---|
| Projets | **Imposés par bloc** (tableau Julie) | Imposés pour 1, 2, 3 ; **Final Project de la Lead** pour le 4 |
| Démonstration | « **en direct** pendant la présentation (pas de captures d'écran, pas de vidéo) » | « en direct … **ou** par le biais de captures d'écran ou d'une vidéo » ; blocs 2, 3, 4 : **vidéo exigée** parmi les livrables |
| Support | « **7 à 8 slides** » | Adapté à la durée |
| Dépôt | ZIP du projet **ou** fichier texte avec le lien GitHub | Code « hébergé sur Github » |
| Notation | Critères du référentiel | Indicateurs notés de **1 à 5** par le jury |
| Préparation | Individuelle | « individuellement ou en groupe », présentation **individuelle** |
| Statut | Plus d'inscriptions depuis le 10/02/2026 ; inscrits avant : certification valide | RNCP41993 remplace 38777 ; version selon le contrat |

## 2. CDSD — RNCP35288

| Bloc | Projet imposé (Julie) | Évaluation (référentiel) | Livrable (référentiel) | Examen |
|---|---|---|---|---|
| **1** Infrastructure | **Kayak** | Étude de cas : « infrastructure Cloud accueillant des données Big Data (collecte web, Data Lake, nettoyage et chargement type AWS Redshift par traitement parallélisé si nécessaire, ETL) », 10 h | « étude de 1 page décrivant schématiquement l'infrastructure » + code source | 5 + 5 min |
| **2** Analyse exploratoire | **Tinder** + **Steam** (Big Data) ; en présenter un | Deux études de cas : valeurs manquantes/aberrantes + tendances ; base massive **avec Spark** ; 20 h | Deux codes sources avec graphiques | 5 + 5 min |
| **3** ML structuré | Walmart, Conversion rate, Uber Pickups (déposer les trois) | Trois études de cas, 30 h | Trois codes + recommandations | 5 + 5 min |
| **4** Données non structurées | **AT&T** | « **Analyse de sentiment** … à l'égard d'un produit (avec possibilité de créer de la nouvelle donnée) », 20 h | « code source incluant la conception de l'algorithme et les métriques de performances sur des données de validation » | 5 + 5 min |
| **5** Industrialisation | **Getaround** | « Web dashboard, construction et mise en production d'une application web d'IA », 10 h | Code : environnement standardisé, déploiement, application web + **URL** de l'application déployée | 5 + 5 min |
| **6** Direction de projet | Final Project (Essentials, Fullstack Data Science, GenAI ou Fullstack Data Analysis) | Projet data de A à Z, thème libre, 50 h | Code source + soutenance 10 min + 5 min de questions | 10 + 10 min |

**Critères transverses du référentiel CDSD, repris ici parce qu'ils coûtent cher s'ils manquent :** PEP8 ; F1-score ou R² ; **validation croisée K-Fold** ; tests de sur- et sous-apprentissage ; comparaison au modèle en place ; conformité **RGPD** de la collecte et du projet ; simplicité et coût de l'infrastructure ; « Containerisation via Docker et normalisation via MLFlow » ; « Qualité des données non-structurées générées » (bloc 4) ; fonction de coût explicitée (bloc 4).

## 3. AIA — référentiel renouvelé

### Bloc 1 — Gouvernance des données et des systèmes d'IA
- **Situation** : dossier de stratégie et de pilotage de la gouvernance Data & IA ; environ 15 h.
- **Livrables** : dossier de gouvernance (traitement de texte) et présentation synthétique.
- **Examen** : **15 min** de présentation, 15 min de questions — 30 min en tout. Aucun temps de lecture du dossier par le jury : la page officielle de Julie n'en prévoit pas (lue le 20/09/2026, `00_sources/2026-09-20_julie_certification_aia.md`).
- **Indicateurs** : sources, flux et sensibilités ; cartographie des systèmes d'IA ; risques (sécurité, biais, confidentialité) ; priorisation ; parties prenantes ; Data Owners et Stewards ; **RACI** ; coordination ; **Data Contracts** ; **catalogue** ; traçabilité ; interopérabilité ; **RBAC/ABAC** ; **anonymisation ou pseudonymisation** ; politique de sécurité ; **RGPD, AI Act, ISO** ; gestion des incidents ; éthique et biais ; sensibilisation ; **accessibilité et handicap** ; **KPI** de gouvernance ; audits ; amélioration continue ; veille réglementaire et technologique.

### Bloc 2 — Infrastructure de données et de calcul
- **Situation** : environ 30 h.
- **Livrables** : plan d'infrastructure (diagramme) ; code de déploiement (**Terraform**…) sur GitHub ; **vidéo** de l'infrastructure en production.
- **Examen** : **5 min** de présentation, 15 min de questions — 20 min en tout. Aucun temps de lecture (source du 20/09/2026).
- **Indicateurs** : besoins **CPU/GPU** justifiés ; dimensionnement du stockage ; architectures logique et physique ; évolutivité ; arbitrage **cloud, on-premise ou hybride** et **PaaS, IaaS ou serverless** ; souveraineté ; **IaC reproductible et idempotente** ; modules et versioning ; **`terraform plan`, linters, scan de sécurité** ; Data Lake et bases vectorielles ; allocation CPU et mémoire ; **auto-scaling** et **failover** ; continuité ; **IAM/RBAC** ; chiffrement et segmentation ; **gestion des secrets** ; **FinOps, GreenOps** ; monitoring ; contrats d'interface ; documentation accessible ; mises à jour sans interruption.

### Bloc 3 — Pipelines de données pour l'IA
- **Situation** : environ 20 h.
- **Livrables** : plan des pipelines ; code sur GitHub ; **vidéo** du pipeline en production.
- **Examen** : **5 min** de présentation, 15 min de questions — 20 min en tout. Aucun temps de lecture (source du 20/09/2026).
- **Indicateurs** : arbitrage **batch, streaming ou ELT** selon la fraîcheur requise ; outils de collecte (**Kafka**, API, **CDC**) dimensionnés « sans perte » ; schéma des flux ; **architecture médaillon** (Bronze, Silver, Gold) ; feature engineering ; **retraitement de l'historique** ; orchestration **Airflow**, sans lancement manuel ; dépendances du DAG ; reproductibilité test et prod ; **validation de schéma à chaque étape** ; **Dead Letter Queues** ; **retries** ; *privacy by design* ; **coffre à secrets** ; **chiffrement en transit** ; **alertes de SLA** ; **FinOps** des pipelines ; journaux d'audit ; **lignage** ; **backlog en sprints** ; documentation reprenable par un tiers.

### Bloc 4 — Industrialisation et déploiement de solutions d'IA
- **Situation** : environ 30 h, « ML classique ou IA générative ».
- **Livrables** : présentation (choix d'infrastructure, stratégie de déploiement, **plan de monitoring**, **note d'orientation technologique**) ; code de déploiement (automatisation du cycle de vie, conteneurs, sécurité, versioning) sur GitHub ; **vidéo** de la solution en production.
- **Examen** : **5 min** de présentation, 10 min de questions — 15 min en tout. Aucun temps de lecture : le total annoncé pour les quatre blocs, 1 h 25, vaut exactement 30 + 20 + 20 + 15 (source du 20/09/2026).
- **Indicateurs** : **CI/CD/CT** sans intervention manuelle ; versioning **du modèle et des données** avec restauration ; **tests de validation avant toute mise à jour** ; choix temps réel, lots ou edge ; conteneurs et orchestration sous charge ; **optimisation** (cache, quantification, élagage) ; **déploiement progressif (A/B, Canary)** ; **détection de dérive** avec alerte ; **réentraînement automatique** en cas de baisse ; **FinOps** précis ; soutenabilité ; **explicabilité (SHAP, LIME, tracing)** ; **garde-fous** (biais, injections) ; **AI Act** ; supervision des équipes et cahier des charges ; dossier d'architecture ; **Model Cards** ; veille : **solutions innovantes testées**, recommandations sur la latence et la sécurité.

## 4. Consignes du Demo Day Lead (rappel)

Cinq exigences non négociables : données réelles ; zone brute inchangée ; transformation (dbt, PySpark ou pandas) avec un test de qualité ; étape d'IA (MLflow ou LangChain) ; une partie automatisée. Démo de 10 min, puis 5 min de questions. Détail : `00_sources/`.

---

## 5. Déduction de conception : une plateforme, des applications

**Constat** : ReviewPulse ne peut pas *remplacer* les projets imposés des blocs CDSD 1 à 5 ni des blocs AIA 1 à 3.

**Conséquence** : pour éviter le travail en double, ReviewPulse devient la **plateforme** dont les projets imposés réemploient les briques. Chaque projet reste présentable seul.

| Brique de la plateforme | ReviewPulse (AIA 4) | Réemploi par les projets imposés |
|---|---|---|
| Ingestion API + manifeste idempotent | avis Steam | **Kayak** (API météo et collecte web, CDSD 1) |
| Lac objet compatible S3 + Iceberg (bronze, silver) | oui | **Kayak** (Data Lake), **Steam** (CDSD 2) |
| Jobs **PySpark** | nettoyage et pseudonymisation | **Kayak** (ETL parallélisé), **Steam** (analyse Big Data) |
| Entrepôt + **dbt** (gold) | indicateurs quotidiens | **Kayak** (entrepôt type Redshift) |
| Qualité : contrôles, **Great Expectations** | oui | tous |
| **Kafka** (Avro, Schema Registry, DLQ) | alertes d'avis négatifs en temps réel | **Fraud Detection** (AIA 3) |
| **Airflow** + retries + alertes de SLA | oui | **Fraud Detection** (AIA 3), **Kayak** |
| MLflow (registre, alias, barrière) | oui | **AT&T** (CDSD 4), **Getaround** (CDSD 5) |
| API FastAPI + tableau de bord + déploiement public | oui | **Getaround** (URL exigée, CDSD 5), **AT&T** |
| CI/CD/CT, tests inverses, test de stack | oui | tous |
| Dérive, déploiement progressif, SHAP, Model Card | oui (à faire) | **AT&T**, **Getaround** |
| **Terraform** (cible cloud) + scans | description de la cible | **Stripe** (AIA 2), **Kayak** (infrastructure cloud) |
| Gouvernance : classification, RACI, contrats, RBAC | oui | **Spotify** (AIA 1) |

**Contraintes qui en découlent :**
- La démo **CDSD** est **en direct** : l'application Getaround doit tourner publiquement le jour J.
- La démo **AIA** admet la vidéo, mais les blocs 2, 3 et 4 exigent une vidéo parmi les livrables : à enregistrer pour chacun.
- Le bloc 4 du CDSD impose le **sentiment** alors que le projet imposé est **AT&T (spam)** : écart à faire trancher par Jedha (question déjà posée dans `03_matrice_reemploi_blocs.md`).

## 6. Énoncés des projets AIA imposés (lus le 16/09/2026, parcours `dse-lead`)

| Projet | Ce qui est demandé | Livrables de l'énoncé | Ce que la plateforme apporte |
|---|---|---|---|
| **Spotify Data Governance** (AIA 1), « à réaliser en 6 heures » | Cadre de gouvernance conforme RGPD, CCPA, PCI-DSS ; maturité ; principes ; rôles ; modèle d'organisation (centralisé, décentralisé, CoE) ; outils (catalogue, qualité) ; **pilote** sur un département ou un jeu de données | Rapport de maturité (1-2 p.), politique (2-3 p.), organigramme (1 p.), plan de mise en œuvre (2-3 p.), présentation (5-10 slides) | Un **pilote réel** à citer : classification des données, pseudonymisation, contrats de données, catalogue et lignage (dbt docs), RACI |
| **Stripe Business Case** (AIA 2) | Architecture intégrant **OLTP, OLAP et NoSQL** ; batch et streaming (**Kafka**, **Airflow**) ; **CDC** ; partitionnement, index, cache ; sécurité (chiffrement, RBAC, audit) ; RGPD, **PCI-DSS** ; intégration du ML de fraude | Diagramme global, ERD OLTP, schéma OLAP (étoile), modèle NoSQL, architecture du pipeline, plan sécurité et conformité, stratégie ML, requêtes SQL et NoSQL | PostgreSQL + Debezium + Kafka, OLAP Iceberg + dbt (étoile), Terraform (exigé par le référentiel AIA 2) |
| **Automatic Fraud Detection** (AIA 3) | **Notification** à chaque fraude détectée ; **rapport chaque matin** sur la veille ; données : jeu étiqueté + **API de paiements en temps réel** mise à jour chaque minute ; « le plus important est le pipeline, pas l'algorithme » ; minimum : collecte et stockage, consommation, ETL | Schéma d'infrastructure justifié, code source, **vidéo** de l'infrastructure en fonctionnement | Producteur Kafka, consommateur qui score (MLflow), DLQ, notification, DAG Airflow du rapport matinal |

**Déduction de conception** : Stripe et Fraud Detection portent sur les **paiements**. Une seule application « paiements » de la plateforme peut servir les deux : l'architecture et l'infrastructure pour l'AIA 2, le pipeline temps réel pour l'AIA 3, sans travail en double.

## 7. Modèles des coachings (dépôts clonés, à lire comme références de format, jamais à recopier)

Emplacement : `Dossier-Jedha/03-plateforme/depots-coaching/` ; liens dans `Jedha_Exercices/AIA/**/*.txt`.

| Bloc | Dépôt | Attente que le modèle rend visible |
|---|---|---|
| AIA 1 | `semarmehdi_bloc1_data_gouv` | Quatre livrables : diagnostic de maturité (DMBOK), politique, organigramme (modèle CoE) et RACI, plan de mise en œuvre avec pilote, formation inclusive, audit, registre des risques ; puis la soutenance |
| AIA 2 | `semarmehdi_bloc2_data_archi` | Neuf documents numérotés (synthèse, **cahier des charges avec matrice de traçabilité**, diagramme, ERD 3NF, OLAP étoile **SCD2**, NoSQL DocumentDB, pipeline **médaillon batch et streaming**, sécurité, ML, requêtes) **plus** « 0A Infrastructure Compute Monitoring » (serveurs pour l'IA, clusters, monitoring) |
| AIA 2 | `*_fitconnect-data-architecture` | Neuf diagrammes drawio : architecture globale, ETL, étoile, OLTP/OLAP/NoSQL, ACID, ETL vs ELT, batch vs streaming, pipeline ML, clés |
| AIA 3 | `semarmehdi_bloc3_workflow_orchestration` | DAG Airflow : extraction de l'API → S3 → prédiction (via l'API modèle **ou** le modèle MLflow `@alias`) → PostgreSQL (opérateur maison) → **notification e-mail** ; Connections et Variables Airflow pour les secrets |
| AIA 3 | `KinSushi_coaching-aia-bloc3` | Kafka producteur et consommateur, modèle MLflow `@champion`, table de prédictions, e-mail d'alerte ; **démonstration de résilience** (consommateur arrêté puis relancé, colonne LAG) ; table de transposition vers la fraude |

## 8. Non encore lu (à compléter)

- Les énoncés détaillés de Kayak, Tinder, Steam, AT&T et Getaround (parcours `full-stack-full-time`).
- La page « Fonctionnement de la certification ».
- Le cahier de cas Spotify (PDF à télécharger depuis Julie).

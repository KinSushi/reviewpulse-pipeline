# Sources primaires relevées le 16/09/2026

Tout ce qui suit a été **lu à l'écran** sur Julie (session connectée, navigateur Edge) ou dans Gmail, le 16/09/2026. Les passages cités restent dans leur langue d'origine. Le reste est un relevé, pas une interprétation.

---

## 1. Parcours réellement suivi : Data Lead v2

- Adresse : `https://app.jedha.co/path/lead-data-v2` (menu *My cohorts → Data Lead (dal-ft-18) → My Training*).
- Intitulé affiché : **Data Lead**, 20 days, 8 modules, Advanced.
- Modules affichés : Prep Work · Data Governance (3 days) · Big Data (2 days) · Modern Data Stack (10 days) · Data Quality & CI/CD (2 days) · Project Prep (3 days) · What's Next? · **AI Architect Certification 🏆**.
- Tags affichés : data-governance, data-catalog, gdpr, big-data, spark, airbyte, kafka, dbt, iceberg, lakehouse, airflow, great-expectations, ci-cd, docker.

⚠ L'ancien parcours `https://app.jedha.co/path/lead-data-analysis` (« Data Analysis Lead », 3 weeks, se concluant par « Data Analyst Certification ») est **encore en ligne mais n'est plus celui de la cohorte**. Le plan du 12/09 visait `project-prep-lds`, qui appartient à un troisième parcours. **La référence à jour est `lead-data-v2`.**

## 2. Énoncé du Final Project

- Adresse : `https://app.jedha.co/course/m05-d01-final-project-lead-data-v2/capstone-project-instructions-lead-data-v2`
- Titre : **Build a Data Pipeline That Feeds an AI Model 🏗️** — 840 min.
- Gabarit de slides lié par la page : `https://docs.google.com/presentation/d/15fl2DkXq3QWOVrYPi_1tHhvFuwk54DMZ4N-HKu_innA/edit` (« Capstone Project Demo Day Template »).

**Les cinq exigences non négociables**, relevées sur la page :

1. un cas métier réel, avec des données réelles trouvées par l'équipe ;
2. les données brutes déposées **sans modification** dans une première zone de stockage ;
3. une transformation en jeu de données propre et prêt pour le modèle, avec **dbt, PySpark ou pandas**, protégée par **au moins un test de qualité** ;
4. une **étape d'IA** qui consomme la sortie du pipeline : modèle de ML suivi avec **MLflow**, ou chaîne LLM avec **LangChain** ;
5. au moins une partie de la chaîne qui **s'exécute seule** : DAG Airflow, cron ou workflow GitHub Actions.

Le reste (domaine, type de modèle, outils) est **au choix**. → **Le sujet n'est pas imposé**, ce qui répond à la question n° 1 du 12/09.

**Déroulé imposé, livrables par jour :**

| Jour | Livrable affiché |
|---|---|
| J1 | Charte d'une page, diagramme d'architecture v1, ingestion qui remplit une zone brute depuis la source vivante (idempotente) |
| J2 | Une exécution de bout en bout, de la source brute à la sortie de l'IA, et **un chiffre de qualité défendable** |
| J3 | Démo fonctionnelle, dépôt, diagramme, présentation : **10 minutes avec démo en direct, puis 5 minutes de questions** |

Charte, contenu demandé : l'utilisateur, la décision, le coût actuel, ce que « utile » veut dire, **ce qui est hors périmètre**, **qui possède la donnée**, et **les champs personnels et leur protection**. Plus une phrase justifiant le choix ML ou LLM.

Objectifs facultatifs affichés : FastAPI ou Streamlit, Docker.

Travail en équipe de **deux ou trois** recommandé ; chaque membre doit pouvoir expliquer toute la chaîne.

## 3. Planning dal-ft-18 (export .ics du 12/09)

| Date | Séance |
|---|---|
| 17/09 | Introduction to Airflow |
| 18/09 | Airflow & Pipeline Orchestration |
| 21/09 | Data Validation with Great Expectations |
| 22/09 | GitHub Actions |
| 23, 24, 25/09 | **Final Project (Project Prep)** |

Horaires affichés : 02:30 et 06:30 (fuseau de l'export).

## 4. Fiche de certification AIA — `https://app.jedha.co/certifications/rncp41993`

- « La certification RNCP41993 est la version renouvelée du RNCP38777 AIA. »
- « Pour savoir à quelle version de l'AIA tu es éligible, il faut te réferer à ton contrat de formation. »
- Durées d'examen : bloc 1 = 15 min de présentation + 15 min de questions · blocs 2 et 3 = 5 + 15 · **bloc 4 = 5 + 10**.
- « La fonctionnalité des éléments produits doit être démontrée en direct pendant la présentation ou par le biais de captures d'écran ou d'une vidéo. »

Projets désignés par le tableau récapitulatif :

| Bloc | Projet désigné (option Lead) |
|---|---|
| 1 | Data Gouvernance (Projet Spotify) |
| 2 | From SQL to NoSQL (Projet Stripe) |
| 3 | Workflow Orchestration (Projet Automatic Fraud Detection) |
| **4** | **Lead Data Science / IA - Final Project** |

Livrables du bloc 4 : présentation de la solution d'IA · code de la solution sur GitHub · **code de déploiement, pipeline CI/CD compris** · **capture vidéo de la solution en production**.

Éligibilité affichée pour la certification complète : « avoir validé la formation AI Fullstack (aifs) et AI Lead (ail) ». Non tranché pour le parcours Data : c'est un point du litige.

## 5. Périmètre écrit par Jedha — courriel de Sabrina, 11/09/2026 14:50 UTC

- CDSD : « afin que tu puisses te présenter aux blocs 1, 4 et 5 du CDSD, nous allons exceptionnellement te donner accès aux contenus nécessaires » — `https://app.jedha.co/path/full-stack-full-time`
- AIA : « nous allons te donner accès aux contenus nécessaires pour préparer les blocs 2, 3 et 4 » — `https://app.jedha.co/path/dse-lead`
- Le bloc 1 de l'AIA n'est pas cité dans ce courriel. Le contrat, article VI, porte « BC01 à BC04 ». **Écart non résolu.**
- Dernier message reçu : Guilhem (program@jedha.co), 16/09/2026 07:14 UTC : « Je reprends ton dossier directement. Je reviens vers toi d'ici la fin de semaine. »

## 6. Non trouvé, non vérifié

- L'heure exacte de passage au Demo Day du 25/09 : **non trouvée**.
- Le caractère individuel ou en équipe du passage d'Enzo : **non trouvé** (la page recommande 2 ou 3).
- La possibilité de présenter un même système devant deux jurys : **non trouvée**.
- Le contenu des pages « Jedha's Certification Process » et « Certification Online Course » du parcours v2 : **non lu**.

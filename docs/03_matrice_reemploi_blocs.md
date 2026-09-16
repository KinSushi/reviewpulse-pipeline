# Ce que ReviewPulse apporte à chaque bloc — et ce qu'il n'apporte pas

**Règle de lecture.** On distingue trois cas, sans les mélanger :

- **Support déclaré** : le projet est celui que la fiche de certification désigne pour le bloc.
- **Brique réemployée** : du code ou un document de ReviewPulse sert à produire le livrable du bloc, mais le projet présenté reste celui que Jedha désigne.
- **Rien** : le bloc est couvert ailleurs.

Selon la fiche AIA (relevé du 16/09) et le dossier maître (réponse Jedha du 21/07 : « les projets sont imposés »), **ReviewPulse n'est le support déclaré que d'un seul bloc : le bloc 4 de l'AIA.** Pour tous les autres, il fournit des briques. Présenter ReviewPulse à la place d'un projet désigné n'est pas autorisé tant que Jedha ne l'a pas écrit.

---

## AIA — RNCP41993 (ex-38777)

| Bloc | Projet désigné | Statut de ReviewPulse | Ce qui est réemployé |
|---|---|---|---|
| **AIA 4** — industrialisation et déploiement | **Final Project de la Lead** | **Support déclaré** | Tout le dépôt. Livrables à produire en plus du Demo Day : fiche modèle, stratégie de déploiement (alias MLflow `champion` / `challenger`, bascule progressive), plan de monitoring (dérive des données et des prédictions), note de veille, **capture vidéo en production**, **CI/CD** |
| AIA 3 — pipelines de données | Automatic Fraud Detection | Brique | Structure du DAG Airflow, tests de qualité bloquants, ingestion idempotente, traçabilité (manifeste, `model_version` dans chaque prédiction), workflow GitHub Actions |
| AIA 2 — infrastructure données et calcul | Stripe (From SQL to NoSQL) | Brique | Conventions de diagramme, `docker-compose`, zonage brut / propre du lac, pseudonymisation et gestion des secrets |
| AIA 1 — gouvernance | Spotify | Brique | Tableau des données personnelles de la charte, analyse RGPD et AI Act, modèle de RACI |

⚠ Le courriel de Jedha du 11/09 ouvre les **blocs 2, 3 et 4** de l'AIA. Le **bloc 1** n'y figure pas, alors que le contrat porte BC01 à BC04. Écart à trancher par Jedha.

## CDSD — RNCP35288

| Bloc | Projet du parcours (selon le plan du 12/09) | Statut de ReviewPulse | Ce qui est réemployé |
|---|---|---|---|
| CDSD 1 — infrastructure de gestion de données | Kayak | Brique | Collecte par API, zone brute, ETL, variante **PySpark** (le référentiel exige Spark ou Redshift en C1.2), section RGPD de la collecte |
| CDSD 2 — analyse exploratoire | Speed Dating + Steam (Spark) | Brique | Même domaine que le cas Steam : les avis collectés peuvent servir une analyse exploratoire complémentaire. Les deux codes sources exigés restent ceux du parcours |
| CDSD 3 — prédictif structuré | Walmart, Conversion Rate, Uber | Rien | Déjà produit à 90 % |
| **CDSD 4 — prédictif non structuré** | AT&T Spam Detector | **Brique majeure** | Le référentiel impose l'**analyse de sentiment d'un utilisateur à l'égard d'un produit** : c'est exactement la tâche de ReviewPulse. En octobre, on remplace le modèle par un réseau profond et on ajoute la **création de données (C4.4)**, sans toucher à la chaîne. ⚠ L'énoncé AT&T porte sur le spam, pas sur le sentiment : **écart à signaler à Jedha** |
| **CDSD 5 — industrialisation** | Getaround | **Brique majeure** | Docker, MLflow, API FastAPI, tableau de bord, déploiement avec **URL publique** : le même véhicule, avec le modèle Getaround dedans |
| CDSD 6 — direction de projet | Demo Day Fullstack (`banking_dataops_monitoring_demoday`) | Rien | Déjà produit. ReviewPulse **ne le remplace pas** : on évite de présenter deux fois le même système |

## Ce qui existe déjà, et où ça se branche

Relevé le 16/09/2026 sur les disques et sur le compte GitHub public `KinSushi`. **« Propre » = écrit par Enzo ; « fork » = code d'un tiers (coach ou éditeur), à lire comme modèle, jamais à recopier dans un livrable.**

| Existant | Où | Nature | Données | Sert à |
|---|---|---|---|---|
| Walmart, Conversion Rate, Uber Pickups | `Jedha_Exercices/Data_Full_stack/Machine _Learning/Exercices_Projet_BLOC_3_Certif/` | propre | réelles (Jedha) | **CDSD 3**, tel quel (3 corrections listées au plan du 12/09) |
| Banking DataOps (Demo Day Fullstack) | `D:/banking_dataops_monitoring_demoday` (privé) ; `KinSushi/banking-dataops-monitoring` (public) | propre | synthétiques | **CDSD 6**, tel quel. Pour ReviewPulse : format ADR, Makefile, publication Hugging Face Space (URL du **CDSD 5**) |
| Churn Telco (4 versions) + gabarit Demo Day | `Jedha_Exercices/Data_Essentiels/Projet_Final/` | propre | réelles (Kaggle) | Gabarit `Template DemoDay Slides - projet Telco.pptx` → **trame des slides du 25/09** ; raisonnement sur classes déséquilibrées → **AIA 3** (fraude) et section métriques de ReviewPulse |
| `jedha-rncp35288-portfolio` | GitHub public | propre | synthétiques | Carte de preuves des 6 blocs du CDSD : **y ajouter ReviewPulse** comme preuve des blocs 4 et 5 une fois le modèle profond branché |
| `fraud-mlops-control-tower` | GitHub public | propre | synthétiques | Seuil choisi par F1, fiche modèle, fiche données → gabarits des documents **AIA 4** ; logique métier → **AIA 3** |
| `secure-wealth-rag-assistant` | GitHub public | propre | synthétiques | Piste LLM/RAG de ReviewPulse (hors périmètre du 25/09) ; **CDSD 4** en appui |
| `swiss-data-ai-engineering-lab` | `D:/BACKUP_G/` et GitHub public | propre | — | Squelettes `mlops/` (plan de monitoring, fiche modèle, registre) et `governance/` (risques, confidentialité) → **AIA 1 et AIA 4** ; `devops/terraform` → **AIA 2** |
| `bloc1_data_gouv`, `bloc2_data_archi`, `bloc3_workflow_orchestration`, `fitconnect-data-architecture`, `coaching-aia-bloc3`, `bloc4_mlops`, `mlops_masterclass`, `full-deployment-project`, `train-repo` | GitHub `KinSushi` | **forks** | — | Modèles de format pour **AIA 1, 2, 3, 4** (livrables, diagrammes drawio, DAG, CI, Evidently) |
| `dbt-jaffle-shop` | GitHub `KinSushi` | fork (cours) | — | Point de départ d'une couche **dbt** si ReviewPulse passe de pandas à dbt |
| Dix schémas ReviewPulse | `docs/diagrams/` | propre (généré le 16/09) | — | Réemployables tels quels ou adaptés : 02 et 07 → **AIA 1** ; 01, 06, 08 → **AIA 2**, **CDSD 1** ; 03, 05 → **AIA 3** ; 04, 05, 10 → **AIA 4**, **CDSD 5** ; 09 → toutes les soutenances |

## Les trois questions à poser à Jedha, par écrit

1. Puis-je présenter le Final Project de la Lead, **seul** et non en équipe, comme support du bloc 4 de l'AIA ?
2. Pour le bloc 4 du CDSD, dont le référentiel impose l'analyse de sentiment, un projet de sentiment sur avis clients est-il recevable à la place d'AT&T ?
3. Une même chaîne d'industrialisation peut-elle porter deux modèles différents devant deux jurys distincts (AIA 4 et CDSD 5) ?

Tant qu'elles restent sans réponse, **on construit quand même** : la chaîne est indispensable au bloc 4 de l'AIA dans tous les cas.

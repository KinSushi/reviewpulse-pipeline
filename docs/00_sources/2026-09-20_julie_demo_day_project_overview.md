# Source primaire — consigne du Final Project (Demo Day), parcours Data Sc. & Eng — Lead

**Lue le** 20/09/2026, dans le navigateur intégré, session d'Enzo.
**Adresse** : `https://app.jedha.co/course/project-prep-lds/project-overview-lds`
**Durée annoncée** : 1 200 min · **Module** : Prepare your final project

> **C'est la consigne qui prime.** ReviewPulse doit d'abord la respecter ; le réemploi vers les
> blocs de certification vient ensuite. Consigne d'Enzo du 20/09/2026.

## Objectif, mot pour mot

> « Your task is to develop a fully functional **MLOps pipeline** that automates the entire
> lifecycle of a machine learning model. »

> « This project will test your ability to independently manage the full spectrum of data science
> and machine learning operations, focusing on building a **scalable, automated pipeline** that
> works in real-world scenarios. »

## Ce qui est demandé

**1. Jeu de données et préparation** — le trouver soi-même, publiquement disponible ou collecté ;
assez complexe pour être un défi ; nettoyage, valeurs manquantes, valeurs aberrantes,
**équilibrage**, et **feature engineering**.

**2. Entraînement du modèle** — choisir un algorithme pertinent ; **justifier ce choix** ;
**régler les hyperparamètres** ; évaluer avec les métriques appropriées (exactitude, précision,
rappel, F1…).

**3. Chaîne MLOps** — six exigences nommées :

| | Exigence |
|---|---|
| a | **Déploiement** par Docker ou Kubernetes, exposé en **API REST**, capable de passer à l'échelle et de traiter des requêtes en temps réel |
| b | **CI/CD** automatisé (GitHub Actions, GitLab CI, Jenkins), avec tests, validation et déploiement déclenchés à chaque mise à jour du modèle |
| c | **Surveillance et journalisation** — outils du type Aporia ou Evidently ; suivre **latence, exactitude et dérive** ; **alerter** quand le modèle dérive ou passe sous un seuil |
| d | **Réentraînement automatique** déclenché par la dérive ou par l'arrivée de données neuves ; Airflow ou Kubeflow |
| e | **Versionnement et retour arrière** — DVC ou MLflow ; pouvoir revenir à une version antérieure |
| f | **API et documentation** — expliquer clairement entrées, sorties et usage, pour qu'un tiers intègre |

## Ce qu'il faut rendre

1. **Rapport sur le jeu de données et le prétraitement** : quel jeu, comment préparé, et
   **pourquoi** ces transformations.
2. **Carnet ou script d'entraînement** montrant l'entraînement, l'évaluation, **le réglage des
   hyperparamètres** et les métriques finales.
3. **Chaîne MLOps** : un **diagramme** de l'architecture ; le **code** de déploiement, CI/CD,
   surveillance et réentraînement ; une **vidéo ou des captures** montrant la chaîne en action.
4. **Dépôt de code** sur GitHub, avec les instructions pour exécuter et déployer.
5. **Documentation de l'API** : un guide clair et concis.
6. **Une présentation**, pour la soutenance devant la classe ou le jury.

## Critères d'évaluation annoncés

- **Préparation des données et performance du modèle** — jeu pertinent, prétraitement correct,
  modèle performant.
- **Complétude de la chaîne** — du déploiement à la surveillance et au réentraînement.
- **Automatisation** — robustesse face aux changements de données ou de performance.
- **Passage à l'échelle et surveillance** — « Can your pipeline scale to handle larger data
  volumes and **heavier user loads** ? Is the monitoring system **proactive** ? »
- **Documentation et facilité d'usage** — lisible par un développeur ou une partie prenante
  qui arrive après.

## Confrontation au dépôt, faite le 20/09/2026

| Exigence | État | Preuve ou manque |
|---|---|---|
| Jeu trouvé et préparé | tenue | collecte Steam, zone brute immuable, nettoyage, `class_weight="balanced"` |
| Choix de l'algorithme justifié | tenue | ADR 0006, ADR 0019 |
| **Réglage des hyperparamètres** | **manquante** | `C=4.0`, `ngram_range=(2, 5)`, `max_features=100000` sont des constantes posées, jamais cherchées — registre **R47** |
| Métriques d'évaluation | tenue | F1 macro, AUC, rappel des négatifs, validation croisée à 5 plis |
| a — déploiement Docker + API REST | tenue | FastAPI, essai de charge 300 requêtes à 10 en parallèle, 0 % d'erreur |
| b — CI/CD | partielle | `ci.yml` et `pipeline.yml` écrits, jamais exécutés en ligne — R01 |
| c — surveillance, latence, dérive, alerte | partielle | PSI et fichier d'alerte daté prouvés en exécution réelle ; **la latence n'est pas surveillée en continu** — registre **R50** |
| d — réentraînement déclenché par la dérive | tenue | branche `derive_gate` prouvée le 20/09, PSI 0,0399 pour un seuil de 0,2 |
| e — versionnement et retour arrière | tenue | MLflow, alias `champion`, `rollback.py`, instantanés Iceberg |
| f — documentation de l'API | **manquante** | aucun guide — registre **R49** |
| Rapport jeu de données et prétraitement | **manquante** | aucun document — registre **R48** |
| Vidéo ou captures de la chaîne en action | manquante | R03, décision d'Enzo |
| Dépôt GitHub avec instructions | manquante | R01, décision d'Enzo |
| Présentation | tenue | `docs/presentation/ReviewPulse_DemoDay.pptx` |

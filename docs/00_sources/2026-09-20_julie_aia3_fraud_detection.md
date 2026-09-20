# Source primaire — énoncé AIA 3 « Automatic Fraud Detection » (Workflow Orchestration)

**Lu le** 20/09/2026, dans le navigateur intégré, session d'Enzo.
**Adresse** : `https://app.jedha.co/course/etl-with-airflow-lds/automatic-fraud-detection-project-lds`
**Durée annoncée** : 90 min · **Module** : ETL with Airflow · **Parcours** : Data Sc. & Eng — Lead

## Ce que le métier demande

Deux besoins, et deux seulement :

1. **Être notifié dès qu'une fraude est détectée.** L'énoncé insiste : « they just need a
   notification though ».
2. **Chaque matin, revoir tous les paiements et toutes les fraudes de la veille.**

## Les données

| Source | Rôle |
|---|---|
| Jeu complet de paiements étiquetés frauduleux ou non | construire l'algorithme |
| API de paiements en temps réel, point d'accès `/current-transactions` | produire des prédictions en direct ; **l'API est mise à jour toutes les minutes** |

## Livrables exigés

- Un **schéma de l'infrastructure** choisie, **et la raison de ce choix** (PowerPoint ou Word).
- Le **code source** de tous les éléments nécessaires à l'infrastructure.
- Une **vidéo** de l'infrastructure en fonctionnement sur un exemple.

## La phrase qui commande tout le projet

> « The most important part is the Data Pipeline - NOT THE ML Algorithm »

Et l'énoncé enfonce le clou : « No matter what you do, the ML algorithm comes second after the
Data Pipeline which should be your main priority. »

## Les trois éléments minimaux imposés

L'infrastructure proposée par Jedha n'est qu'une suggestion — « you can deviate from this
infrastructure » — mais trois éléments sont obligatoires :

1. un élément qui **collecte et stocke** la donnée ;
2. un élément qui **consomme** la donnée ;
3. un processus **ETL ou ELT**.

Trois étapes sont par ailleurs attendues au minimum : entraîner un algorithme, le **mettre en
production**, et stocker la donnée temps réel dans une base.

## Ce que ReviewPulse couvre déjà, et ce qui manquerait

| Élément exigé | Dans ReviewPulse | Écart |
|---|---|---|
| Collecte et stockage | `ingest.py`, zone brute immuable, idempotence par curseur et manifeste | la source est une API d'avis, pas de paiements : le **domaine** change, la mécanique non |
| Consommation | `score.py`, API FastAPI, tableau de bord | aucun |
| ETL ou ELT | Airflow, neuf tâches ; PySpark vers silver ; dbt vers gold | aucun |
| Entraîner puis mettre en production | MLflow, alias `champion`, barrière de promotion, retour arrière | aucun |
| **Notification** dès détection | `drift.py` écrit un fichier d'alerte daté hors journal Airflow | il faut une notification **par évènement métier** (une fraude), pas seulement par dérive |
| **Revue quotidienne** de la veille | résumé quotidien de `score.py`, mart dbt quotidien | aucun |
| **Temps réel** (API rafraîchie chaque minute) | chaîne en **lots quotidiens**, choix justifié pour des avis Steam | **écart réel** : ce projet-ci demande du temps réel, ReviewPulse est en lots |
| Stocker la donnée temps réel dans une base | zones sur fichiers et DuckDB | à compléter |

**Lecture** : sept éléments sur huit se réemploient tels quels. Le seul écart de fond est le
**temps réel**, et il est structurant : c'est lui qui justifierait Kafka, que l'ADR 0027 a
arbitré comme brique absente.

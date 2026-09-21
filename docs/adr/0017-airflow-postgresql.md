# ADR 0017 — Airflow sur PostgreSQL

**Date** : 19/09/2026 · **Statut** : acceptee

## Contexte

Airflow fonctionnait en mode autonome sur SQLite. Le planificateur mourait avec le message « database is locked » dès qu’une commande en ligne interrogeait la base en même temps. Observation le 18/09/2026.  
Après migration, le DAG quotidien a été déclenché pendant qu’une interrogation tournait chaque minute et le planificateur a survécu. Mesure le 19/09/2026.  
Mise en œuvre : service `airflow-db` sur `postgres:16` avec un contrôle de santé dont le `start_period` est de 60 s, variable `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`, exécuteur `LocalExecutor`, package `psycopg2-binary==2.9.10` installé dans l’image Airflow.  
Incident pendant la mise en œuvre : suppression de la ligne `USER airflow` du Dockerfile, pip s’exécutait alors en tant que root, le conteneur a bouclé toute la nuit. La ligne a été restaurée.

## Decision

Migrer la base d’Airflow de SQLite vers PostgreSQL.  
Déployer un service `airflow-db` basé sur l’image `postgres:16`.  
Configurer le contrôle de santé avec un `start_period` de 60 s.  
Définir la variable d’environnement `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` pour pointer vers PostgreSQL.  
Utiliser le `LocalExecutor`.  
Installer `psycopg2-binary==2.9.10` dans l’image Airflow.  
Restaurer la ligne `USER airflow` dans le Dockerfile.

## Alternatives ecartees

| Option | Pourquoi |
|---|---|
| Garder SQLite | Le planificateur meurt dès qu’on interroge la base ; la démonstration nécessite une requête concurrente. |
| CeleryExecutor | Nécessite un courtier de messages et au moins un travailleur supplémentaire, inutile sur une seule machine. |

## Consequences

- Ajout d’un service et d’un volume supplémentaires.  
- Airflow supporte l’accès concurrent à la base.  
- Le jour de la démonstration, il est possible de visualiser le DAG pendant son exécution.

## Preuves

- Plantage du planificateur avec SQLite le 18/09/2026.  
- Survie du planificateur avec PostgreSQL le 19/09/2026 lors d’une exécution concurrente.  
- Service `airflow-db` fonctionnel avec le contrôle de santé configuré.  
- Rétablissement du `USER airflow` a résolu la boucle du conteneur.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

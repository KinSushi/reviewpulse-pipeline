# ADR 0024 — Base de documents NoSQL

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

Le bloc AIA 2 (cas Stripe) impose une architecture à trois étages :  
- **OLTP** : PostgreSQL 16, utilisé comme base de métadonnées d’Airflow (ADR 0017).  
- **OLAP** : DuckDB, zone *gold*, alimentée par dbt.  
- **Base de documents (NoSQL)** : requise pour la zone *brute*.

Dans ReviewPulse :  
- La zone *brute* contient des fichiers JSON / JSONL, un fichier par collecte, jamais modifiés. Ce sont déjà des **documents** : structure imbriquée, champs facultatifs, schéma variable.  
- Aucun moteur de documents (MongoDB, DocumentDB, Elasticsearch…) n’est installé.  
- Le 19/09/2026, il a été affirmé qu’aucune exigence ne demandait de magasin de documents ; cette affirmation était erronée car l’exigence figure depuis plusieurs jours dans `docs/08_exigences_par_bloc.md`.  
- L’outil `make briques` a été introduit pour empêcher que de telles exigences « dormantes » passent inaperçues.  
- Le Demo Day est prévu le 25/09/2026 ; ReviewPulse supporte uniquement le bloc AIA 4.

## Decision

1. **Reconnaissance** : la zone *brute* est déjà une collection de documents stockés sous forme de fichiers. Elle ne fournit pas d’index, de requêtes par champ, ni de schéma souple interrogeable.  
2. **Choix** : ne pas installer de magasin de documents avant le Demo Day. Nous livrerons la spécification de la brique NoSQL (modèle de schéma, exigences d’indexation, API d’accès) sous forme de documentation pour le dossier Stripe du bloc AIA 2.  
3. **Raison** : l’ajout d’un moteur NoSQL impliquerait des changements d’infrastructure, des migrations de données et des tests d’intégration à moins de cinq jours de la soutenance, ce qui représente un risque inacceptable. La livraison papier satisfait l’exigence documentaire sans perturber la chaîne existante.  
4. **Emplacement futur** : si un magasin de documents était installé ultérieurement, il serait placé **en amont de la zone *brute*** et servirait exclusivement les fichiers JSON d’avis Steam (les mêmes fichiers déjà présents).  

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Installer immédiatement un magasin de documents (MongoDB, etc.) | Introduit une dépendance d’infrastructure non testée, nécessite migration des fichiers JSON, risque de rupture de la chaîne à < 5 jours du Demo Day. |
| Installer et livrer la spécification papier simultanément | Complexifie le planning sans bénéfice immédiat pour la soutenance ; la partie installée ne serait pas validée à temps. |
| Ne rien faire (ni installer, ni livrer) | Violenterait l’exigence du bloc AIA 2 et laisserait le dossier Stripe incomplet. |

## Consequences

- **Documentation** : le dossier Stripe inclut désormais une description détaillée de la brique NoSQL (schéma, exigences d’index, API), ce qui satisfait l’exigence formelle.  
- **Aucun impact** sur la chaîne de production : les bases OLTP (PostgreSQL 16) et OLAP (DuckDB) restent inchangées, la zone *brute* continue d’être stockée en fichiers JSON.  
- **Risque réduit** pour le Demo Day : aucune modification d’infrastructure ne peut interrompre le pipeline existant.  
- **Travail futur** : l’ajout d’un magasin de documents pourra être planifié après le Demo Day, avec des tests d’intégration et une migration contrôlée.  
- **Leçon de méthode** : *une exigence qui dort dans un fichier n’existe pas tant qu’un outil ne la réclame pas* (mise en évidence par l’erreur du 19/09/2026 et corrigée par `make briques`).  

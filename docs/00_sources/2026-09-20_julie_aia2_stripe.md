# Source primaire — énoncé AIA 2 « Stripe Business Case » (From SQL to NoSQL)

**Lu le** 20/09/2026, dans le navigateur intégré, session d'Enzo.
**Adresse** : `https://app.jedha.co/course/from-sql-to-nosql-lds/stripe-business-case-lds`
**Durée annoncée** : 180 min · **Module** : NoSQL · **Parcours** : Data Sc. & Eng — Lead

## La situation

Stripe, paiements en ligne, des milliards de transactions par an. L'entreprise doit unifier
**trois** familles de systèmes : transactionnel (OLTP), analytique (OLAP) et **non relationnel
(NoSQL)** — c'est cette exigence que j'avais niée le 19/09/2026 alors qu'elle dormait dans le
dépôt. Voir le registre, sujet R29, et l'ADR 0024.

## Les cinq défis posés

1. **Charges transactionnelles complexes** : paiements, remboursements, rejets de débit,
   abonnements ; disponibilité, cohérence et vitesse ; détection de fraude en temps réel.
2. **Analytique avancée** : revenus, segmentation client, rapports de conformité, suivi produit ;
   requêtes complexes, analyse ad hoc, résultats quasi temps réel.
3. **Données non structurées et semi-structurées** : journaux, retours clients, interactions web
   et mobile — matière première des modèles de fraude et de personnalisation.
4. **Intégration entre les trois systèmes** : un flux cohérent, à jour, accessible.
5. **Conformité et sécurité** : RGPD, **PCI-DSS**, CCPA ; chiffrement au repos et en transit,
   contrôle d'accès, surveillance des usages.

## Les données, par système

| Système | Champs cités par l'énoncé |
|---|---|
| OLTP | identifiant de transaction, de marchand, de client ; montant ; devise ; moyen de paiement ; date et heure ; géolocalisation par IP ; type d'appareil ; statut ; indicateurs de fraude |
| OLAP | métriques de revenu (jour, semaine, mois) ; segmentation client ; performance produit ; analyse de fraude ; journaux de conformité et d'audit |
| NoSQL | journaux d'erreur et d'accès ; parcours et sessions ; variables d'entrée des modèles ; **retours clients : avis et réponses d'enquête** |
| Référentiel | codes pays et région ; taux de change ; informations marchand ; catalogues produits |

## Les huit livrables exigés

1. **Diagramme d'architecture complet** : intégration OLTP, OLAP et NoSQL, flux, pipelines, modèles.
2. **ERD du système OLTP** : schéma normalisé.
3. **Schéma OLAP** : étoile ou flocon, stratégies d'agrégation, optimisation des requêtes.
4. **Modèle NoSQL** : schéma souple, gestion des relations (imbrication, référencement), indexation.
5. **Architecture du pipeline de données** : document technique, outils, intégration et synchronisation.
6. **Plan de sécurité et de conformité** : mesures, stratégies, outils de surveillance.
7. **Stratégie d'intégration du ML** : extraction de variables, déploiement, suivi de performance.
8. **Requêtes SQL et NoSQL** répondant à des questions métier réelles : analyse de revenu,
   détection de fraude, segmentation client.

## Exigences techniques nommément citées

- OLAP : **schéma en étoile ou en flocon**, tables pré-agrégées, vues matérialisées.
- Pipeline : lots **et** temps réel ; **Apache Kafka** pour le flux, **Apache Airflow** pour l'orchestration.
- Passage à l'échelle : indexation, **partitionnement**, cache, bases distribuées, **sharding**.
- Cohérence : **CDC (Change Data Capture)** pour la synchronisation en temps réel ; modèles de
  cohérence à terme ; résolution de conflits.
- Sécurité : chiffrement, **contrôle d'accès par rôle**, journal d'audit ; conformité RGPD et
  PCI-DSS ; contrôles et rapports **automatisés**.

## Ce que ReviewPulse couvre déjà, et ce qui manquerait

| Exigence | Dans ReviewPulse | Écart |
|---|---|---|
| OLAP en étoile | zone gold dbt sur DuckDB, dont un schéma en étoile ; contrats `contract: enforced` | à étendre, pas à créer — voir ADR 0025 |
| Pipeline orchestré | Airflow, neuf tâches, exécution réelle prouvée | aucun |
| ETL / ELT et transformations | PySpark vers silver, dbt vers gold, Great Expectations aux trois zones | aucun |
| Intégration du ML | MLflow, registre, alias, barrière de promotion, dérive | aucun |
| Traçabilité et lignage | `dbt docs generate`, empreinte du jeu, étiquette `code_commit` | aucun |
| **OLTP normalisé** | PostgreSQL présent, mais comme base de métadonnées d'Airflow | **ERD à concevoir** |
| **NoSQL** | zone brute en documents JSON immuables | **moteur absent** — ADR 0024 |
| **Kafka, CDC, temps réel** | absent, choix des lots justifié | **écart de fond** — ADR 0027 |
| **PCI-DSS, RBAC, audit** | pseudonymisation, RGPD, secret obligatoire | **à concevoir** — ADR 0022 |

**Lecture** : cinq exigences sur neuf sont déjà tenues par ReviewPulse et se réemploient telles
quelles. Les quatre autres sont des livrables **de conception** — diagrammes, modèles, plans —
que l'énoncé demande sur le papier, pas en production. C'est ce qui rend ce bloc atteignable sans
reconstruire la chaîne.

# ADR 0025 — Modélisation étoile et SCD2

**Date** : 20/09/2026 · **Statut** : acceptée

## Contexte

- La zone **gold** de ReviewPulse est construite avec dbt sur DuckDB.  
- Les contrats dbt sont définis dans `dbt/models/staging/_staging.yml` et `dbt/models/marts/_marts.yml`.  
- Les données proviennent d’avis Steam : chaque avis possède un `app_id`, une `language`, une `review_date`, un `label`, une prédiction (`pred_label`, `proba_negative`, …) et du texte.  
- Les avis sont **immuables** : la zone brute n’est jamais réécrite, l’ingestion est idempotente (ADR 0002).  
- La chaîne s’exécute quotidiennement.  
- À ce jour, aucune dimension ne possède d’historique d’évolution connu.

## Decision

| Élément | Nom (tel que dans les contrats) | Rôle |
|---|---|---|
| Table de faits | `fct_review_predictions` | Grain : `review_id`. Contient les mesures de sentiment et les attributs de l’avis. |
| Dimension jeu | `dim_game` | Clé : `app_id`. Fournit le nom du jeu (`game_name`). |
| Dimension date | `dim_date` | Clé : `date_day`. Fournit les attributs calendaires (`year`, `month`, …). |

### SCD2

- Parmi les dimensions, seul **`dim_game`** possède un attribut (`game_name`) qui pourrait changer (renommage d’un jeu, correction de titre).  
- Aucun changement historique n’est observé dans les données actuelles ; les jeux sont référencés par leur `app_id` stable.  
- Implémenter le SCD2 sur `dim_game` impliquerait d’ajouter : une clé de substitution, des colonnes de validité (début, fin) et un indicateur de version courante. Ces colonnes n’existent pas dans les contrats actuels et leur ajout augmenterait la complexité du modèle et le temps de construction du DAG quotidien.  
- **Décision** : **ne pas implémenter le SCD2** pour le moment. La dimension `dim_game` restera **statique** (type 1). Si, à l’avenir, des changements de `game_name` deviennent fréquents, un nouveau ADR pourra être créé pour introduire le SCD2.

### Ce qui sera construit

- Aucun changement de schéma dans la zone gold.  
- Le modèle `fct_review_predictions` continue de référencer `dim_game` et `dim_date` via les clés `app_id` et `review_date`.  
- Le tableau de bord utilise les mêmes jointures qu’aujourd’hui : faits ↔ `dim_game` ↔ `dim_date`.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Implémenter le SCD2 sur `dim_game` dès maintenant | Nécessite des colonnes non présentes, augmente le temps de construction et ne répond à aucun besoin actuel (pas de changements observés). |
| Créer une dimension supplémentaire (ex. `dim_language`) en SCD2 | Aucun attribut de langue ne change ; la table `stg_reviews` ne définit pas de métadonnées évolutives pour la langue. |
| Conserver la modélisation actuelle sans étoile | La zone gold expose déjà une étoile (fait + deux dimensions) ; revenir à un modèle plat supprimerait les bénéfices de la normalisation. |

## Consequences

- **Simplicité** : la chaîne quotidienne reste inchangée, aucune charge supplémentaire de gestion de versions de dimension.  
- **Extensibilité** : si un besoin d’historisation apparaît (ex. renommage de jeux), il faudra introduire de nouvelles colonnes et ré‑écrire les modèles ; cela pourra être planifié dans un futur ADR.  
- **Tableau de bord** : aucune modification nécessaire ; les métriques quotidiennes (`mart_sentiment_daily`) continuent de s’appuyer sur les mêmes clés.  
- **Coût** : zéro coût de développement et de maintenance supplémentaire aujourd’hui.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

# ADR 0020 — Porte de qualite etendue aux zones silver et gold

**Date** : 19/09/2026 · **Statut** : acceptée

## Contexte

`expectations.py` ne couvrait que la zone propre. Les zones silver (Iceberg) et gold (DuckDB) n’avaient aucune suite, alors que la zone gold alimente directement le tableau de bord. Une porte de qualité devait être étendue sans toucher au module existant.

## Decision

Création du module `src/reviewpulse/expectations_lake.py`.  
Quatre suites portent sur `silver.reviews`, `silver.predictions`, les faits gold et le mart quotidien, soit **29 attentes** — chiffre corrigé le 20/09/2026 : l'exécution réelle du DAG en a évalué 29, 8 + 7 + 7 + 7 (`docs/evidence/dag_execution_reelle.md`), là où cet ADR en annonçait 28.  
Ajout de la tâche `gx_lake` dans le DAG quotidien, placée après `gold`, bloquante par son code de retour. Le DAG passe à **neuf tâches**.  
Le module `expectations.py` reste inchangé et continue de protéger la zone propre.  
`main` accepte une liste d’arguments, car un module lancé par Airflow ne peut pas lire `sys.argv`.  
Intégration des mutations **M23** et **M24** : relâchement de la borne d’une part, suppression du contrôle du format du pseudonyme d’auteur.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Étendre `expectations.py` | Refondre une porte qui fonctionne à quelques jours de la soutenance serait risqué. |
| Se contenter des **30 tests dbt déclarés** | Ils portent sur la zone gold, pas sur silver, et ne vérifient pas le format du pseudonyme. |
| Contrôler sans bloquer | Une porte qui n’arrête rien n’est pas une porte. |

## Consequences

- Une zone gold fausse arrête la chaîne au lieu d’être servie au tableau de bord.  
- Une étape supplémentaire dans le DAG quotidien.

## Preuves

- Les **29 attentes** sont vertes sur les données réelles.  
- Deux valeurs du mart sont volontairement cassées : part de négatifs à **1,7** et un jour à zéro avis, ce qui rend le verdict faux et fait échouer les deux attentes correspondantes.  
- **Sept tests unitaires** verts, dont celui qui vérifie qu’une table conforme passe.  
- Le DAG montre la tâche `gx_lake` bloquante et le nombre total de tâches à neuf.  
- Mutations **M23** et **M24** appliquées comme décrit.  

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

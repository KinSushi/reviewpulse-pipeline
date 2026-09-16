# ADR 0011 — Airflow et GitHub Actions

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'énoncé exige qu'une partie de la chaîne s'exécute seule (Airflow, cron ou GitHub Actions). Airflow est enseigné les 17 et 18/09.

## Décision

- **Airflow** : DAG `reviewpulse_daily` (6 h UTC : ingestion → transformation et contrôle → score) et DAG `reviewpulse_weekly_train` (lundi 7 h UTC : entraînement → score), deux nouvelles tentatives à 5 minutes, sans rattrapage.
- **GitHub Actions** : `ci.yml` (lint et tests à chaque modification) et `pipeline.yml` (exécution planifiée à 6 h 30 UTC, indépendante de toute machine locale, sel lu dans les secrets du dépôt).
- Le conteneur Airflow tourne avec l'**uid 1000 et le groupe 0**, comme les conteneurs applicatifs.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| cron seul | Pas de visibilité sur les échecs ni de nouvelles tentatives |
| Airflow seul | Dépend d'une machine allumée ; GitHub Actions sert de filet |
| Réentraîner chaque jour | Coût sans bénéfice : la distribution évolue lentement ; hebdomadaire suffit |

## Conséquences

- Airflow en mode `standalone` (base SQLite, une tâche à la fois) : adapté à la démo, **pas à la production** (voir schéma 06 : Airflow managé).
- La réactivation d'un DAG crée l'exécution planifiée de la dernière période : les DAG doivent limiter les exécutions simultanées.

## Preuves (16/09/2026)

- Premier essai : `PermissionError` sur `state/` et `clean/` (Airflow en uid 50000, fichiers créés en uid 1000). Corrigé par l'uid aligné.
- Ensuite : trois exécutions de `reviewpulse_daily` et une de `reviewpulse_weekly_train` **réussies** (ingestion, transformation, score en environ 60 s ; entraînement et score en environ 90 s).

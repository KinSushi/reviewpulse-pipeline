# ADR 0008 — Barrière de promotion et alias MLflow

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Le réentraînement est automatique (DAG hebdomadaire). Un modèle moins bon ne doit jamais remplacer celui en service sans décision.

## Décision

- Chaque entraînement crée une version dans le registre MLflow et reçoit l'alias `challenger`.
- L'alias `champion` n'est déplacé que si **F1 macro ≥ 0,75** et **strictement supérieur** au F1 du champion en place.
- L'API et le score chargent toujours `models:/reviewpulse-sentiment@champion`.

## Histoire du seuil

| Date | Seuil | Pourquoi |
|---|---|---|
| 16/09 matin | 0,80 | Hypothèse de la charte, non mesurée |
| 16/09 | 0,75 | Mesure : quatre variantes plafonnaient entre 0,756 et 0,766 sur la seule distribution naturelle |
| 16/09 soir | 0,75 maintenu | Avec l'ADR 0007, le modèle atteint 0,807 : l'objectif de 0,80 est atteint, la barrière garde une marge |

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Promouvoir chaque nouvelle version | Aucune protection contre une régression |
| Promotion manuelle uniquement | Contraire à l'automatisation demandée ; reste possible en déplaçant l'alias à la main |
| « Supérieur ou égal » | Un réentraînement identique changerait de version sans gain |

## Conséquences

- Si aucun champion n'existe (première installation) et que le premier modèle est sous la barrière, le score s'arrête : l'API répond **503** « Modèle indisponible ». Constaté le 16/09/2026.
- Retour arrière : déplacer l'alias `champion` vers la version précédente ; l'API le recharge au redémarrage.

## Preuves (16/09/2026)

- Version 1 (F1 0,7498) : non promue.
- Version 2 (F1 0,807) : promue.
- Version 3, mêmes données : **F1 identique** → non promue (reproductibilité et règle « strictement supérieur »).
- Version 5 (DAG hebdomadaire, données enrichies, F1 0,798) : non promue, la version 2 reste servie.
- Tests : `test_train_score.py`, `test_artifacts_location.py` (503) ; contrôle M1 de `tools/forward_test.py`.

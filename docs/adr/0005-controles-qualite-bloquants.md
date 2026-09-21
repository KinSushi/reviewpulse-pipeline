# ADR 0005 — Contrôles qualité bloquants

**Date** : 16/09/2026 · **Statut** : acceptée (Great Expectations prévu en complément)

## Contexte

L'énoncé exige « au moins un test de qualité ». Une donnée fausse qui atteint le modèle dégrade la production sans bruit.

## Décision

`quality.check_clean` vérifie, **avant** l'écriture de la zone propre : colonnes et types exacts, au moins une ligne, identifiants non nuls et uniques, étiquette dans {0, 1}, langue autorisée, texte non vide, absence de colonnes interdites, format du pseudonyme, flux connu, part de négatifs **naturels** entre 0,5 % et 95 %. Un seul échec arrête la tâche (code 1, exception Airflow) : la zone propre précédente reste en place.

## Alternatives écartées

| Option | Pourquoi écartée à ce stade |
|---|---|
| Great Expectations seul | Cours du 21/09 ; sera ajouté en complément, avec rapport HTML (Data Docs) |
| Contrôles informatifs non bloquants | Laisseraient passer une donnée corrompue jusqu'au modèle |

## Conséquences

- Le pipeline peut s'arrêter : c'est voulu, et visible dans Airflow (tâche rouge, deux nouvelles tentatives).

## Preuves

Tests : `test_transform_quality.py`, `test_boost.py` ; contrôle F2 de `tools/forward_test.py` sur la zone propre réelle ; tests inverses : `tests/reverse/mutations.json`.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

# ADR 0007 — Avis négatifs complémentaires et seuil appris

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Avec 9 % d'avis négatifs, le modèle plafonnait vers 0,75 de F1 macro : un entraînement du 16/09 a donné **0,7498**, juste sous la barrière de promotion (ADR 0008), et le pipeline s'est arrêté faute de champion. L'API Steam accepte `review_type=negative`.

## Décision

1. Un **second flux** collecte des avis négatifs (`review_type=negative`), stocké à part (`sample=negative_boost`).
2. Ces avis servent **uniquement à l'entraînement**.
3. Le **test est tiré à 100 % des avis naturels** : la mesure reflète la production.
4. Le **seuil de décision** est choisi par validation croisée à 5 plis **sur les avis naturels d'entraînement** (le flux complémentaire est ajouté à chaque pli d'entraînement, jamais évalué), dans la grille 0,30 à 0,80, en maximisant le F1 macro hors-plis.
5. Un avis présent dans les deux flux est gardé comme naturel.
6. Les indicateurs du tableau de bord et le résumé quotidien **n'agrègent que les avis naturels**.

## Alternatives écartées

| Option | Pourquoi écartée |
|---|---|
| Baisser encore la barrière de promotion | Revient à changer la règle pour faire passer le résultat |
| Choisir le seuil sur le jeu de test | Fuite d'information : la mesure serait optimiste |
| Mélanger les deux flux dans le test | Le test ne représenterait plus la production (4 % à 18 % de négatifs selon le jeu) |
| Suréchantillonnage synthétique (SMOTE) | Peu adapté à du texte vectorisé ; des avis réels sont disponibles gratuitement |

## Mesures (même test naturel de 1 192 avis dont 108 négatifs)

| | F1 macro | Rappel négatifs | Précision négatifs | AUC |
|---|---|---|---|---|
| Naturel seul, seuil 0,5 | 0,750 | 0,611 | 0,500 | 0,896 |
| + 2 263 négatifs, seuil 0,7 | 0,798 | 0,667 | 0,605 | 0,928 |
| **Stack déployée, seuil appris 0,75** | **0,807** | 0,639 | 0,657 | 0,948 |

F1 macro hors-plis au seuil retenu : 0,802.

## Conséquences

- Contrôle de cohérence en production : part négative prédite ÷ réelle entre **0,79 et 1,21** selon le jeu et la langue (16/09/2026).
- Le seuil voyage avec le modèle (`decision_threshold_`) et est affiché par l'API et le tableau de bord.

## Preuves

Tests : `test_boost.py` (flux séparés, priorité naturelle, taille du test naturel, seuil dans la grille, résumé limité au naturel) ; contrôles F4 et F5 de `tools/forward_test.py`.

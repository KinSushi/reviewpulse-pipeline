# ADR 0009 — Convention de décision centralisée

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

L'étiquette Steam vaut 1 pour un avis positif, 0 pour un négatif. Le métier raisonne sur la **probabilité d'être négatif**. Cette double convention a été **inversée deux fois** :

1. dans l'entraînement : F1 = 0,0 sur un jeu de test séparable (détecté par les tests) ;
2. dans le score : **95 % d'avis prédits négatifs pour 4 % réels**, précision 0,024 (détecté par le contrôle visuel du tableau de bord, puis confirmé sur les données).

## Décision

Un module unique, `reviewpulse/decision.py`, détient la convention : `LABEL_NEGATIVE`, `LABEL_POSITIVE`, `negative_proba` (qui lit `model.classes_` au lieu de supposer l'ordre des colonnes), `model_threshold`, `predict_labels`, `label_name`. Entraînement, score, API et tableau de bord n'écrivent **aucune** comparaison au seuil.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Réétiqueter (1 = négatif) | Contredit la source et tous les fichiers déjà produits |
| Corriger chaque endroit séparément | C'est exactement ce qui a produit la seconde inversion |

## Preuves

- Recherche du 16/09/2026 : aucune comparaison au seuil hors de `decision.py`.
- Tests : `test_decision.py` (convention, ordre des classes, **test de sens de bout en bout**) ; contrôles A2 et F4 de `tools/forward_test.py` ; mutation « inversion du seuil » dans `tests/reverse/mutations.json`.

# ADR 0019 — Explicabilite par contribution lineaire exacte

**Date** : 19/09/2026 · **Statut** : acceptee

## Contexte

Le référentiel du bloc AIA 4 cite SHAP et LIME.  
Le modèle utilisé est un TF‑IDF sur des n‑grammes de caractères suivi d’une régression logistique.  
La fonction de décision est linéaire : chaque terme contribue exactement par son poids TF‑IDF multiplié par le coefficient de la classe négative.

## Decision

Implémentation dans `src/reviewpulse/explain.py` avec les fonctions `global_terms`, `local_contributions` et `explain_batch`.  
Le point d’accès `/explain` de l’API expose ces contributions.  
Une section du tableau de bord affiche les termes qui pèsent dans la prédiction.  
La somme des contributions reproduit exactement la valeur de la fonction de décision, conformément à la charte.

## Alternatives ecartees

| Option | Pourquoi |
|---|---|
| SHAP | Approximation par échantillonnage, lourde, plus lente, moins exacte ici car la valeur exacte est calculable |
| LIME | Substitut local linéaire d’un modèle déjà linéaire, redondant |
| aucune explicabilité | La charte promettait les termes qui influencent la prédiction |

## Consequences

L’explication est exacte et instantanée, sans dépendance supplémentaire.  
Cette décision devra être revue si le modèle devient un réseau profond, prévu en octobre pour le bloc CDSD 4, moment où SHAP redeviendra pertinent dès que la fonction de décision ne sera plus linéaire.

## Preuves

Un test vérifie que la somme des contributions égale la fonction de décision.  
La charte promettait « les termes qui pèsent dans la prédiction » ; la promesse est tenue.  
La mutation M21, qui inverse le signe des coefficients de la classe négative, est détectée par la batterie de tests.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

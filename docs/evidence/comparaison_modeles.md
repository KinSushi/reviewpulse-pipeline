# Banc de comparaison des familles de modèles

*Date :* 2026-09-21T09:23:40.096371+00:00
*Commit :* `b600144` · *Exécution :* workflow `comparaison.yml`, run `35581880785`, runner GitHub `ubuntu-latest`, 21/09/2026

## Données

- Avis naturels : 2974
- Avis complémentaires : 2484
- Part d'avis négatifs : 0.1049

## Protocole

1. Données : avis `sample_source == SAMPLE_NATURAL` pour X et y ; autres avis pour `boost_df`, ajoutés à l'entraînement de chaque pli uniquement.
2. Validation croisée stratifiée à 5 plis, même graine et mêmes plis pour tous les candidats.
3. Probabilités négatives hors pli via `decision.negative_proba`.
4. Seuil optimal dans `config.THRESHOLD_GRID` maximisant le F1 macro hors pli ; métriques au seuil retenu.
5. Durée moyenne d'entraînement par pli et latence de prédiction pour 1 000 avis (dernier pli).

## Tableau comparatif

| Candidat | F1 macro hors plis | Seuil | AUC | Rappel négatifs | Précision négatifs | Entraînement par pli (s) | Latence 1 000 avis (ms) | Famille | Explication exacte |
|---|---|---|---|---|---|---|---|---|---|
| logreg_caracteres | 0.8116 | 0.775 | 0.9290 | 0.6955 | 0.6364 | 3.67 | 285.53 | lineaire | oui |
| svm_lineaire | 0.8072 | 0.775 | 0.9292 | 0.6795 | 0.6347 | 2.91 | 282.81 | marge | non |
| sgd_modified_huber | 0.8032 | 0.750 | 0.9213 | 0.6731 | 0.6269 | 2.49 | 279.56 | lineaire | oui |
| ridge | 0.7985 | 0.775 | 0.9284 | 0.6667 | 0.6172 | 3.18 | 289.62 | lineaire | non |
| logreg_mots | 0.7847 | 0.775 | 0.9253 | 0.6442 | 0.5912 | 2.25 | 41.79 | lineaire | oui |
| gradient_boosting_sur_svd | 0.7360 | 0.800 | 0.9045 | 0.7051 | 0.4427 | 10.34 | 351.45 | arbres | non |
| xgboost | 0.7345 | 0.800 | 0.9030 | 0.6346 | 0.4626 | 83.53 | 293.87 | arbres | non |
| foret_aleatoire | 0.7189 | 0.700 | 0.8645 | 0.5192 | 0.4807 | 8.91 | 399.79 | arbres | non |
| bayes_naif_complementaire | 0.6681 | 0.800 | 0.9029 | 0.8494 | 0.3189 | 2.52 | 282.83 | bayesien | oui |

## Lecture

Le meilleur candidat est **logreg_caracteres** avec un F1 macro hors plis de 0.8116.
Écart au modèle en service (logreg_caracteres, F1 = 0.8116) : +0.0000.
Cet écart est inférieur à l'erreur type des plis du modèle en service (0.0170) ; il n'est pas interprétable comme un gain significatif.
Le modèle en service reste le meilleur candidat mesuré ici.

## Ce que ce banc ne mesure pas

Aucun modèle de type transformeur ni plongement de phrases n'est évalué. Il faudrait télécharger un modèle de plusieurs centaines de Mo, et l'image du projet ne l'embarque pas. C'est le candidat suivant si un meilleur score devenait nécessaire.

## Provenance, et ce que ce rapport ne dit pas

Ce rapport est **écrit par l'outil** `tools/comparaison_modeles.py` ; seules cette section et la ligne de
provenance ont été ajoutées à la main. Il a été produit sur un runner GitHub, à partir d'une zone brute
vide : les avis ont été collectés en direct sur l'API Steam (`REVIEWPULSE_MAX_PAGES=5`), passés par la zone
silver et par la porte de qualité, puis mesurés. XGBoost 2.1.4 (`xgboost-cpu`) a été installé **pour ce banc
seulement** : ce n'est pas une dépendance du projet.

Deux limites à dire avec les chiffres :

- le jeu du runner compte **2 974 avis naturels**, moins que le lac de la machine de développement ; le
  classement est net, mais les valeurs absolues dépendent du jeu du jour ;
- le modèle en service a été **réglé** (12 points, 20/09/2026), les autres candidats sont à des réglages
  raisonnables mais **non optimisés**. Un écart faible en leur défaveur ne prouverait donc rien — et c'est
  pourquoi la décision (ADR 0030) ne s'appuie que sur les écarts qui dépassent l'écart-type des plis.

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

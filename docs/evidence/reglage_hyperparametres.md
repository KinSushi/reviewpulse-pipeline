# Rapport de réglage d’hyperparamètres
*Date :* 2026-09-20T06:58:25.426024+00:00
*Commit :* 500d353

## Tableau des essais

| C | n‑grammes | max_features | f1_mean | f1_std | durée (s) |
|---|-----------|--------------|--------|-------|-----------|
| 10.0 | (2, 5) | 100000 | 0.7517 | 0.0068 | 52.4 |
| 10.0 | (2, 5) | 50000 | 0.7467 | 0.0065 | 46.1 |
| 10.0 | (2, 4) | 50000 | 0.7441 | 0.0119 | 52.2 |
| 10.0 | (2, 4) | 100000 | 0.7441 | 0.0119 | 50.7 |
| 4.0 | (2, 5) | 100000 | 0.7437 | 0.0068 | 42.3 |
| 4.0 | (2, 5) | 50000 | 0.7422 | 0.0087 | 41.5 |
| 4.0 | (2, 4) | 50000 | 0.7395 | 0.0073 | 40.3 |
| 4.0 | (2, 4) | 100000 | 0.7395 | 0.0073 | 37.6 |
| 1.0 | (2, 5) | 50000 | 0.7152 | 0.0127 | 38.5 |
| 1.0 | (2, 5) | 100000 | 0.7151 | 0.0106 | 34.4 |
| 1.0 | (2, 4) | 50000 | 0.7076 | 0.0098 | 27.8 |
| 1.0 | (2, 4) | 100000 | 0.7076 | 0.0098 | 29.4 |

## Analyse

Le meilleur point est **C=10.0, ngram_range=(2, 5), max_features=100000** avec un `f1_mean` de 0.7517.
Il dépasse le point courant (C=4.0, ngram_range=(2, 5), max_features=100000) de **0.0081** points de `f1_mean`.
Cet écart est supérieur à l’écart‑type du point courant (0.0068), il est donc **significatif** et le nouveau point doit être retenu.
## Relecture critique de ce rapport — 20/09/2026

**Le test écrit ci-dessus n'est pas le bon**, même si sa conclusion tient. Il compare une
**différence de moyennes** à la **dispersion interne d'un seul point** (l'écart-type entre plis).
Ce sont deux grandeurs de nature différente. Le repère correct pour une différence de moyennes
sur *k* plis est l'**erreur type de la moyenne**, soit `écart-type / √k` = 0,0068 / √5 =
**0,0030**. Le gain de 0,0081 vaut donc environ **2,7 erreurs types** : il est significatif, mais
pour cette raison-là, pas pour celle qu'écrit le rapport engendré.

**Deux faits indépendants renforcent la conclusion** :

1. La tendance est **monotone** en `C` : 0,708 à C=1, 0,744 à C=4, 0,752 à C=10. Une progression
   ordonnée sur trois valeurs n'est pas un accident d'échantillonnage.
2. Un **premier passage**, effectué avant la correction d'un import manquant et sur un état
   antérieur de la zone propre, donnait le même écart : 0,7432 pour le point courant contre
   0,7516 pour le meilleur, soit **0,0084**. Deux mesures séparées, le même gain.

**Une réserve qui compte** : entre ces deux passages, l'écart-type du point courant est passé de
0,0153 à 0,0068. La graine est pourtant fixe. L'explication n'est pas une instabilité du code
mais un **changement des données** : le DAG quotidien a tourné entre les deux, de 04:12 à 04:46
UTC, et a ingéré de nouveaux avis. C'est la démonstration concrète de ce que l'ADR 0018 appelle
la seule source de variation du projet — l'ingestion en direct — et la raison pour laquelle
chaque run MLflow porte l'empreinte de son jeu de données.

**Ce que ce rapport n'établit pas.** Les chiffres ci-dessus proviennent d'une validation croisée
à 5 plis sur la zone propre entière. Ils ne sont **pas comparables** au F1 macro annoncé par le
projet (0,797), qui est mesuré sur un jeu de test séparé, après filtrage du flux naturel. Les
douze points sont comparables **entre eux**, et à rien d'autre.

**Décision.** Le point `C=10.0` est adopté dans `train.py`, mais la décision finale n'est pas
prise par ce rapport : elle revient à la **barrière de promotion** de MLflow (ADR 0008), qui
refuse un modèle qui ne serait pas strictement meilleur que le champion en service. Si elle
refuse, le champion actuel reste, et nous aurons la preuve d'avoir cherché.

## Verdict de la barrière de promotion — 20/09/2026

Le rapport ci-dessus ne décide pas : la barrière décide. Elle a été interrogée deux fois le même
jour, sur la même zone propre (8 768 lignes, empreinte `b1e0580575d9…`).

| | `C=4.0` (version 6) | `C=10.0` (version 5) |
|---|---|---|
| F1 macro, jeu de test | 0,7997 | **0,8027** |
| F1 macro, entraînement | 0,9177 | 0,9557 |
| Écart entraînement-test | 0,1181 | **0,1529** |
| Rappel des négatifs | — | 0,6496 |
| AUC | — | 0,9402 |
| **Promu** | **non** | **oui** |

**Ce que cela démontre, au-delà du réglage** : la barrière a **promu** un modèle et **refusé**
l'autre dans la même heure. Elle fonctionne dans les deux sens, et c'est mesuré, pas affirmé.

**La réserve, et pourquoi elle ne change pas la décision.** `C=10.0` élargit l'écart
entraînement-test de 0,118 à 0,153, soit 30 % de plus, pour 0,0030 de gain sur le jeu de test —
environ quatre avis sur 1 303. Un écart qui se creuse est le signe attendu d'une régularisation
plus faible. Il ne suffit pourtant pas à refuser le point : la **validation croisée à 5 plis**
mesure la généralisation sur cinq découpages au lieu d'un, et c'est elle qui donne `C=10.0`
gagnant de 0,0081. Un écart d'apprentissage se lit, il ne se vote pas contre une mesure de
généralisation plus fiable.

**Ce qu'il reste à faire** : le projet n'a **aucun test automatique** de sur- et
sous-apprentissage, alors que c'est un critère transverse du référentiel CDSD. L'écart est
désormais journalisé dans chaque run MLflow (`f1_macro_train`), mais rien ne se déclenche s'il
dérive. Sujet **R53**.

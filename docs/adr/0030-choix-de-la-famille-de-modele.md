# ADR 0030 — Régression logistique plutôt qu'une autre famille de modèles

**Date** : 21/09/2026 · **Statut** : acceptée

## Contexte

Le projet avait mesuré des **variantes d'un même modèle** : mots contre caractères (ADR 0006), flux
complémentaire et seuil (ADR 0007), régularisation (réglage du 20/09/2026). Aucune de ces mesures ne
répondait à la question qu'Enzo a posée le 21/09, et qu'un jury posera : **« ne peut-on pas obtenir
un meilleur score avec un autre modèle ? »** Jusqu'ici, la réponse était une opinion.

Un modèle de cette chaîne n'est pas jugé sur son seul score. Six critères, dans l'ordre où ils
pèsent pour l'utilisateur et pour l'exploitation :

| # | Critère | D'où il vient |
|---|---|---|
| 1 | F1 macro et **rappel des avis négatifs** sur des avis naturels | la charte : l'utilisateur cherche les avis négatifs à lire |
| 2 | **Explication exacte**, terme par terme | promesse de la charte, servie par `/explain` et le tableau de bord (ADR 0019) |
| 3 | Servable sur processeur seul, p99 à chaud sous la seconde | essai de charge, ADR 0029 |
| 4 | Réentraînement en secondes | DAG hebdomadaire, réentraînement déclenché par la dérive, chaîne rejouée en CI |
| 5 | Déterminisme | deux entraînements donnent le même F1 à la seizième décimale (ADR 0018) |
| 6 | Aucune dépendance lourde de plus dans l'image | la place disque a déjà coûté une nuit au projet |

## Règle de décision — écrite avant de lire les résultats

Le 21/09/2026 à 3 h 20, pendant que le banc tournait et avant qu'un seul chiffre ne sorte :

> Le modèle en service est remplacé si, et seulement si, un candidat (1) dépasse son F1 macro hors
> plis de **plus d'un écart-type par pli**, (2) **ne dégrade pas le rappel des avis négatifs**, et
> (3) reste servable sous les mêmes contraintes. **À gain égal — dans l'écart-type — le modèle
> explicable exactement l'emporte.**

Fixer la règle d'abord est ce qui empêche de l'ajuster au résultat.

## Mesure

`tools/comparaison_modeles.py`, exécuté sur un runner GitHub (run `35581880785`) à partir d'une zone
brute vide : **2 974 avis naturels** collectés en direct, 2 484 avis du flux complémentaire, 10,5 %
de négatifs. Protocole identique pour les neuf candidats, et identique à celui de `train.py` : les
**mêmes cinq plis**, le flux complémentaire ajouté à l'entraînement de chaque pli et **jamais** à la
validation, probabilités hors plis par `decision.negative_proba`, seuil choisi sur
`config.THRESHOLD_GRID`. Rapport complet : [`evidence/comparaison_modeles.md`](../evidence/comparaison_modeles.md).

| Candidat | Famille | F1 macro hors plis | AUC | Rappel négatifs | Entraînement par pli | Explication exacte |
|---|---|---|---|---|---|---|
| **Régression logistique, caractères 2-5 (en service)** | linéaire | **0,8116** | 0,9290 | **0,6955** | 3,7 s | **oui** |
| SVM linéaire, calibrée | marge | 0,8072 | 0,9292 | 0,6795 | 2,9 s | non |
| SGD, perte *modified Huber* | linéaire | 0,8032 | 0,9213 | 0,6731 | 2,5 s | oui |
| Ridge, calibrée | linéaire | 0,7985 | 0,9284 | 0,6667 | 3,2 s | non |
| Régression logistique, mots 1-2 | linéaire | 0,7847 | 0,9253 | 0,6442 | 2,3 s | oui |
| Gradient boosting sur SVD (200 composantes) | arbres | 0,7360 | 0,9045 | 0,7051 | 10,3 s | non |
| **XGBoost** (400 arbres, profondeur 6) | arbres | 0,7345 | 0,9030 | 0,6346 | **83,5 s** | non |
| **Forêt aléatoire** (300 arbres) | arbres | 0,7189 | 0,8645 | 0,5192 | 8,9 s | non |
| Bayes naïf complémentaire | bayésien | 0,6681 | 0,9029 | 0,8494 | 2,5 s | oui |

Écart-type du F1 par pli du modèle en service : **0,0170**. Le **témoin** tient : le candidat en
service retrouve 0,8116, dans la marge attendue autour de 0,80 — le banc reproduit bien le protocole.

## Décision

**La régression logistique sur n-grammes de caractères reste le modèle en service.** Aucun candidat
ne satisfait la règle, et la mesure dit pourquoi famille par famille :

- **SVM linéaire** : −0,0044 de F1, quatre fois moins que l'écart-type des plis. C'est une
  **égalité statistique** — et la SVM ne donne pas de probabilités : il faut la calibrer, et un
  modèle calibré n'a plus de coefficients qu'on puisse lire terme par terme. À gain égal, le modèle
  explicable l'emporte : la règle tranche.
- **Arbres — XGBoost, gradient boosting, forêt aléatoire** : de −0,076 à −0,093 de F1, soit quatre à
  cinq écarts-types. Le résultat est attendu sur ce type de données : 100 000 n-grammes très creux
  pour moins de 6 000 textes courts — un espace où une frontière linéaire suffit et où des arbres
  découpent axe par axe sans jamais rassembler assez de signal. XGBoost coûte en plus **23 fois** le
  temps d'entraînement (83,5 s contre 3,7 s par pli), une dépendance de plus, et l'explication exacte.
- **Bayes naïf complémentaire** : le meilleur rappel du banc (0,849) mais une précision de 0,319 —
  deux avis signalés sur trois seraient positifs. Pour un outil de priorisation de lecture, c'est
  noyer l'utilisateur. F1 0,668.
- **SGD** et **Ridge** : même famille que le modèle en service, un peu en dessous, sans avantage.
- **Régression logistique sur mots** : −0,027. Elle confirme l'ADR 0006 sur un jeu neuf, et montre
  son seul atout — une vectorisation sept fois plus rapide (42 ms contre 286 ms pour 1 000 avis).

Un enseignement de conception sort du tableau : **la latence ne dépend pas de la famille** — tous
les candidats sur caractères sont à 280–400 ms pour 1 000 avis, parce que c'est la vectorisation qui
coûte, pas le classifieur. Changer de modèle n'achèterait donc aucune latence.

## Ce que cette mesure ne dit pas

- Le modèle en service a été **réglé** ; les autres candidats sont à des réglages raisonnables,
  **non optimisés**. Un écart faible en leur défaveur ne prouverait rien — d'où une règle qui
  n'écoute que les écarts dépassant l'écart-type. Les arbres, eux, sont à quatre écarts-types :
  aucun réglage plausible ne les ramène.
- Le jeu du runner compte 2 974 avis naturels ; le classement est net, les valeurs absolues
  dépendent du jeu du jour.
- **Aucun transformeur ni plongement de phrases n'est mesuré.** C'est le candidat suivant si un
  meilleur score devenait nécessaire, et son prix est connu d'avance : un modèle de plusieurs
  centaines de Mo dans l'image, une inférence plus lente d'un à deux ordres de grandeur sur
  processeur, et une explication approchée au lieu d'exacte. La consigne du Demo Day le dit aussi :
  « The model is the easy part » — la note est dans la chaîne.

## Conséquences

- Le choix du modèle n'est plus une opinion : il se rejoue par `make comparaison`, ou à la demande
  sur GitHub par le workflow `comparaison.yml`, et se relit dans `evidence/comparaison_modeles.md`.
- L'outil porte six tests, dont le témoin (le candidat en service **est** `train.build_pipeline()`)
  et celui qui compte (aucun avis du flux complémentaire n'est jamais validé).
- XGBoost n'entre **pas** dans les dépendances du projet : l'outil le traite comme optionnel et
  écrit « non mesuré » s'il manque.
- Condition de révision : un candidat qui satisferait la règle sur le lac complet, ou un besoin
  métier qui ferait passer le rappel avant l'explication — la décision serait alors à reprendre
  avec Enzo, chiffres, coût et perte à l'appui.

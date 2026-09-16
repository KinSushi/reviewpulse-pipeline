# ADR 0006 — Modèle ML sur n-grammes de caractères

**Date** : 16/09/2026 · **Statut** : acceptée

## Contexte

Classer des avis courts, en deux langues, avec une étiquette fournie par la source. L'énoncé demande de choisir ML ou LLM « selon la tâche ».

## Décision

`TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=100000, sublinear_tf=True)` puis `LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000)`, suivi dans MLflow.

**ML plutôt que LLM, en une phrase** : la tâche est une classification binaire avec une étiquette déjà fournie, qu'un modèle linéaire résout en quelques secondes, explique terme par terme et sert gratuitement.

## Alternatives mesurées (16/09/2026, 5 974 avis naturels, test stratifié de 1 195 avis)

| Variante | F1 macro | Rappel négatifs | AUC |
|---|---|---|---|
| Mots 1-2 grammes, C=1 (première version) | 0,735 | 0,611 | 0,920 |
| Mots 1-2 grammes, C=4 | 0,756 | 0,556 | 0,923 |
| **Caractères 2-5, C=4 (retenue)** | **0,759** | **0,639** | 0,923 |
| Mots + caractères, C=4 | 0,760 | 0,574 | 0,931 |

La variante retenue a le **meilleur rappel des négatifs** (la métrique métier) pour un F1 équivalent, avec un seul vectoriseur. Les n-grammes de caractères tolèrent les fautes, l'argot et le mélange anglais-français.

## Alternatives écartées sans mesure

| Option | Pourquoi |
|---|---|
| LLM (zéro exemple) | Coût et latence par avis ; pas nécessaire avec une étiquette fournie ; hors périmètre du 25/09 |
| Réseau profond | Réservé au bloc 4 du CDSD (octobre), branché dans la même chaîne |

## Conséquences

- Explicabilité : les 20 termes les plus négatifs et positifs sont enregistrés à chaque entraînement (`artifacts/top_terms.json`).
- Plafond constaté à environ 0,76 de F1 sur la seule distribution naturelle : traité par l'ADR 0007.

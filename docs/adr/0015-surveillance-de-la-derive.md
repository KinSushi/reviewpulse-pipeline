# ADR 0015 — surveillance de la dérive

**Date** : 18/09/2026 · **Statut** : proposée

## Contexte

Le modèle est réentraîné chaque semaine et promu uniquement si le F1 macro dépasse 0,75 et est strictement supérieur au champion en place (ADR 0008).
À ce jour, aucune mesure ne suit l’évolution des données d’entrée (zone propre) ni la stabilité des prédictions quotidiennes : aucune alerte, aucun déclencheur de réentraînement.

## Décision

- **Entrées** : calcul du *Population Stability Index* (PSI) sur les colonnes d’intérêt de la zone propre (`text_len`, `language`, `app_id`, `sample_source`) via `reviewpulse.drift.derive_entrees`.
  - Fenêtre de référence : moitié la plus ancienne de la zone propre (triée par `created_at` ou `updated_at`).
  - Seuils d’interprétation : PSI < 0,1 → *stable* ; 0,1 ≤ PSI < 0,2 → *à surveiller* ; PSI ≥ 0,2 → *dérive* (fonction `interpretation`).

- **Prédictions** : comparaison, pour chaque groupe (`app_id`, `language`, `date`), des parts de négatifs prédites (`share_negative_pred`) et réelles (`share_negative_true`) issues du résumé quotidien (`reviewpulse.score.summarize`).
  - Un ratio hors de l’intervalle acceptable (défini par la charte : 0,79 ≤ ratio ≤ 1,21) est signalé.
  - Le calcul est implémenté dans `reviewpulse.drift.derive_predictions`.

- **Rapport** : les résultats PSI (avec interprétation) et les éventuels écarts de ratio sont écrits dans le répertoire *scored* sous forme de `drift_report.json` (voir `reviewpulse.drift.main`).

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Test de Kolmogorov-Smirnov | Nécessite des distributions continues et n’est pas adapté aux variables catégorielles présentes (language, app_id). |
| Divergence de Kullback-Leibler | Sensible aux zéros, requiert un lissage complexe ; le PSI gère déjà ce problème avec un epsilon. |
| Bibliothèque dédiée de détection de dérive (ex. `alibi-detect`) | Ajoute une dépendance lourde pour un besoin déjà couvert par le PSI et le ratio de prédiction implémentés en interne. |

## Conséquences

- **Ce que cela permet** : disposer d’un indicateur quantitatif de la stabilité des caractéristiques d’entrée et d’un contrôle quotidien de la cohérence entre parts négatives prédites et réelles.
- **Ce qui n’est pas encore couvert** : aucune alerte automatisée n’est générée, aucun déclencheur de réentraînement n’est mis en place ; le rapport doit être consulté manuellement ou intégré ultérieurement à un job d’alerting.

## Preuves

- Le module `src/reviewpulse/drift.py` implémente PSI, dérive des entrées et des prédictions, ainsi que la génération du rapport JSON.
- Les tests unitaires associés (`test_drift.py` ou équivalent) existent dans le dépôt mais n’ont pas encore été exécutés (aucune mesure à ce jour).
- Le plan de monitoring (docs/14_plan_monitoring.md) décrit les signaux de dérive qui seront couverts par cette décision.

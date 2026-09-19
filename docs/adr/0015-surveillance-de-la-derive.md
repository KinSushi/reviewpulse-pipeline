# ADR 0015 — Surveillance de la dérive

**Date** : 18/09/2026, **révisée le 19/09/2026** · **Statut** : acceptée

## Contexte

Le modèle est réentraîné chaque semaine et promu uniquement si le F1 macro dépasse 0,75 et est strictement supérieur au champion en place (ADR 0008).
À ce jour, aucune mesure ne suit l’évolution des données d’entrée (zone propre) ni la stabilité des prédictions quotidiennes : aucune alerte, aucun déclencheur de réentraînement.

## Décision

- **Entrées** : calcul du *Population Stability Index* (PSI) sur les colonnes d’intérêt de la zone propre (`text_len`, `language`, `app_id`, `sample_source`) via `reviewpulse.drift.derive_entrees`.
  - **Périmètre : le flux naturel seul.** Le flux `negative_boost` est une collecte ponctuelle destinée à l’entraînement ; il n’arrive jamais en production. Sa présence dans la seule fenêtre ancienne faisait mesurer notre méthode de collecte au lieu de la population. La zone gold applique déjà ce filtre (`mart_sentiment_daily`).
  - Fenêtre de référence : moitié la plus ancienne du flux naturel (triée par `created_at` ou `updated_at`).
  - Seuils d’interprétation : PSI < 0,1 → *stable* ; 0,1 ≤ PSI < 0,2 → *à surveiller* ; PSI ≥ 0,2 → *dérive* (fonction `interpretation`).
  - **Seules les colonnes de `COLONNES_ALERTE` peuvent lever une alerte** — aujourd’hui `text_len` seul. `language` et `app_id` restent dans le rapport à titre informatif : leur composition est imposée par notre plan de collecte (`config.APP_IDS` × `config.LANGUAGES`), pas observée sur une population.

- **Prédictions** : comparaison, pour chaque groupe (`app_id`, `language`, `date`), des parts de négatifs prédites (`share_negative_pred`) et réelles (`share_negative_true`) issues du résumé quotidien (`reviewpulse.score.summarize`).
  - Un ratio hors de l’intervalle acceptable (défini par la charte : 0,79 ≤ ratio ≤ 1,21) est signalé.
  - Le calcul est implémenté dans `reviewpulse.drift.derive_predictions`.

- **Rapport** : les résultats PSI (avec interprétation) et les éventuels écarts de ratio sont écrits dans le répertoire *scored* sous forme de `drift_report.json` (voir `reviewpulse.drift.main`).

- **Alerte hors journal** : `drift.evaluer_alerte` rend un verdict (`alerte`, `motifs`, `psi_max`, `colonne_psi_max`, `part_hors_bornes`, `colonnes_surveillees`), ajouté au rapport sous la clé `alerte`. Quand l’alerte est levée, `drift.ecrire_alerte` écrit un fichier daté `scored/alertes/derive_<AAAAMMJJ-HHMMSS>.json` portant l’horodatage UTC et le commit (`REVIEWPULSE_COMMIT`). Seuils : PSI ≥ 0,2 sur une colonne surveillée, ou plus de 10 % de couples (jeu, langue, jour) hors des bornes de la charte.

- **Réentraînement déclenché par la dérive** : dans `reviewpulse_daily`, un `ShortCircuitOperator` (`derive_exige_reentrainement`) relit le rapport avec la seule bibliothèque standard — l’interpréteur d’Airflow n’a pas les dépendances du projet (ADR 0013) — et, si l’alerte est levée, un `TriggerDagRunOperator` (`declencher_reentrainement`) déclenche `reviewpulse_weekly_train`. Le court-circuit est placé **en dérivation** de `drift` : la zone gold n’est jamais sautée. Un rapport absent ou illisible rend `False` : une alerte perdue ne doit pas provoquer un réentraînement par accident.

## Alternatives écartées

| Option | Pourquoi |
|---|---|
| Test de Kolmogorov-Smirnov | Nécessite des distributions continues et n’est pas adapté aux variables catégorielles présentes (language, app_id). |
| Divergence de Kullback-Leibler | Sensible aux zéros, requiert un lissage complexe ; le PSI gère déjà ce problème avec un epsilon. |
| Bibliothèque dédiée de détection de dérive (ex. `alibi-detect`) | Ajoute une dépendance lourde pour un besoin déjà couvert par le PSI et le ratio de prédiction implémentés en interne. |

## Conséquences

- **Ce que cela permet** : disposer d’un indicateur quantitatif de la stabilité des caractéristiques d’entrée et d’un contrôle quotidien de la cohérence entre parts négatives prédites et réelles.
- **Ce qui n’est pas encore couvert** : le canal d’alerte est un fichier daté sur le disque, pas un webhook ni un courriel ; c’est suffisant pour être auditable et localisable, pas pour réveiller quelqu’un la nuit.

## Preuves

- Le module `src/reviewpulse/drift.py` implémente PSI, dérive des entrées et des prédictions, ainsi que la génération du rapport JSON.
- `tests/test_drift.py` : **11 tests verts** le 19/09/2026, dont `test_evaluer_alerte_ignore_les_colonnes_de_collecte`, qui porte son témoin (la même dérive sur une colonne surveillée lève bien l’alerte).
- Mesure du 19/09/2026 sur les données réelles, flux naturel seul (6 386 lignes sur 8 640) : `text_len` 0,036 (*stable*), `language` 3,098 et `app_id` 0,332 — informatifs. La fenêtre ancienne est à 85 % francophone, la récente à 91 % anglophone : c’est le plan de collecte, pas la population. Seule la part hors bornes, 10,13 %, lève l’alerte, et le fichier `scored/alertes/derive_20260919-153751.json` a bien été écrit.
- `airflow tasks list reviewpulse_daily` rend **huit tâches**, `derive_exige_reentrainement` et `declencher_reentrainement` comprises, sans erreur d’import.
- Le plan de monitoring (docs/14_plan_monitoring.md) décrit les signaux de dérive qui seront couverts par cette décision.

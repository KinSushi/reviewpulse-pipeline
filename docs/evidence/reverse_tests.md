# Rapport de tests inverses – 2026-09-16 23:11:54Z

Commit : `a274445+mlflow3`

Témoin : 54 passed in 126.15s (0:02:06)

| id | défaut simulé | pourquoi c’est grave | statut | résumé pytest | test qui détecte |
|---|---------------|----------------------|--------|---------------|-----------------|
| M01 | Convention de décision inversée | Défaut réellement rencontré le 16/09/2026 : 95 % d'avis prédits négatifs pour 4 % réels (ADR 0009) | TUEE | 1 failed, 1 passed in 2.83s | tests/test_api.py::test_predict_success |
| M02 | Manifeste d'idempotence ignoré | Chaque passage réécrit les mêmes avis dans la zone brute (ADR 0002) | TUEE | 1 failed, 30 passed in 59.91s | tests/test_fresh_dirs.py::test_ingest_app_fresh_dirs |
| M03 | Réponse d'erreur de l'API acceptée | Une panne de la source passerait pour une page vide et arrêterait la collecte sans alerte | TUEE | 1 failed, 38 passed in 69.18s (0:01:09) | tests/test_ingest.py::test_success_zero_raises |
| M04 | Dédoublonnage supprimé | Un avis présent dans les deux flux ou modifié serait compté deux fois | TUEE | 1 failed, 11 passed in 20.59s | tests/test_boost.py::test_transform_clean_dedup_prioritises_natural |
| M05 | Pseudonymisation supprimée | L'identifiant Steam en clair atteindrait la zone propre (RGPD, ADR 0004) | TUEE | 1 failed, 49 passed in 101.30s (0:01:41) | tests/test_transform_quality.py::test_author_pseudo_stable |
| M06 | Contrôle qualité bloquant désactivé | Une donnée non conforme atteindrait le modèle (ADR 0005) | TUEE | 1 failed, 39 passed in 67.39s (0:01:07) | tests/test_reverse_gaps.py::test_transform_quality_blocking_M06 |
| M07 | Barrière de promotion supprimée | Un modèle sous le seuil de qualité serait mis en service (ADR 0008) | TUEE | 1 failed, 40 passed in 87.05s (0:01:27) | tests/test_reverse_gaps.py::test_train_promotion_barrier_M07 |
| M08 | Comparaison au champion supprimée | Un modèle moins bon que celui en service le remplacerait (ADR 0008) | TUEE | 1 failed, 43 passed in 118.57s (0:01:58) | tests/test_train_score.py::test_second_training_not_promoted_new_version |
| M09 | Avis complémentaires mélangés au jeu de test | La mesure ne refléterait plus la production (ADR 0007) | TUEE | 1 failed, 13 passed in 27.75s | tests/test_boost.py::test_train_and_log_includes_boost_and_decision_threshold |
| M10 | Résumé quotidien incluant le flux complémentaire | La part négative affichée serait gonflée artificiellement (ADR 0007) | TUEE | 1 failed, 14 passed in 30.17s | tests/test_boost.py::test_score_summarize_ignores_negative_boost |
| M11 | Part de négatifs contrôlée sur tous les flux | Le contrôle de distribution ne détecterait plus une dérive du flux naturel (ADR 0005) | TUEE | 1 failed, 41 passed in 87.04s (0:01:27) | tests/test_reverse_gaps.py::test_negative_share_natural_only_M11 |
| M12 | Limite du nombre de textes par requête levée | Une seule requête pourrait saturer l'API | TUEE | 1 failed, 3 passed in 3.60s | tests/test_api.py::test_predict_too_many_texts_422 |
| M13 | Absence de modèle transformée en erreur 500 | Un état attendu (première installation) apparaîtrait comme une panne (ADR 0008) | TUEE | 1 failed, 8 passed in 17.04s | tests/test_artifacts_location.py::test_health_endpoint_without_model |

**Total** : 13 – **TUEES** : 13 – **SURVIVANTES** : 0 – **OBSOLETES** : 0

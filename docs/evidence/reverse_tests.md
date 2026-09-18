# Rapport de tests inverses – 2026-09-18 17:54:38Z

Commit : `inconnu`

Témoin : 43 passed in 743.46s (0:12:23)

| id | défaut simulé | pourquoi c’est grave | statut | résumé pytest | test qui détecte | portée |
|---|---------------|----------------------|--------|---------------|-----------------|-------|
| M01 | Convention de décision inversée | Défaut réellement rencontré le 16/09/2026 : 95 % d'avis prédits négatifs pour 4 % réels (ADR 0009) | TUEE | 1 failed, 1 passed in 0.38s | tests/test_api.py::test_predict_success | tests/test_api.py |
| M02 | Manifeste d'idempotence ignoré | Chaque passage réécrit les mêmes avis dans la zone brute (ADR 0002) | TUEE | 1 failed in 1.31s | tests/test_fresh_dirs.py::test_ingest_app_fresh_dirs | tests/test_fresh_dirs.py |
| M03 | Réponse d'erreur de l'API acceptée | Une panne de la source passerait pour une page vide et arrêterait la collecte sans alerte | TUEE | 1 failed, 4 passed in 0.11s | tests/test_ingest.py::test_success_zero_raises | tests/test_ingest.py |
| M04 | Dédoublonnage supprimé | Un avis présent dans les deux flux ou modifié serait compté deux fois | TUEE | 1 failed, 1 passed in 1.87s | tests/test_boost.py::test_transform_clean_dedup_prioritises_natural | tests/test_boost.py |
| M05 | Pseudonymisation supprimée | L'identifiant Steam en clair atteindrait la zone propre (RGPD, ADR 0004) | TUEE | 1 failed, 2 passed in 0.06s | tests/test_transform_quality.py::test_author_pseudo_stable | tests/test_transform_quality.py |
| M06 | Contrôle qualité bloquant désactivé | Une donnée non conforme atteindrait le modèle (ADR 0005) | TUEE | 1 failed in 1.78s | tests/test_reverse_gaps.py::test_transform_quality_blocking_M06 | tests/test_reverse_gaps.py |
| M07 | Barrière de promotion supprimée | Un modèle sous le seuil de qualité serait mis en service (ADR 0008) | TUEE | 1 failed, 1 passed in 60.81s (0:01:00) | tests/test_reverse_gaps.py::test_train_promotion_barrier_M07 | tests/test_reverse_gaps.py |
| M08 | Comparaison au champion supprimée | Un modèle moins bon que celui en service le remplacerait (ADR 0008) | TUEE | 1 failed, 1 passed in 141.72s (0:02:21) | tests/test_train_score.py::test_second_training_not_promoted_new_version | tests/test_train_score.py |
| M09 | Avis complémentaires mélangés au jeu de test | La mesure ne refléterait plus la production (ADR 0007) | TUEE | 1 failed, 3 passed in 74.86s (0:01:14) | tests/test_boost.py::test_train_and_log_includes_boost_and_decision_threshold | tests/test_boost.py |
| M10 | Résumé quotidien incluant le flux complémentaire | La part négative affichée serait gonflée artificiellement (ADR 0007) | TUEE | 1 failed, 4 passed in 66.19s (0:01:06) | tests/test_boost.py::test_score_summarize_ignores_negative_boost | tests/test_boost.py |
| M11 | Part de négatifs contrôlée sur tous les flux | Le contrôle de distribution ne détecterait plus une dérive du flux naturel (ADR 0005) | TUEE | 1 failed, 2 passed in 71.42s (0:01:11) | tests/test_reverse_gaps.py::test_negative_share_natural_only_M11 | tests/test_reverse_gaps.py |
| M12 | Limite du nombre de textes par requête levée | Une seule requête pourrait saturer l'API | TUEE | 1 failed, 3 passed in 0.40s | tests/test_api.py::test_predict_too_many_texts_422 | tests/test_api.py |
| M13 | Absence de modèle transformée en erreur 500 | Un état attendu (première installation) apparaîtrait comme une panne (ADR 0008) | TUEE | 1 failed, 1 passed in 115.13s (0:01:55) | tests/test_artifacts_location.py::test_health_endpoint_without_model | tests/test_artifacts_location.py |
| M14 | Nettoyage des espaces Unicode désactivé | Des avis contenant des espaces non-ASCII restent inchangés, biaisant le comptage de mots (ADR 0014) | TUEE | 1 failed in 8.84s | tests/test_spark_silver.py::test_spark_vs_pandas | tests/test_spark_silver.py |
| M15 | Priorité de dédoublonnage inversée | Les avis du flux ``negative_boost`` peuvent écraser ceux du flux naturel (ADR 0002) | TUEE | 1 failed in 8.94s | tests/test_spark_silver.py::test_spark_vs_pandas | tests/test_spark_silver.py |
| M16 | Conversion des timestamps nanosecondes ignorée | Les timestamps sont écrits en nanosecondes, provoquant une erreur d’écriture Iceberg (ADR 0014) | TUEE | 1 failed, 1 passed in 10.01s | tests/test_spark_silver.py::test_lakehouse_write_and_history | tests/test_spark_silver.py |

**Total** : 16 – **TUEES** : 16 – **SURVIVANTES** : 0 – **OBSOLETES** : 0

# Rapport de tests inverses – 2026-09-19 21:57:53Z

Commit : `c462ea8`

Témoin : 88 passed in 1355.98s (0:22:35)

| id | défaut simulé | pourquoi c’est grave | statut | résumé pytest | test qui détecte | portée |
|---|---------------|----------------------|--------|---------------|-----------------|-------|
| M01 | Convention de décision inversée | Défaut réellement rencontré le 16/09/2026 : 95 % d'avis prédits négatifs pour 4 % réels (ADR 0009) | TUEE | 1 failed, 1 passed in 1.45s | tests/test_api.py::test_predict_success | tests/test_api.py |
| M02 | Manifeste d'idempotence ignoré | Chaque passage réécrit les mêmes avis dans la zone brute (ADR 0002) | TUEE | 1 failed in 1.71s | tests/test_fresh_dirs.py::test_ingest_app_fresh_dirs | tests/test_fresh_dirs.py |
| M03 | Réponse d'erreur de l'API acceptée | Une panne de la source passerait pour une page vide et arrêterait la collecte sans alerte | TUEE | 1 failed, 4 passed in 0.08s | tests/test_ingest.py::test_success_zero_raises | tests/test_ingest.py |
| M04 | Dédoublonnage supprimé | Un avis présent dans les deux flux ou modifié serait compté deux fois | TUEE | 1 failed, 1 passed in 2.17s | tests/test_boost.py::test_transform_clean_dedup_prioritises_natural | tests/test_boost.py |
| M05 | Pseudonymisation supprimée | L'identifiant Steam en clair atteindrait la zone propre (RGPD, ADR 0004) | TUEE | 1 failed, 2 passed in 0.06s | tests/test_transform_quality.py::test_author_pseudo_stable | tests/test_transform_quality.py |
| M06 | Contrôle qualité bloquant désactivé | Une donnée non conforme atteindrait le modèle (ADR 0005) | TUEE | 1 failed in 3.10s | tests/test_reverse_gaps.py::test_transform_quality_blocking_M06 | tests/test_reverse_gaps.py |
| M07 | Barrière de promotion supprimée | Un modèle sous le seuil de qualité serait mis en service (ADR 0008) | TUEE | 1 failed, 1 passed in 30.38s | tests/test_reverse_gaps.py::test_train_promotion_barrier_M07 | tests/test_reverse_gaps.py |
| M08 | Comparaison au champion supprimée | Un modèle moins bon que celui en service le remplacerait (ADR 0008) | TUEE | 1 failed, 1 passed in 19.74s | tests/test_train_score.py::test_second_training_not_promoted_new_version | tests/test_train_score.py |
| M09 | Avis complémentaires mélangés au jeu de test | La mesure ne refléterait plus la production (ADR 0007) | TUEE | 1 failed, 3 passed in 10.11s | tests/test_boost.py::test_train_and_log_includes_boost_and_decision_threshold | tests/test_boost.py |
| M10 | Résumé quotidien incluant le flux complémentaire | La part négative affichée serait gonflée artificiellement (ADR 0007) | TUEE | 1 failed, 4 passed in 11.16s | tests/test_boost.py::test_score_summarize_ignores_negative_boost | tests/test_boost.py |
| M11 | Part de négatifs contrôlée sur tous les flux | Le contrôle de distribution ne détecterait plus une dérive du flux naturel (ADR 0005) | TUEE | 1 failed, 2 passed in 10.87s | tests/test_reverse_gaps.py::test_negative_share_natural_only_M11 | tests/test_reverse_gaps.py |
| M12 | Limite du nombre de textes par requête levée | Une seule requête pourrait saturer l'API | TUEE | 1 failed, 3 passed in 0.97s | tests/test_api.py::test_predict_too_many_texts_422 | tests/test_api.py |
| M13 | Absence de modèle transformée en erreur 500 | Un état attendu (première installation) apparaîtrait comme une panne (ADR 0008) | TUEE | 1 failed, 1 passed in 27.92s | tests/test_artifacts_location.py::test_health_endpoint_without_model | tests/test_artifacts_location.py |
| M14 | Nettoyage des espaces Unicode désactivé | Des avis contenant des espaces non-ASCII restent inchangés, biaisant le comptage de mots (ADR 0014) | TUEE | 1 failed in 198.17s (0:03:18) | tests/test_spark_silver.py::test_spark_vs_pandas | tests/test_spark_silver.py |
| M15 | Priorité de dédoublonnage inversée | Les avis du flux ``negative_boost`` peuvent écraser ceux du flux naturel (ADR 0002) | TUEE | 1 failed in 11.49s | tests/test_spark_silver.py::test_spark_vs_pandas | tests/test_spark_silver.py |
| M16 | Conversion des timestamps nanosecondes ignorée | Les timestamps sont écrits en nanosecondes, provoquant une erreur d’écriture Iceberg (ADR 0014) | TUEE | 1 failed, 1 passed in 18.12s | tests/test_spark_silver.py::test_lakehouse_write_and_history | tests/test_spark_silver.py |
| M17 | Porte de qualité rendue non bloquante | Une suite Great Expectations en échec laisserait passer des données non conformes vers le modèle (ADR 0005) | SURVIVANTE | 6 passed in 18.27s | - | tests/test_expectations.py |
| M18 | Échec de dbt build ignoré | Une zone gold incomplète ou fausse serait servie aux tableaux de bord sans que rien ne le signale | TUEE | 1 failed, 2 passed in 35.22s | tests/test_gold.py::test_gold_fails_when_scoring_is_stale | tests/test_gold.py |
| M19 | Le franchissement du seuil de PSI ne lève plus d'alerte | La dérive des entrées passerait inaperçue et le réentraînement ne serait jamais déclenché | TUEE | 1 failed, 7 passed in 30.46s | tests/test_drift.py::test_evaluer_alerte_psi_au_dessus_du_seuil | tests/test_drift.py |
| M20 | Un fichier d'alerte est écrit même sans alerte | Le canal d'alerte crierait en permanence : plus personne ne le lirait, et le réentraînement partirait pour rien | TUEE | 1 failed, 9 passed in 0.14s | tests/test_drift.py::test_ecrire_alerte_ecrit_un_fichier_date_et_rien_sans_alerte | tests/test_drift.py |
| M21 | Le signe des coefficients de la classe négative est inversé | Les termes présentés au jury comme « ce qui pèse vers le négatif » seraient exactement les termes positifs : l'explication mentirait | TUEE | 1 failed, 2 passed in 1.16s | tests/test_explain.py::test_somme_contributions_égale_decision_function | tests/test_explain.py |
| M22 | Une restauration vers un instantané inexistant n'est plus refusée | La table silver pourrait être basculée vers un état qui n'existe pas, sans message clair | SURVIVANTE | 5 passed in 10.59s | - | tests/test_spark_silver.py |
| M23 | La part de négatifs prédits peut dépasser 1 sans être refusée | Une part supérieure à 1 est arithmétiquement impossible : la laisser passer signifie que la zone gold peut servir des chiffres faux au tableau de bord | TUEE | 1 failed, 1 passed in 2.43s | tests/test_expectations_lake.py::test_mart_part_hors_bornes_echoue | tests/test_expectations_lake.py |
| M24 | Le format du pseudonyme d'auteur n'est plus vérifié dans la zone silver | Un identifiant en clair passerait la porte de qualité : c'est la pseudonymisation elle-même qui cesserait d'être contrôlée | TUEE | 1 failed, 3 passed in 2.43s | tests/test_expectations_lake.py::test_silver_reviews_pseudo_invalide_echoue | tests/test_expectations_lake.py |
| M25 | Un retour arrière vers une version inexistante n'est plus refusé | Le retour arrière est le dernier recours quand le modèle en service se dégrade : s'il échoue en silence, on croit avoir rebasculé alors que le mauvais modèle sert toujours | TUEE | 1 failed, 3 passed in 0.99s | tests/test_rollback.py::test_basculer_vers_version_inexistante_levre_ValueError | tests/test_rollback.py |
| M26 | Le rapport de bascule affirme que l'ancienne version était déjà la nouvelle | Toute trace du retour arrière devient fausse : le journal et la sortie de commande diraient qu'il ne s'est rien passé | TUEE | 1 failed, 2 passed in 0.91s | tests/test_rollback.py::test_basculer_deplace_alias_et_renvoie_anciennes_nouvelles_versions | tests/test_rollback.py |

**Total** : 26 – **TUEES** : 24 – **SURVIVANTES** : 2 – **OBSOLETES** : 0

---

*Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC*

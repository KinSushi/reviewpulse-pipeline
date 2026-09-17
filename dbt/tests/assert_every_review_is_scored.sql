-- Location: dbt/tests/assert_every_review_is_scored.sql
-- What: Vérifie que chaque avis présent dans `stg_reviews` a bien été scoré et figure dans `stg_predictions`.
-- How: Sélectionne les `review_id` de `stg_reviews` qui n’apparaissent pas dans `stg_predictions`.
-- Why: Le test échoue si le scoring n’a pas été exécuté après la dernière reconstruction de la zone silver ; le DAG exécute dbt uniquement après le calcul du score.

SELECT
    r.review_id
FROM {{ ref('stg_reviews') }} AS r
LEFT JOIN {{ ref('stg_predictions') }} AS p
    ON r.review_id = p.review_id
WHERE p.review_id IS NULL

-- Path: dbt/tests/assert_mart_grain_unique.sql
-- Description: Vérifie l'unicité du grain (app_id, language, review_date) dans la table mart_sentiment_daily.
-- How: Sélectionne les combinaisons qui apparaissent plus d'une fois (COUNT(*) > 1). Le test échoue si le résultat n'est pas vide.
-- Why: Un grain dupliqué indiquerait un problème de agrégation ou de chargement des données, faussant les indicateurs journaliers.

select
    app_id,
    language,
    review_date
from {{ ref('mart_sentiment_daily') }}
group by
    app_id,
    language,
    review_date
having count(*) > 1

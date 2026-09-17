-- OÙ : dbt/models/marts/dim_date.sql (couche marts, table).
-- QUOI : dimension calendrier, une ligne par jour où au moins un avis a été publié.
-- COMMENT : dates distinctes de stg_reviews, attributs extraits par DuckDB (isodow : 1 = lundi).
-- POURQUOI : schéma en étoile classique ; les outils de restitution filtrent par semaine ou mois
--            sans recalcul.

select distinct
    review_date as date_day,
    cast(extract(year from review_date) as integer) as year,
    cast(extract(month from review_date) as integer) as month,
    cast(extract(week from review_date) as integer) as iso_week,
    cast(extract(isodow from review_date) as integer) as day_of_week
from {{ ref('stg_reviews') }}

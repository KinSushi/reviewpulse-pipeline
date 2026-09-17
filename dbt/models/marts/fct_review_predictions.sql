-- OÙ : dbt/models/marts/fct_review_predictions.sql (couche marts, table de faits).
-- QUOI : un avis et sa prédiction ; grain = review_id.
-- COMMENT : jointure interne avis × prédictions ; le test assert_every_review_is_scored garantit
--           qu'aucun avis n'est perdu par cette jointure.
-- POURQUOI : les deux flux (sample_source) sont gardés pour analyser le modèle ; les indicateurs
--            métier (mart_sentiment_daily) ne retiennent que le flux naturel.

select
    r.review_id,
    r.app_id,
    r.language,
    r.sample_source,
    r.review_date,
    r.created_at,
    r.label,
    p.pred_label,
    p.proba_negative,
    p.decision_threshold,
    p.model_version,
    p.scored_at,
    r.votes_up,
    r.playtime_at_review_min,
    r.text_len
from {{ ref('stg_reviews') }} as r
inner join {{ ref('stg_predictions') }} as p
    on r.review_id = p.review_id

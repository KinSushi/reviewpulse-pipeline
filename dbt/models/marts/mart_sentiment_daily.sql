-- Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
-- dbt/models/marts/mart_sentiment_daily.sql
-- OÙ : dans le répertoire `models/marts/` du projet ReviewPulse
-- QUOI : agrégat quotidien du sentiment des avis (échantillon naturel) par application, langue et date
-- COMMENT : jointure entre `fct_review_predictions` (prévisions) et `dim_game` (nom du jeu), filtrage sur `sample_source = 'natural'`, agrégation au grain (app_id, language, review_date)
-- POURQUOI : fournir des indicateurs de sentiment fiables (excluant le biais du flux `negative_boost`) pour le reporting quotidien tout en respectant le RGPD (pas de texte d'avis ni d'auteur)

with predictions as (
    select
        p.app_id,
        g.game_name,
        p.language,
        p.review_date,
        cast(count(*) as bigint) as n_reviews,
        cast(sum(case when p.pred_label = 0 then 1 else 0 end) as bigint) as n_pred_negative,
        cast(sum(case when p.label = 0 then 1 else 0 end) as bigint) as n_actual_negative,
        cast(sum(case when p.pred_label = 0 then 1 else 0 end) as double) / cast(count(*) as double) as share_pred_negative,
        cast(sum(case when p.label = 0 then 1 else 0 end) as double) / cast(count(*) as double) as share_actual_negative,
        -- Versions MLflow numériques stockées en texte : comparaison numérique (« 10 » > « 9 »).
        cast(max(cast(p.model_version as bigint)) as varchar) as model_version
    from {{ ref('fct_review_predictions') }} as p
    join {{ ref('dim_game') }} as g
        on p.app_id = g.app_id
    where p.sample_source = 'natural'
    group by
        p.app_id,
        g.game_name,
        p.language,
        p.review_date
)

select
    app_id,
    game_name,
    language,
    review_date,
    n_reviews,
    n_pred_negative,
    n_actual_negative,
    share_pred_negative,
    share_actual_negative,
    model_version
from predictions

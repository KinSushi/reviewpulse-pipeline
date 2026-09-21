-- Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
-- OÙ : dbt/models/staging/stg_reviews.sql (couche staging, vue).
-- QUOI : les avis nettoyés de la zone silver, une ligne par avis, sans texte ni pseudonyme d'auteur.
-- COMMENT : lecture directe de la table Iceberg silver.reviews (emplacement des métadonnées passé
--           par reviewpulse.gold) ; review_date est calculée en UTC (fuseau fixé dans profiles.yml).
-- POURQUOI : minimisation RGPD — la zone gold n'a besoin ni du texte ni de l'auteur ;
--            le texte reste en silver pour l'entraînement.

select
    review_id,
    app_id,
    language,
    label,
    created_at,
    cast(created_at as date) as review_date,
    updated_at,
    votes_up,
    weighted_vote_score,
    playtime_at_review_min,
    text_len,
    sample_source
from iceberg_scan('{{ var("silver_reviews_metadata") }}')

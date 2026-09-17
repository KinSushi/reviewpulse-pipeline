-- OÙ : dbt/models/staging/stg_predictions.sql (couche staging, vue).
-- QUOI : les prédictions du modèle champion, une ligne par avis.
-- COMMENT : lecture directe de la table Iceberg silver.predictions ; le module reviewpulse.gold
--           passe l'emplacement du fichier de métadonnées courant dans la variable dbt.
-- POURQUOI : seules les colonnes propres au score sont gardées ; les attributs de l'avis
--            viennent de stg_reviews (une seule source de vérité par attribut).

select
    review_id,
    pred_label,
    proba_negative,
    decision_threshold,
    model_version,
    scored_at
from iceberg_scan('{{ var("silver_predictions_metadata") }}')

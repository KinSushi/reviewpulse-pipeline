-- File: tests/assert_shares_and_probas_in_range.sql
-- Location: tests/
-- What: Vérifie que les parts et probabilités sont bien dans l’intervalle [0, 1].
-- How:  Sélectionne les lignes où les colonnes concernées sortent de cet intervalle et renvoie une seule colonne « anomaly » contenant la valeur hors‑borne (castée en varchar).
-- Why:  Garantir l’intégrité des indicateurs avant agrégation et éviter les biais dans les métriques.

select cast(share_pred_negative as varchar) as anomaly
from {{ ref('mart_sentiment_daily') }}
where share_pred_negative < 0 or share_pred_negative > 1

union all

select cast(share_actual_negative as varchar) as anomaly
from {{ ref('mart_sentiment_daily') }}
where share_actual_negative < 0 or share_actual_negative > 1

union all

select cast(proba_negative as varchar) as anomaly
from {{ ref('fct_review_predictions') }}
where proba_negative < 0 or proba_negative > 1

union all

select cast(decision_threshold as varchar) as anomaly
from {{ ref('fct_review_predictions') }}
where decision_threshold < 0 or decision_threshold > 1

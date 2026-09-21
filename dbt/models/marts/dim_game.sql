-- Copyright © 2026 · Auteur — KinSushi · Enzo · Sovralys LLC
-- OÙ : dbt/models/marts/dim_game.sql (couche marts, table).
-- QUOI : dimension des jeux suivis (identifiant Steam, nom).
-- COMMENT : copie du seed games.csv, versionné dans le dépôt.
-- POURQUOI : trois jeux seulement, noms stables : un seed suffit, sans appel réseau au moment du build.

select
    app_id,
    game_name
from {{ ref('games') }}

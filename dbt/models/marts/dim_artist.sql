{{ config(
    materialized='table'
) }}

WITH history AS (
    SELECT 
        artist_id,
        artist_name,
        artist_genres,
        popularity,
        artist_followers,
        fetched_at,
        -- Use HASH to detect changes across all tracked columns
        HASH(artist_name, artist_genres, popularity, artist_followers) as data_hash
    FROM {{ ref('stg_artist') }}
),
changes AS (
    SELECT 
        *,
        LAG(data_hash) OVER (PARTITION BY artist_id ORDER BY fetched_at ASC) as prev_hash
    FROM history
),
filtered_changes AS (
    SELECT *
    FROM changes
    WHERE prev_hash IS NULL OR data_hash != prev_hash
)

SELECT 
    artist_id,
    artist_name,
    artist_genres,
    popularity,
    artist_followers,
    fetched_at as dbt_valid_from,
    LEAD(fetched_at) OVER (PARTITION BY artist_id ORDER BY fetched_at ASC) as dbt_valid_to,
    CASE WHEN LEAD(fetched_at) OVER (PARTITION BY artist_id ORDER BY fetched_at ASC) IS NULL 
         THEN TRUE ELSE FALSE END as is_current
FROM filtered_changes
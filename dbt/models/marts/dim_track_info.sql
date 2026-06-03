{{ config(
    materialized='table'
) }}

WITH history AS (
    SELECT 
        track_id,
        track_name,
        artist_id,
        popularity,
        duration_ms,
        explicit,
        album_name,
        album_release_date,
        fetched_at,
        HASH(
            track_name,
            artist_id,
            popularity,
            duration_ms,
            explicit,
            album_name,
            album_release_date
        ) as data_hash
    FROM {{ ref('stg_track_info') }}
),
changes AS (
    SELECT 
        *,
        LAG(data_hash) OVER (PARTITION BY track_id ORDER BY fetched_at ASC) as prev_hash
    FROM history
),
filtered_changes AS (
    SELECT *
    FROM changes
    WHERE prev_hash IS NULL OR data_hash != prev_hash
)

SELECT 
    track_id,
    track_name,
    artist_id,
    popularity,
    duration_ms,
    explicit,
    album_name,
    album_release_date,
    fetched_at as dbt_valid_from,
    LEAD(fetched_at) OVER (PARTITION BY track_id ORDER BY fetched_at ASC) as dbt_valid_to,
    CASE WHEN LEAD(fetched_at) OVER (PARTITION BY track_id ORDER BY fetched_at ASC) IS NULL 
         THEN TRUE ELSE FALSE END as is_current
FROM filtered_changes
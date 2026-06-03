{{ config(
    materialized='table'
) }}

WITH history AS (
    SELECT 
        track_id,
        acousticness,
        danceability,
        energy,
        instrumentalness,
        key,
        liveness,
        mode,
        speechiness,
        tempo,
        time_signature,
        valence,
        fetched_at,
        HASH(
            acousticness,
            danceability,
            energy,
            instrumentalness,
            key,
            liveness,
            mode,
            speechiness,
            tempo,
            time_signature,
            valence
        ) as data_hash
    FROM {{ ref('stg_audio_feature') }}
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
        acousticness,
        danceability,
        energy,
        instrumentalness,
        key,
        liveness,
        mode,
        speechiness,
        tempo,
        time_signature,
        valence,
        fetched_at as dbt_valid_from,
        LEAD(fetched_at) OVER (PARTITION BY track_id ORDER BY fetched_at ASC) as dbt_valid_to,
        CASE WHEN LEAD(fetched_at) OVER (PARTITION BY track_id ORDER BY fetched_at ASC) IS NULL 
             THEN TRUE ELSE FALSE END as is_current
FROM filtered_changes

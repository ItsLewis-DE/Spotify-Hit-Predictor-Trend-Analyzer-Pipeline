{{ 
    config(
        materialized = 'incremental'
    )
}}
WITH top_track AS(
    SELECT *
    FROM {{ ref('stg_top_track') }}
),
track_info AS (
    SELECT DISTINCT track_id, artist_id
    FROM {{ ref('dim_track_info') }}
)
SELECT tt.rank,
    tt.peak_rank,
    tt.previous_rank,
    tt.weeks_on_chart,
    tt.track_id,
    ti.artist_id,
    tt.source,
    tt.streams,
    tt.day,
    tt.week_of_month,
    tt.month,
    tt.year
FROM top_track tt
LEFT JOIN track_info ti
    ON ti.track_id = tt.track_id
{% if is_incremental() %}
WHERE NOT EXISTS (
    SELECT 1 FROM {{ this }} existing
    WHERE existing.track_id = tt.track_id
        AND existing.artist_id = ti.artist_id
        AND existing.week_of_month = tt.week_of_month
        AND existing.month = tt.month
        AND existing.year = tt.year
)
{% endif %}

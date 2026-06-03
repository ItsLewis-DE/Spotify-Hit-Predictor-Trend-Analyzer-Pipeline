WITH top_track AS(
    SELECT *
    FROM {{ ref('stg_top_track') }}
),
track_info AS (
    SELECT track_id,artist_id
    FROM {{ ref('dim_track_info') }}
)
SELECT rank,
    peak_rank,
    previous_rank,
    weeks_on_chart,
    tt.track_id,
    artist_id,
    source,
    streams,
    week_of_month,
    month,
    year
FROM top_track tt
LEFT JOIN track_info ti
ON ti.track_id = tt.track_id
    

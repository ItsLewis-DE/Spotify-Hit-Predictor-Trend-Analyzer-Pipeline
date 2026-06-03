WITH raw_top_track AS (
    SELECT * 
    FROM {{ source('raw_data','raw_top_track') }}
)

SELECT "RANK",
    SPLIT_PART(uri,':',-1) AS track_id,
    track_name,
    SPLIT(artist_names,', ') AS artists_names,
    source,
    peak_rank,
    previous_rank,
    weeks_on_chart,
    streams,
    CEIL(DAY(fetched_date) / 7.0) AS WEEK_OF_MONTH,
    DAY(fetched_date) AS DAY,
    MONTH(fetched_date) AS MONTH,
    YEAR(fetched_date) AS YEAR
FROM raw_top_track
    
WITH raw_track_info AS(
    SELECT * 
    FROM {{ source('raw_data','raw_track_info') }}
)

SELECT raw_data:track_id::string AS track_id,
    REGEXP_REPLACE(raw_data:track_name::string,'\\s*\\((feat|ft|WITH).*\\)','',1,0,'i') as track_name,
    SPLIT(raw_data:artist_id::string,', ') AS artist_id,
    raw_data:popularity::int AS popularity,
    raw_data:duration_ms::bigint AS duration_ms,
    raw_data:explicit::boolean AS explicit,
    raw_data:album_name::string AS album_name,
    raw_data:album_release_date::date AS album_release_date
FROM raw_track_info

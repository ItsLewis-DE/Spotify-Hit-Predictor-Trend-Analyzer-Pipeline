WITH raw_artist AS(
    SELECT * 
    FROM {{ source('raw_data', 'raw_artist') }}
)

SELECT raw_data:artist_id::string as artist_id,
    raw_data:artist_followers_total::bigint as artist_followers,
    SPLIT(raw_data:artist_genres::string,', ') as artist_genres,
    raw_data:artist_name::string as artist_name,
    raw_data:artist_popularity::int as popularity,
    raw_data:fetched_at::timestamp_ntz as fetched_at
FROM raw_artist
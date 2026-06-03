WITH raw_artist AS(
    SELECT * 
    FROM {{ source('raw_data', 'raw_artist') }}
)

SELECT raw_data:artist_id::string as artist_id,
    raw_data:artist_followers_total::bigint as artist_followers,
    SPLIT(raw_data:artist_genres::string,', ') as artist_genres,
    raw_data:artist_name::string as artist_name,
    raw_data:artist_popularity::int as popularity
FROM raw_artist
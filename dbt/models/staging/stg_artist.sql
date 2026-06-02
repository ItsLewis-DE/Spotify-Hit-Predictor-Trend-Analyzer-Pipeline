WITH artist_table AS(
    SELECT * 
    FROM {{ source(raw_data,raw_artist) }}
)

SELECT raw_data:artist_id::string,

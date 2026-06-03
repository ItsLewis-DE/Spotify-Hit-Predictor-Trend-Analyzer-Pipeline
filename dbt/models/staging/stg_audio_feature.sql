WITH raw_audio_feature AS (
    SELECT * 
    FROM {{ source('raw_data','raw_audio_feature') }}
)

SELECT raw_data:id::string as track_id,
    raw_data:acousticness::float as acousticness,
    raw_data:danceability::float as danceability,
    raw_data:energy::float as energy,
    raw_data:instrumentalness::float as instrumentalness,
    raw_data:key::int as key,
    raw_data:liveness::float as liveness,
    raw_data:mode::int as mode,
    raw_data:speechiness::float as speechiness,
    raw_data:tempo::float as tempo,
    raw_data:time_signature::int as time_signature,
    raw_data:valence::float as valence
FROM raw_audio_feature
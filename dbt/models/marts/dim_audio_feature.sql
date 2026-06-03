WITH audio_feature AS (
    SELECT * 
    FROM {{ ref('stg_audio_feature') }}
)
SELECT * 
FROM audio_feature af

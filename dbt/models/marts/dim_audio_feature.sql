WITH audio_feature AS (
    SELECT * 
    FROM {{ ref('dim_audio_feature_snapshot') }}
)
SELECT * 
FROM audio_feature af

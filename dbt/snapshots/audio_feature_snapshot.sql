{% snapshot dim_audio_feature_snapshot %}
{{
    config(
        unique_key='track_id',
        strategy='check',
        check_cols='all'
    )
}}
SELECT *
FROM {{ ref('stg_audio_feature') }}

{% endsnapshot %}
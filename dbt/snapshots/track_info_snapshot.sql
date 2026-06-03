{% snapshot dim_track_info_snapshot %}
{{
    config(
        unique_key='track_id',
        strategy='check',
        check_cols='all'
    )
}}
SELECT *
FROM {{ ref('stg_track_info') }}

{% endsnapshot %}

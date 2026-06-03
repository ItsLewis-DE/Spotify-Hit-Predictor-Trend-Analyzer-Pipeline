{% snapshot dim_artist_snapshot %}
{{
    config(
        unique_key='artist_id',
        strategy='check',
        check_cols=['artist_name', 'artist_genres', 'popularity', 'artist_followers']
    )
}}
SELECT *
FROM {{ ref('stg_artist') }}

{% endsnapshot %}
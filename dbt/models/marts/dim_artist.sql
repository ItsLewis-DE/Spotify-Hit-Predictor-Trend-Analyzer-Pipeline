{{
    flatten_array(
        source_model = 'dim_artist_snapshot',
        pk_columns = ['artist_id', 'artist_followers', 'artist_name', 'popularity', 'dbt_valid_from', 'dbt_valid_to', 'dbt_scd_id'],
        array_column = 'artist_genres',
        flattened_alias = 'genres'
    )
}}
{{
    flatten_array(
        source_model = 'dim_track_info_snapshot',
        pk_columns = ['track_id','track_name','popularity','duration_ms','explicit','album_name','album_release_date','dbt_valid_from','dbt_valid_to','dbt_scd_id'],
        array_column = 'artist_id',
        flattened_alias = 'artist_id'
    )
}}
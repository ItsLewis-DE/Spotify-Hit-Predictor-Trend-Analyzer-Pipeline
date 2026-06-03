{{
    flatten_array(
        source_model = 'stg_track_info',
        pk_columns = ['track_id','track_name','popularity','duration_ms','explicit','album_name','album_release_date'],
        array_column = 'artist_id',
        flattened_alias = 'artist_id'
    )
}}
{{
    
    flatten_array(
        source_model = 'stg_artist',
        pk_columns = ['artist_id','artist_followers','artist_name','popularity'],
        array_column = 'artist_genres',
        flattened_alias = 'genres'
    )

}}
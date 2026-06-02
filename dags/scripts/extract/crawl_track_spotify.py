import requests
import json
import os, logging
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import time
import argparse
import re
import sys
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 50

def get_chart_date(file_path):
    match = re.search(r"\d{4}-\d{2}-\d{2}", file_path.name)
    if match:
        return match.group(0)
    return ""

def read_newest_file(dirpath,extension):
    path = Path(dirpath)
    if not path.exists():
        logger.error("Can not found file!!")
    files = [file for file in path.iterdir() 
             if file.is_file() and file.suffix == extension
            ]
    if not files:
        return None
    newest_file = max(
        files,
        key = lambda file : (file.stat().st_mtime,file.name)
    )
    return newest_file

def get_api_track_info(spotify_id_string: str,timezone: int)-> pd.DataFrame:
    BASE_URL = 'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/tracks'
    params = {'ids': spotify_id_string}
    if timezone ==1:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_1')
    elif timezone==2:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_2')
    elif timezone==3:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_3')
    else:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_4')
    headers = {
        "X-RapidAPI-Key": X_RapidAPI_Key, 
        "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com" 
    }

    response = requests.get(BASE_URL, headers=headers,params = params)
    if response.status_code == 429:
        return None
    if response.status_code == 200:
        logger.info("Extracting track info....")
        tracks = response.json().get('tracks', [])
        records = []
        for track in tracks:
            if track is None:
                continue
            album = track.get("album", {})
            ext_ids = track.get("external_ids", {})
            artists = track.get("artists", [])
            album_artists = album.get("artists", [])

            records.append({
                # Track-level
                "uri": track.get("uri"),
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "track_number": track.get("track_number"),
                "disc_number": track.get("disc_number"),
                "duration_ms": track.get("duration_ms"),
                "explicit": track.get("explicit"),
                "popularity": track.get("popularity"),
                "type": track.get("type"),
                "is_local": track.get("is_local"),
                "preview_url": track.get("preview_url"),
                "href": track.get("href"),
                "external_urls": track.get("external_urls", {}).get("spotify"),
                # External IDs
                "isrc": ext_ids.get("isrc"),
                "ean": ext_ids.get("ean"),
                "upc": ext_ids.get("upc"),
                # Artists (flattened)
                "artist_id": ", ".join([a.get("id", "") for a in artists]),
                "artist_name": ", ".join([a.get("name", "") for a in artists]),
                # Album
                "album_id": album.get("id"),
                "album_name": album.get("name"),
                "album_type": album.get("album_type"),
                "album_total_tracks": album.get("total_tracks"),
                "album_release_date": album.get("release_date"),
                "album_release_date_precision": album.get("release_date_precision"),
                "album_external_urls": album.get("external_urls", {}).get("spotify"),
                "album_artist_id": ", ".join([a.get("id", "") for a in album_artists]),
                "album_artist_name": ", ".join([a.get("name", "") for a in album_artists]),
            })
        return pd.DataFrame(records)
    else:
        logger.error(f"API error: {response.status_code} - {response.text[:200]}")
        return None

def get_track_info(input_file: Path,output_dir: Path):
    date = get_chart_date(input_file)
    file_path = Path(output_dir/f'track_info-{date}.json')
    last_id = None
    if file_path.exists():
        try:
            old_df = pd.read_csv(file_path)
            if not old_df.empty:
                last_uri = old_df['uri'].iloc[-1]
                last_id = last_uri.split(':')[-1]
        except ValueError:
            pass

    df_rank = pd.read_csv(input_file)
    df_rank['uri'] = df_rank['uri'].str.split(':').str[-1] 
    df_rank.rename(columns= {'uri':'spotify_id'},inplace=True)
    if last_id and last_id in df_rank['spotify_id'].values:
        last_index = df_rank[df_rank['spotify_id'] == last_id].index[0]
        df_rank = df_rank.iloc[last_index+1:]
    else:
        pass
    spotify_id_string = df_rank['spotify_id'].to_list()
    list_df = []
    timezone = [1,2,3,4]
    date = get_chart_date(input_file)
    id_tz=1
    output_dir.mkdir(parents=True,exist_ok = True)
    i=0
    while i < len(spotify_id_string):
        id_string = ','.join(spotify_id_string[i : i + BATCH_SIZE])
        df = get_api_track_info(id_string,id_tz)
        if df is not None:
            batch_end = min(i + BATCH_SIZE, len(spotify_id_string))
            logger.info(f"Extracting {batch_end}/{len(spotify_id_string)}")
            list_df.append(df)
            i += BATCH_SIZE
        else:
            logger.warning("API het request...")
            if list_df:
                logger.info("Dang luu file....")
                df_track_info = pd.concat(list_df,ignore_index =True)
                df_track_info['fetched_at'] = date
                df_track_info.to_json(f'{output_dir}/track_info-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
                # clear list_df sau khi save de khong luu trung
                list_df = []
            id_tz+=1
        if id_tz > len(timezone):
            break
        time.sleep(2)   
    if list_df:
        df_track_info = pd.concat(list_df,ignore_index =True)
        df_track_info['fetched_at'] = date
        df_track_info.to_json(f'{output_dir}/track_info-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
    else:
        if not list_df and i == 0:
            logger.error("There is no data..")
            sys.exit(1)
    return output_dir / f'track_info-{date}.json'

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify track info tu API'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/track_info',
        type=Path,
        help = 'Dir output'
    )
    return parser.parse_known_args()[0]

def crawl_track_spotify(file_top_track):
    args = parse_args()
    logger.info("Extracting track info to file json...")
    output_file = get_track_info(Path(file_top_track),args.output_dir)
    logger.info(f"saved data into {args.output_dir}")
    return str(output_file) if output_file else None
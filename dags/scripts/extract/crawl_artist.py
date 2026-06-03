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

def get_api_artist_info(spotify_id_string: str,timezone: int)-> pd.DataFrame:
    BASE_URL = 'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/artists'
    params = {'ids': spotify_id_string}
    if timezone ==1:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_1')
    elif timezone==2:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_2')
    elif timezone==3:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_3')
    elif timezone==4:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_4')
    elif timezone==5:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_5')
    elif timezone==6:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_6')
    else:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_7')
    headers = {
        "X-RapidAPI-Key": X_RapidAPI_Key, 
        "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com" 
    }

    response = requests.get(BASE_URL, headers=headers,params = params)
    if response.status_code == 429:
        return None
    if response.status_code == 200:
        logger.info("Extracting artist info....")
        artists = response.json().get('artists', [])
        records = []
        for artist in artists:
            if artist is None:
                continue
            followers = artist.get("followers", {})
            records.append({
                "artist_id": artist.get("id"),
                "artist_name": artist.get("name"),
                "artist_popularity": artist.get("popularity"),
                "artist_type": artist.get("type"),
                "artist_uri": artist.get("uri"),
                "artist_href": artist.get("href"),
                "artist_external_urls": artist.get("external_urls", {}).get("spotify"),
                "artist_followers_total": followers.get("total"),
                "artist_genres": ", ".join(artist.get("genres", [])),
            })
        return pd.DataFrame(records)
    else:
        logger.error(f"API error: {response.status_code} - {response.text[:200]}")
        return None

def get_artist_data(input_file: Path,output_dir: Path):
    date = get_chart_date(input_file)
    file_path = Path(output_dir/f'artist-{date}.json')
    last_id = None
    if file_path.exists():
        try:
            old_df = pd.read_json(file_path, lines=True)
            if not old_df.empty:
                last_uri = old_df['artist_uri'].iloc[-1]
                last_id = last_uri.split(':')[-1]
        except ValueError:
            pass

    # Doc track_info JSON lines -> lay artist_id unique
    df_track = pd.read_json(input_file, lines=True)

    # artist_id co the la "id1, id2" -> split ra unique list
    all_artist_ids = []
    for ids_str in df_track['artist_id'].dropna().unique():
        for aid in str(ids_str).split(', '):
            aid = aid.strip()
            if aid and aid not in all_artist_ids:
                all_artist_ids.append(aid)

    if last_id and last_id in all_artist_ids:
        last_index = all_artist_ids.index(last_id)
        all_artist_ids = all_artist_ids[last_index+1:]
        if not all_artist_ids:
            return file_path
    else:
        pass

    logger.info(f"Total unique artist IDs: {len(all_artist_ids)}")

    list_df = []
    timezone = [1,2,3,4,5,6,7]
    date = get_chart_date(input_file)
    id_tz=1
    output_dir.mkdir(parents=True,exist_ok = True)
    i=0
    while i < len(all_artist_ids):
        id_string = ','.join(all_artist_ids[i : i + BATCH_SIZE])
        df = get_api_artist_info(id_string,id_tz)
        if df is not None:
            batch_end = min(i + BATCH_SIZE, len(all_artist_ids))
            logger.info(f"Extracting {batch_end}/{len(all_artist_ids)}")
            list_df.append(df)
            i += BATCH_SIZE
        else:
            logger.warning("API het request...")
            if list_df:
                logger.info("Dang luu file....")
                df_artist = pd.concat(list_df,ignore_index =True)
                df_artist['fetched_at'] = date
                df_artist.to_json(f'{output_dir}/artist-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
                # clear list_df sau khi save de khong luu trung
                list_df = []
            id_tz+=1
        if id_tz > len(timezone):
            break
        time.sleep(2)   
    if list_df:
        df_artist = pd.concat(list_df,ignore_index =True)
        df_artist['fetched_at'] = date
        df_artist.to_json(f'{output_dir}/artist-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
    else:
        if not list_df and i == 0:
            logger.error("There is no data..")
            sys.exit(1)
    return output_dir / f'artist-{date}.json'

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify artist info tu API'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/artist',
        type=Path,
        help = 'Dir output'
    )
    return parser.parse_known_args()[0]

def crawl_artist(file_track_info):
    args = parse_args()
    logger.info("Extracting artist data to file json...")
    output_file = get_artist_data(Path(file_track_info),args.output_dir)
    logger.info(f"saved data into {args.output_dir}")
    return str(output_file) if output_file else None
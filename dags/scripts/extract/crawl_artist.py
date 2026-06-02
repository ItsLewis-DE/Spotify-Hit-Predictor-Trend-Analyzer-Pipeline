import requests
import json
import os, logging
from dotenv import load_dotenv
import csv
from pathlib import Path
import pandas as pd
import time
import argparse
import re
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def get_artist_info(spotify_id_string: str,timezone: int,i: int)-> pd.DataFrame:
    BASE_URL = f'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/artists'
    params = {'ids': spotify_id_string}
    if timezone ==1:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_5')
    elif timezone==2:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_6')
    elif timezone==3:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_7')
    else:
        X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_8')
    headers = {
        "X-RapidAPI-Key": X_RapidAPI_Key, 
        "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com" 
    }

    response = requests.get(BASE_URL, headers=headers,params = params)
    if response.status_code == 429:
        return None
    if response.status_code == 200:
        logger.info("Extracting data audio feature....")
        df = pd.DataFrame(response.json()['audio_features'])
        return df

def extract_artist_info(input_file: Path,output_dir: Path):
    df_track = pd.read_json(input_file)
    df_track.rename(columns= {'id':'artist_id'},inplace=True)
    spotify_id_string = df_track['artist_id'].to_list()
    list_df = []
    timezone = [1,2,3,4]
    date = get_chart_date(input_file)
    id_tz=1
    output_dir.mkdir(parents=True,exist_ok = True)
    i=0
    while i < len(spotify_id_string):
        id_string = ','.join(spotify_id_string[i : i +5])
        df = get_artist_info(id_string,id_tz,i)
        if df is not None:
            logger.info(f"Extracting {i+5}/200")
            list_df.append(df)
            i+=5
        else:
            logger.warning("API het request...")
            if list_df:
                logger.info("Dang luu file....")
                df_artist = pd.concat(list_df,ignore_index =True)
                df_merge = pd.merge(df_track,df_artist,left_on = 'artist_id',right_on = 'id')
                df_merge.to_json(f'{output_dir}/artist-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
                # clear list_df sau khi save de khong luu trung
                list_df = []
            id_tz+=1
        if id_tz > len(timezone):
            break
        time.sleep(2)   
    if list_df:
        df_audio_feature = pd.concat(list_df,ignore_index =True)
        df_merge = pd.merge(df_track,df_audio_feature,left_on = 'spotify_id',right_on = 'id')
        df_merge.to_json(f'{output_dir}/feature-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
    else:
        logger.error("There is no data..")
        return

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify audio feature tu API'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/artist',
        type=Path,
        help = 'Dir output'
    )
    return parser.parse_known_args()[0]

def crawl_artist(file_top_track):
    args = parse_args()
    logger.info("Extracting data to file json...")
    get_artist(Path(file_top_track),args.output_dir)
    logger.info(f"saved data into {args.output_dir}")
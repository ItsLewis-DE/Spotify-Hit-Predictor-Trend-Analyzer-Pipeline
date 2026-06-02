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
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 5

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


def get_api_audio_feature(spotify_id_string: str,timezone: int,i: int)-> pd.DataFrame:
    BASE_URL = f'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/audio-features'
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
        logger.info("Extracting data audio feature....")
        df = pd.DataFrame(response.json()['audio_features'])
        return df
    else:
        logger.error(f"API error: {response.status_code} - {response.text[:200]}")
        return None

def get_audio_feature(input_file: Path,output_dir: Path):
    date = get_chart_date(input_file)
    file_path = Path(output_dir/f'feature-{date}.json')
    last_id = None
    if file_path.exists():
        try:
            old_df = pd.read_json(file_path, lines=True)
            if not old_df.empty:
                last_uri = old_df['uri'].iloc[-1]
                last_id = str(last_uri).split(':')[-1]
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
        df = get_api_audio_feature(id_string,id_tz,i)
        if df is not None:
            batch_end = min(i + BATCH_SIZE, len(spotify_id_string))
            logger.info(f"Extracting {batch_end}/{len(spotify_id_string)}")
            list_df.append(df)
            i += BATCH_SIZE
        else:
            logger.warning("API het request...")
            if list_df:
                logger.info("Dang luu file....")
                df_audio_feature = pd.concat(list_df,ignore_index =True)
                df_merge = pd.merge(df_rank,df_audio_feature,left_on = 'spotify_id',right_on = 'id')
                df_merge.to_json(f'{output_dir}/feature-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
                # clear list_df sau khi save de khong luu trung
                list_df = []
            id_tz+=1
        if id_tz > len(timezone):
            break
        time.sleep(2)   
    if list_df:
        df_audio_feature = pd.concat(list_df,ignore_index =True)
        df_merge = pd.merge(df_rank,df_audio_feature,left_on = 'spotify_id',right_on = 'id')
        df_merge.to_json(f'{output_dir}/feature-{date}.json',orient='records',lines=True,force_ascii=False,date_format='iso',mode='a')
    else:
        if not list_df and i == 0:
            logger.error("There is no data..")
            sys.exit(1)
    return output_dir / f'feature-{date}.json'

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify audio feature tu API'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/audio_feature',
        type=Path,
        help = 'Dir output'
    )
    return parser.parse_known_args()[0]

def crawl_audio_feature(file_top_track):
    args = parse_args()
    logger.info("Extracting data to file json...")
    output_file = get_audio_feature(Path(file_top_track),args.output_dir)
    logger.info(f"saved data into {args.output_dir}")
    return str(output_file) if output_file else None
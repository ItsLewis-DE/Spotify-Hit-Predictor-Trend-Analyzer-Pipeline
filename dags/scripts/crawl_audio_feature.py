import requests
import json
import os, logging
from dotenv import load_dotenv
import csv
from pathlib import Path
import pandas as pd
import time
import argparse
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
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

def get_access_token() ->str:
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data = {'grant_type':'client_credentials'},
        auth= {client_id,client_secret},
        timeout=30
    )
    response.raise_for_status()
    return response.json()['access_token']

def get_api_audio_feature(spotify_id_string: str)-> pd.DataFrame:
    BASE_URL = f'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/audio-features'
    params = {'ids': spotify_id_string}
    headers = {
        "X-RapidAPI-Key": '890ef3de4dmsh514efe84ee4b162p1e8d4cjsn4edbcaa14778', 
        "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com" 
    }

    # Gọi API trực tiếp không cần biến params nữa
    response = requests.get(BASE_URL, headers=headers,params = params)
    response.raise_for_status()
    if response.status_code == 200:
        logger.info("Extracting data audio feature....")
        df = pd.DataFrame(response.json()['audio_features'])
        return df

def get_audio_feature(input_file: Path,output_dir: Path):
    df_rank = pd.read_csv(input_file)
    df_rank['uri'] = df_rank['uri'].str.split(':').str[-1] 
    df_rank.rename(columns= {'uri':'spotify_id'},inplace=True)
    spotify_id_string = df_rank['spotify_id'].to_list()
    list_df = []
    for i in range(0,50,5):
        id_string = ','.join(spotify_id_string[i : i +5])
        df = get_api_audio_feature(id_string)
        if df is not None:
            list_df.append(df)
        time.sleep(1)
    df_audio_feature = pd.concat(list_df,ignore_index =True)
    df_merge = pd.merge(df_rank,df_audio_feature,left_on = 'spotify_id',right_on = 'id')
    date = '-'.join(input_file.stem.split('-')[3:])
    output_dir.mkdir(parents=True,exist_ok = True)
    df_merge.to_json(f'{output_dir}/feature-{date}.json',orient='records',lines=True,force_ascii=False)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify audio feature tu API'
    )
    parser.add_argument(
        '--input_file',
        type=Path,
        help='File input'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/audio_feature',
        type=Path,
        help = 'Dir output'
    )
    parser.add_argument(
        '--input_dir',
        default = 'data/top_track',
        type=Path,
        help='Dir input'
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    input_path = args.input_file or read_newest_file(args.input_dir,'.csv')
    logger.info("Extracting data to file json...")
    get_audio_feature(input_path,args.output_dir)
    logger.info(f"saved data into {args.output_dir}")

if __name__ == '__main__':
    main()
import requests
import json
import os,logging
from dotenv import load_dotenv
import time
import boto3
import string
from pathlib import Path
load_dotenv()

logging.basicConfig(
    level=logging.INFO, # Cho phép hiển thị log từ mức INFO trở lên
    format='%(asctime)s - %(levelname)s - %(message)s' # Định dạng cho dòng log dễ nhìn hơn
)

BASE_URL = 'https://api.spotify.com/v1'
# s3_client = boto3.client(
#     's3',
#     aws_access_key_id = os.getenv("AWS_ACCESS_KEY"),
#     aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
#     region_name='ap-southest-1'
# )
def read_newest_file(dirpath,extension):
    logger = logging.getLogger(__name__)
    path = Path(dirpath)
    if not path.exists():
        logger.error("Can not found file!!")
        raise
    files = [file for file in path.iterdir() 
             if file.is_file() and file.suffix == extension
            ]
    if not files:
        return None
    newest_file = max(
        files,
        key = lambda file : file.stat().st_mtime
    )
    return newest_file
 
def get_access_token():
    logger = logging.getLogger(__name__)
    auth_url = "https://accounts.spotify.com/api/token"
    logger.info("Taking access key...")
    try:
        response = requests.post(auth_url,data = {
            'grant_type':'client_credentials',
            'client_id':os.getenv('SPOTIFY_CLIENT_ID'),
            'client_secret':os.getenv('SPOTIFY_CLIENT_SECRET')
        })
        response.raise_for_status()
        access_key = response.json()['access_token']
        return access_key
    except requests.exceptions.RequestException as e:
        logger.error(f"There is an error while extracting data from API: {e}")

ACCESS_TOKEN = get_access_token()
HEADERS = {'Authorization':f"Bearer {ACCESS_TOKEN}"}

# def (your_def):
#     asjhdg
#     asdjhq

        
# your_def()
import requests
import json
import os,logging
from dotenv import load_dotenv
import time
import boto3
load_dotenv()

logging.basicConfig(
    level=logging.INFO, # Cho phép hiển thị log từ mức INFO trở lên
    format='%(asctime)s - %(levelname)s - %(message)s' # Định dạng cho dòng log dễ nhìn hơn
)

s3_client = boto3.client(
    's3',
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name='ap-southest-1'
)
BASE_URL = 'https://api.spotify.com/v1'
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
def search_batch_using_next():
    logger = logging.getLogger(__name__)
    url = f"{BASE_URL}/search"
    years = [2025,2026]
    for year in years:
        logger.info(f"Extracting data year: {year}")
        temp_url = url
        params = {
        'q' : f'year: {year}',
        'type': 'track',
        'limit':10,
        'offset':0,
        'market':'VN'
        }
        batch_num =1
        while temp_url:
            logger.info(f"Page: {batch_num}")
            if batch_num==1:
                response = requests.get(temp_url,headers = HEADERS, params = params,stream=True)
                response.raise_for_status()
                s3_client.upload_filepbj(
                    Fileobj=response.raw,
                    Bucket='spotify-stream-bucket',
                    Key=s3_object_name
                )
            else:
                # The 'next' url from Spotify already includes all the necessary query parameters.
                response = requests.get(temp_url, headers=HEADERS)
                response.raise_for_status()
            data = response.json()    
            # 'next' URL is inside the 'tracks' paging object.
            temp_url = data.get('tracks', {}).get('next')
            batch_num += 1
            with open('ouput.json','a') as f:
                json.dump(data,f,indent=2)
            time.sleep(1)
        logger.info("Extracting data successfully!!")
        
search_batch_using_next()
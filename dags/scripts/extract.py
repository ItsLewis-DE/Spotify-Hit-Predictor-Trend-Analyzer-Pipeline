import requests
import json
import os,logging
from dotenv import load_dotenv
import time
import boto3
import string 
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
two_letters =[a+b for a in string.ascii_lowercase for b in string.ascii_lowercase]
numbers = [str(i) for i in range(10)]
all_keywords = two_letters + numbers

def search_batch_using_next():
    logger = logging.getLogger(__name__)
    url = f"{BASE_URL}/search"
    years = [2026]
    for year in years:
        logger.info(f"Extracting data year: {year}")
        for key in all_keywords:
            temp_url = url
            params = {
            'q' : f'{key} year: {year}',
            'type': 'track',
            'limit':10,
            'offset':0,
            'market':'VN'
            }
            batch_num =1
            while temp_url:
                logger.info(f"Page: {batch_num}")
                try:
                    if batch_num==1:
                        response = requests.get(temp_url,headers = HEADERS, params = params)
                        # s3_client.upload_filepbj(
                        #     Fileobj=response.raw,
                        #     Bucket='spotify-stream-bucket',
                        #     Key=s3_object_name
                        # )
                    else:
                        # The 'next' url from Spotify already includes all the necessary query parameters.
                        response = requests.get(temp_url, headers=HEADERS)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After",5))
                        logger.warning(f"Rate limit!! You have to wait {retry_after}s")
                        time.sleep(retry_after)
                        continue
                    data = response.json()    
                    # 'next' URL is inside the 'tracks' paging object.
                    temp_url = data.get('tracks', {}).get('next')
                    batch_num += 1
                    with open('ouput.json','a') as f:
                        json.dump(data,f,indent=2)
                except requests.exceptions.RequestException as e:
                    logger.error(f'There is an error: {e}')
                time.sleep(1)
        logger.info("Extracting data successfully!!")
        
search_batch_using_next()
import requests
import os
from dotenv import load_dotenv

load_dotenv()
X_RapidAPI_Key = os.getenv('X_RapidAPI_Key_1')
BASE_URL = 'https://spotify-extended-audio-features-api.p.rapidapi.com/v1/audio-features'
headers = {
    "X-RapidAPI-Key": X_RapidAPI_Key, 
    "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com" 
}
# Using valid track IDs from Spotify
ids = "4JpKVNYnVcJ8tuZMRraQz2,7xGfCGCR8ch2H5lEVB5BKE"
params = {'ids': ids}

response = requests.get(BASE_URL, headers=headers, params=params)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

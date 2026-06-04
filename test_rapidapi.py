import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

key = os.getenv('X_RapidAPI_Key_7')
if not key:
    print("Error: X_RapidAPI_Key_1 not found in .env")
    exit(1)

url = "https://spotify-extended-audio-features-api.p.rapidapi.com/v1/audio-features"
# Demo track ID (The Killers - Mr. Brightside)
params = {"ids": "3n3Ppam7vgaVa1iaRUc9Lp"} 
headers = {
    "X-RapidAPI-Key": key,
    "X-RapidAPI-Host": "spotify-extended-audio-features-api.p.rapidapi.com"
}

print(f"Testing key: {key[:5]}...{key[-5:]}")
print("Sending request to RapidAPI...")

response = requests.get(url, headers=headers, params=params)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("SUCCESS! Data received:")
    print(json.dumps(response.json(), indent=2))
else:
    print("FAILED!")
    print(response.text)

import argparse
import os
import json
import logging
import pandas as pd
import requests
import re
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_chart_date(filename):
    match = re.search(r"\d{4}-\d{2}-\d{2}", str(filename))
    return match.group(0) if match else ""

def get_access_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30
    )
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_spotify_single(ids, url_endpoint, token):
    headers = {"Authorization": f"Bearer {token}"}
    results = {}
    
    total_ids = len(ids)
    for i, item_id in enumerate(ids):
        for _ in range(3):
            response = requests.get(
                f"{url_endpoint}/{item_id}",
                headers=headers,
                timeout=30
            )
            if response.status_code == 429:
                time.sleep(int(response.headers.get("Retry-After", 5)))
                continue
            
            if response.status_code == 404:
                logger.warning(f"Item not found: {item_id}")
                break
                
            response.raise_for_status()
            
            item = response.json()
            if item and "id" in item:
                results[item["id"]] = item
            break
            
        # Delay to prevent rate limits
        time.sleep(0.1)
        
        if (i + 1) % 10 == 0 or (i + 1) == total_ids:
            logger.info(f"Fetched {i + 1}/{total_ids} items...")
            
    return results

def get_spotify_id(uri):
    if pd.isna(uri): return None
    uri = str(uri).strip()
    if uri.startswith("spotify:track:"): return uri.split(":")[-1]
    if "open.spotify.com/track/" in uri: return uri.split("/track/")[-1].split("?")[0].split("/")[0]
    return uri

def crawl_artist(input_file=None):
    if not input_file:
        files = list(Path("data/top_track").glob("regional-vn-weekly-*.csv"))
        if not files:
            raise FileNotFoundError("No input file provided and no CSV found in data/top_track")
        input_file = max(files, key=lambda f: f.stat().st_mtime)
        
    input_path = Path(input_file)
    date = get_chart_date(input_path.name)
    if not date:
        date = time.strftime("%Y-%m-%d")
        
    df = pd.read_csv(input_path)
    
    df['spotify_id'] = df['uri'].apply(get_spotify_id)
    unique_track_ids = df['spotify_id'].dropna().unique().tolist()
    
    token = get_access_token()
    
    logger.info(f"Fetching {len(unique_track_ids)} tracks...")
    tracks_by_id = fetch_spotify_single(unique_track_ids, "https://api.spotify.com/v1/tracks", token)
    
    artist_ids = set()
    for track in tracks_by_id.values():
        for artist in track.get("artists", []):
            if artist.get("id"):
                artist_ids.add(artist["id"])
                
    logger.info(f"Fetching {len(artist_ids)} artists...")
    artists_by_id = fetch_spotify_single(artist_ids, "https://api.spotify.com/v1/artists", token)
    
    records = []
    for _, row in df.iterrows():
        track_id = row['spotify_id']
        track = tracks_by_id.get(track_id)
        
        row_dict = row.to_dict()
        if not track:
            row_dict.update({
                "artist_id": "",
                "artist_name_from_track": "",
                "spotify_track_api_found": False,
                "source_file": input_path.name,
                "fetched_at": date,
                "spotify_artist_api_found": False,
                "spotify_artist": None
            })
            records.append(row_dict)
            continue
            
        for artist in track.get("artists", []):
            artist_id = artist.get("id")
            if not artist_id: continue
            
            artist_data = artists_by_id.get(artist_id)
            if artist_data and "images" in artist_data:
                artist_data = artist_data.copy()
                del artist_data["images"]
                
            new_row = row_dict.copy()
            new_row.update({
                "artist_id": artist_id,
                "artist_name_from_track": artist.get("name"),
                "spotify_track_api_found": True,
                "source_file": input_path.name,
                "fetched_at": date,
                "spotify_artist_api_found": artist_id in artists_by_id,
                "spotify_artist": artist_data
            })
            records.append(new_row)
            
    output_dir = Path("data/artist")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"artist_{date}.json"
    
    with out_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    logger.info(f"Saved {len(records)} records to {out_file}")
    return str(out_file)
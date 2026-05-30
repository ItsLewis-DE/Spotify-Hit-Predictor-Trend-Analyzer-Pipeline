import argparse
import json
import logging
import os
import time
from pathlib import Path
import re
import pandas as pd
import requests
from dotenv import load_dotenv

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

def get_access_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]

def fetch_spotify_metadata_by_uri(input_path,uri_series,output_dir,date,uri_column_name="uri"):
    access_token = get_access_token()
    unique_uris = uri_series.dropna().unique().tolist()
    track_data_list = []
    total_tracks = len(unique_uris)

    for i, uri in enumerate(unique_uris):
        try:
            # Lấy track_id từ dạng spotify:track:xxxx...
            track_id = uri.split(":")[-1]
            
            # Simple retry logic để handle 429 Too Many Requests
            max_retries = 3
            for attempt in range(max_retries):
                response = requests.get(
                    f"https://api.spotify.com/v1/tracks/{track_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                break
                
            if response.status_code == 404:
                print(f"Track {i + 1}/{total_tracks} không tìm thấy: {uri}")
                continue
                
            response.raise_for_status()
            track = response.json()

            if track is None or "id" not in track:
                continue

            album    = track.get("album", {})
            ext_ids  = track.get("external_ids", {})

            track_data_list.append({
                uri_column_name:      track.get("uri"),
                "track_id":           track.get("id"),
                "duration_ms":        track.get("duration_ms"),
                "explicit":           track.get("explicit"),
                "isrc":               ext_ids.get("isrc"),
                "album_type":         album.get("album_type"),  
                "album_release_date": album.get("release_date"),
                'album_name': album.get('name')
            })

            print(f"Track {i + 1}/{total_tracks} xong: {track.get('name')}")

            # autosave mỗi 10 bài
            if (i + 1) % 10 == 0:
                temp_df = pd.DataFrame(track_data_list)
                temp_df['fetched_at'] = date
                temp_df.to_json(output_dir/f'track_info-{date}.json', orient="records", lines=True, force_ascii=False,date_format='iso')
                print(" -> Đã autosave")

            time.sleep(1)  # Delay giữa các lần gọi API (2s/bài)

        except Exception as e:
            print(f"Lỗi tại track {i + 1} ({uri}): {e}")
            time.sleep(2)
            continue

    return pd.DataFrame(track_data_list, columns=[
        uri_column_name,
        "track_id",
        "duration_ms",
        "explicit",
        "isrc",
        "album_type",
        "album_release_date",
        'album_name'
    ])

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = 'Lay data Spotify audio feature tu API'
    )
    parser.add_argument(
        '--output_dir',
        default = 'data/track_info',
        type=Path,
        help = 'Dir output'
    )
    return parser.parse_known_args()[0]

def read_newest_file(dirpath,extension):
    path = Path(dirpath)
    if not path.exists():
        logger.error("Can not found file!!")
        return
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


def crawl_track_spotify(file_top_track):
    args = parse_args()
    input_path = Path(file_top_track)
    df = pd.read_csv(input_path)
    args.output_dir.mkdir(parents=True,exist_ok = True)
    date = get_chart_date(input_path)
    metadata_df = fetch_spotify_metadata_by_uri(input_path,df["uri"],args.output_dir,date)
    output_file = args.output_dir / f"track_info-{date}.json"

    # lưu JSON để dùng lại, không cần fetch lại lần sau
    metadata_df['fetched_at'] = date
    metadata_df.to_json(output_file, orient="records",lines=True,force_ascii=False,date_format='iso')
    time.sleep(30)
    return str(output_file)

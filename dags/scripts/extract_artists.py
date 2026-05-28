import argparse
import csv
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_TRACKS_URL = "https://api.spotify.com/v1/tracks"
SPOTIFY_ARTISTS_URL = "https://api.spotify.com/v1/artists"

DEFAULT_INPUT_DIR = Path("data/top_track")
DEFAULT_OUTPUT_DIR = Path("data/artist")
FILE_PATTERN = "regional-vn-weekly-*.csv"
BATCH_SIZE = 50

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_chart_date(file_path):
    match = re.search(r"\d{4}-\d{2}-\d{2}", file_path.name)
    if match:
        return match.group(0)
    return ""


def get_latest_csv(input_dir=DEFAULT_INPUT_DIR):
    files = list(Path(input_dir).glob(FILE_PATTERN))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    return max(files, key=lambda file: (get_chart_date(file), file.stat().st_mtime))


def get_spotify_id(row):
    if row.get("spotify_id"):
        return row["spotify_id"].strip()

    uri = row.get("uri", "").strip()
    if uri.startswith("spotify:track:"):
        return uri.split(":")[-1]

    if "open.spotify.com/track/" in uri:
        return uri.split("/track/")[-1].split("?")[0].split("/")[0]

    return uri


def read_top_track_csv(input_file):
    rows = []
    track_ids = []
    seen_ids = set()

    with Path(input_file).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            track_id = get_spotify_id(row)
            if not track_id:
                continue

            row["spotify_id"] = track_id
            rows.append(row)

            if track_id not in seen_ids:
                track_ids.append(track_id)
                seen_ids.add(track_id)

    if not track_ids:
        raise ValueError(f"No Spotify track IDs found in {input_file}")

    return rows, track_ids


def get_access_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_tracks(track_ids, headers, market="VN"):
    tracks_by_id = {}

    for start in range(0, len(track_ids), BATCH_SIZE):
        batch = track_ids[start : start + BATCH_SIZE]
        response = requests.get(
            SPOTIFY_TRACKS_URL,
            headers=headers,
            params={"ids": ",".join(batch), "market": market},
            timeout=30,
        )
        response.raise_for_status()

        for track in response.json()["tracks"]:
            if track:
                tracks_by_id[track["id"]] = track

        logger.info("Fetched %s/%s tracks", len(tracks_by_id), len(track_ids))

    return tracks_by_id


def get_artist_rows(rows, tracks_by_id):
    artist_rows = []
    artist_ids = []
    seen_artist_ids = set()

    for row in rows:
        track_id = row["spotify_id"]
        track = tracks_by_id.get(track_id)

        if not track:
            artist_row = dict(row)
            artist_row["artist_id"] = ""
            artist_row["artist_name_from_track"] = ""
            artist_row["spotify_track_api_found"] = False
            artist_rows.append(artist_row)
            continue

        for artist in track.get("artists", []):
            artist_id = artist.get("id")
            if not artist_id:
                continue

            artist_row = dict(row)
            artist_row["artist_id"] = artist_id
            artist_row["artist_name_from_track"] = artist.get("name")
            artist_row["spotify_track_api_found"] = True
            artist_rows.append(artist_row)

            if artist_id not in seen_artist_ids:
                artist_ids.append(artist_id)
                seen_artist_ids.add(artist_id)

    if not artist_ids:
        raise ValueError("No Spotify artist IDs found from track data")

    return artist_rows, artist_ids


def fetch_artists(artist_ids, headers):
    artists_by_id = {}

    for start in range(0, len(artist_ids), BATCH_SIZE):
        batch = artist_ids[start : start + BATCH_SIZE]
        response = requests.get(
            SPOTIFY_ARTISTS_URL,
            headers=headers,
            params={"ids": ",".join(batch)},
            timeout=30,
        )
        response.raise_for_status()

        for artist in response.json()["artists"]:
            if artist:
                artists_by_id[artist["id"]] = artist

        logger.info("Fetched %s/%s artists", len(artists_by_id), len(artist_ids))

    return artists_by_id


def build_output_file(input_file, output_dir):
    chart_date = get_chart_date(Path(input_file))
    if not chart_date:
        chart_date = datetime.now().strftime("%Y-%m-%d")

    return Path(output_dir) / f"artist_{chart_date}.jsonl"


def save_jsonl(records, output_file):
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with Path(output_file).open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_artists(input_file, output_dir=DEFAULT_OUTPUT_DIR, market="VN"):
    logger.info("Reading top track CSV: %s", input_file)
    rows, track_ids = read_top_track_csv(input_file)

    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    tracks_by_id = fetch_tracks(track_ids, headers, market=market)
    artist_rows, artist_ids = get_artist_rows(rows, tracks_by_id)
    artists_by_id = fetch_artists(artist_ids, headers)

    fetched_at = datetime.now().isoformat(timespec="seconds")
    records = []

    for row in artist_rows:
        artist_id = row["artist_id"]
        row["source_file"] = Path(input_file).name
        row["fetched_at"] = fetched_at
        row["spotify_artist_api_found"] = artist_id in artists_by_id
        row["spotify_artist"] = artists_by_id.get(artist_id)
        records.append(row)

    output_file = build_output_file(input_file, output_dir)
    save_jsonl(records, output_file)
    logger.info("Saved output file: %s", output_file)

    return str(output_file)


def extract_artists_from_latest_chart(
    input_dir=DEFAULT_INPUT_DIR,
    output_dir=DEFAULT_OUTPUT_DIR,
    market="VN",
):
    input_file = get_latest_csv(input_dir)
    logger.info("Latest CSV selected: %s", input_file)
    return extract_artists(input_file, output_dir, market)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--market", default=os.getenv("SPOTIFY_MARKET", "VN"))
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = args.input_file or get_latest_csv(args.input_dir)
    output_file = extract_artists(input_file, args.output_dir, args.market)
    print(output_file)


if __name__ == "__main__":
    main()

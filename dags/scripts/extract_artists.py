import argparse
import csv
import json
import logging
import os
import re
import time
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
DEFAULT_TRACK_REQUEST_DELAY_SECONDS = 2
DEFAULT_ARTIST_REQUEST_DELAY_SECONDS = 2
DEFAULT_SPOTIFY_MAX_RETRIES = 5
DEFAULT_SPOTIFY_MAX_RETRY_WAIT_SECONDS = float(
    os.getenv("SPOTIFY_MAX_RETRY_WAIT_SECONDS", "300")
)
SPOTIFY_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

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
    raise_for_spotify_status(response, "getting access token")
    return response.json()["access_token"]


def get_spotify_error_detail(response):
    try:
        payload = response.json()
    except ValueError:
        body = response.text.strip()
        return body[:500] if body else "<empty response body>"

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        status = error.get("status", response.status_code)
        message = error.get("message", "")
        return f"status={status}, message={message}"

    return json.dumps(payload, ensure_ascii=False)[:500]


def raise_for_spotify_status(response, context):
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = get_spotify_error_detail(response)
        raise requests.HTTPError(
            f"{exc}; Spotify response: {detail}; context: {context}",
            response=response,
        ) from exc


def get_retry_after_seconds(response, fallback_seconds):
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return fallback_seconds

    try:
        return max(float(retry_after), 0)
    except ValueError:
        return fallback_seconds


def spotify_get(
    url,
    headers,
    context,
    params=None,
    max_retries=DEFAULT_SPOTIFY_MAX_RETRIES,
    max_retry_wait_seconds=DEFAULT_SPOTIFY_MAX_RETRY_WAIT_SECONDS,
):
    last_response = None

    for attempt in range(max_retries + 1):
        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=30,
        )
        last_response = response

        if (
            response.status_code not in SPOTIFY_RETRYABLE_STATUS_CODES
            or attempt == max_retries
        ):
            return response

        fallback_seconds = min(2**attempt, 60)
        wait_seconds = get_retry_after_seconds(response, fallback_seconds)
        if wait_seconds > max_retry_wait_seconds:
            raise requests.HTTPError(
                f"Spotify asked to wait {wait_seconds} seconds while {context}, "
                f"which exceeds SPOTIFY_MAX_RETRY_WAIT_SECONDS="
                f"{max_retry_wait_seconds}. Retry later or raise that limit. "
                f"Spotify response: {get_spotify_error_detail(response)}",
                response=response,
            )

        logger.warning(
            "Spotify returned %s while %s. Waiting %s seconds before retry %s/%s. "
            "Response: %s",
            response.status_code,
            context,
            wait_seconds,
            attempt + 1,
            max_retries,
            get_spotify_error_detail(response),
        )
        time.sleep(wait_seconds)

    return last_response


def fetch_tracks(
    track_ids,
    headers,
    market="VN",
    request_delay_seconds=DEFAULT_TRACK_REQUEST_DELAY_SECONDS,
):
    tracks_by_id = {}
    total_tracks = len(track_ids)

    for track_number, track_id in enumerate(
        track_ids,
        start=1,
    ):
        params = {}
        if market:
            params["market"] = market

        response = spotify_get(
            f"{SPOTIFY_TRACKS_URL}/{track_id}",
            headers=headers,
            params=params,
            context=f"fetching track {track_number}/{total_tracks}",
        )
        if response.status_code == 403 and market:
            logger.warning(
                "Spotify returned 403 for track %s/%s with market=%s. "
                "Retrying without market. Response: %s",
                track_number,
                total_tracks,
                market,
                get_spotify_error_detail(response),
            )
            response = spotify_get(
                f"{SPOTIFY_TRACKS_URL}/{track_id}",
                headers=headers,
                context=f"fetching track {track_number}/{total_tracks} without market",
            )

        if response.status_code == 404:
            logger.warning(
                "Spotify track not found: %s (%s/%s). Response: %s",
                track_id,
                track_number,
                total_tracks,
                get_spotify_error_detail(response),
            )
            continue

        raise_for_spotify_status(
            response,
            f"fetching track {track_number}/{total_tracks}",
        )

        track = response.json()
        if track:
            tracks_by_id[track["id"]] = track

        logger.info(
            "Fetched track %s/%s. Total tracks fetched: %s/%s",
            track_number,
            total_tracks,
            len(tracks_by_id),
            total_tracks,
        )

        if track_number < total_tracks and request_delay_seconds > 0:
            logger.info(
                "Waiting %s seconds before the next track request",
                request_delay_seconds,
            )
            time.sleep(request_delay_seconds)

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


def fetch_artists(
    artist_ids,
    headers,
    request_delay_seconds=DEFAULT_ARTIST_REQUEST_DELAY_SECONDS,
):
    artists_by_id = {}
    total_artists = len(artist_ids)

    for artist_number, artist_id in enumerate(
        artist_ids,
        start=1,
    ):
        response = spotify_get(
            f"{SPOTIFY_ARTISTS_URL}/{artist_id}",
            headers=headers,
            context=f"fetching artist {artist_number}/{total_artists}",
        )

        if response.status_code == 404:
            logger.warning(
                "Spotify artist not found: %s (%s/%s). Response: %s",
                artist_id,
                artist_number,
                total_artists,
                get_spotify_error_detail(response),
            )
            continue

        raise_for_spotify_status(
            response,
            f"fetching artist {artist_number}/{total_artists}",
        )

        artist = response.json()
        if artist:
            artists_by_id[artist["id"]] = artist

        logger.info(
            "Fetched artist %s/%s. Total artists fetched: %s/%s",
            artist_number,
            total_artists,
            len(artists_by_id),
            total_artists,
        )

        if artist_number < total_artists and request_delay_seconds > 0:
            logger.info(
                "Waiting %s seconds before the next artist request",
                request_delay_seconds,
            )
            time.sleep(request_delay_seconds)

    return artists_by_id


def remove_artist_images(artist):
    if not artist:
        return None

    return {key: value for key, value in artist.items() if key != "images"}


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


def extract_artists(
    input_file,
    output_dir=DEFAULT_OUTPUT_DIR,
    market="VN",
    track_request_delay_seconds=DEFAULT_TRACK_REQUEST_DELAY_SECONDS,
    artist_request_delay_seconds=DEFAULT_ARTIST_REQUEST_DELAY_SECONDS,
):
    logger.info("Reading top track CSV: %s", input_file)
    rows, track_ids = read_top_track_csv(input_file)

    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    tracks_by_id = fetch_tracks(
        track_ids,
        headers,
        market=market,
        request_delay_seconds=track_request_delay_seconds,
    )
    artist_rows, artist_ids = get_artist_rows(rows, tracks_by_id)
    artists_by_id = fetch_artists(
        artist_ids,
        headers,
        request_delay_seconds=artist_request_delay_seconds,
    )

    fetched_at = get_chart_date(Path(input_file))
    if not fetched_at:
        raise ValueError(f"No chart date found in input CSV file name: {input_file}")

    records = []

    for row in artist_rows:
        artist_id = row["artist_id"]
        row["source_file"] = Path(input_file).name
        row["fetched_at"] = fetched_at
        row["spotify_artist_api_found"] = artist_id in artists_by_id
        row["spotify_artist"] = remove_artist_images(artists_by_id.get(artist_id))
        records.append(row)

    output_file = build_output_file(input_file, output_dir)
    save_jsonl(records, output_file)
    logger.info("Saved output file: %s", output_file)

    return str(output_file)


def extract_artists_from_latest_chart(
    input_dir=DEFAULT_INPUT_DIR,
    output_dir=DEFAULT_OUTPUT_DIR,
    market="VN",
    track_request_delay_seconds=DEFAULT_TRACK_REQUEST_DELAY_SECONDS,
    artist_request_delay_seconds=DEFAULT_ARTIST_REQUEST_DELAY_SECONDS,
):
    input_file = get_latest_csv(input_dir)
    logger.info("Latest CSV selected: %s", input_file)
    return extract_artists(
        input_file,
        output_dir,
        market,
        track_request_delay_seconds=track_request_delay_seconds,
        artist_request_delay_seconds=artist_request_delay_seconds,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--market", default=os.getenv("SPOTIFY_MARKET", "VN"))
    parser.add_argument(
        "--track-request-delay-seconds",
        "--track-batch-delay-seconds",
        dest="track_request_delay_seconds",
        type=float,
        default=float(
            os.getenv(
                "SPOTIFY_TRACK_REQUEST_DELAY_SECONDS",
                os.getenv(
                    "SPOTIFY_TRACK_BATCH_DELAY_SECONDS",
                    DEFAULT_TRACK_REQUEST_DELAY_SECONDS,
                ),
            )
        ),
    )
    parser.add_argument(
        "--artist-request-delay-seconds",
        "--artist-batch-delay-seconds",
        dest="artist_request_delay_seconds",
        type=float,
        default=float(
            os.getenv(
                "SPOTIFY_ARTIST_REQUEST_DELAY_SECONDS",
                os.getenv(
                    "SPOTIFY_ARTIST_BATCH_DELAY_SECONDS",
                    DEFAULT_ARTIST_REQUEST_DELAY_SECONDS,
                ),
            )
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = args.input_file or get_latest_csv(args.input_dir)
    output_file = extract_artists(
        input_file,
        args.output_dir,
        args.market,
        track_request_delay_seconds=args.track_request_delay_seconds,
        artist_request_delay_seconds=args.artist_request_delay_seconds,
    )
    print(output_file)


if __name__ == "__main__":
    main()

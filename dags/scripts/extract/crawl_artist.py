import argparse
import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"


def get_chart_date(file_path: Path) -> str:
    # Lay ngay chart tu ten file; neu khong co thi dung ngay hien tai.
    match = re.search(r"\d{4}-\d{2}-\d{2}", file_path.name)
    if match:
        return match.group(0)
    return time.strftime("%Y-%m-%d")


def read_newest_file(dirpath: Path, pattern: str) -> Path:
    # Tim file moi nhat trong thu muc theo pattern, uu tien mtime roi ten file.
    if not dirpath.exists():
        raise FileNotFoundError(f"Can not found dir: {dirpath}")

    files = [
        file for file in dirpath.glob(pattern)
        if file.is_file()
    ]
    if not files:
        raise FileNotFoundError(f"Can not found file match {pattern} in {dirpath}")

    return max(files, key=lambda file: (file.stat().st_mtime, file.name))


def read_json_records(file_path: Path) -> list[dict]:
    # Doc track_info tu cac format JSON pho bien thanh danh sach dict.
    """
    Doc file JSON co dang JSON Lines, JSON array, hoac nhieu JSON object lien tiep.
    File track_info hien co trong project co the duoc ghi theo nhieu format.
    """
    content = file_path.read_text(encoding="utf-8-sig").strip()
    if not content:
        return []

    decoder = json.JSONDecoder()
    records = []
    idx = 0

    while idx < len(content):
        while idx < len(content) and content[idx].isspace():
            idx += 1
        if idx >= len(content):
            break

        item, idx = decoder.raw_decode(content, idx)
        if isinstance(item, list):
            records.extend(item)
        else:
            records.append(item)

    return [record for record in records if isinstance(record, dict)]


def get_spotify_id(uri: str | None) -> str | None:
    # Chuan hoa Spotify URI/link thanh track id thuan.
    if not uri:
        return None
    uri = str(uri).strip()
    if uri.startswith("spotify:track:"):
        return uri.split(":")[-1]
    if "open.spotify.com/track/" in uri:
        return uri.split("/track/")[-1].split("?")[0].split("/")[0]
    return uri


def get_track_ids(track_info_records: list[dict]) -> list[str]:
    # Lay danh sach track_id duy nhat tu data track_info.
    track_ids = []
    seen = set()

    for record in track_info_records:
        track_id = record.get("track_id") or get_spotify_id(record.get("uri"))
        if track_id and track_id not in seen:
            track_ids.append(track_id)
            seen.add(track_id)

    return track_ids


def get_access_token() -> str:
    # Lay access token bang Client Credentials Flow cua Spotify.
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30
    )
    response.raise_for_status()
    return response.json()["access_token"]


def spotify_get(url: str, token: str, params: dict | None = None) -> dict:
    # Goi Spotify API voi retry don gian khi gap rate limit 429.
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(3):
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        response.raise_for_status()
        return response.json()

    response.raise_for_status()
    return {}


def fetch_tracks(track_ids: list[str], token: str) -> dict[str, dict]:
    # Goi Track API de lay full track object cho tung track_id.
    tracks_by_id = {}

    for index, track_id in enumerate(track_ids, start=1):
        logger.info(f"Fetching track {index}/{len(track_ids)}: {track_id}")
        track = spotify_get(f"{SPOTIFY_API_BASE_URL}/tracks/{track_id}", token)
        if track and track.get("id"):
            tracks_by_id[track["id"]] = track
        time.sleep(0.2)

    return tracks_by_id


def fetch_artists(artist_ids: list[str], token: str) -> dict[str, dict]:
    # Goi Artist API de lay full artist object va bo field images.
    artists_by_id = {}

    for index, artist_id in enumerate(artist_ids, start=1):
        logger.info(f"Fetching artist {index}/{len(artist_ids)}: {artist_id}")
        artist = spotify_get(f"{SPOTIFY_API_BASE_URL}/artists/{artist_id}", token)
        if artist and artist.get("id"):
            artist.pop("images", None)
            artists_by_id[artist["id"]] = artist
        time.sleep(0.2)

    return artists_by_id


def build_artist_records(
    track_info_records: list[dict],
    tracks_by_id: dict[str, dict],
    artists_by_id: dict[str, dict],
    source_file: Path,
    fetched_at: str
) -> list[dict]:
    # Ghep track_info voi artist data de tao record output theo tung artist cua track.
    records = []

    for track_info in track_info_records:
        track_id = track_info.get("track_id") or get_spotify_id(track_info.get("uri"))
        track = tracks_by_id.get(track_id)

        if not track:
            row = track_info.copy()
            row.update({
                "artist_id": None,
                "artist_name_from_track": None,
                "source_file": source_file.name,
                "fetched_at": fetched_at,
                "spotify_track_api_found": False,
                "spotify_artist_api_found": False,
                "spotify_artist": None
            })
            records.append(row)
            continue

        for artist in track.get("artists", []):
            artist_id = artist.get("id")
            if not artist_id:
                continue

            row = track_info.copy()
            row.update({
                "artist_id": artist_id,
                "artist_name_from_track": artist.get("name"),
                "source_file": source_file.name,
                "fetched_at": fetched_at,
                "spotify_track_api_found": True,
                "spotify_artist_api_found": artist_id in artists_by_id,
                "spotify_artist": artists_by_id.get(artist_id)
            })
            records.append(row)

    return records


def parse_args() -> argparse.Namespace:
    # Dinh nghia tham so CLI cho input track_info va output artist.
    parser = argparse.ArgumentParser(
        description="Lay data Spotify artist tu track_info moi nhat"
    )
    parser.add_argument(
        "--input_file",
        default=None,
        type=Path,
        help="File track_info JSON dau vao"
    )
    parser.add_argument(
        "--input_dir",
        default="data/track_info",
        type=Path,
        help="Dir track_info dau vao"
    )
    parser.add_argument(
        "--output_dir",
        default="data/artist",
        type=Path,
        help="Dir output"
    )
    return parser.parse_known_args()[0]


def crawl_artist(file_track: str | Path | None = None) -> str:
    # Orchestrate toan bo luong: doc track_info, fetch track/artist, luu JSON output.
    args = parse_args()
    input_path = Path(file_track) if file_track else args.input_file

    if input_path is None:
        input_path = read_newest_file(args.input_dir, "track_info-*.json")

    logger.info(f"Reading track info from {input_path}")
    track_info_records = read_json_records(input_path)
    if not track_info_records:
        raise RuntimeError(f"There is no track info data in {input_path}")

    track_ids = get_track_ids(track_info_records)
    if not track_ids:
        raise RuntimeError(f"There is no track_id in {input_path}")

    token = get_access_token()
    tracks_by_id = fetch_tracks(track_ids, token)

    artist_ids = []
    seen_artist_ids = set()
    for track in tracks_by_id.values():
        for artist in track.get("artists", []):
            artist_id = artist.get("id")
            if artist_id and artist_id not in seen_artist_ids:
                artist_ids.append(artist_id)
                seen_artist_ids.add(artist_id)

    artists_by_id = fetch_artists(artist_ids, token)

    date = get_chart_date(input_path)
    artist_records = build_artist_records(
        track_info_records,
        tracks_by_id,
        artists_by_id,
        input_path,
        date
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.output_dir / f"artist_{date}.json"
    with output_file.open("w", encoding="utf-8") as file:
        for record in artist_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"Saved {len(artist_records)} artist records to {output_file}")
    return str(output_file)


if __name__ == "__main__":
    print(crawl_artist())

"""Lay thong tin track Spotify tu file top-track da crawl."""

import argparse
import json
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/tracks/{spotify_id}"

DEFAULT_INPUT_DIR = Path("data/top_track")
DEFAULT_OUTPUT_DIR = Path("data/output_data")
DEFAULT_MARKET = "VN"
REQUEST_TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_latest_json_file(input_dir: Path) -> Path:
    """Tim file JSON moi nhat trong thu muc input."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Khong tim thay thu muc input: {input_dir}")

    json_files = [
        file
        for file in input_dir.glob("*.json")
        if file.is_file() and not file.name.endswith("_enriched.json")
    ]
    if not json_files:
        raise FileNotFoundError(f"Khong co file .json nao trong: {input_dir}")

    return max(json_files, key=lambda file: file.stat().st_mtime)


def build_output_path(input_path: Path, output_dir: Path) -> Path:
    """Tao duong dan output dua tren ten file input."""
    output_name = f"{input_path.stem}_enriched.json"
    return output_dir / output_name


def read_tracks(input_path: Path) -> list[dict]:
    """Doc danh sach track da crawl tu file JSON."""
    with input_path.open("r", encoding="utf-8") as file:
        tracks = json.load(file)

    if not isinstance(tracks, list):
        raise ValueError(f"File input phai la list JSON: {input_path}")

    return tracks


def get_access_token() -> str:
    """Lay Spotify access token bang Client Credentials."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Thieu SPOTIFY_CLIENT_ID hoac SPOTIFY_CLIENT_SECRET")

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_track_data(
    session: requests.Session,
    spotify_id: str,
    access_token: str,
    market: str,
) -> dict:
    """Dung spotify_id de lay thong tin track tu Spotify API."""
    response = session.get(
        SPOTIFY_TRACK_URL.format(spotify_id=spotify_id),
        headers={"Authorization": f"Bearer {access_token}"},
        params={"market": market} if market else None,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    track = response.json()
    return {
        "track_name": track.get("name"),
        "artists": [artist.get("name") for artist in track.get("artists", [])],
        "album_name": track.get("album", {}).get("name"),
        "release_date": track.get("album", {}).get("release_date"),
        "duration_ms": track.get("duration_ms"),
        "popularity": track.get("popularity"),
        "explicit": track.get("explicit"),
        "spotify_url": track.get("external_urls", {}).get("spotify"),
    }


def enrich_tracks(tracks: list[dict], access_token: str, market: str) -> list[dict]:
    """Them data Spotify vao tung track trong file input."""
    enriched_tracks = []

    with requests.Session() as session:
        for track in tracks:
            spotify_id = track.get("spotify_id")
            if not spotify_id:
                enriched_tracks.append(
                    {**track, "track_lookup_error": "missing_spotify_id"}
                )
                continue

            spotify_data = fetch_track_data(
                session=session,
                spotify_id=spotify_id,
                access_token=access_token,
                market=market,
            )
            enriched_tracks.append({**track, **spotify_data})

    return enriched_tracks


def write_tracks(tracks: list[dict], output_path: Path) -> None:
    """Luu ket qua extract ra thu muc output_data."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(tracks, file, indent=2, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lay data Spotify track tu file JSON trong data/top_track."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="File input cu the. Neu khong truyen, script se lay file moi nhat.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Thu muc chua file top-track JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Thu muc luu file output.",
    )
    parser.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        help="Ma market Spotify, vi du: VN, US. De rong neu khong muon gui market.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    input_path = args.input or find_latest_json_file(args.input_dir)
    output_path = build_output_path(input_path, args.output_dir)
    market = args.market or ""

    logger.info("Reading input: %s", input_path)
    tracks = read_tracks(input_path)

    logger.info("Fetching Spotify data for %s tracks...", len(tracks))
    access_token = get_access_token()
    enriched_tracks = enrich_tracks(tracks, access_token, market)

    write_tracks(enriched_tracks, output_path)
    logger.info("Saved %s tracks to %s", len(enriched_tracks), output_path)


if __name__ == "__main__":
    main()

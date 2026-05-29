import os
import json
import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
import time

load_dotenv(r"D:\US\Nhập môn KHDL\miniProject\.env")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

print("CLIENT_ID:", CLIENT_ID)
print("CLIENT_SECRET:", CLIENT_SECRET)

auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)


def fetch_spotify_metadata_by_uri(uri_series, uri_column_name="uri"):
    unique_uris = uri_series.dropna().unique().tolist()
    track_data_list = []
    total_tracks = len(unique_uris)

    for i, uri in enumerate(unique_uris):
        try:
            track = sp.track(uri)

            if track is None:
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
            })

            print(f"Track {i + 1}/{total_tracks} xong: {track.get('name')}")

            # autosave mỗi 10 bài
            if (i + 1) % 10 == 0:
                with open("temp_tracks.json", "w", encoding="utf-8") as f:
                    json.dump(track_data_list, f, ensure_ascii=False, indent=2)
                print(" -> Đã autosave")

            time.sleep(2)

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
    ])


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "regional-vn-weekly-2026-05-21.csv")

    df = pd.read_csv(csv_path)
    metadata_df = fetch_spotify_metadata_by_uri(df["uri"])

    # lưu JSON để dùng lại, không cần fetch lại lần sau
    out_json = os.path.join(BASE_DIR, "tracks_metadata.json")
    metadata_df.to_json(out_json, orient="records", force_ascii=False, indent=2)
    print(f"Đã lưu metadata đến {out_json}")

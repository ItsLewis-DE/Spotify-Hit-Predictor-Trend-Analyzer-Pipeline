import os
import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
import time

load_dotenv(r"D:\US\Nhập môn KHDL\miniProject\.env")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

print(os.getenv("CLIENT_ID"))
print(os.getenv("CLIENT_SECRET"))

auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)


def fetch_spotify_metadata_by_uri(uri_series, uri_column_name="uri"):
    unique_uris = uri_series.dropna().unique().tolist()

    track_data_list = []

    total_tracks = len(unique_uris)

    for i, uri in enumerate(unique_uris):
        try:
            track = sp.track(uri)
            print(track.keys())

            if track is None:
                continue

            track_data_list.append({
                uri_column_name: track["uri"],
                "duration_ms": track["duration_ms"],
                "explicit": track["explicit"],
                "album_name": track["album"]["name"],
                "release_date": track["album"]["release_date"],
            })

            print(f"Track {i + 1}/{total_tracks} xong")

            # mỗi 10 bài auto save cho chắc 
            if (i + 1) % 10 == 0:
                temp_df = pd.DataFrame(track_data_list)
                temp_df.to_csv(
                    "temp_tracks.csv",
                    index=False
                )
                print("Đã autosave")

            time.sleep(2)

        except Exception as e:
            print(f"Lỗi tại track {i + 1}: {e}")
            time.sleep(2)
            continue

    return pd.DataFrame(
        track_data_list,
        columns=[
            uri_column_name,
            "duration_ms",
            "explicit",
            "album_name",
            "release_date",
        ]
    )


# load CSV 
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "regional-vn-weekly-2026-05-21.csv")
    
    df = pd.read_csv(csv_path)
    metadata_df = fetch_spotify_metadata_by_uri(df["uri"])
    result_df = df.merge(metadata_df, on="uri", how="left")
    print(result_df.head())
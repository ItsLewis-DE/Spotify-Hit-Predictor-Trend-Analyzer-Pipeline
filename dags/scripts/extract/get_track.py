import os
import json
import time
import logging
import pandas as pd
import requests
from dotenv import load_dotenv

# Cấu hình logging giống code mẫu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load biến môi trường
load_dotenv()
if not os.getenv("SPOTIFY_CLIENT_ID"):
    load_dotenv(r"D:\US\Nhập môn KHDL\miniProject\.env")

SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_RATE_LIMIT_FALLBACK_SECONDS = 5


def parse_retry_after(value: str | None) -> int:
    try:
        return max(int(value or SPOTIFY_RATE_LIMIT_FALLBACK_SECONDS), 1)
    except ValueError:
        return SPOTIFY_RATE_LIMIT_FALLBACK_SECONDS


def get_access_tokens() -> list[dict]:
    """Lấy danh sách Access Token từ nhiều tài khoản (Chính + Backup)"""
    tokens = []
    credential_keys = [
        ("Account_1", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"),
        ("Account_2", "SPOTIFY_CLIENT_ID_2", "SPOTIFY_CLIENT_SECRET_2")
    ]

    for name, id_key, secret_key in credential_keys:
        client_id = os.getenv(id_key)
        client_secret = os.getenv(secret_key)

        if not client_id or not client_secret:
            continue

        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=30
        )
        response.raise_for_status()
        tokens.append({"name": name, "token": response.json()["access_token"]})

    if not tokens:
        raise RuntimeError("Thiếu credentials. Hãy cấu hình SPOTIFY_CLIENT_ID và SPOTIFY_CLIENT_SECRET trong .env")

    logger.info(f"Đã tải {len(tokens)} Spotify API token(s)")
    return tokens


MAX_RETRIES = 5


def spotify_get(url: str, tokens: list[dict], params: dict | None = None, _retry: int = 0) -> dict:
    """Gọi Spotify API; gặp 429 thì tự động đổi sang token tiếp theo."""
    if _retry > MAX_RETRIES:
        raise RuntimeError(f"Đã thử lại {MAX_RETRIES} lần nhưng vẫn thất bại: {url}")

    last_response = None
    
    for _ in range(len(tokens)):
        token_info = tokens[0]
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token_info['token']}"},
            params=params,
            timeout=30
        )
        
        if response.status_code == 429:
            last_response = response
            # Đưa token bị giới hạn xuống cuối danh sách
            tokens.append(tokens.pop(0))
            logger.warning(
                f"Rate limited cho {token_info['name']}. "
                "Đang tự động chuyển sang tài khoản Spotify khác..."
            )
            continue
            
        response.raise_for_status()
        return response.json()

    # Nếu tất cả các token đều dính 429
    retry_after = parse_retry_after(
        last_response.headers.get("Retry-After") if last_response else None
    )
    logger.warning(
        f"Tất cả tài khoản đều bị Rate Limit. "
        f"Ngủ đông {retry_after} giây trước khi thử lại (lần {_retry + 1}/{MAX_RETRIES})..."
    )
    time.sleep(retry_after)
    return spotify_get(url, tokens, params, _retry + 1)


def fetch_metadata_batch(track_ids: list[str], tokens: list[dict], batch_size=50) -> pd.DataFrame:
    """Gọi API /tracks để lấy dữ liệu metadata theo lô"""
    unique_ids = list(set(track_ids))
    track_data_list = []
    total = len(unique_ids)

    logger.info(f"Bắt đầu cào Metadata cho {total} tracks...")

    for i in range(0, total, batch_size):
        batch_ids = unique_ids[i: i + batch_size]
        batch_ids_str = ",".join(batch_ids)
        
        url = f"{SPOTIFY_API_BASE_URL}/tracks"
        try:
            data = spotify_get(url, tokens, params={"ids": batch_ids_str})
            tracks = data.get("tracks", [])

            for track in tracks:
                if track is None:
                    continue
                album = track.get("album", {})
                ext_ids = track.get("external_ids", {})

                track_data_list.append({
                    "uri": track.get("uri"),
                    "track_id": track.get("id"),
                    "track_name": track.get("name"),
                    "duration_ms": track.get("duration_ms"),
                    "explicit": track.get("explicit"),
                    "isrc": ext_ids.get("isrc"),
                    "album_type": album.get("album_type"),  
                    "album_release_date": album.get("release_date"),
                    "popularity": track.get("popularity")
                })
                
            logger.info(f"-> Đã xử lý Metadata: {min(i + batch_size, total)}/{total}")
            
            # Tự động lưu tạm thời
            with open("temp_metadata.json", "w", encoding="utf-8") as f:
                json.dump(track_data_list, f, ensure_ascii=False, indent=2)
                
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Lỗi khi cào Metadata tại lô {i}: {e}")

    return pd.DataFrame(track_data_list)


def fetch_audio_features_batch(track_ids: list[str], tokens: list[dict], batch_size=50) -> pd.DataFrame:
    """Gọi API /audio-features để lấy thuộc tính âm thanh theo lô"""
    unique_ids = list(set(track_ids))
    features_list = []
    total = len(unique_ids)

    logger.info(f"Bắt đầu cào Audio Features cho {total} tracks...")

    for i in range(0, total, batch_size):
        batch_ids = unique_ids[i: i + batch_size]
        batch_ids_str = ",".join(batch_ids)
        
        url = f"{SPOTIFY_API_BASE_URL}/audio-features"
        try:
            data = spotify_get(url, tokens, params={"ids": batch_ids_str})
            features = data.get("audio_features", [])

            for feat in features:
                if feat is None:
                    continue
                features_list.append({
                    "track_id": feat.get("id"),
                    "danceability": feat.get("danceability"),
                    "energy": feat.get("energy"),
                    "key": feat.get("key"),
                    "loudness": feat.get("loudness"),
                    "mode": feat.get("mode"),
                    "speechiness": feat.get("speechiness"),
                    "acousticness": feat.get("acousticness"),
                    "instrumentalness": feat.get("instrumentalness"),
                    "liveness": feat.get("liveness"),
                    "valence": feat.get("valence"),
                    "tempo": feat.get("tempo")
                })
                
            logger.info(f"-> Đã xử lý Audio Features: {min(i + batch_size, total)}/{total}")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Lỗi khi cào Audio Features tại lô {i}: {e}")

    return pd.DataFrame(features_list)


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "regional-vn-weekly-2026-05-21.csv")

    if not os.path.exists(csv_path):
        logger.error(f"Không tìm thấy file CSV tại: {csv_path}")
    else:
        # Load API Tokens
        tokens = get_access_tokens()

        # Đọc file CSV
        df = pd.read_csv(csv_path)
        
        # Tách lấy track_id từ uri (ví dụ: 'spotify:track:0VjIjW4GlUZAMYd2vXMi3b' -> '0VjIjW4GlUZAMYd2vXMi3b')
        df["track_id"] = df["uri"].apply(lambda x: x.split(":")[-1] if isinstance(x, str) else x)
        track_ids = df["track_id"].dropna().tolist()

        # 1. Chạy lấy Metadata
        metadata_df = fetch_metadata_batch(track_ids, tokens)
        
        # 2. Chạy lấy Audio Features
        if not metadata_df.empty:
            features_df = fetch_audio_features_batch(metadata_df["track_id"].tolist(), tokens)
            
            # 3. Hợp nhất thành 1 DataFrame hoàn chỉnh
            final_df = pd.merge(metadata_df, features_df, on="track_id", how="left")
            
            # Xuất JSON
            out_json = os.path.join(BASE_DIR, "tracks_full_dataset.json")
            final_df.to_json(out_json, orient="records", force_ascii=False, indent=2)
            logger.info(f"Hoàn thành! Đã lưu dataset tại: {out_json}")
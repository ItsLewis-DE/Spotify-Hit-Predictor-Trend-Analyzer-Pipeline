import os
import requests

# Lấy credentials từ biến môi trường (KHÔNG hardcode trong code!)
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Thiếu SPOTIFY_CLIENT_ID hoặc SPOTIFY_CLIENT_SECRET trong biến môi trường!")
    print("   Hãy cấu hình trong file .env")
    exit(1)

# 1. Lấy Access Token
auth_url = 'https://accounts.spotify.com/api/token'
auth_response = requests.post(auth_url, {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})

if auth_response.status_code != 200:
    print("❌ Không thể lấy Access Token!")
    print(auth_response.json())
    exit(1)

access_token = auth_response.json()['access_token']
print("🎉 Lấy Access Token thành công!")

# 2. Tìm kiếm tracks trên Spotify
url = 'https://api.spotify.com/v1/search'

headers = {
    'Authorization': f'Bearer {access_token}'
}

params = {
    'q': 'remaster year:2024-2025',
    'type': 'track',
    'limit': 5,
    'offset': 0
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(response.json())

    absd
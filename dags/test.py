import requests

ACCESS_TOKEN = 'BQB2bEhPKfReypo7tHizISI-Iquc8TJrw2O6ZXZxuNYG1JI9G2jMaDECUJFaG3eTT5IeDDbp5LZA_4nXf9KO3heKszI2hvKEP0sWJNKv5oKJUBU0ZV5COK60PEYqaRDKzbYDG5664Fo' 

url = 'https://api.spotify.com/v1/search'

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

params = {
    'q': 'remaster year:2024-2025',
    'type': 'track',
    'limit': 5,      # Lấy 5 kết quả
    'offset': 0      # Bắt đầu từ vị trí số 0
}

# 4. Gửi yêu cầu GET đến máy chủ Spotify
response = requests.get(url, headers=headers, params=params)

# 5. Kiểm tra và xử lý kết quả trả về
if response.status_code == 200:
    data = response.json()
    print(data)
        
else:
    # In ra thông báo lỗi nếu Token hết hạn hoặc sai cú pháp
    print(f"❌ Có lỗi xảy ra. Mã lỗi: {response.status_code}")
    print(response.json())
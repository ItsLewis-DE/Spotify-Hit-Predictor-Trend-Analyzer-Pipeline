# Spotify Hit Predictor & Trend Analyzer Pipeline

Dự án Data Pipeline phân tích xu hướng âm nhạc và dự đoán bài hit trên Spotify, sử dụng Apache Airflow để orchestrate các workflow.

## 📋 Yêu cầu

- [Docker Desktop](https://docs.docker.com/get-docker/) (bật WSL 2 integration nếu dùng Windows)
- Python 3.11+
- Git

## 🚀 Hướng dẫn cài đặt

### 1. Clone project

```bash
git clone https://github.com/ItsLewis-DE/Spotify-Hit-Predictor-Trend-Analyzer-Pipeline.git
cd Spotify-Hit-Predictor-Trend-Analyzer-Pipeline
```

### 2. Cấu hình môi trường

```bash
# Copy file cấu hình mẫu
cp .env.example .env
```

Mở file `.env` và cập nhật các giá trị:

| Biến | Mô tả | Bắt buộc |
|------|--------|----------|
| `POSTGRES_PASSWORD` | Mật khẩu PostgreSQL | ✅ |
| `AIRFLOW_FERNET_KEY` | Khóa mã hóa Connections | ✅ |
| `AIRFLOW_WEBSERVER_SECRET_KEY` | Khóa ký session | ✅ |
| `SPOTIFY_CLIENT_ID` | Spotify API Client ID | ✅ |
| `SPOTIFY_CLIENT_SECRET` | Spotify API Client Secret | ✅ |
| `_AIRFLOW_WWW_USER_PASSWORD` | Mật khẩu đăng nhập Airflow UI | ✅ |

Tạo các khóa bảo mật:

```bash
# Fernet Key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Webserver Secret Key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Khởi động Airflow

```bash
# Khởi tạo database & tạo admin user (chỉ chạy lần đầu)
docker compose up airflow-init

# Chạy tất cả services
docker compose up -d
```

### 4. Truy cập Airflow UI

Mở trình duyệt tại: **http://localhost:8080**

- **Username:** giá trị `_AIRFLOW_WWW_USER_USERNAME` trong `.env` (mặc định: `airflow`)
- **Password:** giá trị `_AIRFLOW_WWW_USER_PASSWORD` trong `.env` (mặc định: `airflow`)

## 📁 Cấu trúc dự án

```
├── dags/               # DAG definitions (Airflow workflows)
├── plugins/            # Custom Airflow plugins
├── config/             # Airflow configuration files
├── data/               # Data files (gitignored)
├── logs/               # Airflow logs (gitignored)
├── docker-compose.yaml # Docker Compose cho Airflow
├── requirements.txt    # Python dependencies
├── .env.example        # Template biến môi trường
├── .env                # Biến môi trường thực (gitignored)
└── .gitignore          # Git ignore rules
```

## 🔧 Các lệnh thường dùng

```bash
# Khởi động
docker compose up -d

# Dừng
docker compose down

# Xem logs
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler

# Restart một service
docker compose restart airflow-webserver

# Chạy Airflow CLI
docker compose run --rm airflow-cli airflow dags list
```

## 👥 Hướng dẫn đóng góp

Xem chi tiết tại [CONTRIBUTING.md](CONTRIBUTING.md).

**Quy tắc quan trọng:**
- **KHÔNG BAO GIỜ** commit secrets (API keys, tokens, passwords) vào code
- Sử dụng biến môi trường qua file `.env` cho tất cả thông tin nhạy cảm
- Tạo branch mới cho mỗi tính năng: `git checkout -b feature/ten-tinh-nang`
- Viết commit message rõ ràng bằng tiếng Anh

## 📄 License

MIT

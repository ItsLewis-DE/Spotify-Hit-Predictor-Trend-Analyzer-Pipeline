# 🎵 Spotify Hit Predictor & Trend Analyzer Pipeline

Dự án Data Pipeline tự động thu thập, lưu trữ và phân tích xu hướng âm nhạc (Regional VN Weekly) để dự đoán bài hit trên Spotify. Hệ thống áp dụng kiến trúc **ELT (Extract, Load, Transform)** hiện đại và được quản lý tự động bằng **Apache Airflow**.

---

## 🏗️ Kiến trúc luồng dữ liệu (Data Architecture)

Dự án này tuân theo luồng dữ liệu chuẩn cho một Data Lake/Data Warehouse:

1. **Extract (Thu thập dữ liệu):**
   - Tự động tải Spotify Charts (Regional VN Weekly) bằng **Selenium** (`crawl_top_track.py`).
   - Kết nối với **Spotify Web API** để lấy thông số âm thanh (Audio Features) và dữ liệu Nghệ sĩ (Artist) (`crawl_audio_feature.py`, `crawl_artist.py`).
2. **Load (Tải lên hệ thống lưu trữ):**
   - Dữ liệu thô (Raw Data) dưới dạng CSV/JSON được đẩy lên **Amazon S3** (vai trò Data Lake).
   - Từ S3, dữ liệu được tự động load (COPY INTO) vào **Snowflake** (Data Warehouse).
3. **Transform (Biến đổi & Phân tích):**
   - Làm sạch, nối bảng và tạo các data mart bằng SQL/dbt bên trong Snowflake để phục vụ phân tích xu hướng hoặc Machine Learning.
4. **Orchestration:** **Apache Airflow** chịu trách nhiệm lập lịch và điều phối toàn bộ các tiến trình trên.

---

## 📁 Cấu trúc dự án

```text
├── dags/
│   ├── DAG/                  # Các định nghĩa Airflow DAGs
│   └── scripts/              # Chứa các Python script chạy thực tế
│       ├── extract/          # Code cào dữ liệu (Selenium, Spotify API)
│       ├── load/             # Code đẩy dữ liệu (S3, Snowflake)
│       └── transform/        # Code xử lý dữ liệu (SQL, dbt)
├── data/                     # Thư mục lưu tạm dữ liệu thô (đã gitignore)
├── chrome_profile/           # Profile Chrome để lưu session đăng nhập Spotify
├── config/                   # Các file cấu hình Airflow
├── logs/                     # File log của Airflow (đã gitignore)
├── plugins/                  # Custom plugins cho Airflow
├── docker-compose.yaml       # Cấu hình hạ tầng Airflow & Postgres
├── pyproject.toml            # Quản lý dependencies (pandas, selenium, boto3...)
├── .env.example              # Template cho biến môi trường
└── README.md                 # Tài liệu hướng dẫn (File này)
```

---

## 📋 Yêu cầu hệ thống (Prerequisites)

- [Docker Desktop](https://docs.docker.com/get-docker/) (Bật WSL 2 integration nếu dùng Windows).
- Python 3.12+ (uv hoặc pip để quản lý package cục bộ).
- Tài khoản Spotify (để đăng nhập Spotify Charts).
- [Spotify Developer App](https://developer.spotify.com/dashboard) (Cấp Client ID & Secret).
- Trình duyệt Google Chrome được cài sẵn trên máy (nếu chạy local debug).

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Clone dự án

```bash
git clone https://github.com/ItsLewis-DE/Spotify-Hit-Predictor-Trend-Analyzer-Pipeline.git
cd Spotify-Hit-Predictor-Trend-Analyzer-Pipeline
```

### 2. Cấu hình biến môi trường

```bash
# Copy file cấu hình mẫu
cp .env.example .env
```

Mở file `.env` và cập nhật các thông tin sau:
- **Spotify API:** `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`.
- **Bảo mật Airflow:** Tạo chuỗi ngẫu nhiên cho `AIRFLOW_FERNET_KEY` và `AIRFLOW_WEBSERVER_SECRET_KEY`.
- **Tài khoản Airflow UI:** Cài đặt mật khẩu cho biến `_AIRFLOW_WWW_USER_PASSWORD`.

### 3. Đăng nhập Spotify Charts (Chạy lần đầu)

Vì script cần tải dữ liệu từ Spotify Charts (yêu cầu đăng nhập), bạn cần chạy script này một lần thủ công ở chế độ có giao diện (không headless) để lưu Cookies:

```bash
# Tạo môi trường ảo và cài thư viện
python -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate
pip install -r pyproject.toml

# Mở Chrome, thực hiện đăng nhập bằng tay. Script sẽ tự động lưu session vào `spotify_cookies.json`.
python dags/scripts/extract/crawl_top_track.py --login
```

### 4. Khởi động hệ thống Airflow

```bash
# Khởi tạo database và tạo user admin (CHỈ CHẠY 1 LẦN ĐẦU)
docker compose up airflow-init

# Chạy tất cả các dịch vụ (Webserver, Scheduler, Postgres)
docker compose up -d
```

### 5. Truy cập Airflow UI

Mở trình duyệt truy cập: **http://localhost:8080**
- **Username:** `airflow` (hoặc giá trị trong `.env`)
- **Password:** Mật khẩu bạn đã set trong `.env`

Từ đây bạn có thể bật (unpause) các DAG để hệ thống bắt đầu chạy pipeline tự động.

---

## 🔧 Các lệnh Docker thường dùng

```bash
# Dừng và xóa containers
docker compose down

# Xem logs của scheduler (nếu DAG bị lỗi)
docker compose logs -f airflow-scheduler

# Truy cập bash của Airflow CLI container để test task
docker compose run --rm airflow-cli bash
```

---

## 👥 Đóng góp & Phát triển

Xem thêm chi tiết tại [CONTRIBUTING.md](CONTRIBUTING.md).
1. **KHÔNG BAO GIỜ** commit các thông tin nhạy cảm (API Keys, AWS Credentials).
2. Code tuân theo chuẩn PEP-8 (khuyến khích dùng `black`, `flake8`).
3. Tạo nhánh riêng `feature/ten-tinh-nang` cho mỗi luồng công việc mới.

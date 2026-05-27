# AGENTS.md

Tài liệu này cung cấp ngữ cảnh cho ChatGPT/Codex hoặc người mới bắt đầu làm việc với repository này. Khi yêu cầu AI hỗ trợ code, hãy gửi kèm file này để AI hiểu đúng cấu trúc project, stack công nghệ, các lệnh cần dùng và những giới hạn hiện tại.

## 1. Tổng quan dự án

Tên dự án: `Spotify-Hit-Predictor-Trend-Analyzer-Pipeline`

Mục tiêu: xây dựng data pipeline để thu thập dữ liệu từ Spotify, phân tích xu hướng âm nhạc và chuẩn bị nền tảng cho bài toán dự đoán bài hát có khả năng trở thành hit.

Trạng thái hiện tại:

- Project đang ở giai đoạn khởi tạo nền tảng.
- Có Docker Compose stack để chạy Apache Airflow 2.10.5 với PostgreSQL metadata database.
- Có script `dags/test.py` để kiểm tra Spotify Web API bằng Client Credentials flow.
- `dags/test.py` hiện chưa phải Airflow DAG hoàn chỉnh.
- Chưa có test suite tự động.
- Chưa có CI/CD.
- Chưa có module riêng cho extract/transform/load hoặc machine learning.

Stack chính:

- Python 3.11
- Apache Airflow 2.10.5
- PostgreSQL 16
- Docker Compose
- Spotify Web API
- `requests`
- `pandas`

## 2. Cấu trúc thư mục hiện tại

```text
.
├── dags/
│   └── test.py              # Script kiểm tra Spotify API, chưa phải DAG hoàn chỉnh
├── .editorconfig            # Quy tắc format cơ bản cho editor
├── .env.example             # Template biến môi trường, được commit
├── .gitignore               # Danh sách file/thư mục không commit
├── AGENTS.md                # Ngữ cảnh project cho AI/người mới
├── CONTRIBUTING.md          # Hướng dẫn đóng góp
├── README.md                # Tài liệu setup và mô tả dự án
├── docker-compose.yaml      # Stack local: Airflow + PostgreSQL
└── requirements.txt         # Dependency Python cho script/project
```

Các thư mục runtime có thể được tạo khi chạy project:

```text
config/                      # Mount vào /opt/airflow/config trong container
data/                        # Dữ liệu local, không commit
logs/                        # Airflow logs, không commit
plugins/                     # Custom Airflow plugins nếu cần
```

Các thư mục/file không nên commit:

- `.env`
- `.venv/`
- `venv/`
- `logs/`
- `data/`
- `__pycache__/`
- secret files như `*.pem`, `*.key`

## 3. File quan trọng cần biết

### `docker-compose.yaml`

Định nghĩa local stack gồm:

- `postgres`: PostgreSQL metadata database cho Airflow.
- `airflow-webserver`: Airflow UI.
- `airflow-scheduler`: Scheduler quét và chạy DAG.
- `airflow-triggerer`: Triggerer cho deferrable operators.
- `airflow-init`: Chạy migration database và tạo admin user ban đầu.
- `airflow-cli`: Utility container để chạy lệnh Airflow CLI.

Port mặc định:

- Airflow UI: `http://localhost:8080`
- PostgreSQL trên máy host: `localhost:5433`
- PostgreSQL trong Docker network: `postgres:5432`

### `.env.example`

Template biến môi trường. Khi setup local, copy thành `.env`:

```bash
cp .env.example .env
```

Sau đó cập nhật các biến trong `.env`. Không commit `.env`.

### `dags/test.py`

Script kiểm tra Spotify API:

- Đọc `SPOTIFY_CLIENT_ID` và `SPOTIFY_CLIENT_SECRET` từ biến môi trường.
- Gọi endpoint `https://accounts.spotify.com/api/token` để lấy access token.
- Gọi Spotify Search API để tìm track mẫu.

Lưu ý quan trọng:

- File này hiện chạy như Python script bình thường.
- File này chưa định nghĩa `DAG`, `task`, `schedule`, `start_date` theo chuẩn Airflow.
- Không nên hardcode API key, token hoặc password vào file này.

### `requirements.txt`

Dependency hiện có:

```text
requests>=2.31.0
pandas>=2.1.0
```

Airflow không được cài trực tiếp từ `requirements.txt` vì project đang dùng Docker image `apache/airflow:2.10.5-python3.11`.

## 4. Setup lần đầu cho người mới

Chạy các lệnh bên dưới từ thư mục project:

```bash
cd /Users/thanhdanh/Documents/mini_project/Spotify-Hit-Predictor-Trend-Analyzer-Pipeline
```

Kiểm tra đang đứng đúng thư mục:

```bash
pwd
ls
```

Kết quả `ls` nên thấy các file như:

```text
README.md
CONTRIBUTING.md
docker-compose.yaml
requirements.txt
dags
```

## 5. Chuẩn bị file môi trường

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

Mở `.env` bằng editor và điền giá trị thật:

```bash
code .env
```

Nếu không dùng VS Code, có thể mở bằng editor khác. Các biến cần chú ý:

```text
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
AIRFLOW_FERNET_KEY=
AIRFLOW_WEBSERVER_SECRET_KEY=
AIRFLOW_UID=50000
AIRFLOW_WEBSERVER_PORT=8080
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

Tạo `AIRFLOW_FERNET_KEY`:

```bash
python3 -m pip install cryptography
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy kết quả vào:

```text
AIRFLOW_FERNET_KEY=<ket_qua_vua_tao>
```

Tạo `AIRFLOW_WEBSERVER_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy kết quả vào:

```text
AIRFLOW_WEBSERVER_SECRET_KEY=<ket_qua_vua_tao>
```

Lấy Spotify credentials:

1. Vào Spotify Developer Dashboard.
2. Tạo app mới.
3. Copy `Client ID` vào `SPOTIFY_CLIENT_ID`.
4. Copy `Client Secret` vào `SPOTIFY_CLIENT_SECRET`.

Không gửi `.env` cho người khác và không paste nội dung `.env` vào ChatGPT nếu trong đó có secret thật.

## 6. Tạo thư mục runtime

Docker Compose mount các thư mục này vào container Airflow:

```bash
mkdir -p logs data plugins config
```

Ý nghĩa:

- `logs/`: chứa log chạy DAG/task của Airflow.
- `data/`: nơi có thể lưu dữ liệu local tạm thời.
- `plugins/`: nơi đặt custom Airflow plugin nếu sau này cần.
- `config/`: nơi mount config bổ sung cho Airflow.

## 7. Chạy Airflow bằng Docker Compose

Kiểm tra Docker hoạt động:

```bash
docker --version
docker compose version
docker compose config
```

Khởi tạo Airflow database và admin user lần đầu:

```bash
docker compose up airflow-init
```

Nếu lệnh này thành công, khởi động toàn bộ service:

```bash
docker compose up -d
```

Kiểm tra trạng thái container:

```bash
docker compose ps
```

Xem log webserver:

```bash
docker compose logs -f airflow-webserver
```

Xem log scheduler:

```bash
docker compose logs -f airflow-scheduler
```

Mở Airflow UI:

```text
http://localhost:8080
```

Đăng nhập bằng thông tin trong `.env`:

```text
_AIRFLOW_WWW_USER_USERNAME
_AIRFLOW_WWW_USER_PASSWORD
```

Nếu đã đổi `AIRFLOW_WEBSERVER_PORT`, thay `8080` bằng port mới.

## 8. Dừng, restart và xóa môi trường Docker

Dừng container nhưng giữ database volume:

```bash
docker compose down
```

Khởi động lại:

```bash
docker compose up -d
```

Restart riêng webserver:

```bash
docker compose restart airflow-webserver
```

Restart riêng scheduler:

```bash
docker compose restart airflow-scheduler
```

Xóa container và xóa cả database volume:

```bash
docker compose down -v
```

Cẩn thận với `docker compose down -v`: lệnh này xóa volume PostgreSQL, làm mất Airflow metadata database local, user, connection, variable và lịch sử chạy task.

## 9. Chạy Airflow CLI

Liệt kê DAG:

```bash
docker compose run --rm airflow-cli airflow dags list
```

Kiểm tra DAG import có lỗi không:

```bash
docker compose run --rm airflow-cli airflow dags list-import-errors
```

Xem task trong một DAG:

```bash
docker compose run --rm airflow-cli airflow tasks list <dag_id>
```

Trigger một DAG thủ công:

```bash
docker compose run --rm airflow-cli airflow dags trigger <dag_id>
```

Xem thông tin Airflow:

```bash
docker compose run --rm airflow-cli airflow info
```

## 10. Chạy script Spotify API trên máy local

Tạo virtual environment:

```bash
python3 -m venv .venv
```

Kích hoạt virtual environment trên macOS/Linux:

```bash
source .venv/bin/activate
```

Cập nhật `pip`:

```bash
python3 -m pip install --upgrade pip
```

Cài dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Nạp biến môi trường từ `.env` vào terminal hiện tại:

```bash
set -a
source .env
set +a
```

Chạy script kiểm tra Spotify API:

```bash
python3 dags/test.py
```

Nếu thành công, script sẽ in thông báo lấy access token thành công và JSON response từ Spotify Search API.

Nếu báo thiếu credential, kiểm tra lại:

```bash
echo "$SPOTIFY_CLIENT_ID"
echo "$SPOTIFY_CLIENT_SECRET"
```

Không paste giá trị thật của hai biến này vào chat hoặc commit lên Git.

Thoát virtual environment:

```bash
deactivate
```

## 11. Quy tắc khi phát triển DAG

Khi thêm DAG mới:

- Đặt file trong thư mục `dags/`.
- Dùng tên file dạng `snake_case.py`, ví dụ `spotify_extract_tracks.py`.
- Dùng `dag_id` trùng hoặc gần giống tên file, ví dụ `spotify_extract_tracks`.
- Thêm docstring ở đầu file để mô tả DAG.
- Không hardcode secrets trong DAG.
- Không gọi API hoặc chạy logic nặng ngay ở top-level khi file được import.
- Tách logic lấy dữ liệu, transform và lưu dữ liệu thành hàm rõ ràng.
- Airflow scheduler thường cần 30-60 giây để phát hiện DAG mới.

Ví dụ cấu trúc tối thiểu cho DAG sau này:

```python
from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="spotify_extract_tracks",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["spotify"],
)
def spotify_extract_tracks():
    @task
    def extract():
        return {"status": "ok"}

    extract()


spotify_extract_tracks()
```

Sau khi thêm DAG, kiểm tra import:

```bash
docker compose run --rm airflow-cli airflow dags list-import-errors
```

Nếu không có lỗi, kiểm tra DAG có xuất hiện không:

```bash
docker compose run --rm airflow-cli airflow dags list
```

## 12. Quy tắc bảo mật

Không bao giờ commit:

- `.env`
- Spotify Client Secret
- API tokens
- Passwords
- Private keys
- Database dumps có dữ liệu nhạy cảm

Trước khi commit, luôn kiểm tra diff:

```bash
git status
git diff
git diff --staged
```

Nếu lỡ commit secret:

1. Reset/revoke secret ngay trên service provider.
2. Tạo secret mới.
3. Thông báo cho người phụ trách project.
4. Không chỉ xóa secret khỏi commit mới, vì secret cũ vẫn có thể nằm trong Git history.

## 13. Git workflow

Cập nhật branch `main`:

```bash
git checkout main
git pull origin main
```

Tạo branch tính năng:

```bash
git checkout -b feature/ten-tinh-nang
```

Tạo branch sửa lỗi:

```bash
git checkout -b fix/mo-ta-loi
```

Kiểm tra file thay đổi:

```bash
git status
git diff
```

Stage file:

```bash
git add <duong_dan_file>
```

Hoặc stage toàn bộ thay đổi:

```bash
git add .
```

Kiểm tra staged diff:

```bash
git diff --staged
```

Commit theo Conventional Commits:

```bash
git commit -m "feat: add spotify extract dag"
```

Push branch:

```bash
git push -u origin feature/ten-tinh-nang
```

Các prefix commit nên dùng:

- `feat:` thêm tính năng mới.
- `fix:` sửa lỗi.
- `docs:` cập nhật tài liệu.
- `refactor:` tái cấu trúc code không đổi hành vi.
- `test:` thêm hoặc sửa test.
- `chore:` cập nhật config, dependency hoặc việc bảo trì.

## 14. Format và style

Theo `.editorconfig`:

- Charset: UTF-8.
- Line ending: LF.
- Indent bằng space.
- Python và hầu hết file dùng 4 spaces.
- YAML dùng 2 spaces.
- Luôn có newline ở cuối file.
- Trim trailing whitespace, trừ Markdown.

Style Python nên theo hướng:

- Tên hàm và biến: `snake_case`.
- Tên hằng số: `UPPER_SNAKE_CASE`.
- Tách hàm nhỏ, dễ test.
- Không để side effect nguy hiểm ở top-level module.
- Ưu tiên type hints khi thêm logic mới.
- Log lỗi rõ ràng, không in secret.

## 15. Kiểm tra và debug thường dùng

Kiểm tra Docker Compose config:

```bash
docker compose config
```

Xem toàn bộ log:

```bash
docker compose logs -f
```

Xem log PostgreSQL:

```bash
docker compose logs -f postgres
```

Xem container đang chạy:

```bash
docker compose ps
```

Chạy Python compile check cho file DAG/script:

```bash
python3 -m py_compile dags/test.py
```

Kiểm tra dependency local đã cài:

```bash
python3 -m pip list
```

Kiểm tra biến môi trường Spotify đã được nạp chưa:

```bash
printenv SPOTIFY_CLIENT_ID
printenv SPOTIFY_CLIENT_SECRET
```

Không chia sẻ output của các lệnh này nếu chúng in ra secret thật.

## 16. Troubleshooting cho người mới

### Lỗi `Cannot connect to the Docker daemon`

Docker chưa chạy. Mở Docker Desktop rồi chạy lại:

```bash
docker compose ps
```

### Airflow UI không mở ở `localhost:8080`

Kiểm tra container:

```bash
docker compose ps
```

Xem log webserver:

```bash
docker compose logs -f airflow-webserver
```

Nếu port `8080` bị trùng, đổi trong `.env`:

```text
AIRFLOW_WEBSERVER_PORT=8081
```

Sau đó restart:

```bash
docker compose down
docker compose up -d
```

Truy cập:

```text
http://localhost:8081
```

### PostgreSQL port `5433` bị trùng

Trong `docker-compose.yaml`, service `postgres` đang map:

```yaml
ports:
  - "5433:5432"
```

Nếu `5433` bị trùng, đổi host port thành port khác, ví dụ:

```yaml
ports:
  - "5434:5432"
```

Sau đó chạy lại:

```bash
docker compose down
docker compose up -d
```

### DAG không xuất hiện trong Airflow UI

Kiểm tra import errors:

```bash
docker compose run --rm airflow-cli airflow dags list-import-errors
```

Kiểm tra scheduler log:

```bash
docker compose logs -f airflow-scheduler
```

Đảm bảo file DAG nằm trong:

```text
dags/
```

Đợi 30-60 giây vì scheduler không quét liên tục từng giây.

### Script Spotify báo thiếu credential

Nạp lại `.env`:

```bash
set -a
source .env
set +a
```

Kiểm tra biến đã có trong terminal:

```bash
printenv SPOTIFY_CLIENT_ID
printenv SPOTIFY_CLIENT_SECRET
```

Sau đó chạy lại:

```bash
python3 dags/test.py
```

### Spotify trả lỗi authentication

Kiểm tra:

- `SPOTIFY_CLIENT_ID` đúng chưa.
- `SPOTIFY_CLIENT_SECRET` đúng chưa.
- App trong Spotify Developer Dashboard còn hoạt động không.
- Không có dấu cách thừa khi copy secret vào `.env`.

## 17. Hướng phát triển tiếp theo

Các bước hợp lý để phát triển project:

1. Chuyển `dags/test.py` thành Airflow DAG thật.
2. Tách Spotify API client thành module riêng, ví dụ `src/spotify_client.py`.
3. Thêm bước extract track/audio data từ Spotify.
4. Lưu raw data vào `data/raw/`.
5. Thêm transform bằng `pandas`, lưu vào `data/processed/`.
6. Thêm feature engineering cho hit prediction.
7. Thêm model training/evaluation.
8. Thêm test cho Spotify client và transform logic.
9. Thêm dashboard hoặc báo cáo trend.
10. Cân nhắc thêm CI để chạy lint/test.

## 18. Hướng dẫn cho ChatGPT/Codex khi sửa project

Khi AI làm việc trong repository này, hãy tuân thủ:

- Đọc `README.md`, `CONTRIBUTING.md`, `docker-compose.yaml`, `requirements.txt` và file liên quan trước khi sửa.
- Không đọc hoặc in nội dung `.env` trừ khi người dùng yêu cầu rõ và hiểu rủi ro.
- Không commit secrets.
- Không xóa `logs/`, `data/`, Docker volumes hoặc database nếu người dùng chưa yêu cầu.
- Không chạy `docker compose down -v` nếu chưa được người dùng đồng ý.
- Ưu tiên thay đổi nhỏ, đúng phạm vi yêu cầu.
- Nếu thêm dependency Python, cập nhật `requirements.txt`.
- Nếu thêm DAG, kiểm tra bằng `airflow dags list-import-errors`.
- Nếu sửa Docker Compose, chạy `docker compose config` để validate YAML.
- Nếu sửa Python script, chạy ít nhất `python3 -m py_compile <file>`.
- Nếu thêm hướng dẫn setup, cập nhật cả `README.md` hoặc tài liệu liên quan.

## 19. Lệnh nhanh theo tình huống

Setup lần đầu:

```bash
cd /Users/thanhdanh/Documents/mini_project/Spotify-Hit-Predictor-Trend-Analyzer-Pipeline
cp .env.example .env
mkdir -p logs data plugins config
docker compose up airflow-init
docker compose up -d
```

Mở Airflow:

```text
http://localhost:8080
```

Xem container:

```bash
docker compose ps
```

Xem log:

```bash
docker compose logs -f
```

Dừng project:

```bash
docker compose down
```

Chạy script Spotify local:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
set -a
source .env
set +a
python3 dags/test.py
```

Kiểm tra lỗi DAG:

```bash
docker compose run --rm airflow-cli airflow dags list-import-errors
```

Kiểm tra Git trước khi commit:

```bash
git status
git diff
git diff --staged
```

## 20. Ghi chú về giới hạn hiện tại

- Project chưa có package structure như `src/`.
- Project chưa có test framework như `pytest`.
- Project chưa có lint/formatter như `ruff`, `black` hoặc `isort`.
- Airflow container hiện chưa truyền `SPOTIFY_CLIENT_ID` và `SPOTIFY_CLIENT_SECRET` vào environment của các service Airflow trong `docker-compose.yaml`. Script `dags/test.py` chạy local tốt nếu terminal đã nạp `.env`; nếu muốn chạy trong Airflow container/DAG thật, cần cấu hình credentials qua Airflow Connections/Variables hoặc thêm biến môi trường phù hợp vào Compose.
- PostgreSQL hiện chỉ là metadata database cho Airflow, chưa phải data warehouse cho dữ liệu Spotify.


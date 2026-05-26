## 🔀 Quy trình làm việc (Git Workflow)

Dự án sử dụng **Git Flow** đơn giản:

```
main          ← code ổn định, luôn chạy được
  └── feature/xxx   ← nhánh phát triển tính năng mới
  └── fix/xxx       ← nhánh sửa lỗi
```

### Bước 1: Tạo branch mới

```bash
# Cập nhật code mới nhất
git checkout main
git pull origin main

# Tạo nhánh mới cho tính năng
git checkout -b feature/ten-tinh-nang

# Hoặc tạo nhánh sửa lỗi
git checkout -b fix/mo-ta-loi
```

### Bước 2: Code và commit

```bash
# Thêm file đã thay đổi
git add .

# Commit với message rõ ràng (tiếng Anh)
git commit -m "feat: add spotify data extraction DAG"
```

### Bước 3: Push và tạo Pull Request

```bash
git push -u origin feature/ten-tinh-nang
```

Sau đó vào GitHub tạo Pull Request từ nhánh của bạn vào `main`.

## 📝 Quy ước commit message

Sử dụng [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Sử dụng khi |
|--------|-------------|
| `feat:` | Thêm tính năng mới |
| `fix:` | Sửa lỗi |
| `docs:` | Cập nhật tài liệu |
| `refactor:` | Tái cấu trúc code (không thay đổi chức năng) |
| `test:` | Thêm hoặc sửa test |
| `chore:` | Cập nhật config, dependencies |

**Ví dụ:**
```
feat: add DAG to extract Spotify top tracks
fix: resolve token expiration issue in API calls
docs: update README with setup instructions
chore: add pandas to requirements.txt
```

## 🔒 Quy tắc bảo mật

> **QUAN TRỌNG:** Vi phạm các quy tắc này có thể gây lộ thông tin nhạy cảm!

1. **KHÔNG BAO GIỜ** hardcode secrets (API keys, tokens, passwords) trong code
2. Luôn sử dụng biến môi trường qua file `.env` hoặc Airflow Connections/Variables
3. Kiểm tra kỹ trước khi commit: `git diff --staged` để đảm bảo không có secrets
4. Nếu lỡ commit secrets, hãy:
   - Reset secret đó ngay lập tức trên service provider
   - Thông báo cho team

## 📁 Quy ước đặt tên

### DAGs
- Tên file: `snake_case.py` (ví dụ: `spotify_extract_tracks.py`)
- DAG ID: trùng với tên file (không có `.py`)
- Thêm docstring mô tả DAG ở đầu file

### Branches
- Feature: `feature/mo-ta-ngan-gon`
- Fix: `fix/mo-ta-loi`

## ⚙️ Thiết lập môi trường phát triển

1. Clone repo và cài đặt theo hướng dẫn trong [README.md](README.md)
2. Tạo file `.env` từ `.env.example` - **không bao giờ commit file `.env`**
3. Chạy `docker compose up -d` để khởi động Airflow
4. Đặt DAG mới vào thư mục `dags/`
5. Airflow sẽ tự động nhận DAG mới sau 30-60 giây

## ❓ Cần hỗ trợ?

Tạo Issue trên GitHub hoặc liên hệ trực tiếp với team lead.

import os
import logging
import argparse
import snowflake.connector
from dotenv import load_dotenv
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:

    # Dinh nghia tham so CLI cho input track_info va output artist.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        default=None
    )
    return parser.parse_known_args()[0]

def setup_snowflake(date:None):
    # Tải biến môi trường từ file .env
    load_dotenv()

    SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
    SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
    SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

    if not all([SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD]):
        logger.error("Lỗi: Thiếu thông tin đăng nhập Snowflake trong file .env")
        sys.exit(1)
        return
    if date is None:
        logger.error("Loi. Ban chua truyen ngay thang vao!")
        sys.exit(1)
    # Kết nối với Snowflake bằng role ACCOUNTADMIN để tạo DB, Role và cấp quyền
    logger.info("Đang kết nối vào Snowflake với role ACCOUNTADMIN...")
    try:
        conn_admin = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            role='ACCOUNTADMIN'
        )
        cursor_admin = conn_admin.cursor()

        # Mình đã sửa dbt_roleC thành dbt_role cho đúng cú pháp
        admin_queries = [
            "CREATE DATABASE IF NOT EXISTS SPOTIFY_DB",
            "CREATE ROLE IF NOT EXISTS dbt_role",
            "GRANT USAGE ON WAREHOUSE compute_wh TO ROLE dbt_role",
            "GRANT ALL ON DATABASE spotify_db TO ROLE dbt_role",
            f"GRANT ROLE dbt_role TO USER {SNOWFLAKE_USER}"
        ]

        for query in admin_queries:
            cursor_admin.execute(query)

    except Exception as e:
        logger.error("Lỗi khi chạy lệnh ACCOUNTADMIN: %s", e)
        sys.exit(1)
    finally:
        if 'cursor_admin' in locals():
            cursor_admin.close()
        if 'conn_admin' in locals():
            conn_admin.close()

    # Kết nối với Snowflake bằng role dbt_role để tạo Schema, File Format và Stage
    logger.info("Đang kết nối vào Snowflake với role dbt_role...")
    try:
        conn_dbt = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            role='dbt_role',
            database='SPOTIFY_DB',
            warehouse='COMPUTE_WH'
        )
        cursor_dbt = conn_dbt.cursor()

        dbt_queries = [
            "CREATE SCHEMA IF NOT EXISTS spotify_db.spotify_schema",
            "USE SCHEMA spotify_db.spotify_schema",
            """
            CREATE OR REPLACE FILE FORMAT spotify_csv_format
            TYPE='CSV'
            SKIP_HEADER=1
            FIELD_OPTIONALLY_ENCLOSED_BY='"'
            """,
            """
            CREATE OR REPLACE FILE FORMAT spotify_json_format
            TYPE = 'JSON'
            STRIP_OUTER_ARRAY = FALSE
            """,
            f"""
            CREATE OR REPLACE STAGE s3
            URL = 's3://spotify-stream-bucket/'
            CREDENTIALS = (aws_key_id='{AWS_ACCESS_KEY_ID}' aws_secret_key='{AWS_SECRET_ACCESS_KEY}')
            """
        ]

        for query in dbt_queries:
            cursor_dbt.execute(query)

        # Tạo các bảng (Raw Tables)
        logger.info("Đang tạo các bảng Raw...")
        table_queries = [
            "CREATE TABLE IF NOT EXISTS spotify_schema.raw_artist (raw_data VARIANT)",
            "CREATE TABLE IF NOT EXISTS spotify_schema.raw_audio_feature (raw_data VARIANT)",
            "CREATE TABLE IF NOT EXISTS spotify_schema.raw_track_info (raw_data VARIANT)",
            """
            CREATE TABLE IF NOT EXISTS spotify_schema.raw_top_track (
                rank INT,
                uri VARCHAR,
                artist_names VARCHAR,
                track_name VARCHAR,
                source VARCHAR,
                peak_rank INT,
                previous_rank INT,
                weeks_on_chart INT,
                streams INT,
                fetched_date DATE
            )
            """
        ]
        for query in table_queries:
            cursor_dbt.execute(query)

        # Chạy lệnh COPY INTO để load dữ liệu từ Stage s3 vào bảng
        logger.info("Đang chạy lệnh COPY INTO load dữ liệu từ S3...")
        # Ở đây dùng 2026-02-05 theo dữ liệu mẫu, bạn có thể truyền tham số linh hoạt
        
        copy_queries = [
            f"COPY INTO spotify_schema.raw_artist FROM @s3/{date}/artist/ FILE_FORMAT=spotify_json_format PATTERN='.*.json' ON_ERROR='CONTINUE'",
            f"COPY INTO spotify_schema.raw_audio_feature FROM @s3/{date}/audio_feature/ FILE_FORMAT=spotify_json_format PATTERN='.*.json' ON_ERROR='CONTINUE'",
            f"COPY INTO spotify_schema.raw_track_info FROM @s3/{date}/track_info/ FILE_FORMAT=spotify_json_format PATTERN='.*.json' ON_ERROR='CONTINUE'",
            f"""COPY INTO spotify_schema.raw_top_track (rank, uri, artist_names, track_name, source, peak_rank, previous_rank, weeks_on_chart, streams, fetched_date)
            FROM (
                SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    TO_DATE(SPLIT_PART(METADATA$FILENAME, '/', 1), 'YYYY-MM-DD')
                FROM @s3/{date}/top_track/
            )
            FILE_FORMAT=spotify_csv_format PATTERN='.*.csv' ON_ERROR='CONTINUE'"""
        ]

        for query in copy_queries:
            logger.info("Thực thi: %s", query)
            try:
                cursor_dbt.execute(query)
            except Exception as e:
                logger.error("Lỗi khi load: %s", e)
                sys.exit(1)

        logger.info("Hoàn tất cài đặt Snowflake và load dữ liệu thành công!")

    except Exception as e:
        logger.error("Lỗi khi chạy lệnh dbt_role: %s", e)
        sys.exit(1)
    finally:
        if 'cursor_dbt' in locals():
            cursor_dbt.close()
        if 'conn_dbt' in locals():
            conn_dbt.close()

if __name__ == "__main__":
    args = parse_args()
    date = args.date
    setup_snowflake(date)

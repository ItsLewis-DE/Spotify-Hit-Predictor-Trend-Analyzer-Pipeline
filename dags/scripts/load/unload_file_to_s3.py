import os
import logging
import argparse
import snowflake.connector
from dotenv import load_dotenv
import sys
from datetime import datetime, timedelta
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

    dt = datetime.strptime(date, "%Y-%m-%d")
    offset = (dt.weekday() + 4) % 7
    date = (dt - timedelta(days=offset)).strftime("%Y-%m-%d")
    logger.info("Converted to nearest Thursday: %s", date)

    logger.info("Connecting to Snowflake with role dbt_role...")
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            role='dbt_role',
            database='SPOTIFY_DB',
            warehouse='COMPUTE_WH',
            schema='SPOTIFY_SCHEMA'
        )
        cursor = conn.cursor()

        tables = [
            'fact_top_track',
            'dim_artist',
            'dim_audio_feature',
            'dim_track_info'
        ]

        for table in tables:
            query = f"""
                COPY INTO @s3/{date}/ml_features/{table}.parquet
                FROM spotify_db.spotify_schema.{table}
                FILE_FORMAT = (TYPE = PARQUET COMPRESSION = SNAPPY)
                HEADER = TRUE
                OVERWRITE = TRUE
                SINGLE = TRUE;
            """
            logger.info("Unloading %s...", table)
            cursor.execute(query)

        logger.info("All tables unloaded successfully!")

    except Exception as e:
        logger.error("Unload failed: %s", e)
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    args = parse_args()
    setup_snowflake(args.date)

"""Extract Spotify artist metadata for artists in the newest Vietnam weekly chart."""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from scripts.extract_artists import extract_artists_from_latest_chart


with DAG(
    dag_id="spotify_extract_artists",
    description="Read the latest regional-vn-weekly CSV and fetch Spotify artist metadata.",
    start_date=datetime(2026, 5, 21),
    schedule="@daily",
    catchup=False,
    default_args={
        "owner": "airflow",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["spotify", "artist"],
) as dag:
    extract_latest_artists = PythonOperator(
        task_id="extract_latest_artists",
        python_callable=extract_artists_from_latest_chart,
        op_kwargs={
            "input_dir": "data/top_track",
            "output_dir": "data/artist",
            "market": os.getenv("SPOTIFY_MARKET", "VN"),
        },
    )

"""Extract Spotify track metadata for the newest Vietnam weekly chart CSV."""

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from scripts.extract_tracks import extract_tracks_from_latest_chart


with DAG(
    dag_id="spotify_extract_tracks",
    description="Read the latest regional-vn-weekly CSV and fetch Spotify track metadata.",
    start_date=datetime(2026, 5, 21),
    schedule="@daily",
    catchup=False,
    default_args={
        "owner": "airflow",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["spotify", "track"],
) as dag:
    extract_latest_tracks = PythonOperator(
        task_id="extract_latest_tracks",
        python_callable=extract_tracks_from_latest_chart,
        op_kwargs={
            "input_dir": "data/top_track",
            "output_dir": "data/track",
            "market": os.getenv("SPOTIFY_MARKET", "VN"),
        },
    )

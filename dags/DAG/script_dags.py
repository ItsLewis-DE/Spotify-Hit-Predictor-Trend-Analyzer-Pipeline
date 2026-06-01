from airflow.decorators import dag,task
import pendulum
from airflow.operators.bash import BashOperator
from scripts.extract.crawl_audio_feature import crawl_audio_feature
from scripts.extract.crawl_track_spotify import crawl_track_spotify
from scripts.extract.crawl_artist import crawl_artist
default_args = {
   'owner':'platon_team',
   'retries':3,
   'retry_delay':300
 }

@dag(
   dag_id='spotify_pipeline',
   default_args = default_args,
   schedule='0 0 * * 6',
   start_date = pendulum.datetime(2026,4,30,tz='Asia/Ho_Chi_Minh'),
   catchup=False,
   tags=['spotify','music']
 )

def spotify_pipeline():
   # extract_top_track = BashOperator(
   #    task_id = 'extract_top_track',
   #    bash_command=" python3 -u /opt/airflow/dags/scripts/extract/crawl_top_track.py --date {{ logical_date.strftime('%Y-%m-%d') }} ",
   #    do_xcom_push=True
   # )

   @task
   def extract_audio_feature(file_top_track):
      crawl_audio_feature(file_top_track)

   @task
   def extract_track_spotify(file_top_track):
      return crawl_track_spotify(file_top_track)

   @task
   def extract_artist(file_track):
      crawl_artist(file_track)

   load_all_data_s3_to_snow_task = BashOperator(
      task_id = 'load_all_data_s3_to_snow_task',
      bash_command = "python3 -u /opt/airflow/dags/scripts/load/load_all_data_s3_to_snow.py --date 2026-05-28",
   )
   # load_top_track_to_s3_task = BashOperator(
   #    task_id = "load_all_data_to_s3",
   #    bash_command = "/opt/airflow/dags/scripts/load/load_all_data_to_s3.sh {{ logical_date.strftime('%Y-%m-%d') }}"
   # )
   # file_top_track = extract_top_track
   # task_audio_feature = extract_audio_feature(file_top_track.output)
   # file_track = extract_track_spotify(file_top_track.output)
   # task_artist= extract_artist(file_track)
   # task_artist >> load_top_track_to_s3_task

dag = spotify_pipeline()
   


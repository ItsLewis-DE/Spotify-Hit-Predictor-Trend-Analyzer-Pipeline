from bs4 import BeautifulSoup
import requests
import json
import pendulum
import logging

logging.basicConfig(
    level=logging.INFO, # Cho phép hiển thị log từ mức INFO trở lên
    format='%(asctime)s - %(levelname)s - %(message)s' # Định dạng cho dòng log dễ nhìn hơn
)

def crawl_top_track():
    logger = logging.getLogger(__name__)
    data = []
    url = 'https://kworb.net/spotify/country/vn_daily.html'
    logger.info("Crawing data....")
    try:
        response = requests.get(url,timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error(f"There is an error while crawing data! : {e}")
        raise
    soup = BeautifulSoup(response.text,'lxml')
    records = soup.select('.sortable tbody tr')
    for record in records:
        track = {}
        pos = record.select('.np')
        track['pos'] = pos[0].text
        track['P+'] = pos[1].text
        if len(record.select('.text.mp a')) >1:
            track['spotify_id'] = record.select('.text.mp a')[1]['href'].split('/')[-1].replace('.html','')
        td = record.select('td')
        if len(td) > 10:
            track['days'] = td[3].text
            track['streams'] = td[6].text
            track['streams+'] = td[7].text
            track['7day'] = td[8].text
            track['7day+'] =td[9].text
            track['total'] = td[10].text
        if track:
            data.append(track)
    date = pendulum.now(tz='Asia/Ho_Chi_Minh').strftime('%Y_%m_%d')
    path_to_save = f'data/top_tract_{date}.json'
    with open(path_to_save,'w') as f:
        json.dump(data,f,indent=2)
    logger.info(f"Data saved to {path_to_save} successfully!")
 
crawl_top_track()
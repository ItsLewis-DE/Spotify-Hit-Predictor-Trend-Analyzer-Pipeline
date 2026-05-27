"""
Spotify Charts CSV Auto Downloader
===================================
Tu dong tai file CSV tu Spotify Charts.
Ho tro tai nhieu tuan, luu moi tuan vao 1 thu muc rieng.

Yeu cau:
    pip install selenium webdriver-manager

Cach dung:
    python download_spotify_charts.py                  # Tai chart moi nhat
    python download_spotify_charts.py --weeks 10       # Tai 10 tuan gan nhat
    python download_spotify_charts.py --date 2026-05-14  # Tai chart cu the
    python download_spotify_charts.py --login            # Dang nhap lan dau

Lan dau chay: python download_spotify_charts.py --login
"""

import os
import sys
import time
import argparse
import glob
from datetime import datetime, timedelta
import shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None


# --- Cau hinh ---
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "data")
CHROME_PROFILE_DIR = os.path.join(SCRIPT_DIR, "chrome_profile")
BASE_URL = "https://charts.spotify.com/charts/view/regional-vn-weekly"
LOGIN_WAIT_TIMEOUT = 180


def setup_driver(download_dir, headless=False, use_profile=True):
    """Khoi tao Chrome voi profile de luu session dang nhap."""
    os.makedirs(download_dir, exist_ok=True)

    chrome_options = Options()

    # Cau hinh download - luon dung thu muc goc cho profile
    prefs = {
        "download.default_directory": BASE_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Dung Chrome Profile de luu cookies/session
    if use_profile:
        os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        chrome_options.add_argument("--profile-directory=SpotifyCharts")

    # Tranh bi phat hien la bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

    if ChromeDriverManager:
        service = Service(ChromeDriverManager().install())
    else:
        service = Service()

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(60)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    
    # Cho phep download trong headless mode
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": BASE_DOWNLOAD_DIR
    })
    
    return driver


def is_logged_in(driver):
    """Kiem tra da dang nhap chua bang URL hien tai va UI."""
    current_url = driver.current_url
    if "login" in current_url or "accounts.spotify.com" in current_url:
        return False
    if current_url.endswith("/home") or current_url.strip("/") == "https://charts.spotify.com":
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, '[data-testid="charts-login"]')
        return False
    except:
        return True


def handle_login(driver, target_url, force_login=False, is_headless=False):
    """
    Xu ly dang nhap.
    Neu da luu session tu truoc -> tu dong dang nhap.
    Neu chua -> cho nguoi dung dang nhap thu cong.
    """
    print("[*] Truy cap trang chart...")
    driver.get(target_url)
    time.sleep(5)

    current_url = driver.current_url
    print(f"[INFO] URL: {current_url}")

    if is_logged_in(driver) and not force_login:
        print("[OK] Da dang nhap tu session truoc! (Khong can dang nhap lai)")
        return True

    # Chua dang nhap
    print("=" * 60)
    if force_login:
        print("[*] CHE DO DANG NHAP - Hay dang nhap trong Chrome")
    else:
        print("[!] Session het han hoac khong duoc nhan dien - Hay dang nhap lai trong Chrome")
        
    if is_headless and not force_login:
        print("[FAIL] Khong the dang nhap trong che do Headless (an).")
        print("       Vui long chay script voi tham so --login (khong dung --headless) de dang nhap truoc.")
        print("=" * 60)
        return False

    print(f"[*] Ban co {LOGIN_WAIT_TIMEOUT} giay.")
    print("[*] Sau khi dang nhap, session se duoc luu lai.")
    print("[*] Cac lan chay sau se KHONG can dang nhap nua!")
    print("=" * 60)

    start_time = time.time()
    last_url = ""
    while time.time() - start_time < LOGIN_WAIT_TIMEOUT:
        try:
            current_url = driver.current_url
            if current_url != last_url:
                elapsed = int(time.time() - start_time)
                print(f"    [{elapsed}s] {current_url}")
                last_url = current_url
            if is_logged_in(driver):
                print("\n[OK] Dang nhap thanh cong! Session da duoc luu.")
                time.sleep(3)
                return True
        except Exception:
            pass
        time.sleep(2)

    print("[FAIL] Het thoi gian cho!")
    return False


def dismiss_popups(driver):
    """Dong cookie banner va cac popup khac."""
    try:
        driver.execute_script("""
            // Cookie banner
            const acceptBtn = document.querySelector('#onetrust-accept-btn-handler');
            if (acceptBtn) acceptBtn.click();
            
            // Dismiss button
            const dismissBtn = document.querySelector('[aria-label="Dismiss"]');
            if (dismissBtn) dismissBtn.click();
        """)
        time.sleep(1)
    except Exception:
        pass


def find_and_click_download(driver):
    """Tim va click nut download bang ActionChains."""
    print("[*] Tim nut Download...")

    btn = driver.execute_script("""
        const buttons = document.querySelectorAll('button');
        for (let btn of buttons) {
            const svg = btn.querySelector('svg');
            if (!svg) continue;
            const paths = svg.querySelectorAll('path');
            for (let path of paths) {
                const d = path.getAttribute('d') || '';
                if (d.startsWith('M12 6.05') || d.includes('v7.486l1.793-1.793')) {
                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    return btn;
                }
            }
        }
        return null;
    """)

    if btn:
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            # Them sleep nho de browser scroll den noi
            time.sleep(1)
            ActionChains(driver).move_to_element(btn).click().perform()
            print("[OK] Da click nut Download! (method: action_chains)")
            return True
        except Exception as e:
            print(f"[!] ActionChains loi: {e}, thu click qua JS...")
            driver.execute_script("arguments[0].click();", btn)
            return True
            
    print("[FAIL] Khong tim thay nut Download!")
    return False


def wait_for_download(existing_files, base_dir, dest_dir, timeout=30):
    """Cho file CSV moi xuat hien trong thu muc goc va di chuyen sang thu muc dich."""
    print("[*] Cho file tai xuong...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        current = set(glob.glob(os.path.join(base_dir, "*.csv")))
        new_files = current - existing_files
        if new_files:
            new_file = list(new_files)[0]
            if not os.path.exists(new_file + ".crdownload"):
                # Di chuyen file sang thu muc dich
                filename = os.path.basename(new_file)
                dest_path = os.path.join(dest_dir, filename)
                try:
                    shutil.move(new_file, dest_path)
                    return dest_path
                except Exception as e:
                    print(f"Loi khi di chuyen file: {e}")
                    return new_file
        time.sleep(1)
    
    return None


def download_chart(url, download_dir, headless=False, force_login=False):
    """Quy trinh chinh: mo trang -> dang nhap (neu can) -> tai CSV."""
    driver = None
    try:
        print("=" * 60)
        print(f"  URL:      {url}")
        print(f"  Download: {download_dir}")
        print("=" * 60)

        driver = setup_driver(download_dir=download_dir, headless=headless, use_profile=True)

        # Dang nhap
        if not handle_login(driver, url, force_login=force_login, is_headless=headless):
            return None

        # Chuyen den trang chart dung
        if "charts.spotify.com/charts/view" not in driver.current_url:
            print("[*] Chuyen den trang chart...")
            driver.get(url)

        # Cho render
        print("[*] Cho trang render...")
        time.sleep(8)

        # Dong popups
        dismiss_popups(driver)
        time.sleep(1)

        # Kiem tra xem co trang 404 hoac "We couldn't find what you're looking for"
        page_source = driver.page_source.lower()
        if "we couldn't find what you're looking for" in page_source or "page not found" in page_source:
            print("[FAIL] Ngay nay khong co du lieu tren Spotify (404 Not Found)!")
            return None

        # Ghi nhan files hien co o thu muc GOC
        existing = set(glob.glob(os.path.join(BASE_DOWNLOAD_DIR, "*.csv")))

        # Click download
        if not find_and_click_download(driver):
            screenshot = os.path.join(download_dir, "debug_screenshot.png")
            driver.save_screenshot(screenshot)
            
            page_source_file = os.path.join(download_dir, "debug_page_source.html")
            with open(page_source_file, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
                
            print(f"[DEBUG] Screenshot: {screenshot}")
            print(f"[DEBUG] Page source: {page_source_file}")
            return None

        # Cho download xong, move tu BASE_DOWNLOAD_DIR sang download_dir
        time.sleep(3)
        downloaded = wait_for_download(existing, BASE_DOWNLOAD_DIR, download_dir, timeout=30)

        if downloaded:
            size = os.path.getsize(downloaded)
            print(f"[SUCCESS] TAI THANH CONG!")
            print(f"  File: {downloaded}")
            print(f"  Kich thuoc: {size:,} bytes")
            return downloaded
        else:
            print("[!] Khong tim thay file CSV.")
            screenshot = os.path.join(download_dir, "timeout_screenshot.png")
            driver.save_screenshot(screenshot)
            print(f"[DEBUG] Timeout screenshot: {screenshot}")
            return None

    except Exception as e:
        print(f"[FAIL] Loi: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Spotify Charts Auto Downloader"
    )
    parser.add_argument("--date", default=None, help="Ngay chart (YYYY-MM-DD). Mac dinh: tu dong")
    parser.add_argument("--weeks", type=int, default=1, help="So tuan muon tai (mac dinh: 1)")
    parser.add_argument("--headless", action="store_true", help="Chay an Chrome")
    parser.add_argument("--login", action="store_true", help="Mo Chrome de dang nhap (lan dau)")

    args = parser.parse_args()

    # Khong cho headless khi login
    headless = args.headless and not args.login

    dates_to_download = []
    if args.date:
        dates_to_download.append(args.date)
    else:
        # Tinh ngay chart moi nhat (lay theo thu 4)
        today = datetime.now()
        days_since_wednesday = (today.weekday() - 2) % 7
        if days_since_wednesday == 0 and today.hour < 12:
            days_since_wednesday = 7
        latest_wednesday = today - timedelta(days=days_since_wednesday)
        
        # Lay data cua n tuan truoc
        for i in range(args.weeks):
            d = latest_wednesday - timedelta(days=i*7)
            # Vi ngay 27/05/2026 dang the hien la loi (khong co data), 
            # de chac chan ta lay tu thu 5 tuan truoc hoac chinh xac ngay Spotify phat hanh chart.
            # Thuong thi Regional Weekly Chart duoc tinh vao thu 5 (Thursday) va url co ngay thu 5 do
            dates_to_download.append(d.strftime("%Y-%m-%d"))

    # Cap nhat logic tinh ngay cho dung chuan Spotify (Thursday):
    # Neu ban thay "2026-05-27" khong ton tai ma chi co "2026-05-14", co the cong thuc ngay la:
    # Spotify thuong update vao thu 5 voi date la ngay thu 5 cua tuan TRUOC.
    
    if not args.date:
        # Tinh lai theo chuan Spotify
        today = datetime.now()
        # Find the most recent Thursday
        days_since_thursday = (today.weekday() - 3) % 7
        latest_thursday = today - timedelta(days=days_since_thursday)
        # Lay ngay thu 5 gan nhat lam tuan hien tai
        latest_chart_date = latest_thursday
        
        dates_to_download = []
        for i in range(args.weeks):
            d = latest_chart_date - timedelta(days=i*7)
            dates_to_download.append(d.strftime("%Y-%m-%d"))


    print(f"[*] Tong so tuan can tai: {len(dates_to_download)}")
    
    success_count = 0
    for idx, chart_date in enumerate(dates_to_download):
        print(f"\n[*] Dang xu ly tuan {idx+1}/{len(dates_to_download)} (Date: {chart_date})")
        url = f"{BASE_URL}/{chart_date}"
        
        # Tao folder rieng cho tuan nay
        week_dir = os.path.join(BASE_DOWNLOAD_DIR, chart_date)
        
        result = download_chart(url=url, download_dir=week_dir, headless=headless, force_login=args.login)

        if result:
            success_count += 1
            print(f"[OK] Da tai va luu vao: {week_dir}")
        else:
            print(f"[FAIL] Khong the tai chart ngay {chart_date}")
            
    print("\n" + "=" * 60)
    print(f"HOAN TAT! Tai thanh cong {success_count}/{len(dates_to_download)} tuan.")
    print("=" * 60)


if __name__ == "__main__":
    main()

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
import json
import argparse
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BASE_DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "data", "top_track")
CHROME_PROFILE_DIR = os.path.join(SCRIPT_DIR, "chrome_profile")
COOKIES_FILE = os.path.join(SCRIPT_DIR, "spotify_cookies.json")
BASE_URL = "https://charts.spotify.com/charts/view/regional-vn-weekly"
LOGIN_WAIT_TIMEOUT = 180


def clean_stale_locks():
    """Xoa file lock cu cua Chrome profile (neu Chrome bi crash truoc do)."""
    lock_files = [
        os.path.join(CHROME_PROFILE_DIR, "SingletonLock"),
        os.path.join(CHROME_PROFILE_DIR, "SingletonSocket"),
        os.path.join(CHROME_PROFILE_DIR, "SingletonCookie"),
    ]
    for f in lock_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            pass


def save_cookies(driver):
    """Luu cookies cua driver ra file JSON."""
    try:
        cookies = driver.get_cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"[OK] Da luu {len(cookies)} cookies vao {COOKIES_FILE}")
        return True
    except Exception as e:
        logger.info(f"[!] Khong the luu cookies: {e}")
        return False


def load_cookies(driver):
    """Load cookies tu file JSON vao driver."""
    if not os.path.exists(COOKIES_FILE):
        logger.info("[INFO] Chua co file cookies. Can dang nhap lan dau voi --login")
        return False
    
    try:
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        
        if not cookies:
            logger.info("[INFO] File cookies rong.")
            return False
        
        # Phai truy cap domain truoc khi add cookies
        driver.get("https://charts.spotify.com")
        time.sleep(2)
        
        for cookie in cookies:
            # Xoa cac truong khong can thiet co the gay loi
            for key in ["sameSite", "storeId", "id"]:
                cookie.pop(key, None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass  # Bo qua cookie loi (het han, sai domain, v.v.)
        
        logger.info(f"[OK] Da load {len(cookies)} cookies tu file.")
        return True
    except Exception as e:
        logger.info(f"[!] Loi khi load cookies: {e}")
        return False


def setup_driver(download_dir, headless=False, use_profile=False):
    """Khoi tao Remote Chrome."""
    os.makedirs(download_dir, exist_ok=True)
    try:
        os.chmod(download_dir, 0o777)
    except Exception as e:
        logger.warning(f"Could not chmod download_dir: {e}")
    
    chrome_options = Options()

    # Cau hinh Chrome cho viec tu dong tai file ma khong can xac nhan
    # LUY Y: Duong dan nay la ben trong container Selenium!
    prefs = {
        "download.default_directory": "/home/seluser/Downloads",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Tranh bi phat hien la bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    
    # Khi chay trong container luon can sandbox flags
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")

    logger.info("[*] Connecting to Remote Selenium Server at http://selenium:4444/wd/hub ...")
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=chrome_options
    )
    
    driver.set_page_load_timeout(60)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    
    return driver


def is_logged_in(driver):
    """Kiem tra da dang nhap chua bang URL hien tai va UI."""
    current_url = driver.current_url
    # Dang o trang login cua Spotify -> chua login
    if "accounts.spotify.com" in current_url:
        return False
    # URL co chua "/login" trong path
    if "/login" in current_url:
        return False
    # Kiem tra co nut login tren trang khong
    try:
        driver.find_element(By.CSS_SELECTOR, '[data-testid="charts-login"]')
        return False
    except:
        pass
    # Kiem tra co nut "Log in" / "Sign in" tren trang
    try:
        sign_in_buttons = driver.find_elements(By.XPATH, 
            '//button[contains(text(),"Log in") or contains(text(),"Sign in")]'
            '|//a[contains(text(),"Log in") or contains(text(),"Sign in")]')
        if sign_in_buttons:
            return False
    except:
        pass
    # Neu khong co dau hieu chua login -> da login
    return True


def handle_login(driver, target_url, force_login=False, is_headless=False):
    """
    Xu ly dang nhap.
    1. Thu load cookies tu file truoc
    2. Neu da luu session tu truoc -> tu dong dang nhap.
    3. Neu chua -> cho nguoi dung dang nhap thu cong.
    """
    # === BUOC 1: Thu load cookies da luu ===
    if not force_login:
        logger.info("[*] Thu load cookies da luu...")
        if load_cookies(driver):
            # Sau khi load cookies, truy cap trang chart de kiem tra
            logger.info("[*] Truy cap trang chart de kiem tra session...")
            driver.get(target_url)
            time.sleep(5)
            
            current_url = driver.current_url
            logger.info(f"[INFO] URL sau khi load cookies: {current_url}")
            
            if is_logged_in(driver):
                logger.info("[OK] Da dang nhap tu cookies da luu! (Khong can dang nhap lai)")
                return True
            else:
                logger.info("[!] Cookies het han hoac khong hop le.")
    
    # === BUOC 2: Truy cap trang truc tiep (co the profile van con session) ===
    if not force_login:
        logger.info("[*] Thu truy cap trang chart bang Chrome profile...")
        driver.get(target_url)
        time.sleep(5)
        
        current_url = driver.current_url
        logger.info(f"[INFO] URL: {current_url}")
        
        if is_logged_in(driver):
            logger.info("[OK] Da dang nhap tu Chrome profile!")
            # Luu cookies ra file de lan sau dung
            save_cookies(driver)
            return True

    # === BUOC 3: Can dang nhap thu cong ===
    if force_login:
        logger.info("[*] Truy cap trang chart...")
        driver.get(target_url)
        time.sleep(5)
        current_url = driver.current_url
        logger.info(f"[INFO] URL: {current_url}")
    
    logger.info("=" * 60)
    if force_login:
        logger.info("[*] CHE DO DANG NHAP - Hay dang nhap trong Chrome")
    else:
        logger.info("[!] Session het han - Hay dang nhap lai trong Chrome")
        
    if is_headless and not force_login:
        logger.info("[FAIL] Khong the dang nhap trong che do Headless (an).")
        logger.info("       Vui long chay script voi tham so --login (khong dung --headless) de dang nhap truoc.")
        logger.info("=" * 60)
        return False

    logger.info(f"[*] Ban co {LOGIN_WAIT_TIMEOUT} giay.")
    logger.info("[*] Sau khi dang nhap, session se duoc luu lai.")
    logger.info("[*] Cac lan chay sau se KHONG can dang nhap nua!")
    logger.info("=" * 60)

    start_time = time.time()
    last_url = ""
    while time.time() - start_time < LOGIN_WAIT_TIMEOUT:
        try:
            current_url = driver.current_url
            if current_url != last_url:
                elapsed = int(time.time() - start_time)
                logger.info(f"    [{elapsed}s] {current_url}")
                last_url = current_url
            if is_logged_in(driver):
                logger.info("\n[OK] Dang nhap thanh cong!")
                time.sleep(3)
                # === LUU COOKIES SAU KHI LOGIN THANH CONG ===
                save_cookies(driver)
                return True
        except Exception:
            pass
        time.sleep(2)

    logger.info("[FAIL] Het thoi gian cho!")
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
    logger.info("[*] Tim nut Download...")

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
            logger.info(f"[*] Button HTML found: {driver.execute_script('return arguments[0].outerHTML;', btn)}")
            
            # Click banner dismiss if present
            driver.execute_script("""
                const closeBtns = document.querySelectorAll('button[aria-label="Close"], button.onetrust-close-btn-handler');
                for (let b of closeBtns) b.click();
            """)
            time.sleep(1)
            
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[OK] Da click nut Download! (method: js_click)")
            return True
        except Exception as e:
            logger.info(f"[!] Loi click: {e}")
            return False
            
    logger.info("[FAIL] Khong tim thay nut Download!")
    return False


def wait_for_download(existing_files, download_dir, timeout=30):
    """Cho file CSV moi xuat hien trong thu muc download."""
    logger.info("[*] Cho file tai xuong...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        current = set(glob.glob(os.path.join(download_dir, "*.csv")))
        new_files = current - existing_files
        if new_files:
            new_file = list(new_files)[0]
            if not os.path.exists(new_file + ".crdownload"):
                return new_file
        time.sleep(1)
    
    return None


def download_chart(url, download_dir, headless=False, force_login=False):
    """Quy trinh chinh: mo trang -> dang nhap (neu can) -> tai CSV."""
    driver = None
    try:
        logger.info("=" * 60)
        logger.info(f"  URL:      {url}")
        logger.info(f"  Download: {BASE_DOWNLOAD_DIR}")
        logger.info("=" * 60)

        driver = setup_driver(download_dir=download_dir, headless=headless, use_profile=True)

        # Dang nhap
        if not handle_login(driver, url, force_login=force_login, is_headless=headless):
            return None

        # Chuyen den trang chart dung
        if "charts.spotify.com/charts/view" not in driver.current_url:
            logger.info("[*] Chuyen den trang chart...")
            driver.get(url)

        # Cho render
        logger.info("[*] Cho trang render...")
        time.sleep(8)

        # Dong popups
        dismiss_popups(driver)
        time.sleep(1)

        # Kiem tra xem co trang 404 hoac "We couldn't find what you're looking for"
        page_source = driver.page_source.lower()
        if "we couldn't find what you're looking for" in page_source or "page not found" in page_source:
            logger.info("[FAIL] Ngay nay khong co du lieu tren Spotify (404 Not Found)!")
            return None

        # Ghi nhan files hien co o thu muc GOC
        existing = set(glob.glob(os.path.join(BASE_DOWNLOAD_DIR, "*.csv")))

        # Click download
        if not find_and_click_download(driver):
            return None

        # Cho download xong
        time.sleep(3)
        downloaded = wait_for_download(existing, BASE_DOWNLOAD_DIR, timeout=30)

        if downloaded:
            size = os.path.getsize(downloaded)
            logger.info(f"[SUCCESS] TAI THANH CONG!")
            logger.info(f"  File: {downloaded}")
            logger.info(f"  Kich thuoc: {size:,} bytes")
            return downloaded
        else:
            logger.info("[!] Khong tim thay file CSV.")
            return None

    except Exception as e:
        logger.info(f"[FAIL] Loi: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            try:
                # Luu cookies 1 lan nua truoc khi quit (phong truong hop)
                save_cookies(driver)
            except:
                pass
            try:
                time.sleep(1)
            except:
                pass
            driver.quit()


def crawl_top_track():
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
        provided_date = datetime.strptime(args.date, "%Y-%m-%d")
        days_since_thursday = (provided_date.weekday() - 3) % 7
        actual_date = provided_date - timedelta(days=days_since_thursday)
        dates_to_download.append(actual_date.strftime("%Y-%m-%d"))
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


    logger.info(f"[*] Tong so tuan can tai: {len(dates_to_download)}")
    
    success_count = 0
    downloaded_paths = []
    for idx, chart_date in enumerate(dates_to_download):
        logger.info(f"\n[*] Dang xu ly tuan {idx+1}/{len(dates_to_download)} (Date: {chart_date})")
        url = f"{BASE_URL}/{chart_date}"
        
        result = download_chart(url=url, download_dir=BASE_DOWNLOAD_DIR, headless=headless, force_login=args.login)

        if result:
            success_count += 1
            downloaded_paths.append(Path(result))
            logger.info(f"[OK] Da tai va luu vao: {BASE_DOWNLOAD_DIR}")
        else:
            logger.info(f"[FAIL] Khong the tai chart ngay {chart_date}")
            
    logger.info("\n" + "=" * 60)
    logger.info(f"HOAN TAT! Tai thanh cong {success_count}/{len(dates_to_download)} tuan.")
    logger.info("=" * 60)

    if len(dates_to_download) == 1:
        return downloaded_paths[0] if downloaded_paths else None
    return downloaded_paths

if __name__ == "__main__":
    import sys
    result = crawl_top_track()
    if result:
        print(str(result))
    else:
        sys.exit(1)

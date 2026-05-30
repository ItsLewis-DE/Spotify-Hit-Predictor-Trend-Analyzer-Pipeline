import json, time, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
driver = webdriver.Remote(command_executor="http://localhost:4444/wd/hub", options=chrome_options)

with open('spotify_cookies.json', 'r') as f:
    cookies = json.load(f)
driver.get("https://charts.spotify.com")
time.sleep(2)
for cookie in cookies:
    for key in ["sameSite", "storeId", "id"]:
        cookie.pop(key, None)
    try:
        driver.add_cookie(cookie)
    except: pass

driver.get("https://charts.spotify.com/charts/view/regional-vn-weekly/2026-05-28")
time.sleep(5)
print("URL:", driver.current_url)

btn = driver.execute_script("""
    const buttons = document.querySelectorAll('button');
    for (let btn of buttons) {
        const svg = btn.querySelector('svg');
        if (!svg) continue;
        const paths = svg.querySelectorAll('path');
        for (let path of paths) {
            const d = path.getAttribute('d') || '';
            if (d.startsWith('M12 6.05') || d.includes('v7.486l1.793-1.793')) {
                return btn.outerHTML;
            }
        }
    }
    return 'NOT FOUND';
""")
print("Button HTML:", btn)
driver.save_screenshot("screenshot.png")
driver.quit()

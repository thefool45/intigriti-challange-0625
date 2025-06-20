import re
from selenium.webdriver.chrome.options import Options
from instance_manager import get_instance_path

def sanitize_filename(filename):
    return re.sub(r'[^A-Za-z0-9_/]', '', filename)

def sanitize_username(username):
    return re.sub(r'[^A-Za-z0-9_.-]', '', username)

def get_chrome_options(instance_id):
    chrome_options = Options()
   
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--user-data-dir={get_instance_path(instance_id, 'chrome_profile')}")
    
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--disable-3d-apis")
    
    chrome_options.add_argument("--disable-file-system")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-component-update")
 
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-notifications")

    return chrome_options

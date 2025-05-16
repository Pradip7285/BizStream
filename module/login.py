import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import shutil
from . import stock 
from . import invoice
from . import inventory as inventory
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(".env",override=True)
user= 1

# Constants
#BASE_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "MyAppDownloads")
LOGIN_URL = os.getenv("LOGIN_URL")
USERNAME = os.getenv("BEVCO_USER")
PASSWORD = os.getenv("BEVCO_PASSWORD")

def setup_browser(download_dir):
    try:
        if not os.path.isdir(download_dir):
            raise ValueError("Download directory does not exist.")

        chrome_options = Options()

        # # ✅ HEADLESS + download enabled
        chrome_options.add_argument("--headless=new")  # or try --headless if this fails
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # ✅ Preferences to enable downloads
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": True,  # Can still fail sometimes
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("prefs", prefs)

        # ✅ Experimental: disable safe browsing (ONLY in test env)
        chrome_options.add_argument("--safebrowsing-disable-download-protection")
        chrome_options.add_argument("--safebrowsing-disable-extension-blacklist")

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        return driver

    except Exception as e:
        print(f"❌ Failed to set up browser: {e}")
        return None    
    

        
def get_captcha_image(driver, user = "default"):
    try:
        if not driver:
            print("driver not Found")
        print(LOGIN_URL)
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "Label1")))
        captcha_elem = driver.find_element(By.ID, "Image1")  # Adjust ID if needed
        captcha_image = captcha_elem.screenshot_as_png  # ❗ No parentheses here

        # Save the screenshot locally
        imagePath = f"captcha_{user}.png"
        with open(imagePath, "wb") as f:
            f.write(captcha_image)

        print(f"📸 CAPTCHA saved to: {imagePath}")
        return imagePath  # Return image path
    except Exception as e:
        print(f"❌ Could not capture CAPTCHA: {e}")
        return None

def login(driver,captcha_text=None):
    try:
        driver.find_element(By.ID, "txt_username").send_keys(USERNAME)
        driver.find_element(By.ID, "txt_password").send_keys(PASSWORD)
        print (captcha_text)
        if captcha_text is None:
          return "AWAITING_CAPTCHA"
        # captcha_text = input("🔒 Enter CAPTCHA manually: ").strip()
        driver.find_element(By.ID, "CodeNumberTextBox").send_keys(captcha_text)
        driver.find_element(By.ID, "ImageButton1").click()
        time.sleep(3)
    except Exception as e:
        print(f"❌ Login failed: {e}")
        driver.quit()
        exit()

# def main():
#     try:
#         print("\nWhich task would you like to perform?")
#         print("1. Download invoices")
#         print("2. Scrape reports section")
#         print("3. Download inventory details")
#         choice = input("Enter choice (1/2/3): ").strip()

#         if choice == "1":
#             module = "invoice"
#         elif choice == "2":
#             module = "stock"
#         elif choice == "3":
#             module = "inventory"
#         else:
#             print("❌ Invalid choice.")
#             return

#         today_str = datetime.today().strftime('%Y-%m-%d')
#         download_dir = os.path.join(BASE_DOWNLOAD_DIR, module, today_str)
#         os.makedirs(download_dir, exist_ok=True)

#         driver = setup_browser(download_dir)
#         if driver is None:
#             print("❌ Exiting due to browser setup failure.")
#             return
#         get_captcha_image(driver)
#         login(driver)

#         if module == "invoice":
#             invoice.scrape_invoice(driver, download_dir)
#         elif module == "inventory":
#             inventory.scrap_inventory(driver, download_dir)
#         else:
#             stock.scrape_reports(driver, download_dir)

#         driver.quit()
#         print(f"✅ All files downloaded to {download_dir} and renamed.")
    
#     except Exception as e:
#         print(f"❌ An unexpected error occurred: {e}")
#     try:
#         zip_download_folder(download_dir)
#     except Exception as e:
#         print (f"❌ An unexpected error occurred: {e}")



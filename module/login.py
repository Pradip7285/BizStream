import os
import time
import pandas as pd
import logging
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

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv(".env",override=True)
user= 1

# Constants
#BASE_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "MyAppDownloads")
LOGIN_URL = os.getenv("LOGIN_URL")
USERNAME = os.getenv("BEVCO_USER")
PASSWORD = os.getenv("BEVCO_PASSWORD")

def setup_browser(download_dir):
    """Setup and configure Chrome browser with optimized settings"""
    try:
        if not os.path.isdir(download_dir):
            raise ValueError("Download directory does not exist.")

        chrome_options = Options()

        # DISABLE headless mode for debugging
        # chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # chrome_options.add_argument("--disable-images")  # Faster loading
        # chrome_options.add_argument("--disable-javascript")  # If not needed
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")

        # Download preferences
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_settings.popups": 0
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Disable safe browsing for faster downloads
        chrome_options.add_argument("--safebrowsing-disable-download-protection")
        chrome_options.add_argument("--safebrowsing-disable-extension-blacklist")

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(30)  # 30 second timeout
        logger.info(f"Browser setup successful for download_dir: {download_dir}")
        return driver

    except Exception as e:
        logger.error(f"Failed to set up browser: {e}")
        return None

def get_captcha_image(driver, user="default", max_retries=3):
    """Get CAPTCHA image with retry logic"""
    for attempt in range(max_retries):
        try:
            if not driver:
                logger.error("Driver not found")
                return None
                
            logger.info(f"Attempting to get CAPTCHA (attempt {attempt + 1})")
            driver.get(LOGIN_URL)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "Label1"))
            )
            
            # Wait a bit more for CAPTCHA to load
            time.sleep(2)
            
            captcha_elem = driver.find_element(By.ID, "Image1")
            captcha_image = captcha_elem.screenshot_as_png

            # Save the screenshot locally
            imagePath = f"captcha_{user}_{int(time.time())}.png"
            with open(imagePath, "wb") as f:
                f.write(captcha_image)

            logger.info(f"CAPTCHA saved successfully: {imagePath}")
            return imagePath
            
        except Exception as e:
            logger.warning(f"CAPTCHA capture attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                logger.error(f"Failed to capture CAPTCHA after {max_retries} attempts")
                return None
    
    return None

def login(driver, captcha_text=None):
    """Login to the portal with error handling"""
    try:
        if not driver:
            raise ValueError("Driver is not initialized")
            
        if not captcha_text:
            logger.warning("No CAPTCHA text provided")
            return "AWAITING_CAPTCHA"
            
        logger.info("Attempting to login...")
        
        # Find and fill username
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txt_username"))
        )
        username_field.clear()
        username_field.send_keys(USERNAME)
        
        # Find and fill password
        password_field = driver.find_element(By.ID, "txt_password")
        password_field.clear()
        password_field.send_keys(PASSWORD)
        
        # Find and fill CAPTCHA
        captcha_field = driver.find_element(By.ID, "CodeNumberTextBox")
        captcha_field.clear()
        captcha_field.send_keys(captcha_text)
        
        # Click login button
        login_button = driver.find_element(By.ID, "ImageButton1")
        login_button.click()
        
        # Wait for login to complete
        time.sleep(3)
        
        # Check if login was successful (look for error messages or redirect)
        try:
            # Check for common error elements
            error_elements = driver.find_elements(By.CLASS_NAME, "error")
            if error_elements:
                error_text = error_elements[0].text
                logger.error(f"Login failed with error: {error_text}")
                raise Exception(f"Login failed: {error_text}")
                
            logger.info("Login successful")
            return "SUCCESS"
            
        except Exception as e:
            logger.error(f"Login verification failed: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Login failed: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        raise Exception(f"Login failed: {str(e)}")

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



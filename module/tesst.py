from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from dotenv import load_dotenv

load_dotenv()
# ✅ Define URL directly — avoid .env for now
url =  os.getenv("LOGIN_URL")

# ✅ Setup Chrome options
options = Options()
options.add_experimental_option("detach", True)  # Keep browser open

# ✅ Setup WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ✅ Open URL
driver.get(url)

# ✅ Wait for manual observation
time.sleep(5)

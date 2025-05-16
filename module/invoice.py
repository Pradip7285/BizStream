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
from datetime import datetime ,date
import shutil
LOG_FILENAME= "report.txt"
today = today = date.today().strftime("%d-%m-%Y") 
EXCEL_PATH = os.path.join(os.path.dirname(__file__),"distict&warehouse.xlsx")
def wait_for_download(download_dir, filename_part, timeout=30):
    for _ in range(timeout):
        for filename in os.listdir(download_dir):
            if filename_part in filename and not filename.endswith(".crdownload"):
                return filename
        time.sleep(1)
    raise TimeoutError("Download did not complete in time.")
def navigate(driver):
    driver.find_element(By.ID, 'ctl00_ImageButton11').click()
    time.sleep(5)
    driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_TabContainer1_Tab_BI_Module_grid_crop_suppl_ctl10_link_crop_supplier').click()
    time.sleep(10)
def submit_request(driver, destination, date):
    # Replace with correct selectors or logic
    select = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_Warehouse"))
    select.select_by_visible_text(destination)

    date_input =Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_date"))
    date_input.select_by_visible_text(date.strftime('%d/%m/%Y'))
    # date_input.send_keys(date.strftime("%d/%m/%Y"))
    # date_input.send_keys(Keys.RETURN)
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn_Show"))
    ).click()
    time.sleep(5)

def rename_file(download_dir, old_filename, new_name):
    src = os.path.join(download_dir, old_filename)
    ext = os.path.splitext(old_filename)[1]
    dst = os.path.join(download_dir, f"{new_name}{ext}")
    shutil.move(src, dst)
    
def log_failure(destination, date, reason, download_dir):
    log_path = os.path.join(download_dir, LOG_FILENAME)
    with open(log_path, "a") as f:  # Append mode
        f.write(f"[{date.strftime('%d-%m-%Y')}] {destination} - {reason}\n")
        
def scrape_invoice( driver,download_dir,inputDate):
    df = pd.read_excel(EXCEL_PATH)
    navigate(driver)
    WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    parsed_date = datetime.strptime(inputDate, '%d-%m-%Y')
    date = parsed_date
    for _, row in df.iterrows():
        destination = row["Warehouse Name"]
         #pd.to_datetime(row["Date"])
        submit_request(driver, destination, date)
        try:
            filename = wait_for_download(download_dir, "BEVCO_Invoice.pdf")
            if filename:
                rename_file(download_dir, filename, destination.replace(" ", "_"))
            else:
                log_failure(destination,date,"No file Name", download_dir)
                print(f"⚠️ File was not downloaded for {destination} on {date} (filename is None).")
        except TimeoutError:
            print(f"❌ No invoice downloaded for {destination} on {date} (timeout).")
            log_failure(destination,date,"Time-Out", download_dir)

    print("✅ all inventory download completed")
    return download_dir


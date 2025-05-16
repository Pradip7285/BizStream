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

excelpath=os.path.join(os.path.dirname(__file__), "distict&warehouse.xlsx")

def navigate(driver):
    driver.find_element(By.ID, "ctl00_ImageButton_Home").click()
    WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')

def wait_for_download(download_dir, filename_part, timeout=30):
    for _ in range(timeout):
        for filename in os.listdir(download_dir):
            if filename_part in filename and not filename.endswith(".crdownload"):
                return filename
        time.sleep(1)
    raise TimeoutError("Download did not complete in time.") 
def submit_request(driver, destination, depot):
    try:
        # Select district
        district_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_Excise_district"))
        )
        Select(district_dropdown).select_by_visible_text(destination)
        time.sleep(10)
        # ✅ Wait until depot options are loaded (more than one option)
        WebDriverWait(driver, 10).until(
            lambda d: len(Select(
                d.find_element(By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_warehouse")
            ).options) > 1  # assumes 1 default or empty option, real options load after that
        )

        # Select depot
        warehouse_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_warehouse"))
        warehouse_dropdown.select_by_visible_text(depot)

        # Wait for inventory grid
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_GridView1"))
        )

        # Click PDF button
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ImgButton_WarehousePdf"))
        ).click()

        time.sleep(10)

    except Exception as e:
        print(f"❌ Error during submission for {destination} → {depot}: {e}")


def rename_file(download_dir,old_filename,depot):
    src = os.path.join(download_dir, old_filename)
    new_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{depot.replace(' ', '_')}"
    ext = os.path.splitext(old_filename)[1]
    dst = os.path.join(download_dir, f"{new_name}{ext}")
    shutil.move(src, dst)

def scrap_inventory(driver,download_dir):
    navigate(driver)
    df= pd.read_excel(excelpath)
    for _, row in df.iterrows():
        destination= row['District']
        depot = row['Warehouse Name']
        submit_request(driver,destination,depot)
        try:
            filename=wait_for_download(download_dir,"WBSBCL_Inventory") 
            if filename:
                 rename_file(download_dir, filename, depot.replace(" ", "_"))
            else:
                print (f"no data for the location {destination}- {depot}")
        except TimeoutError:
            print(f"❌ No invoice downloaded for {destination} on {depot} (timeout).")
    print("✅ all inventory download completed")

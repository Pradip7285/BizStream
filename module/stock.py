import os
import time
import pandas as pd
from io import StringIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, date
from openpyxl import load_workbook, Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Constraints
today = date.today().strftime("%Y-%m-%d")
EXCEL_PATH = os.path.join(os.path.dirname(__file__),"Depot.xlsx")
filename = "stocks.xlsx"

def navigate(driver):
    driver.find_element(By.ID, 'ctl00_ImageButton11').click()
    time.sleep(5)
    driver.find_element(By.ID, 'ctl00_ContentPlaceHolder1_TabContainer1_Tab_BI_Module_grid_crop_suppl_ctl09_link_crop_supplier').click()
    time.sleep(10)

def submit_request(driver, destination, download_dir):
    filepath = os.path.join(download_dir, filename)
    print(f"➡️ Processing: {destination} -> {filepath}")

    select = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_ddl_warehouse_Name"))
    select.select_by_visible_text(destination)

    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_Grid_req")))
    table = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Grid_req")
    html = table.get_attribute('outerHTML')

    df = pd.read_html(StringIO(html))[0]
    if df.empty:
        print(f"⚠️ No data for {destination}")
        return
    df.insert(0, "Depot", destination)

    try:
        append_df_to_excel(filepath, df)
        print(f"✅ Data saved for {destination}")
    except Exception as e:
        print(f"❌ Error saving for {destination}: {e}")

def append_df_to_excel(filepath, df, sheet_name='Sheet1'):
    # Load the workbook, or create it if it doesn't exist
    if not os.path.exists(filepath):
        wb = Workbook()
        wb.save(filepath)

    wb = load_workbook(filepath)
    ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.create_sheet(sheet_name)

    # Append data to the sheet
    for r in dataframe_to_rows(df, index=False, header=ws.max_row == 1):
        ws.append(r)

    # Save the workbook to the correct path
    wb.save(filepath)

def scrape_reports(driver,download_dir):
    navigate(driver)
    df = pd.read_excel(EXCEL_PATH)
    for _, row in df.iterrows():
        destination = row["Depot"]
        submit_request(driver, destination,download_dir)
    driver.quit()
    print("✅ All files downloaded and renamed.")

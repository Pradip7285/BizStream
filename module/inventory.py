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

# Configure logging
logger = logging.getLogger(__name__)

excelpath = os.path.join(os.path.dirname(__file__), "distict&warehouse.xlsx")

def navigate(driver):
    """Navigate to the inventory section with error handling"""
    try:
        logger.info("Navigating to inventory section...")
        
        # Click on home button
        home_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ImageButton_Home"))
        )
        home_button.click()
        
        # Wait for page to load completely
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        logger.info("Successfully navigated to inventory section")
        
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        raise Exception(f"Failed to navigate to inventory section: {str(e)}")

def wait_for_download(download_dir, filename_part, timeout=60):
    """Wait for file download with improved timeout and error handling"""
    logger.info(f"Waiting for download containing '{filename_part}' in {download_dir}")
    
    for attempt in range(timeout):
        try:
            for filename in os.listdir(download_dir):
                if filename_part in filename and not filename.endswith(".crdownload"):
                    logger.info(f"Download completed: {filename}")
                    return filename
        except Exception as e:
            logger.warning(f"Error checking download directory: {e}")
        
        time.sleep(1)
    
    logger.error(f"Download timeout after {timeout} seconds for '{filename_part}'")
    raise TimeoutError(f"Download did not complete in {timeout} seconds for '{filename_part}'")

def submit_request(driver, destination, depot, max_retries=3):
    """Submit inventory request with retry logic and comprehensive error handling"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Submitting inventory request for {destination} → {depot} (attempt {attempt + 1})")
            
            # Select district
            district_dropdown = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_Excise_district"))
            )
            Select(district_dropdown).select_by_visible_text(destination)
            time.sleep(2)
            
            # Wait for depot options to load
            WebDriverWait(driver, 15).until(
                lambda d: len(Select(
                    d.find_element(By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_warehouse")
                ).options) > 1
            )
            
            # Select depot
            warehouse_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ddl_warehouse"))
            warehouse_dropdown.select_by_visible_text(depot)
            time.sleep(2)
            
            # Wait for inventory grid to update
            grid_elem = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_GridView1"))
            )
            old_html = grid_elem.get_attribute('outerHTML')
            WebDriverWait(driver, 15).until(
                lambda d: d.find_element(By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_GridView1").get_attribute('outerHTML') != old_html
            )
            # Click PDF button
            pdf_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_TabContainer1_tab_war_ImgButton_WarehousePdf"))
            )
            pdf_button.click()
            time.sleep(5)
            logger.info(f"✅ Request submitted successfully for {destination} → {depot}")
            return True
            
        except Exception as e:
            logger.warning(f"Request attempt {attempt + 1} failed for {destination} → {depot}: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)  # Wait before retry
            else:
                logger.error(f"Failed to submit request for {destination} → {depot} after {max_retries} attempts")
                return False
    
    return False

def rename_file(download_dir, old_filename, depot):
    """Rename downloaded file with error handling"""
    try:
        src = os.path.join(download_dir, old_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = f"{timestamp}_{depot.replace(' ', '_')}"
        ext = os.path.splitext(old_filename)[1]
        dst = os.path.join(download_dir, f"{new_name}{ext}")
        
        if os.path.exists(src):
            shutil.move(src, dst)
            logger.info(f"File renamed: {old_filename} -> {new_name}{ext}")
            return True
        else:
            logger.error(f"Source file not found: {src}")
            return False
            
    except Exception as e:
        logger.error(f"Error renaming file {old_filename}: {e}")
        return False

def scrap_inventory(driver, download_dir):
    """Main inventory scraping function with comprehensive error handling"""
    try:
        logger.info("Starting inventory scraping...")
        
        # Load Excel data
        if not os.path.exists(excelpath):
            raise FileNotFoundError(f"Excel file not found: {excelpath}")
            
        df = pd.read_excel(excelpath)
        logger.info(f"Loaded {len(df)} district/warehouse entries from Excel")
        
        # Navigate to inventory section
        navigate(driver)
        
        success_count = 0
        failure_count = 0
        
        # Process each district/warehouse pair
        for index, row in df.iterrows():
            try:
                destination = row['District']
                depot = row['Warehouse Name']
                logger.info(f"Processing entry {index + 1}/{len(df)}: {destination} → {depot}")
                
                # Submit request
                if submit_request(driver, destination, depot):
                    try:
                        # Wait for download
                        filename = wait_for_download(download_dir, "WBSBCL_Inventory")
                        if filename:
                            # Rename file
                            if rename_file(download_dir, filename, depot):
                                success_count += 1
                                logger.info(f"✅ Successfully processed {destination} → {depot}")
                            else:
                                failure_count += 1
                                logger.error(f"❌ Failed to rename file for {destination} → {depot}")
                        else:
                            failure_count += 1
                            logger.warning(f"⚠️ No file downloaded for {destination} → {depot}")
                            
                    except TimeoutError:
                        failure_count += 1
                        logger.error(f"❌ Download timeout for {destination} → {depot}")
                        
                else:
                    failure_count += 1
                    logger.error(f"❌ Request submission failed for {destination} → {depot}")
                    
            except Exception as e:
                failure_count += 1
                logger.error(f"❌ Error processing {destination} → {depot}: {e}")
                continue
        
        logger.info(f"✅ Inventory scraping completed. Success: {success_count}, Failures: {failure_count}")
        
    except Exception as e:
        logger.error(f"❌ Inventory scraping failed: {e}")
        raise Exception(f"Inventory scraping failed: {str(e)}")

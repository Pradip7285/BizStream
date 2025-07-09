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
from datetime import datetime, date
import shutil

# Configure logging
logger = logging.getLogger(__name__)

LOG_FILENAME = "report.txt"
today = date.today().strftime("%d-%m-%Y") 
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "distict&warehouse.xlsx")

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

def navigate(driver):
    """Navigate to the invoice section with error handling"""
    try:
        logger.info("Navigating to invoice section...")
        
        # Click on the main menu button
        menu_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'ctl00_ImageButton11'))
        )
        menu_button.click()
        time.sleep(5)
        
        # Click on the invoice link
        invoice_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, 'ctl00_ContentPlaceHolder1_TabContainer1_Tab_BI_Module_grid_crop_suppl_ctl10_link_crop_supplier'))
        )
        invoice_link.click()
        time.sleep(10)
        
        logger.info("Successfully navigated to invoice section")
        
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        raise Exception(f"Failed to navigate to invoice section: {str(e)}")

def submit_request(driver, destination, date, max_retries=3):
    """Submit invoice request with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Submitting request for {destination} on {date.strftime('%d/%m/%Y')} (attempt {attempt + 1})")
            
            # Select warehouse
            warehouse_select = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_Warehouse"))
            )
            select = Select(warehouse_select)
            select.select_by_visible_text(destination)
            time.sleep(1)
            
            # Select date
            date_select = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddl_date"))
            )
            date_dropdown = Select(date_select)
            date_dropdown.select_by_visible_text(date.strftime('%d/%m/%Y'))
            time.sleep(1)
            
            # Wait for table to update
            table_elem = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_Grid_req"))
            )
            old_html = table_elem.get_attribute('outerHTML')
            # Click or trigger the event that loads new data if needed (if not automatic)
            # Wait for the table's HTML to change
            WebDriverWait(driver, 15).until(
                lambda d: d.find_element(By.ID, "ctl00_ContentPlaceHolder1_Grid_req").get_attribute('outerHTML') != old_html
            )
            # Now the table is updated
            # Click show button
            show_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btn_Show"))
            )
            show_button.click()
            time.sleep(5)
            
            logger.info(f"Request submitted successfully for {destination}")
            return True
            
        except Exception as e:
            logger.warning(f"Request submission attempt {attempt + 1} failed for {destination}: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)  # Wait before retry
            else:
                logger.error(f"Failed to submit request for {destination} after {max_retries} attempts")
                return False
    
    return False

def rename_file(download_dir, old_filename, new_name):
    """Rename downloaded file with error handling"""
    try:
        src = os.path.join(download_dir, old_filename)
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
        
def log_failure(destination, date, reason, download_dir):
    """Log failed operations"""
    try:
        log_path = os.path.join(download_dir, LOG_FILENAME)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_path, "a", encoding='utf-8') as f:
            f.write(f"[{timestamp}] {destination} - {reason}\n")
        logger.warning(f"Logged failure: {destination} - {reason}")
    except Exception as e:
        logger.error(f"Error logging failure: {e}")
        
def scrape_invoice(driver, download_dir, inputDate):
    """Main invoice scraping function with comprehensive error handling"""
    try:
        logger.info(f"Starting invoice scraping for date: {inputDate}")
        
        # Load Excel data
        if not os.path.exists(EXCEL_PATH):
            raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}")
            
        df = pd.read_excel(EXCEL_PATH)
        logger.info(f"Loaded {len(df)} warehouse entries from Excel")
        
        # Navigate to invoice section
        navigate(driver)
        
        # Wait for page to be ready
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Parse date
        parsed_date = datetime.strptime(inputDate, '%d-%m-%Y')
        date_obj = parsed_date
        
        success_count = 0
        failure_count = 0
        
        # Process each warehouse
        for index, row in df.iterrows():
            try:
                destination = row["Warehouse Name"]
                logger.info(f"Processing warehouse {index + 1}/{len(df)}: {destination}")
                
                # Submit request
                if submit_request(driver, destination, date_obj):
                    try:
                        # Wait for download
                        filename = wait_for_download(download_dir, "BEVCO_Invoice.pdf")
                        if filename:
                            # Rename file
                            if rename_file(download_dir, filename, destination.replace(" ", "_")):
                                success_count += 1
                                logger.info(f"✅ Successfully processed {destination}")
                            else:
                                log_failure(destination, date_obj, "File rename failed", download_dir)
                                failure_count += 1
                        else:
                            log_failure(destination, date_obj, "No file downloaded", download_dir)
                            failure_count += 1
                            logger.warning(f"⚠️ No file downloaded for {destination}")
                            
                    except TimeoutError:
                        log_failure(destination, date_obj, "Download timeout", download_dir)
                        failure_count += 1
                        logger.error(f"❌ Download timeout for {destination}")
                        
                else:
                    log_failure(destination, date_obj, "Request submission failed", download_dir)
                    failure_count += 1
                    logger.error(f"❌ Request submission failed for {destination}")
                    
            except Exception as e:
                log_failure(destination, date_obj, f"Processing error: {str(e)}", download_dir)
                failure_count += 1
                logger.error(f"❌ Error processing {destination}: {e}")
                continue
        
        logger.info(f"✅ Invoice scraping completed. Success: {success_count}, Failures: {failure_count}")
        return download_dir
        
    except Exception as e:
        logger.error(f"❌ Invoice scraping failed: {e}")
        raise Exception(f"Invoice scraping failed: {str(e)}")


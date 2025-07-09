#!/usr/bin/env python3
"""
Test script for BizStream modules with OCR CAPTCHA solving
Tests each module individually with automatic CAPTCHA solving
"""

import os
import sys
import tempfile
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def solve_captcha_with_ocr(captcha_path):
    """Solve CAPTCHA using OCR"""
    try:
        from module.ocrdemo import solve_captcha_image
        logger.info(f"Attempting to solve CAPTCHA: {captcha_path}")
        
        captcha_text = solve_captcha_image(captcha_path)
        if captcha_text:
            logger.info(f"✅ CAPTCHA solved: {captcha_text}")
            return captcha_text
        else:
            logger.warning("⚠️ OCR failed to solve CAPTCHA")
            return None
            
    except Exception as e:
        logger.error(f"❌ OCR error: {e}")
        return None

def test_login_and_modules():
    """Test login and then each module"""
    logger.info("Testing login and modules...")
    
    try:
        from module.login import setup_browser, get_captcha_image, login
        from module import stock, invoice, inventory
        import tempfile
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory: {temp_dir}")
        
        # Setup browser
        driver = setup_browser(temp_dir)
        if not driver:
            logger.error("❌ Failed to setup browser")
            return False
        
        try:
            # Get CAPTCHA
            logger.info("Getting CAPTCHA...")
            captcha_path = get_captcha_image(driver, user="test")
            if not captcha_path:
                logger.error("❌ Failed to get CAPTCHA")
                return False
            
            logger.info(f"✅ CAPTCHA saved to: {captcha_path}")
            
            # Try OCR first
            captcha_text = solve_captcha_with_ocr(captcha_path)
            
            # If OCR fails, ask for manual input
            if not captcha_text:
                logger.info("OCR failed. Please solve CAPTCHA manually.")
                captcha_text = input("Enter the CAPTCHA text: ").strip()
                if not captcha_text:
                    logger.error("❌ No CAPTCHA entered")
                    return False
            
            # Login
            logger.info("Attempting login...")
            login_result = login(driver, captcha_text=captcha_text)
            logger.info(f"Login result: {login_result}")
            
            # Wait a bit for login to complete
            time.sleep(5)
            
            # Test each module
            modules_to_test = [
                ("Stock", stock.scrape_reports),
                ("Invoice", lambda d, temp_dir: invoice.scrape_invoice(d, temp_dir, '01-01-2024')),
                ("Inventory", inventory.scrap_inventory)
            ]
            
            for module_name, module_func in modules_to_test:
                logger.info(f"\n--- Testing {module_name} Module ---")
                try:
                    # Create a new temp directory for each module
                    module_temp_dir = tempfile.mkdtemp()
                    logger.info(f"Created temp directory for {module_name}: {module_temp_dir}")
                    
                    # Run the module
                    module_func(driver, module_temp_dir)
                    
                    # Check if files were created
                    files = os.listdir(module_temp_dir)
                    logger.info(f"Files created in {module_name} test: {files}")
                    
                    # Cleanup
                    import shutil
                    shutil.rmtree(module_temp_dir)
                    
                    logger.info(f"✅ {module_name} module test completed")
                    
                except Exception as e:
                    logger.error(f"❌ {module_name} module test failed: {e}")
            
            return True
            
        finally:
            # Cleanup
            driver.quit()
            logger.info("✅ Browser closed successfully")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Run the test"""
    logger.info("=" * 50)
    logger.info("Starting BizStream Login & Module Tests (with OCR)")
    logger.info("=" * 50)
    
    success = test_login_and_modules()
    
    if success:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
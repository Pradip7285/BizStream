#!/usr/bin/env python3
"""
Test script for BizStream modules
Tests each module individually to verify functionality
"""

import os
import sys
import tempfile
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_module_imports():
    """Test if all modules can be imported successfully"""
    logger.info("Testing module imports...")
    
    try:
        from module import stock
        logger.info("✅ Stock module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import stock module: {e}")
        return False
    
    try:
        from module import invoice
        logger.info("✅ Invoice module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import invoice module: {e}")
        return False
    
    try:
        from module import inventory
        logger.info("✅ Inventory module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import inventory module: {e}")
        return False
    
    try:
        from module import login
        logger.info("✅ Login module imported successfully")
    except Exception as e:
        logger.error(f"❌ Failed to import login module: {e}")
        return False
    
    return True

def test_excel_files():
    """Test if Excel files can be read"""
    logger.info("Testing Excel file reading...")
    
    try:
        import pandas as pd
        
        # Test district & warehouse file
        df_district = pd.read_excel('module/distict&warehouse.xlsx')
        logger.info(f"✅ District & Warehouse file: {len(df_district)} rows")
        
        # Test depot file
        df_depot = pd.read_excel('module/Depot.xlsx')
        logger.info(f"✅ Depot file: {len(df_depot)} rows")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to read Excel files: {e}")
        return False

def test_browser_setup():
    """Test browser setup without actual scraping"""
    logger.info("Testing browser setup...")
    
    try:
        from module.login import setup_browser
        import tempfile
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory: {temp_dir}")
        
        # Setup browser
        driver = setup_browser(temp_dir)
        if driver:
            logger.info("✅ Browser setup successful")
            driver.quit()
            logger.info("✅ Browser closed successfully")
            return True
        else:
            logger.error("❌ Browser setup failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Browser setup test failed: {e}")
        return False

def test_stock_module():
    """Test stock module functionality"""
    logger.info("Testing stock module...")
    
    try:
        from module import stock
        from module.login import setup_browser
        import tempfile
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory for stock test: {temp_dir}")
        
        # Setup browser
        driver = setup_browser(temp_dir)
        if not driver:
            logger.error("❌ Failed to setup browser for stock test")
            return False
        
        # Test stock scraping
        stock.scrape_reports(driver, temp_dir)
        
        # Check if files were created
        files = os.listdir(temp_dir)
        logger.info(f"Files created in stock test: {files}")
        
        # Cleanup
        driver.quit()
        import shutil
        shutil.rmtree(temp_dir)
        
        logger.info("✅ Stock module test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Stock module test failed: {e}")
        return False

def test_invoice_module():
    """Test invoice module functionality"""
    logger.info("Testing invoice module...")
    
    try:
        from module import invoice
        from module.login import setup_browser
        import tempfile
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory for invoice test: {temp_dir}")
        
        # Setup browser
        driver = setup_browser(temp_dir)
        if not driver:
            logger.error("❌ Failed to setup browser for invoice test")
            return False
        
        # Test invoice scraping
        invoice.scrape_invoice(driver, temp_dir, '01-01-2024')
        
        # Check if files were created
        files = os.listdir(temp_dir)
        logger.info(f"Files created in invoice test: {files}")
        
        # Cleanup
        driver.quit()
        import shutil
        shutil.rmtree(temp_dir)
        
        logger.info("✅ Invoice module test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Invoice module test failed: {e}")
        return False

def test_inventory_module():
    """Test inventory module functionality"""
    logger.info("Testing inventory module...")
    
    try:
        from module import inventory
        from module.login import setup_browser
        import tempfile
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temp directory for inventory test: {temp_dir}")
        
        # Setup browser
        driver = setup_browser(temp_dir)
        if not driver:
            logger.error("❌ Failed to setup browser for inventory test")
            return False
        
        # Test inventory scraping
        inventory.scrap_inventory(driver, temp_dir)
        
        # Check if files were created
        files = os.listdir(temp_dir)
        logger.info(f"Files created in inventory test: {files}")
        
        # Cleanup
        driver.quit()
        import shutil
        shutil.rmtree(temp_dir)
        
        logger.info("✅ Inventory module test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Inventory module test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 50)
    logger.info("Starting BizStream Module Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Module Imports", test_module_imports),
        ("Excel Files", test_excel_files),
        ("Browser Setup", test_browser_setup),
        ("Stock Module", test_stock_module),
        ("Invoice Module", test_invoice_module),
        ("Inventory Module", test_inventory_module),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
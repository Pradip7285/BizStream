from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import pytesseract
import os
import cv2
import numpy as np
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(path):
    """Enhanced image preprocessing for better OCR results"""
    try:
        # Open image and convert to numpy array for OpenCV processing
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        
        # Apply adaptive thresholding
        img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
        
        # Remove noise
        kernel = np.ones((2, 2), np.uint8)
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        
        # Convert back to PIL Image for Tesseract
        img = Image.fromarray(img)
        
        # Resize for better recognition
        img = img.resize((img.width * 3, img.height * 3), Image.BICUBIC)
        
        # Sharpening
        img = img.filter(ImageFilter.SHARPEN)
        
        return img
    except Exception as e:
        print(f"Error during image preprocessing: {e}")
        return Image.open(path).convert("L")  # Fallback to simple conversion

def solve_captcha_image(path="captcha.png", max_attempts=3):
    """Improved CAPTCHA solving with multiple attempts and validation"""
    for attempt in range(max_attempts):
        try:
            img = preprocess_image(path)
            
            # Try different configurations
            configs = [
                '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789',
                '--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789',
                '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            ]
            
            best_text = ""
            best_confidence = 0
            
            for config in configs:
                data = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
                
                # Get text with highest confidence
                for i, conf in enumerate(data['conf']):
                    if int(conf) > best_confidence and data['text'][i].strip():
                        best_confidence = int(conf)
                        best_text = data['text'][i].strip()
            
            print(f"🔍 Attempt {attempt + 1}: Extracted CAPTCHA: {repr(best_text)} (confidence: {best_confidence})")
            
            # Validate result (assuming CAPTCHA is numeric and 4-6 digits)
            if best_text.isdigit() and 0 <= len(best_text) <= 6:
                return best_text
                
            # If not valid, try different preprocessing
            if attempt == 1:
                print("⚠ Trying alternative preprocessing...")
                img = Image.open(path).convert("L")
                img = ImageOps.invert(img)
                img = img.filter(ImageFilter.MedianFilter(size=3))
                
        except Exception as e:
            print(f"⚠ Attempt {attempt + 1} failed: {str(e)}")
    
    print("❌ Failed to solve CAPTCHA after multiple attempts")
    return ""

def solve_captcha(driver, element_id="Image1"):
    """Screenshot and solve CAPTCHA from web element"""
    try:
        # Ensure directory exists
        os.makedirs("captchas", exist_ok=True)
        timestamp = int(time.time())
        path = f"captchas/captcha_{timestamp}.png"
        
        # Take screenshot of CAPTCHA element
        driver.find_element(By.ID, element_id).screenshot(path)
        
        # Solve CAPTCHA
        return solve_captcha_image(path)
    except Exception as e:
        print(f"Error solving CAPTCHA: {str(e)}")
        return ""
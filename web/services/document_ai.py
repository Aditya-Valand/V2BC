import cv2
import pytesseract
import re
from PIL import Image
import numpy as np

class DocumentAI:
    def __init__(self, tesseract_path=None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def preprocess_image(self, image_path):
        """Clean the image to improve OCR accuracy for various invoice types."""
        # Load image with OpenCV
        img = cv2.imread(image_path)
        
        # 1. Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Denoise and sharpen
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 3. Thresholding (Binarization) to make text pop
        # Uses Otsu's method to automatically find the best threshold
        thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        return thresh

    def extract_data(self, image_path):
        """Main pipeline to extract structured data from any invoice image."""
        processed_img = self.preprocess_image(image_path)
        
        # Perform OCR
        # PSM 6: Assume a single uniform block of text
        raw_text = pytesseract.image_to_string(processed_img, config='--psm 6')
        
        return self.parse_text(raw_text)

    def parse_text(self, text):
        """Uses regex patterns to find fields across different invoice formats."""
        data = {
            "vendor_name": "Unknown",
            "date": None,
            "total_amount": 0.0,
            "gstin": None,
            "invoice_number": None
        }

        # 1. Extract GSTIN (15-digit Indian format)
        gstin_pattern = r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}'
        gstin_match = re.search(gstin_pattern, text)
        if gstin_match:
            data["gstin"] = gstin_match.group(0)

        # 2. Extract Total Amount
        # Looks for keywords like Total, Amount, Payable, Net followed by a number
        amount_pattern = r'(?:TOTAL|AMOUNT|PAYABLE|NET|GRAND TOTAL)\s*[:\-\s]*[₹Rs\.]*\s*([\d,]+\.?\d*)'
        amounts = re.findall(amount_pattern, text, re.IGNORECASE)
        if amounts:
            # Take the largest numeric value found near "Total" keywords
            data["total_amount"] = max([float(a.replace(',', '')) for a in amounts])

        # 3. Extract Date (Handles DD/MM/YY, DD-MM-YYYY, etc.)
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        date_match = re.search(date_pattern, text)
        if date_match:
            data["date"] = date_match.group(1)

        # 4. Vendor Name (Heuristic: usually the first non-numeric line)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            data["vendor_name"] = lines[0]

        return data

# Usage Example:
# ai = DocumentAI()
# result = ai.extract_data('path/to/invoice.jpg')
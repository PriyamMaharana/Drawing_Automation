import os
import pytesseract
from pytesseract import Output
import numpy as np
import logging

logger = logging.getLogger(__name__) 

try:
    from core.utils.settings import PlatformSettings
    from core.dictionaries.ocr_autocorrect import OCRAutoCorrect
except ImportError as e:
    logger.error(f"Microservices import failure: {e}")

if os.name == 'nt':
    if PlatformSettings.TESSERACT_CMD.exists():
        pytesseract.pytesseract.tesseract_cmd = str(PlatformSettings.TESSERACT_CMD)
    else:
        fallback_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(fallback_path):
            pytesseract.pytesseract.tesseract_cmd = fallback_path

class TesseractEngine:
    def extract_text(self, image: np.ndarray) -> list:
        results = []
        
        whitelist = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,-+()[]Ø±°⌀⌖↗⌰⟂∥∠▱⌭⌓⌒ⓂⓁⓈ⌯◎─○⌴⌵↧'
        custom_config = f'--oem 3 --psm 11 -c tessedit_char_whitelist="{whitelist}"'

        try:
            d = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
            n_boxes = len(d['text'])
            
            for i in range(n_boxes):
                if int(d['conf'][i]) > PlatformSettings.OCR_MIN_CONFIDENCE: 
                    raw_text = d['text'][i].strip()
                    
                    if len(raw_text) > 0:
                        corrected_text = OCRAutoCorrect.clean_text(raw_text)
                        
                        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
                        results.append({"text": corrected_text, "bbox": [x, y, x + w, y + h]})
                        
                        if raw_text != corrected_text:
                            logger.info(f"🛠️ GD&T Auto-Corrected: '{raw_text}' -> '{corrected_text}'")
                            
        except Exception as e:
            logger.error(f"OCR Engine failed: {e}")
        
        return results
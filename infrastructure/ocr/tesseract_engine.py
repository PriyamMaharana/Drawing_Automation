import os
import pytesseract
from pytesseract import Output
import numpy as np
import logging

logger = logging.getLogger(__name__) 

try:
    from core.utils.settings import PlatformSettings
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
        try:
            d = pytesseract.image_to_data(image, output_type=Output.DICT)
            n_boxes = len(d['text'])
            
            for i in range(n_boxes):
                if int(d['conf'][i]) > PlatformSettings.OCR_MIN_CONFIDENCE: 
                    text = d['text'][i].strip()
                    if len(text) > 0:
                        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
                        results.append({"text": text, "bbox": [x, y, x + w, y + h]})
        except Exception as e:
            logger.error(f"OCR Engine failed: {e}")
        
        return results
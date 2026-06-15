import pytesseract
import logging
from pathlib import Path

try:
    from infrastructure.ocr.image_processor import prepare_for_ocr
except ImportError as e:
    logging.error(f"Unable to import microservices: {e}")
    
# Point to your local Tesseract binary
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TESSERACT_PATH = BASE_DIR / "bin" / "Tesseract-OCR" / "tesseract.exe"

logging.debug(f"Looking for Tesseract at: {TESSERACT_PATH}")
logging.debug(f"Tesseract exists? {TESSERACT_PATH.exists()}")

if TESSERACT_PATH.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)
else:
    print("WARNING: Tesseract not found! Check your folder structure.")


def run_ocr(image_bytes, debug_name="ocr_feed.png"):
    if not TESSERACT_PATH.exists():
        logging.error("OCR Skipped: Tesseract executable not found.")
        return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}

    # Pass the name down to the processor
    processed_img = prepare_for_ocr(image_bytes, debug_name=debug_name)
    
    custom_config = r'--oem 3 --psm 11' 
    data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=custom_config)
    
    return data


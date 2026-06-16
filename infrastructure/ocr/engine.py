import pytesseract
import logging
from pathlib import Path

try:
    from infrastructure.ocr.image_processor import prepare_for_ocr
    from rules.cad_dictionary import CADSignatures
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    
# Point to your local Tesseract binary
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TESSERACT_PATH = BASE_DIR / "bin" / "Tesseract-OCR" / "tesseract.exe"

logging.debug(f"Looking for Tesseract at: {TESSERACT_PATH}")
logging.debug(f"Tesseract exists? {TESSERACT_PATH.exists()}")

if TESSERACT_PATH.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)
else:
    logging.warning("WARNING: Tesseract not found! Check your folder structure.")


def get_dynamic_whitelist() -> str:
    base_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.:,-()°/+\"' "
    raw_regex = CADSignatures.SYMBOLS.pattern
    cad_symbols = raw_regex.replace('[', '').replace(']', '').replace('\\', '')
    
    return "".join(set(base_chars + cad_symbols))

def run_ocr(image_bytes, debug_name="ocr_feed.png"):
    if not TESSERACT_PATH.exists():
        logging.error("OCR Skipped: Tesseract executable not found.")
        return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}

    # Pass the name down to the processor
    processed_img = prepare_for_ocr(image_bytes, debug_name=debug_name)
    
    whitelist = get_dynamic_whitelist()
    custom_config = fr'-c tessedit_char_whitelist="{whitelist}" --oem 3 --psm 11' 
    
    raw_data = pytesseract.image_to_data(
        processed_img,
        output_type=pytesseract.Output.DICT, 
        config=custom_config
    )
    
    clean_data = {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    
    for i in range(len(raw_data["text"])):
        text = raw_data["text"][i].strip()
        
        if not raw_data["conf"][i]:
            continue
        
        conf = float(raw_data["conf"][i])
        
        # If the text is not empty AND the AI is more than 30% confident
        if text and (conf > 30.0 or conf == -1): 
            clean_data["text"].append(text)
            clean_data["conf"].append(conf)
            clean_data["left"].append(raw_data["left"][i])
            clean_data["top"].append(raw_data["top"][i])
            clean_data["width"].append(raw_data["width"][i])
            clean_data["height"].append(raw_data["height"][i])

    return clean_data



import sys
import subprocess
import logging
import cv2
import numpy as np
from pathlib  import Path

def ensure_package(pip_name: str, import_name: str):
    try:
        __import__(import_name)
    except ImportError:
        logging.warning(f"Package '{import_name}' not found. Installing '{pip_name}'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            logging.info(f"Successfully installed {pip_name}.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install {pip_name}. Please install manually.", exc_info=True)
            sys.exit(1)

ensure_package("opencv-python", "cv2")
ensure_package("numpy", "numpy")


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEBUG_DIR = PROJECT_ROOT / "debug" / "crops"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

def prepare_for_ocr(image_bytes, debug_name="ocr_feed.png", save_debug=False):
    """
    Production-hardened OCR pre-processing.
    Uses Otsu's binarization for superior CAD text isolation.
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Upscale (Crucial for small engineering text)
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 3. Thresholding (Otsu's for high contrast)
    _, thresh = cv2.threshold(resized, 220, 255, cv2.THRESH_BINARY)
    
    # 4. Morphological Opening (the noise eraser)
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    # cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    if save_debug:
        debug_path = DEBUG_DIR / debug_name
        cv2.imwrite(str(debug_path), thresh)
        logging.info(f"Saved OCR feed diagnostic to: {debug_path.name}")
    
    # return cleaned
    return thresh


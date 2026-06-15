import sys
import subprocess
import logging
from pathlib  import Path

def ensure_package(pip_name: str, import_name: str):
    """Attempts to import a package, and installs it via pip if missing."""
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

import cv2
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEBUG_DIR = PROJECT_ROOT / "debug" / "crops"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

def prepare_for_ocr(image_bytes, debug_name="ocr_feed.png"):
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Upscale (Crucial for small engineering text)
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 3. Thresholding (Otsu's for high contrast)
    thresh = cv2.adaptiveThreshold(
        resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 31, 2
    )
    
    debug_path = DEBUG_DIR / debug_name
    cv2.imwrite(str(debug_path), thresh)
    logging.info(f"Saved OCR feed diagnostic to: {debug_path.name}")
    
    return thresh


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

logger = logging.getLogger(__name__)

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEBUG_DIR = PROJECT_ROOT / "debug" / "crops"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
   
    
class ImageProcessor2:
    def standardize_for_ocr(self, img_bytes: bytes, debug_path: str = None) -> np.ndarray:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        _, binary_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        if debug_path:
            cv2.imwrite(debug_path, binary_img)
            
        return binary_img


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

def normalize_image(image_bytes: bytes) -> np.ndarray:
    """
    The Normalization Preamble.
    Forces ANY wild client upload into a predictable baseline:
    No transparency, standard size, and strictly black-on-white.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    
    # 1. Read with Unchanged channels (Catches Alpha/Transparency)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("OpenCV could not decode the image bytes.")

    # 2. Kill Transparency (Force Alpha to White)
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha_channel = img[:, :, 3]
        rgb_channels = img[:, :, :3]
        
        # Create a white background
        white_bg = np.ones_like(rgb_channels, dtype=np.uint8) * 255
        
        # Blend the image onto the white background using the alpha mask
        alpha_factor = alpha_channel[:, :, np.newaxis].astype(np.float32) / 255.0
        img = (rgb_channels * alpha_factor + white_bg * (1 - alpha_factor)).astype(np.uint8)

    # 3. Convert to Standard Grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 4. Inversion Defense (Dark Mode to Light Mode)
    median_intensity = np.median(gray)
    if median_intensity < 127:
        gray = cv2.bitwise_not(gray)

    # 5. Size Clamping (Prevent kernel math from breaking on 8K or 144p images)
    target_width = 2000
    h, w = gray.shape
    if w > 3000 or w < 800:
        scale_ratio = target_width / w
        gray = cv2.resize(gray, None, fx=scale_ratio, fy=scale_ratio, interpolation=cv2.INTER_AREA)

    return gray

def prepare_for_ocr(image_bytes, debug_name="ocr_feed.png", save_debug=False):
    """
    Production-hardened OCR pre-processing.
    Uses Otsu's binarization for superior CAD text isolation.
    Strategy: Fix Pixels -> Upscale -> Sharpen -> Smart Binarize.
    """
    gray = normalize_image(image_bytes)
    
    paper_brightness = np.percentile(gray, 90)
    
    pixels = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    upscaled = cv2.resize(pixels, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
    
    if paper_brightness > 240:
        _, final_img = cv2.threshold(upscaled, 200, 255, cv2.THRESH_BINARY)
    else:
        sharpen_kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])
        sharpened = cv2.filter2D(upscaled, -1, sharpen_kernel)
        
        thresh = cv2.adaptiveThreshold(
            sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 35, 12   
        )
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        final_img = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
    if save_debug:
        debug_path = DEBUG_DIR / debug_name
        cv2.imwrite(str(debug_path), final_img)
        
    return final_img
    
    
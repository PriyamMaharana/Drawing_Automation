import cv2
import numpy as np
import logging
from typing import List

logger = logging.getLogger(__name__)

class TableDetector:
    """
    Layer 4.1: Table & Annotation Isolation
    Uses OpenCV morphological operations to detect continuous grids (BOMs, Revision Tables).
    Outputs bounding boxes of tables so the OCR engine can quarantine/ignore them.
    """
    
    @staticmethod
    def detect_tables(image_array: np.ndarray) -> List[List[int]]:
        logger.info("Scanning for BOM/Revision Tables...")
        quarantine_zones = []
        
        try:
            # 1. Grayscale and Binary Inverse
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_array
                
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

            # 2. Define kernels to detect horizontal and vertical lines
            # Length of kernel defines how long a line must be to be considered a "Table Border"
            kernel_length = np.array(binary).shape[1] // 80
            vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
            hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))

            # 3. Detect Lines
            img_vh = cv2.erode(binary, vert_kernel, iterations=3)
            vert_lines = cv2.dilate(img_vh, vert_kernel, iterations=3)

            img_hh = cv2.erode(binary, hori_kernel, iterations=3)
            hori_lines = cv2.dilate(img_hh, hori_kernel, iterations=3)

            # 4. Combine lines into a grid mask
            grid_mask = cv2.addWeighted(vert_lines, 0.5, hori_lines, 0.5, 0.0)
            _, grid_mask = cv2.threshold(grid_mask, 50, 255, cv2.THRESH_BINARY)

            # 5. Find Grid Contours
            contours, _ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                
                # If the grid is large enough to be a BOM or Note Table
                if area > 10000:  
                    quarantine_zones.append([x, y, x + w, y + h])
                    logger.debug(f"Table Detected at [x:{x}, y:{y}, w:{w}, h:{h}]. Flagged for quarantine.")

            return quarantine_zones

        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return []
        
import cv2
import numpy as np
import logging

try:
    from core.utils.settings import app_settings 
except ImportError:
    OCR_DENSITY_LOWER_BOUND = 0.005
    OCR_DENSITY_UPPER_BOUND = 0.60
    HEALTH_SCORE_ACCEPT = 50.0
    HEALTH_SCORE_OPTIMAL = 80.0

logger = logging.getLogger(__name__)

class ZoneHealthValidator:
    @staticmethod
    def evaluate_zone(image_crop: np.ndarray) -> dict:
        """
        Evaluates the health of a drawn Green Zone to prevent user error.
        Returns a dictionary with 'score' (0-100) and 'status' (HEALTHY, WARNING, REJECT).
        """
        OCR_DENSITY_LOWER_BOUND = app_settings.OCR_DENSITY_LOWER_BOUND, 
        OCR_DENSITY_UPPER_BOUND = app_settings.OCR_DENSITY_UPPER_BOUND, 
        HEALTH_SCORE_ACCEPT = app_settings.HEALTH_SCORE_ACCEPT,
        HEALTH_SCORE_OPTIMAL = app_settings.HEALTH_SCORE_OPTIMAL
        
        try:
            # 1. Convert to grayscale and apply binary thresholding
            gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            total_pixels = binary.shape[0] * binary.shape[1]
            if total_pixels == 0:
                return {"score": 0, "status": "REJECT", "reason": "Empty Zone"}

            # 2. Geometry Density Check (Ink ratio)
            ink_pixels = cv2.countNonZero(binary)
            density_ratio = ink_pixels / total_pixels
            
            # 3. Find Contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            score = 100.0
            reasons = []

            # Penalty: Blank or extremely sparse zone
            if density_ratio < OCR_DENSITY_LOWER_BOUND:
                score -= 60
                reasons.append(f"Extremely sparse ink density (Ratio: {density_ratio:.4f}) - Blank zone?")
            
            # Penalty: Massive ink blob (User selected a solid black region/image instead of drawing)
            elif density_ratio > OCR_DENSITY_UPPER_BOUND:
                score -= 60
                reasons.append(f"Unusually high ink density (Ratio: {density_ratio:.4f}) - Solid block?")

            # Status assignment
            status = "HEALTHY"
            if score < HEALTH_SCORE_ACCEPT:
                status = "REJECT"
            elif score < HEALTH_SCORE_OPTIMAL:
                status = "WARNING"

            logger.debug(f"Zone Health Score: {score} | Density: {density_ratio:.4f} | Contours: {len(contours)}")
            return {
                "score": max(0.0, score), 
                "status": status, 
                "reason": " | ".join(reasons) if reasons else "Optimal Zone Density"
            }
            
        except Exception as e:
            logger.error(f"Zone validation failed: {e}")
            return {"score": 100, "status": "WARNING", "reason": "Validation Skipped"} # Fail open
        
        
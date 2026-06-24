import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ZoneHealthValidator:
    @staticmethod
    def evaluate_zone(image_crop: np.ndarray) -> dict:
        """
        Evaluates the health of a drawn Green Zone to prevent user error.
        Returns a dictionary with 'score' (0-100) and 'status' (HEALTHY, WARNING, REJECT).
        """
        try:
            # 1. Convert to grayscale and apply binary thresholding
            gray = cv2.cvtColor(image_crop, cv2.COLOR_BGR2GRAY)
            # Use Otsu's thresholding to isolate ink from background
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            total_pixels = binary.shape[0] * binary.shape[1]
            if total_pixels == 0:
                return {"score": 0, "status": "REJECT", "reason": "Empty Zone"}

            # 2. Geometry Density Check (Ink ratio)
            ink_pixels = cv2.countNonZero(binary)
            density_ratio = ink_pixels / total_pixels
            
            # 3. Find Contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            score = 100
            reasons = []

            # Penalty: Blank or extremely sparse zone
            if density_ratio < 0.005:  # Less than 0.5% ink
                score -= 60
                reasons.append("Extremely sparse ink density (Blank zone?)")
            
            # Penalty: Massive ink blob (User selected a solid black region/image instead of drawing)
            elif density_ratio > 0.60:
                score -= 60
                reasons.append("Unusually high ink density (Solid block?)")

            # Status assignment
            status = "HEALTHY"
            if score < 50:
                status = "REJECT"
            elif score < 80:
                status = "WARNING"

            logger.debug(f"Zone Health Score: {score} | Density: {density_ratio:.4f} | Contours: {len(contours)}")
            return {"score": max(0, score), "status": status, "reason": " | ".join(reasons)}
            
        except Exception as e:
            logger.error(f"Zone validation failed: {e}")
            return {"score": 100, "status": "HEALTHY", "reason": "Validation Skipped"} # Fail open
        
        
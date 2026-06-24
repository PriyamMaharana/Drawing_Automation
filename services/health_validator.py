import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class GreenZoneValidator:
    """
    Layer 3.6: Green Zone Health Validator
    Calculates a Health Score (0-100) for a specific rectangular zone on a document.
    """
    def __init__(self):
        pass

    def calculate_health_score(self, image: np.ndarray) -> dict:
        """
        Receives an OpenCV image (numpy array) representing the crop of the 'Green Zone'.
        Returns a dictionary with the score and components.
        """
        if image is None or image.size == 0:
            logger.warning("Zone Rejected (Score < 50): Empty image provided.")
            return {"score": 0, "status": "REJECTED", "details": "Empty image"}

        # Convert to grayscale if it's not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 1. Geometry Density (ink to whitespace ratio)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        ink_pixels = cv2.countNonZero(thresh)
        total_pixels = gray.shape[0] * gray.shape[1]
        
        ink_ratio = ink_pixels / total_pixels if total_pixels > 0 else 0
        
        # 2. Text Density / Contour extraction
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find potential text-like contours (small-medium size) vs geometry (long/large)
        text_contours = 0
        geometry_contours = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 5 < area < 1000:
                text_contours += 1
            elif area >= 1000:
                geometry_contours += 1

        # Calculate base score (starting at 100)
        score = 100.0
        
        # Deductions
        if ink_ratio < 0.01:
            score -= 40 # Too blank
        elif ink_ratio > 0.50:
            score -= 50 # Too dense (probably an image block or heavily shaded region)

        if text_contours == 0 and geometry_contours == 0:
            score -= 50 # No useful information

        # 3. Boundary Intersections (simplified heuristic: how many contours touch the edges)
        h, w = gray.shape
        edge_touches = 0
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if x <= 1 or y <= 1 or (x + cw) >= w - 1 or (y + ch) >= h - 1:
                edge_touches += 1

        # If many things cross the green line, the zone might be poorly placed
        if edge_touches > 5:
            score -= (edge_touches * 2) 

        score = max(0.0, min(100.0, score))
        
        status = "ACCEPTED" if score >= 50 else "REJECTED"
        
        metrics = {
            "score": round(score, 1),
            "status": status,
            "metrics": {
                "ink_ratio": round(ink_ratio, 4),
                "text_contours": text_contours,
                "geometry_contours": geometry_contours,
                "edge_touches": edge_touches
            }
        }
        
        logger.debug(f"Zone Health Score metrics: {metrics}")
        if status == "REJECTED":
            logger.warning(f"Zone Rejected (Score < 50): Score was {score}")

        return metrics

import cv2
import logging
import numpy as np
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GeometricViewFinder:
    """
    Enterprise View Isolator (Core Vision Algorithm).
    Uses a Pure Raster-CV approach to shrink-wrap high-signal geometry,
    physically obliterating page borders and text notes before clustering.
    """
    def __init__(self, cluster_tolerance: float = 20.0):
        self.cluster_tolerance = cluster_tolerance 
        self.view_label_pattern = re.compile(
            r"(SECTION|SEC\.?|DETAIL|DET\.?|VIEW)\s*[A-Z0-9-]*", 
            re.IGNORECASE
        )

    def isolate_views(self, vector_page, semantic_lines: list, raw_image_bytes: bytes, spatial_zones: dict, image_dpi: int) -> List[dict]:
        logger.info("Initializing Core Geometric View Finder (Pure Raster Engine)...")
        raw_clusters = self._precision_raster_extraction(raw_image_bytes, spatial_zones, image_dpi, semantic_lines)

        labeled_views = []
        unlabeled_counter = 1 

        for cluster_box in raw_clusters:
            view_data = {
                "view_name": None,
                "bounding_box": cluster_box,
                "contained_text": []
            }
            
            for line in semantic_lines:
                bbox = line.get("bbox")
                if not bbox: continue                
                if self._is_in_exclusion_zone(bbox, spatial_zones): continue  
                                   
                if self._is_inside_or_near(bbox, cluster_box, margin=30):
                    view_data["contained_text"].append(line)
                    
                    if view_data["view_name"] is None:
                        text_val = line.get("text", "").upper()
                        match = self.view_label_pattern.search(text_val)
                        if match: view_data["view_name"] = match.group(0).strip()
            
            if view_data["view_name"] is None:
                view_data["view_name"] = f"UNLABELED_VIEW_{unlabeled_counter}"
                unlabeled_counter += 1    
            labeled_views.append(view_data)

        logger.info(f"Geometric View Finder Complete. Carved {len(labeled_views)} tightly wrapped views.")
        return labeled_views

    def _precision_raster_extraction(self, raw_image_bytes: bytes, spatial_zones: dict, image_dpi: int, semantic_lines: list) -> list:
        if not raw_image_bytes: return []
        nparr = np.frombuffer(raw_image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None: return []
        
        img_h, img_w = img.shape
        scale = image_dpi / 72.0
        _, binary = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)
        
        margin_x = int(img_w * 0.04)
        margin_y = int(img_h * 0.04)        
        cv2.rectangle(binary, (0, 0), (img_w, margin_y), 0, -1) 
        cv2.rectangle(binary, (0, img_h - margin_y), (img_w, img_h), 0, -1) 
        cv2.rectangle(binary, (0, 0), (margin_x, img_h), 0, -1) 
        cv2.rectangle(binary, (img_w - margin_x, 0), (img_w, img_h), 0, -1) 

        if spatial_zones:
            exclusion_rects = []
            if spatial_zones.get("TITLE_BLOCK"): 
                exclusion_rects.append(spatial_zones["TITLE_BLOCK"].get("rect_pdf"))
            for table in spatial_zones.get("TABLES", []): 
                exclusion_rects.append(table.get("rect_pdf"))
            for rect in exclusion_rects:
                if rect:
                    x0, y0 = int(rect[0] * scale), int(rect[1] * scale)
                    x1, y1 = int(rect[2] * scale), int(rect[3] * scale)
                    cv2.rectangle(binary, (x0, y0), (x1, y1), 0, -1)

        for line in semantic_lines:
            bbox = line.get("bbox")
            if bbox:
                x0, y0 = int(bbox[0] * scale), int(bbox[1] * scale)
                x1, y1 = int(bbox[2] * scale), int(bbox[3] * scale)
                cv2.rectangle(binary, (x0-4, y0-4), (x1+4, y1+4), 0, -1)

        kernel_size = int(0.15 * image_dpi) 
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        dilated = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rects_pdf = []
        page_area = img_w * img_h
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            if area < (page_area * 0.005) or area > (page_area * 0.85): continue
            if w / h > 12 or h / w > 12: continue    
            rects_pdf.append([
                x / scale, 
                y / scale, 
                (x + w) / scale, 
                (y + h) / scale
            ])

        return self._merge_rectangles(rects_pdf, self.cluster_tolerance)

    # ---------------------------------------------------------
    # UTILITIES
    # ---------------------------------------------------------
    def _is_in_exclusion_zone(self, bbox: List[float], spatial_zones: dict) -> bool:
        if not spatial_zones: return False
        exclusion_rects = []
        if spatial_zones.get("TITLE_BLOCK"): exclusion_rects.append(spatial_zones["TITLE_BLOCK"].get("rect_pdf"))
        for table in spatial_zones.get("TABLES", []): exclusion_rects.append(table.get("rect_pdf"))
        for rect in exclusion_rects:
            if rect and self._is_inside_or_near(bbox, rect, margin=5): return True
        return False

    def _merge_rectangles(self, rects: list, tolerance: float) -> list:
        if not rects: return []
        expanded = [[r[0]-tolerance, r[1]-tolerance, r[2]+tolerance, r[3]+tolerance] for r in rects]
        changed = True
        while changed:
            changed = False
            merged = []
            consumed = [False] * len(expanded)
            for i in range(len(expanded)):
                if consumed[i]: continue
                current = list(expanded[i])
                for j in range(i + 1, len(expanded)):
                    if consumed[j]: continue
                    other = expanded[j]
                    if not (current[2] < other[0] or current[0] > other[2] or current[3] < other[1] or current[1] > other[3]):
                        current[0] = min(current[0], other[0])
                        current[1] = min(current[1], other[1])
                        current[2] = max(current[2], other[2])
                        current[3] = max(current[3], other[3])
                        consumed[j] = True
                        changed = True
                merged.append(current)
                consumed[i] = True
            expanded = merged
        return [[r[0]+tolerance, r[1]+tolerance, r[2]-tolerance, r[3]-tolerance] for r in expanded]

    def _is_inside_or_near(self, inner_box: List[float], outer_box: List[float], margin: float = 0) -> bool:
        return (
            inner_box[0] >= outer_box[0] - margin and 
            inner_box[1] >= outer_box[1] - margin and
            inner_box[2] <= outer_box[2] + margin and 
            inner_box[3] <= outer_box[3] + margin
        )
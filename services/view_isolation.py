import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ViewIsolationService:
    """
    Enterprise Spatial Partitioner.
    Carves the MAIN_CANVAS into isolated drawing views using high-speed
    convergent multi-pass clustering and Red Zone exclusion shielding.
    """
    def __init__(self, cluster_tolerance: float = 50.0):
        self.cluster_tolerance = cluster_tolerance
        
        # Regex Net: Catches unpredictable naming formats
        self.view_label_pattern = re.compile(
            r"(SECTION|SEC\.?|DETAIL|DET\.?|VIEW)\s*[A-Z0-9-]*", 
            re.IGNORECASE
        )

    def isolate_views(self, vector_page, semantic_lines: list, spatial_zones: dict = None) -> List[dict]:
        logger.info("Initializing Spatial Density Clustering for View Isolation...")
        
        # 1. Safely extract bounding boxes regardless of data hydration state
        rects = []
        for path in vector_page.path_elements:
            if hasattr(path, 'bbox'):
                b = path.bbox
                rects.append([b.x0, b.y0, b.x1, b.y1])
            elif isinstance(path, dict) and 'bbox' in path:
                b = path['bbox']
                rects.append([b[0], b[1], b[2], b[3]])
                
        if not rects:
            logger.warning("No vector paths found for view isolation.")
            return []

        # 2. Convergent Multi-Pass Merge (Prevents O(N^2) CPU Freezing)
        view_clusters = self._merge_rectangles(rects, self.cluster_tolerance)
        logger.debug(f"Geometry Pass: Detected {len(view_clusters)} distinct physical clusters.")

        labeled_views = []
        unlabeled_counter = 1 

        # 3. Semantic Anchoring & Red Zone Filtering
        for cluster_box in view_clusters:
            view_data = {
                "view_name": None,
                "bounding_box": cluster_box,
                "contained_text": []
            }
            
            for line in semantic_lines:
                bbox = line.get("bbox")
                if not bbox: continue
                
                # THE EXCLUSION SHIELD: Ignore text inside Title Blocks and BOM Tables
                if self._is_in_exclusion_zone(bbox, spatial_zones):
                    continue 
                    
                if self._is_inside_or_near(bbox, cluster_box, margin=100):
                    view_data["contained_text"].append(line)
                    
                    if view_data["view_name"] is None:
                        text_val = line.get("text", "").upper()
                        match = self.view_label_pattern.search(text_val)
                        if match:
                            view_data["view_name"] = match.group(0).strip()
            
            # The Fallback Execution
            if view_data["view_name"] is None:
                view_data["view_name"] = f"UNLABELED_VIEW_{unlabeled_counter}"
                unlabeled_counter += 1
                        
            labeled_views.append(view_data)

        logger.info(f"View Isolation Complete. Carved {len(labeled_views)} distinct views.")
        return labeled_views

    def _is_in_exclusion_zone(self, bbox: List[float], spatial_zones: dict) -> bool:
        """Checks if a text box falls inside a Phase 1 Red Zone."""
        if not spatial_zones: return False
        
        exclusion_rects = []
        if spatial_zones.get("TITLE_BLOCK"):
            exclusion_rects.append(spatial_zones["TITLE_BLOCK"].get("rect_pdf"))
            
        for table in spatial_zones.get("TABLES", []):
            exclusion_rects.append(table.get("rect_pdf"))

        for rect in exclusion_rects:
            if rect and self._is_inside_or_near(bbox, rect, margin=5):
                return True
        return False

    def _merge_rectangles(self, rects: list, tolerance: float) -> list:
        """Highly optimized Convergent Multi-Pass algorithm."""
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
                    
                    # Check Intersection
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
        return (inner_box[0] >= outer_box[0] - margin and
                inner_box[1] >= outer_box[1] - margin and
                inner_box[2] <= outer_box[2] + margin and
                inner_box[3] <= outer_box[3] + margin)
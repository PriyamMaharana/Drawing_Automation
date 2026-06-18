import logging
import re
from typing import List, Dict, Tuple

try:
    from core.entities.geometry import VectorPage
    from core.entities.drawing_view import DrawingView
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise 

logger = logging.getLogger(__name__)

class ViewIsolationService:
    """
    The Spatial Partitioner.
    Carves the MAIN_CANVAS into isolated drawing views (Front, Top, Section)
    using bounding box intersection and semantic anchoring.
    """
    def __init__(self, cluster_tolerance: float = 50.0):
        self.cluster_tolerance = cluster_tolerance
        
        self.view_label_pattern = re.compile(
            r"(SECTION|SEC\.?|DETAIL|DET\.?|VIEW)\s*[A-Z0-9-]*", 
            re.IGNORECASE
        )
        
    def isolate_views(self, vector_page: VectorPage, semantic_lines: List[dict]) ->List[dict]:
        logger.info(f"Initializing spatial density clustering for view isolation...")
        
        rects = []
        for path in vector_page.path_elements:
            r = path.get("rect")
            if r and r.is_valid:
                rects.append([r.x0, r.y0, r.x1, r.y1])
                
        if not rects:
            return []

        view_clusters = self._merge_rectangles(rects, self.cluster_tolerance)
        logger.debug(f"Geometry Pass: Detected {len(view_clusters)} distinct physical clusters.")

        labeled_views = []
        unlabeled_counter = 1
        
        for cluster_box in view_clusters:
            view_data = {
                "view_name": None,
                "bounding_box": cluster_box,
                "contained_text": [],
                "contained_paths": []
            }
            
            for line in semantic_lines:
                text = line["text"].upper()
                if self._is_inside_or_near(line["bbox"], cluster_box, margin=100):
                    view_data["contained_text"].append(line)
        
                    if view_data["view_name"] is None:
                        match = self.view_label_pattern.search(text)
                        if match:
                            view_data["view_name"] = match.group(0).strip()
                            
                            
            if view_data["view_name"] is None:
                view_data["view_name"] = f"UNLABELED_VIEW_{unlabeled_counter}"
                unlabeled_counter += 1
                        
            labeled_views.append(view_data)

        logger.info(f"View Isolation Complete. Carved {len(labeled_views)} distinct views.")
        return labeled_views
    
    def _merge_rectangles(self, rects: List[List[float]], tolerance: float) -> List[List[float]]:
        """
        Takes thousands of tiny line boxes and melts them into massive View boxes.
        """
        # Expand all rectangles by the tolerance
        expanded = [[r[0]-tolerance, r[1]-tolerance, r[2]+tolerance, r[3]+tolerance] for r in rects]
        
        merged = []
        for rect in expanded:
            matched = False
            for m in merged:
                # Check for intersection
                if not (rect[2] < m[0] or rect[0] > m[2] or rect[3] < m[1] or rect[1] > m[3]):
                    # Merge them
                    m[0] = min(m[0], rect[0])
                    m[1] = min(m[1], rect[1])
                    m[2] = max(m[2], rect[2])
                    m[3] = max(m[3], rect[3])
                    matched = True
                    break
            if not matched:
                merged.append(rect)
                
        # Shrink them back to actual size
        final_boxes = [[r[0]+tolerance, r[1]+tolerance, r[2]-tolerance, r[3]-tolerance] for r in merged]
        return final_boxes

    def _is_inside_or_near(self, inner_box, outer_box, margin=0):
        """Checks if text belongs to a geometry cluster."""
        return (inner_box[0] >= outer_box[0] - margin and
                inner_box[1] >= outer_box[1] - margin and
                inner_box[2] <= outer_box[2] + margin and
                inner_box[3] <= outer_box[3] + margin)
        
        
        
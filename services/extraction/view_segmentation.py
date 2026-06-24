import logging
import re
import math
from typing import List, Dict

logger = logging.getLogger(__name__)

class ViewSegmentationEngine:
    """
    Layer 5.2: View Segmentation Engine
    Finds drawing view labels (e.g., "SECTION A-A", "DETAIL B", "FRONT VIEW") 
    and clusters nearby dimensions into those semantic groups.
    """
    
    VIEW_PATTERNS = [
        r'SECTION\s+[A-Z]-[A-Z]',
        r'DETAIL\s+[A-Z]',
        r'(?:FRONT|TOP|RIGHT|LEFT|BOTTOM|ISOMETRIC)\s+VIEW'
    ]

    @classmethod
    def segment_dimensions(cls, text_blocks: List[Dict], dimensions: List[Dict]) -> List[Dict]:
        logger.info("Executing View Segmentation...")
        
        views = []
        
        # 1. Identify View Headers
        for block in text_blocks:
            text = block.get("text", "").upper()
            bbox = block.get("bbox", [0,0,0,0])
            
            for pattern in cls.VIEW_PATTERNS:
                if re.search(pattern, text):
                    views.append({
                        "view_name": text,
                        "header_bbox": bbox,
                        "dimensions": []
                    })
                    logger.debug(f"Found View Header: {text}")
                    break

        # 2. If no views found, put everything in a 'Default View'
        if not views:
            logger.debug("No specific views detected. Falling back to Default View.")
            return [{"view_name": "Main View", "dimensions": dimensions}]

        # 3. Assign Dimensions to the closest View Header
        for dim in dimensions:
            dim_bbox = dim.get("bounding_box_pdf", [0,0,0,0])
            dim_cx = (dim_bbox[0] + dim_bbox[2]) / 2
            dim_cy = (dim_bbox[1] + dim_bbox[3]) / 2
            
            closest_view = None
            min_dist = float('inf')
            
            for view in views:
                vbox = view["header_bbox"]
                v_cx = (vbox[0] + vbox[2]) / 2
                v_cy = (vbox[1] + vbox[3]) / 2
                
                # Euclidean distance
                dist = math.hypot(dim_cx - v_cx, dim_cy - v_cy)
                
                if dist < min_dist:
                    min_dist = dist
                    closest_view = view
            
            if closest_view:
                closest_view["dimensions"].append(dim)
                
        return views
    
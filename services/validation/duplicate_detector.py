import logging
import math
from typing import List, Dict

logger = logging.getLogger(__name__)

class DuplicateDetectionEngine:
    """
    Layer 12.5: Duplicate Detection Engine
    Cross-references extracted dimensions to ensure overlapping Green Zones 
    do not result in duplicate inspection rows in the final ERP export.
    """
    
    @staticmethod
    def clean_duplicates(views: List[Dict], spatial_tolerance: float = 15.0) -> List[Dict]:
        logger.info("Running Duplicate Detection Sweep...")
        
        all_unique_dims = []
        duplicate_count = 0
        
        for view in views:
            unique_dims_for_view = []
            
            for current_dim in view.get("dimensions", []):
                is_duplicate = False
                
                # Compare against already verified unique dimensions
                for safe_dim in unique_dims_for_view:
                    # 1. Value Match Check (Do they say the exact same thing?)
                    val_match = (current_dim.get("specification") == safe_dim.get("specification") and 
                                 current_dim.get("tolerance") == safe_dim.get("tolerance"))
                                 
                    if val_match:
                        # 2. Spatial Match Check (Are they in the exact same physical spot?)
                        c_box = current_dim.get("bounding_box_pdf", [0,0,0,0])
                        s_box = safe_dim.get("bounding_box_pdf", [0,0,0,0])
                        
                        if c_box != [0,0,0,0] and s_box != [0,0,0,0]:
                            c_cx = (c_box[0] + c_box[2]) / 2
                            c_cy = (c_box[1] + c_box[3]) / 2
                            s_cx = (s_box[0] + s_box[2]) / 2
                            s_cy = (s_box[1] + s_box[3]) / 2
                            
                            dist = math.hypot(c_cx - s_cx, c_cy - s_cy)
                            
                            if dist < spatial_tolerance:
                                is_duplicate = True
                                duplicate_count += 1
                                logger.debug(f"Duplicate destroyed: {current_dim.get('raw_text')} at Dist: {dist:.2f}")
                                break
                
                if not is_duplicate:
                    unique_dims_for_view.append(current_dim)
                    
            view["dimensions"] = unique_dims_for_view
            
        if duplicate_count > 0:
            logger.info(f"Sweep complete: {duplicate_count} duplicates neutralized.")
            
        return views
    
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BallooningService:
    """
    AS9102 FAI Ballooning Engine.
    Assigns sequential inspection IDs to all extracted features.
    """
    def __init__(self, start_index: int = 1):
        self.start_index = start_index

    def apply_balloons(self, intelligence_data: List[Dict[str, Any]]) -> int:
        """
        Mutates the intelligence dictionary by injecting a 'balloon_id' into every feature.
        Returns the total number of balloons applied.
        """
        logger.info("Applying AS9102 FAI Balloons to extracted features...")
        current_balloon = self.start_index
        
        for view in intelligence_data:
            dimensions = view.get("dimensions", [])
            
            # Sort dimensions top-to-bottom, left-to-right based on their bounding box
            # This ensures balloons are numbered logically across the page, not randomly.
            dimensions.sort(key=lambda d: (d["bounding_box"][1], d["bounding_box"][0]) if d.get("bounding_box") else (0,0))
            
            for dim in dimensions:
                dim["balloon_id"] = current_balloon
                current_balloon += 1
                
        total_applied = current_balloon - self.start_index
        logger.debug(f"Successfully generated {total_applied} sequential balloons.")
        return total_applied
    
    
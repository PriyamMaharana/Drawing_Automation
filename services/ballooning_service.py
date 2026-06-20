import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BallooningService:
    def __init__(self, start_index: int = 1):
        self.current_id = start_index

    def apply_balloons(self, intelligence: list) -> int:
        logger.info("Applying AS9102 FAI Balloons to extracted features...")
        count = 0
        for view in intelligence:
            for dim in view.get("dimensions", []):
                dim["balloon_id"] = self.current_id
                self.current_id += 1
                count += 1
        return count
    
    
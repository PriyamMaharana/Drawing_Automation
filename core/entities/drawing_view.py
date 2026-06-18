from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class DrawingView:
    view_name: str
    bounding_box: List[float]
    
    contained_text: List[Dict[str, Any]] = field(default_factory=list)
    
    contained_paths: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Serializes the view for JSON export or logging."""
        return {
            "view_name": self.view_name,
            "bounding_box": self.bounding_box,
            "text_count": len(self.contained_text),
            "path_count": len(self.contained_paths)
        }
    
    
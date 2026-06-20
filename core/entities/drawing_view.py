from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class DrawingView:
    view_name: str
    bounding_box: List[float]
    contained_text: List[Dict] = field(default_factory=list)
    contained_paths: List = field(default_factory=list)
    
    
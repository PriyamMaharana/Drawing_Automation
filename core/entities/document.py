from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class PageProfile:
    page_number: int
    health_status: str = "UNKNOWN"
    is_vector: bool = False
    is_drawing: bool = False             
    score: int = 0
    confidence_score: float = 0.0        
    diagnostics: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentProfile:
    health_status: str = "UNKNOWN"
    oem: str = "UNKNOWN"                 
    paper_size: str = "DYNAMIC"
    recommended_dpi: int = 400
    total_pages: int = 1                 

@dataclass
class DrawingPackage:
    document_profile: DocumentProfile
    primary_page: Optional[int] = None
    drawing_pages: List[int] = field(default_factory=list)
    pages: List[PageProfile] = field(default_factory=list)
    spatial_zones: Dict[str, Any] = field(default_factory=dict) 
    
    def to_dict(self):
        return {
            "document_profile": self.document_profile.__dict__,
            "primary_page": self.primary_page,
            "drawing_pages": self.drawing_pages,
            "spatial_zones": self.spatial_zones
        }
        
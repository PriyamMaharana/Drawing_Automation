from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class PageProfile:
    page_number: int
    health_status: str
    is_vector: bool
    score: int
    diagnostics: List[str]

@dataclass
class DocumentProfile:
    oem: str
    paper_size: str
    recommended_dpi: int
    health_status: str

@dataclass
class DrawingPackage:
    document_profile: DocumentProfile
    primary_page: Optional[int]
    drawing_pages: List[int]
    pages: List[PageProfile] = field(default_factory=list)
    spatial_zones: Dict[str, Any] = field(default_factory=dict) 
    
    def to_dict(self):
        return {
            "document_profile": self.document_profile.__dict__,
            "primary_page": self.primary_page,
            "drawing_pages": self.drawing_pages,
            "spatial_zones": self.spatial_zones
        }
        


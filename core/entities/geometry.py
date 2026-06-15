from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float: return self.x1 - self.x0
    
    @property
    def height(self) -> float: return self.y1 - self.y0
    
    @property
    def center_y(self) -> float: return (self.y0 + self.y1) / 2
    
    def expand(self, other: 'BoundingBox'):
        self.x0 = min(self.x0, other.x0)
        self.y0 = min(self.y0, other.y0)
        self.x1 = max(self.x1, other.x1)
        self.y1 = max(self.y1, other.y1)
        
@dataclass
class PDFCharacter:
    text: str
    bbox: BoundingBox
    font_size: float
    font_name: str
    confidence: float = 100.0
    page_number: int = 1
    
@dataclass
class PDFWord:
    text: str
    bbox: BoundingBox
    characters: List[PDFCharacter] = field(default_factory=list)
    
@dataclass
class PDFLine:
    text: str
    bbox: BoundingBox
    words: List[PDFWord] = field(default_factory=list)
 
@dataclass
class PDFImage:
    bbox: BoundingBox
    width: int
    height: int
    ocr_text: list = field(default_factory=list)

@dataclass
class PDFPath:
    path_type: str  
    items: list
    bbox: BoundingBox
    stroke_color: Optional[List] = None
    fill_color: Optional[List] = None
    line_width: float = 1.0
    page_number: int = 1

@dataclass
class VectorPage:
    page_number: int
    page_width: float = 0.0
    page_height: float = 0.0
    raw_characters: List[PDFCharacter] = field(default_factory=list)
    path_elements: List[PDFPath] = field(default_factory=list)
    image_elements: List[PDFImage] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "page_number": self.page_number,
            "page_dimensions": {                
                "width": self.page_width,
                "height": self.page_height
            },
            "metrics": {
                "total_raw_characters": len(self.raw_characters), 
                "total_vector_paths": len(self.path_elements),
                "total_images": len(self.image_elements)
            },
            "raw_characters": [
                {
                    "text": c.text,
                    "bbox": [c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1],
                    "font_size": c.font_size,
                    "font_name": c.font_name,
                    "confidence": c.confidence
                } for c in self.raw_characters
            ],
            "path_elements": [
                {
                    "path_type": p.path_type, 
                    "items": p.items,
                    "bbox": [p.bbox.x0, p.bbox.y0, p.bbox.x1, p.bbox.y1],
                    "stroke_color": p.stroke_color, 
                    "fill_color": p.fill_color, 
                    "line_width": p.line_width
                } for p in self.path_elements
            ],
            "image_elements": [
                {
                    "bbox": [img.bbox.x0, img.bbox.y0, img.bbox.x1, img.bbox.y1],
                    "width": img.width, 
                    "height": img.height, 
                    "ocr_text": [
                        {
                            "text": t.text,
                            "bbox": [t.bbox.x0, t.bbox.y0, t.bbox.x1, t.bbox.y1],
                            "confidence": t.confidence
                        } for t in img.ocr_text
                    ]
                } for img in self.image_elements
            ]
        }
        

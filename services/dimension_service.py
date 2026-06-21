import logging
import re

try:
    from core.entities.drawing_view import DrawingView
    from core.dictionaries.cad_dictionary import CADSignatures, OEMSignatures, PaperSizeSignatures
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

logger = logging.getLogger(__name__)

class DimensionService:
    def __init__(self):
        self.base_pattern = re.compile(r'\d+')

    def extract_dimensions(self, view: DrawingView) -> list:
        dimensions = []
        for line in view.contained_text:
            text = line.get("text", "").strip()

            if any([CADSignatures.SYMBOLS.search(text),
                CADSignatures.KEYWORDS.search(text),
                CADSignatures.TOLERANCES.search(text),
                CADSignatures.DIMENSIONS.search(text),
                self.base_pattern.search(text)]):
                
                entity_type = "Specification"
                
                if CADSignatures.SYMBOLS.search(text):
                    if any(s in text for s in ['Ø','°','⌀','⌖','↗','⌰','⟂','∥','∠','▱','⌭','⌓','⌒']):
                        entity_type = "Specification"
                    elif any(t in text for t in ['±','+','-']):
                        entity_type = "Tolerance"
                    else:
                        entity_type = "GD&T Symbol"
                        
                elif CADSignatures.TOLERANCES.search(text):
                    entity_type = "Tolerence"
                
                else:
                    entity_type = "Specification"
                    
                dimensions.append({
                    "entity_type": entity_type,
                    "raw_text": text,
                    "bounding_box_pdf": line.get("bbox", [0,0,0,0]),
                    "confidence": 0.95
                })
                
        if not dimensions:
            logger.warning(f"⚠️ No dimensions or CAD signatures found in {view.view_name}.")
            
        return dimensions



import logging
from typing import List, Dict, Any
from core.entities.drawing_view import DrawingView

try:
    # Import all your new micro-engines
    from parsers.dimensions.diameter_parser import DiameterParser
    from parsers.dimensions.radius_parser import RadiusParser
    from parsers.dimensions.angle_parser import AngleParser
    from parsers.dimensions.linear_dimension_parser import LinearDimensionParser
    from parsers.tolerances.gdt_parser import GDTParser
    from parsers.tolerances.fit_parser import FitParser
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

logger = logging.getLogger(__name__)

class DimensionService:
    def __init__(self):
        # the engine will test the string against
        self.parsers = [
            DiameterParser(),
            RadiusParser(),
            AngleParser(),
            GDTParser(),
            FitParser(),
            LinearDimensionParser()
        ]
        
    def extract_dimensions(self, view: DrawingView) -> List[Dict[str, Any]]:
        structured_data = []
        
        for block in view.contained_text:
            raw_text = block.get("text", "").strip()
            
            for parser in self.parsers:
                parsed_data = parser.parse(raw_text)
                
                if parsed_data:
                    parsed_data["bounding_box"] = block.get("bbox")
                    structured_data.append(parsed_data)
                    break
                
        return structured_data

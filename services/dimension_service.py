import logging

try:
    from core.entities.drawing_view import DrawingView
    from parsers.dimensions.compound_parser import CompoundParser
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

logger = logging.getLogger(__name__)

class DimensionService:
    def __init__(self):
        pass

    def extract_dimensions(self, view: DrawingView) -> list:
        logger.info(f"Extracting & Splitting dimensions from view: {view.view_name}")
        dimensions = []
        
        for line in view.contained_text:
            raw_text = line.get("text", "").strip()
            bbox = line.get("bbox", [0, 0, 0, 0])
            
            if not raw_text:
                continue
                
            logger.debug(f"Passing raw block to NLP Parser: '{raw_text}'")
            parsed_features = CompoundParser.parse_annotation(raw_text)
            
            for feature in parsed_features:
                dimensions.append({
                    "entity_type": "Dimension",
                    "raw_text": feature["raw_balloon_text"],
                    "specification": feature["specification"],
                    "tolerance": feature["tolerance"],
                    "bounding_box_pdf": bbox,
                    "confidence": 0.95
                })
                
        if not dimensions:
            logger.warning(f"⚠️ No dimensions or CAD signatures found in {view.view_name}.")
        else:
            logger.info(f"Successfully finalized {len(dimensions)} dimensions for {view.view_name}.")
            
        return dimensions
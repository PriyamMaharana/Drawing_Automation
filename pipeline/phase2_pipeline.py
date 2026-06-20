import logging
import fitz
import json
import sys
from pathlib import Path

try:
    from infrastructure.pdf.vector_extractor import PDFVectorExtractor
    from core.vision.geometric_view_finder import GeometricViewFinder
    from core.entities.document import DrawingPackage
except ImportError as e:
    logging.error(f"Microservices import failure: {e}", exc_info=True)
    
logger = logging.getLogger(__name__)

class Phase2Pipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.log_dir = self.project_root / "debug" / "logs" / "phase2"
        self.res_dir = self.project_root / "debug" / "results" / "phase2"        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)        
        self.view_finder = GeometricViewFinder(cluster_tolerance=20.0)

    def execute(self, pdf_path: Path, drawing_package):
        logging.info(f"Starting Phase 2 Execution for: {pdf_path.name}")
        
        extractor = PDFVectorExtractor()
        vector_page = extractor.extract_page_vectors(pdf_path, drawing_package)
        
        doc_profile = drawing_package.document_profile if drawing_package else None
        image_dpi = doc_profile.recommended_dpi if doc_profile else 400
        spatial_zones = drawing_package.spatial_zones if drawing_package else {}
        
        doc = fitz.open(str(pdf_path))
        page = doc[vector_page.page_number - 1]
        pix = page.get_pixmap(dpi=image_dpi, alpha=False)
        raw_image_bytes = pix.tobytes("png")
        doc.close()
        
        pseudo_lines = [
            {"text": c.text, "bbox": [c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1]}
            for c in vector_page.raw_characters
        ]
        
        logger.info("Executing Shift-Left View Isolation...")
        isolated_views = self.view_finder.isolate_views(
            vector_page=vector_page,
            semantic_lines=pseudo_lines,
            raw_image_bytes=raw_image_bytes,
            spatial_zones=spatial_zones,
            image_dpi=image_dpi
        )
        
        vector_page.isolated_views = isolated_views        
        self._export_json(pdf_path, vector_page)
        return vector_page
    
    def _export_json(self, pdf_path: Path, vector_page):
        output_payload = {
            "phase": "vector_extraction",
            "input": pdf_path.name,
            "output": vector_page.to_dict()
        }
        
        result_file = self.res_dir / f"{pdf_path.stem}_phase2.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4) 
        logging.info(f"Phase 2 Complete. Results exported to {result_file}")

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python pipeline/phase2_pipeline.py <path_to_pdf>")
#     else:
#         project_root = (Path(__file__).resolve().parent.parent)
#         pass
        
        
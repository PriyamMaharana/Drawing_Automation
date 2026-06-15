import logging
import json
import sys
from pathlib import Path

try:
    from infrastructure.pdf.vector_extractor import PDFVectorExtractor
    from core.entities.document import DrawingPackage
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")

class Phase2Pipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.log_dir = self.project_root / "debug" / "logs" / "phase2"
        self.res_dir = self.project_root / "debug" / "results" / "phase2"
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)


    def execute(self, pdf_path: Path, drawing_package):
        logging.info(f"Starting Phase 2 Execution for: {pdf_path.name}")
        
        extractor = PDFVectorExtractor()
        vector_page = extractor.extract_page_vectors(pdf_path, drawing_package)
        
        self._export_json(pdf_path, vector_page)
        return vector_page
    
    def _export_json(self, pdf_path: Path, vector_page):
        # Export Results per Standard
        output_payload = {
            "phase": "vector_extraction",
            "input": pdf_path.name,
            "output": vector_page.to_dict()
        }
        
        result_file = self.res_dir / f"{pdf_path.stem}_phase2.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4)
            
        logging.info(f"Phase 2 Complete. Results exported to {result_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline/phase2_pipeline.py <path_to_pdf>")
    else:
        project_root = (Path(__file__).resolve().parent.parent)
        pipeline = Phase2Pipeline(project_root)
        pipeline.execute(Path(sys.argv[1]).resolve())
        
        
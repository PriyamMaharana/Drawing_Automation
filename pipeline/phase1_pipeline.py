import logging
import json
import sys
from pathlib import Path

try:
    from infrastructure.pdf.document_scout import DocumentScout
except ImportError as e:
    logging.error(f"Microservices not loaded: {e}")

class Phase1Pipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.log_dir = self.project_root / "debug" / "logs" / "phase1"
        self.res_dir = self.project_root / "debug" / "results" / "phase1"
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.res_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "scout_execution.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def execute(self, pdf_path: Path):
        logging.info(f"Starting Phase 1 Execution for: {pdf_path.name}")
        
        scout = DocumentScout()
        drawing_package = scout.analyze_document(pdf_path)
        
        self._log_summary(drawing_package)
        self._export_json(pdf_path, drawing_package)

        return drawing_package
        
    def _log_summary(self, drawing_package):
        # Terminal Feedback
        logging.info(f"Health Status: {drawing_package.document_profile.health_status}")
        logging.info(f"Detected OEM: {drawing_package.document_profile.oem}")
        logging.info(f"Primary Drawing Page: {drawing_package.primary_page}")
        logging.info(f"Total Drawing Pages: {drawing_package.drawing_pages}")
        
        zones = getattr(drawing_package, "spatial_zones", {})

        debug = zones.get("_debug", {})
        logging.info(f"Spatial Mapping Summary: ")

        logging.info(
            f"  Main Canvas: "
            f"{'FOUND' if zones.get('MAIN_CANVAS') else 'NOT FOUND'}"
        )

        logging.info(
            f"  Title Block: "
            f"{'FOUND' if zones.get('TITLE_BLOCK') else 'NOT FOUND'}"
        )

        logging.info(
            f"  Tables Found: "
            f"{len(zones.get('TABLES', []))}"
        )

        if debug:
            logging.info(
                f"  Threshold Method: "
                f"{debug.get('threshold_method')}"
            )

            logging.info(
                f"  Contours Found: "
                f"{debug.get('contours_found')}"
            )

            logging.info(
                f"  Boxes After Filter: "
                f"{debug.get('boxes_after_filter')}"
            )
        
    def _export_json(self, pdf_path: Path, drawing_package):
        # Export Results per Standard
        output_payload = {
            "phase": "document_scout",
            "input": pdf_path.name,
            "output": drawing_package.to_dict()
        }
        
        result_file = self.res_dir / f"{pdf_path.stem}_phase1.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4)
            
        logging.info(f"Phase 1 Complete. Results exported to {result_file}")
        return drawing_package

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline/phase1_pipeline.py <path_to_pdf>")
    else:
        project_root = (Path(__file__).resolve.parent.parent)
        pipeline = Phase1Pipeline(project_root)
        pipeline.execute(Path(sys.argv[1]).resolve())
        
        
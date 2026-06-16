import json
import logging
import sys
from pathlib import Path

# --- INJECT PROJECT ROOT ---
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.entities.geometry import BoundingBox, PDFCharacter
    from infrastructure.pdf.semantic_cluster import build_semantic_hierarchy
    from core.utils.logger import setup_3_tier_logging
except ImportError as e:
    logging.exception(f"Microservices import failure: {e}")
    raise

class Phase3Pipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.p2_res_dir = self.project_root / "debug" / "results" / "phase2"
        self.p3_res_dir = self.project_root / "debug" / "results" / "phase3"
        
        # Ensure the Phase 3 output directory exists
        self.p3_res_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, pdf_filename: str):
        print("=" * 60)
        print(f"  PHASE 3: SEMANTIC RECONSTRUCTION ENGINE ({pdf_filename})")
        print("=" * 60)
        
        logging.info(f"Starting Phase 3 Execution for: {pdf_filename}")
        
        # 1. Load Raw Phase 2 Data
        p2_json_path = self.p2_res_dir / f"{pdf_filename}_phase2.json"
        if not p2_json_path.exists():
            logging.exception(f"Phase 2 JSON not found: {p2_json_path.name}. Run Phase 2 first!")
            return

        
        with open(p2_json_path, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
                
        p2_data = raw_json.get("output", raw_json)
        raw_chars_data = p2_data.get("raw_characters", [])
        
        # 2. Rehydrate raw JSON into PDFCharacter objects
        logging.info(f"Rehydrating {len(raw_chars_data)} raw characters into memory...")
        pdf_characters = []
        for c in raw_chars_data:
            bx = c["bbox"]
            pdf_characters.append(PDFCharacter(
                text=c["text"],
                bbox=BoundingBox(bx[0], bx[1], bx[2], bx[3]),
                font_size=c["font_size"],
                font_name=c["font_name"],
                confidence=c["confidence"]
            ))

        # 3. Run the Spatial Clustering Math!
        logging.debug("Igniting Spatial Clustering Math...")
        semantic_lines = build_semantic_hierarchy(pdf_characters)
        
        # 4. Export the clean Phase 3 JSON
        self._export_json(pdf_filename, p2_data, semantic_lines)
        
    def _export_json(self, pdf_name: str, p2_data: dict, semantic_lines: list):
        
        output_payload = {
            "page_number": p2_data.get("page_number", 1),
            "page_dimensions": p2_data.get("page_dimensions", {}),
            "metrics": {
                "total_semantic_lines": len(semantic_lines),
                "total_vector_paths": p2_data.get("metrics", {}).get("total_vector_paths", 0),
                "total_images": p2_data.get("metrics", {}).get("total_images", 0)
            },
            "semantic_lines": [
                {
                    "text": line.text,
                    "bbox": [line.bbox.x0, line.bbox.y0, line.bbox.x1, line.bbox.y1],
                    "words": [
                        {
                            "text": w.text,
                            "bbox": [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1],
                            "character_count": len(w.characters)
                        } for w in line.words
                    ]
                } for line in semantic_lines
            ],
            # Pass through native vectors and image bounding boxes untouched
            "path_elements": p2_data.get("path_elements", []),
            "image_elements": p2_data.get("image_elements", [])
        }
        
        result_file = self.p3_res_dir / f"{pdf_name}_phase3.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4)
            
        logging.info(f"Phase 3 Complete! Reconstructed {len(semantic_lines)} clean rows of text.")
        logging.info(f"Results exported to {result_file.name}")

if __name__ == "__main__":
    setup_3_tier_logging(phase_name="phase3", project_root=PROJECT_ROOT)
    pipeline = Phase3Pipeline(PROJECT_ROOT)
    
    
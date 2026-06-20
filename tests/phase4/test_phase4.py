import sys
import json
import logging
from pathlib import Path
import concurrent.futures
import multiprocessing

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure dependencies for Phase 4
def ensure_packages():
    import subprocess
    try:
        import pandas
        import fitz
    except ImportError:
        logging.warning("Installing Pandas, OpenPyXL, and PyMuPDF for Phase 4 Exports...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "PyMuPDF"])

ensure_packages()
import fitz

try:
    from pipeline.phase4_pipeline import Phase4Pipeline
    from core.entities.geometry import VectorPage
    from core.utils.logger import setup_3_tier_logging
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

def _process_single_phase4(pdf_path: Path) -> dict:
    """Isolated worker function for Phase 4."""
    p4_pipeline = Phase4Pipeline(PROJECT_ROOT)
    
    p1_file = PROJECT_ROOT / "debug" / "results" / "phase1" / f"{pdf_path.stem}_phase1.json"
    p2_file = PROJECT_ROOT / "debug" / "results" / "phase2" / f"{pdf_path.stem}_phase2.json"
    p3_file = PROJECT_ROOT / "debug" / "results" / "phase3" / f"{pdf_path.stem}_phase3.json"
    
    if not p2_file.exists() or not p3_file.exists():
        return {"file": pdf_path.name, "status": "SKIPPED", "reason": "Missing Phase 2 or 3 Cache Data"}
        
    try:
        # 0. Load Phase 1 Spatial Zones (The Red Zones)
        spatial_zones = {}
        image_dpi = 300
        if p1_file.exists():
            with open(p1_file, 'r', encoding='utf-8') as f:
                p1_data = json.load(f).get("output", {})
                spatial_zones = p1_data.get("spatial_zones", {})
                doc_profile = p1_data.get("document_profile", {})
                image_dpi = doc_profile.get("recommended_dpi", 300)

        # 1. Load Phase 2 Vector Math
        with open(p2_file, 'r', encoding='utf-8') as f:
            p2_raw = json.load(f)
            p2_data = p2_raw.get("output", p2_raw)
            dims = p2_data.get("page_dimensions", {})
            v_page = VectorPage(
                page_number=1, 
                page_width=dims.get("width", 2000), 
                page_height=dims.get("height", 2000)
            )
            v_page.path_elements = p2_data.get("path_elements", [])
            
        # 2. Load Phase 3 Semantic Text
        with open(p3_file, 'r', encoding='utf-8') as f:
            p3_raw = json.load(f)
            p3_data = p3_raw.get("output", p3_raw)
            semantic_lines = p3_data.get("semantic_lines", [])
            
        # 3. Extract High-Res Raw Image for the Balloon Renderer
        doc = fitz.open(str(pdf_path))
        page = doc[0] 
        pix = page.get_pixmap(dpi=image_dpi, alpha=False)
        raw_image_bytes = pix.tobytes("png")
        doc.close()
            
        # 4. RUN FULL INTELLIGENCE ENGINE
        intelligence, total_balloons = p4_pipeline.execute(
            pdf_path, 
            v_page, 
            semantic_lines, 
            raw_image_bytes, 
            spatial_zones=spatial_zones,
            image_dpi=image_dpi
        )
        
        return {
            "file": pdf_path.name, 
            "status": "PASSED", 
            "views": len(intelligence), 
            "balloons": total_balloons
        }

    except Exception as e:
        return {"file": pdf_path.name, "status": "FAILED", "error": str(e)}

def run_phase4_tests():
    setup_3_tier_logging(phase_name="phase4", project_root=PROJECT_ROOT)
    print("=" * 60)
    print("  PHASE 4: INTELLIGENCE LAYER (BALLOONING & EXCEL)")
    print("=" * 60)

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    test_pdfs = list(sample_dir.glob("*.pdf"))    
    
    if not test_pdfs:
        logging.warning("⚠️ No PDFs found in sample_data directory.")
        return
    
    PASSED, SKIPPED, FAILED = 0, 0, 0
    max_cores = max(1, multiprocessing.cpu_count() - 1)

    logging.info(f"🚀 Igniting Parallel Intelligence Engine across {max_cores} CPU Cores...")

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_cores) as executor:
        future_to_pdf = {executor.submit(_process_single_phase4, pdf): pdf for pdf in test_pdfs}
        
        for future in concurrent.futures.as_completed(future_to_pdf):
            result = future.result()
            if result["status"] == "PASSED":
                logging.info(f"  └─ ✅ PASSED {result['file']} ({result['views']} Views, {result['balloons']} Balloons Stamped)")
                PASSED += 1
            elif result["status"] == "SKIPPED":
                logging.warning(f"  └─ ⏩ SKIPPED {result['file']} ({result['reason']})")
                SKIPPED += 1
            else:
                logging.exception(f"  └─ ❌ CRASH {result['file']} (Error: {result['error']})")
                FAILED += 1

    logging.info("-" * 60)
    logging.info(f"  PHASE 4 RUN COMPLETE: {PASSED} PASSED | {SKIPPED} SKIPPED | {FAILED} FAILED")
    logging.info("-" * 60)

if __name__ == "__main__":
    run_phase4_tests()
    
    
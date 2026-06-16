import sys
import logging
from pathlib import Path

# --- 1. INJECT PROJECT ROOT INTO PYTHON PATH ---
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try: 
    from pipeline.phase1_pipeline import Phase1Pipeline
    from pipeline.phase2_pipeline import Phase2Pipeline
    from core.entities.geometry import VectorPage
    from core.utils.logger import setup_3_tier_logging
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

def run_phase2_tests():
    setup_3_tier_logging(phase_name="phase2", project_root=PROJECT_ROOT)
    
    print("=" * 60)
    print("  PHASE 2: NATIVE PDF VECTOR EXTRACTION TEST RUNNER")
    print("=" * 60)

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    test_pdfs = list(sample_dir.glob("*.pdf"))    
    # test_pdfs = [sample_dir / "ch3.pdf"]
    
    if not test_pdfs:
        logging.warning("⚠️ No PDFs found.")
        return

    p1_pipeline = Phase1Pipeline(PROJECT_ROOT)
    p2_pipeline = Phase2Pipeline(PROJECT_ROOT)
    
    passed = 0
    skipped = 0
    failed = 0

    for pdf_path in test_pdfs:
        logging.info(f"\n▶  Processing Pipeline for {pdf_path.name}")
        
        try:
            package = p1_pipeline.execute(pdf_path)
            
            if package.document_profile.health_status not in ["CLEAN", "VECTOR_BOMB"] or not package.primary_page:
                logging.warning(f"  └─ ⏩ SKIPPED (Phase 1 rejected: {package.document_profile.health_status})")
                skipped += 1
                continue
            
            vector_page = p2_pipeline.execute(pdf_path, package)
            
            assert isinstance(vector_page, VectorPage), "Did not return VectorPage entity."
            t_count = len(vector_page.raw_characters)
            p_count = len(vector_page.path_elements)
            
            logging.info(f"  └─ ✅ PASSED (Extracted {t_count} Text Blocks, {p_count} Paths)")
            passed += 1

        except Exception:
            logging.exception(f"  └─ ❌ CRASH processing {pdf_path.name}")
            failed += 1

    logging.info("\n" + "-" * 70)
    logging.info(f"  PHASE 2 RUN COMPLETE: {passed} PASSED | {skipped} SKIPPED | {failed} FAILED")
    logging.info("-" * 70)

if __name__ == "__main__":
    run_phase2_tests()
    
    
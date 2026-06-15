import sys
import logging
import json
from pathlib import Path

# --- 1. INJECT PROJECT ROOT INTO PYTHON PATH ---
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try: 
    from pipeline.phase3_pipeline import Phase3Pipeline
    from core.utils.logger import setup_3_tier_logging
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

def run_phase3_tests():
    setup_3_tier_logging(phase_name="phase3", project_root=PROJECT_ROOT)
    
    print("=" * 60)
    print("  PHASE 3: SEMANTIC RECONSTRUCTION TEST RUNNER")
    print("=" * 60)

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    
    # You can uncomment this to run the entire folder:
    test_pdfs = list(sample_dir.glob("*.pdf"))    
    
    # Currently hardcoded to run your known test files
    # test_pdfs = [sample_dir / "1.pdf", sample_dir / "ch2.pdf", sample_dir / "ch3.pdf"]
    
    if not test_pdfs:
        logging.warning("⚠️ No PDFs found in sample_data directory.")
        return

    p3_pipeline = Phase3Pipeline(PROJECT_ROOT)
    
    passed = 0
    skipped = 0
    failed = 0

    for pdf_path in test_pdfs:
        pdf_stem = pdf_path.stem
        logging.info(f"\n▶  Processing Phase 3 for {pdf_path.name}")
        
        # 1. Pre-Check: Ensure Phase 2 data actually exists before trying Phase 3
        p2_json_path = PROJECT_ROOT / "debug" / "results" / "phase2" / f"{pdf_stem}_phase2.json"
        if not p2_json_path.exists():
            logging.info(f"  └─ ⏩ SKIPPED (Missing Phase 2 JSON for {pdf_stem}. Run Phase 2 first!)")
            skipped += 1
            continue
        
        try:
            # 2. Execute the Pipeline
            p3_pipeline.execute(pdf_stem)
            
            # 3. Verify the output was successfully written to disk
            p3_json_path = PROJECT_ROOT / "debug" / "results" / "phase3" / f"{pdf_stem}_phase3.json"
            
            if p3_json_path.exists():
                # Open it up to grab the metrics for the log
                with open(p3_json_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                    
                line_count = result_data.get("metrics", {}).get("total_semantic_lines", 0)
                logging.info(f"  └─ ✅ PASSED (Reconstructed {line_count} Semantic Lines)")
                passed += 1
            else:
                logging.error(f"  └─ ❌ FAILED (Pipeline ran, but {pdf_stem}_phase3.json was not generated)")
                failed += 1

        except Exception:
            logging.exception(f"  └─ ❌ CRASH processing {pdf_stem}")
            failed += 1

    logging.info("\n" + "-" * 70)
    logging.info(f"  PHASE 3 RUN COMPLETE: {passed} PASSED | {skipped} SKIPPED | {failed} FAILED")
    logging.info("-" * 70)

if __name__ == "__main__":
    run_phase3_tests()
    
    
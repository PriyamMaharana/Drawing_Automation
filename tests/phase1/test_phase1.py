import sys
import logging
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try: 
    from pipeline.phase1_pipeline import Phase1Pipeline
    from core.entities.document import DrawingPackage
    from core.utils.logger import setup_3_tier_logging
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

def run_true_phase1():
    setup_3_tier_logging(phase_name="phase1", project_root=PROJECT_ROOT)
    
    logging.info("=" * 70)
    logging.info("  PHASE 1: DOCUMENT SCOUT & SPATIAL MAPPING TEST RUNNER")
    logging.info("=" * 70)

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"

    test_pdfs = list(sample_dir.glob("*.pdf"))
    if not test_pdfs:
        logging.warning(f"⚠️ No PDFs found in {sample_dir.relative_to(PROJECT_ROOT)}")
        return
    
    pipeline = Phase1Pipeline(PROJECT_ROOT)
    
    passed = 0
    failed = 0
    skipped = 0

    for pdf_path in test_pdfs:
        logging.info(f"Phase 1 | Initiating Pipeline for {pdf_path.name}")
        
        try:
            package = pipeline.execute(pdf_path)

            assert isinstance(package, DrawingPackage), "Output is not a DrawingPackage entity."
            assert package.document_profile is not None, "DocumentProfile is missing."
            
            health = package.document_profile.health_status
            
            if health in ["RASTER_SCAN", "CORRUPT_DOCUMENT", "CORRUPT_FONT"]:
                logging.info(f"  └─ ⏩ SKIPPED  (Health: {health})")
                skipped += 1
                continue

            if package.primary_page:
                assert (package.primary_page in package.drawing_pages), "Primary page not found in drawing pages."
                
                zones = (package.spatial_zones if hasattr(package, "spatial_zones") else {})
                assert isinstance(zones, dict), "Spatial Zones did not generate correctly."
                assert "MAIN_CANVAS" in zones, "OpenCV failed to map the Main Canvas."
                assert "TITLE_BLOCK" in zones, "OpenCV failed to map the Title Block."
                
                if package.primary_page:
                    assert (zones.get("MAIN_CANVAS") is not None), ("Main Canvas detection failed")
                    assert (zones.get("TITLE_BLOCK") is not None), ("Title Block detection failed")

                tables = zones.get("TABLES", [])
                logging.info(
                    f"  └─ Spatial Mapping: "
                    f"Canvas="
                    f"{'YES' if zones.get('MAIN_CANVAS') else 'NO'} | "
                    f"TitleBlock="
                    f"{'YES' if zones.get('TITLE_BLOCK') else 'NO'} | "
                    f"Tables={len(tables)}"
                )
                
                debug = zones.get("_debug", {})
                if debug:
                    logging.info(
                        f"  └─ Debug: "
                        f"Threshold="
                        f"{debug.get('threshold_method')} | "
                        f"Contours="
                        f"{debug.get('contours_found')} | "
                        f"Boxes="
                        f"{debug.get('boxes_after_filter')}"
                    )
                    
                logging.info("  └─ ✅ PASSED")
                
                passed += 1
           
        except AssertionError as ae:
            logging.info(f"  └─ ❌ VALIDATION FAILED: {str(ae)}")
            logging.error(f"Validation Failure on {pdf_path.name}: {str(ae)}")
            failed += 1
           
        except Exception:
            logging.info("  └─ ❌ CRASH: See crash.log")
            logging.exception(f"Fatal crash processing {pdf_path.name}")
            failed += 1

    logging.info("-" * 70)
    logging.info(f"  PHASE 1 RUN COMPLETE: {passed} PASSED | {skipped} SKIPPED | {failed} FAILED")
    logging.info("-" * 70)

if __name__ == "__main__":
    run_true_phase1()
    
    
import os
import sys
import json
import logging
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  PATH RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────
THIS_DIR = Path(__file__).resolve().parent

def _find_project_root(start: Path) -> Path:
    current = start
    for _ in range(6):          
        has_src = (current / "src").is_dir()
        has_resources = (current / "resources").is_dir()
        if has_src and has_resources:
            return current
        if current.parent == current:   
            break
        current = current.parent
    return THIS_DIR

PROJECT_ROOT = _find_project_root(THIS_DIR)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────
log_dir = PROJECT_ROOT / "log"
log_dir.mkdir(exist_ok=True)

# Set up logging to output to BOTH the terminal and a pipeline.log file
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s', # Keep terminal clean
    handlers=[
        logging.FileHandler(log_dir / "pipeline.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
#  IMPORTS (Phase 3)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import fitz
    import cv2
    import numpy as np
except ImportError:
    logging.error("[Error] Missing core libraries. Run: pip install pymupdf opencv-python-headless scipy")
    sys.exit(1)

# Import the Microservices
try:
    from src.services.health_checker import run_pre_flight_check
    from src.services.extractor import PDFExtractor
    from src.services.vision_service import VisionProcessor
except ImportError as exc:
    logging.error(f"[Error] Architecture broken. Cannot import microservice: {exc}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_pdf(cli_arg: str | None) -> Path:
    """Finds the PDF dynamically."""
    if cli_arg:
        path = Path(cli_arg).resolve()
        if not path.exists():
            logging.error(f"[Error] PDF not found: {path}")
            sys.exit(1)
        return path

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    if sample_dir.is_dir():
        pdfs = sorted(sample_dir.glob("*.pdf"))
        if pdfs:
            chosen = pdfs[0]
            return chosen

    logging.error("[Error] No PDF found. Pass a path:  python tests/test_phase2.py your.pdf")
    sys.exit(1)

def _find_drawing_page(pdf_path: Path, force_page: int | None):
    """
    THE PRODUCTION CASCADE:
    1. Pre-Flight Check (Health)
    2. Phase 1 Check (Extractor)
    3. Hand-off to Phase 3
    """
    doc = fitz.open(str(pdf_path))
    valid_pages = []

    if force_page is not None:
        if force_page >= len(doc):
            doc.close()
            logging.error(f"[Error] Page {force_page} does not exist.")
            sys.exit(1)
        logging.info(f"[Info]  Force-bypassing pipeline. Testing page index {force_page}.")
        return [(doc[force_page], force_page)], doc

    logging.info("\n[PIPELINE] Booting Production Cascade sequence...")
    extractor = PDFExtractor(str(pdf_path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        human_page = page_num + 1
        
        # --- STEP 1: PRE-FLIGHT ---
        health_status = run_pre_flight_check(page, human_page)
        if health_status not in ("CLEAN", "VECTOR_BOMB"):
            if health_status in ("RASTER_SCAN", "CORRUPT_FONT"):
                continue
            
        # --- STEP 2: PHASE 1 (EXTRACTOR VALIDATION) ---
        is_drawing = extractor.is_drawing_page(page, human_page, health_status)
        if not is_drawing:
            logging.info(f" -> [PHASE 1] Page {human_page} REJECTED: Not a recognized CAD drawing.")
            continue
            
        # --- STEP 3: PHASE 3 HAND-OFF ---
        logging.info(f" -> [PHASE 1] Page {human_page} APPROVED: Valid CAD geometry found.")
        logging.info(f" -> [PIPELINE] Queuing Page {human_page} to Phase 3 Semantic Extractor...\n")
        valid_pages.append((page, page_num))
        
    if not valid_pages:
        doc.close()
        logging.error("[Error] Pipeline failed to find any valid, clean CAD pages.")
        sys.exit(1)

    return valid_pages, doc


def _print_dimensions(dimensions: list[dict]) -> None:
    """UPDATED: Beautifully formats the new DimensionEntity JSON schema."""
    if not dimensions:
        logging.info("  (none)")
        return
        
    col = "{:<12} {:<15} {:<15} {:<15} {:<6} {:<20}"
    logging.info("  " + col.format(
        "ID", "Type", "Specification", "Tolerance", "Ref", "Raw Text"
    ))
    logging.info("  " + "─" * 85)
    
    for d in dimensions[:10]:
        # Format the tolerance display gracefully
        tol_str = "-"
        if d.get("tolerance"):
            t = d["tolerance"]
            if t.get("symmetric"):
                tol_str = t["symmetric"]
            else:
                up = t.get("upper", "")
                dn = t.get("lower", "")
                tol_str = f"{up}/{dn}" if up or dn else "-"
        
        ref_flag = "Yes" if d.get("reference_dimension") else ""
        
        logging.info("  " + col.format(
            d.get("id", ""),
            d.get("type", "unknown"),
            d.get("specification", ""),
            tol_str,
            ref_flag,
            d.get("raw_text", "")
        ))
        
    if len(dimensions) > 10:
        logging.info(f"  ... and {len(dimensions) - 10} more dimension entities safely exported to JSON.")

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
def test_vision_service() -> None:
    pdf_arg  = sys.argv[1] if len(sys.argv) > 1 else None
    page_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

    pdf_path = _resolve_pdf(pdf_arg)
    logging.info(f"[Info]  TARGET PDF  → {pdf_path.name}")

    # ── RUN THE CASCADE ───────────────────────────────────────────────────────
    valid_pages, doc = _find_drawing_page(pdf_path, page_arg)

    # ── RUN PHASE 3 ───────────────────────────────────────────────────────────
    logging.info("═" * 88)
    logging.info("  Phase 2 — Semantic Extractor & Dimensional Reconstruction")
    logging.info("═" * 88)

    # Instantiate the new V12 engine (600 DPI for high precision OCR mapping)
    extractor = VisionProcessor(render_dpi=600, debug=True)
    dimension_payload = {}

    try:
        for page, page_idx in valid_pages:
            human_page = page_idx + 1
            logging.info(f"\n[Info] Scanning Page {human_page} for Engineering Dimensions...")
            
            # Extract structured semantic entities
            dimensions = extractor.process_page(page, str(pdf_path), page_idx=page_idx)
            dimension_payload[f"page_{human_page}"] = dimensions
            
            # ── RESULTS ───────────────────────────────────────────────────────────────
            logging.info(f"\nSuccessfully parsed {len(dimensions)} dimensional entities:\n")
            _print_dimensions(dimensions)
            
    finally:
        doc.close()
        
    # ── THE MICROSERVICE HANDOFF (Save to Temp File) ──────────────────────────
    # Save the strictly formatted dimension payload
    temp_json_path = PROJECT_ROOT / "debug" / "dimension_payloads" / f"temp_{pdf_path.stem}_dimensions.json"
    temp_json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_json_path, "w", encoding="utf-8") as f:
        json.dump(dimension_payload, f, indent=4, ensure_ascii=False)
        
    logging.info(f"\n[Done] All Semantic Data safely dumped to → {temp_json_path.relative_to(PROJECT_ROOT)}")
        
    # ── DEBUG OUTPUT ──────────────────────────────────────────────────────────
    # Point to the new Audit Images folder
    base_dir = Path(os.environ.get("VISION_DEBUG_DIR", PROJECT_ROOT / "debug"))
    debug_dir = base_dir / "audit"
    
    if debug_dir.is_dir():
        overlays = sorted(
            list(debug_dir.glob("*_audit.png")),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if overlays:
            try:
                rel_path = overlays[0].relative_to(PROJECT_ROOT)
            except ValueError:
                rel_path = overlays[0]
            logging.info(f"[Info]  Visual HUD Audit generated at   → {rel_path}")
            logging.info(f"[Info]  Full execution log saved to     → debug/pipeline.log")

    logging.info(f"[Done]  Verify KD-Tree clustering and Semantic Parsing in the HUD Audit image.\n\n")

if __name__ == "__main__":
    test_vision_service()
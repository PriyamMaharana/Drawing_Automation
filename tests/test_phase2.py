import sys
import json
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
#  IMPORTS (Phase 2)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import fitz
    import cv2
    import numpy as np
except ImportError:
    sys.exit("[error] Missing core libraries. Run: pip install pymupdf opencv-python-headless")

# Import all 3 Microservices
try:
    from src.services.health_checker import run_pre_flight_check
    from src.services.extractor import PDFExtractor
    from src.services.vision_service import VisionProcessor
except ImportError as exc:
    sys.exit(f"[error] Architecture broken. Cannot import microservice: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_pdf(cli_arg: str | None) -> Path:
    """Finds the PDF dynamically."""
    if cli_arg:
        path = Path(cli_arg).resolve()
        if not path.exists():
            sys.exit(f"[error] PDF not found: {path}")
        return path

    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    if sample_dir.is_dir():
        pdfs = sorted(sample_dir.glob("*.pdf"))
        if pdfs:
            chosen = pdfs[0]
            return chosen

    sys.exit("[error] No PDF found. Pass a path:  python tests/test_phase2.py your.pdf")

def _find_drawing_page(pdf_path: Path, force_page: int | None):
    """
    THE PRODUCTION CASCADE:
    1. Pre-Flight Check (Health)
    2. Phase 1 Check (Extractor)
    3. Hand-off to Phase 2
    """
    doc = fitz.open(str(pdf_path))
    valid_pages = []

    if force_page is not None:
        if force_page >= len(doc):
            doc.close()
            sys.exit(f"[error] Page {force_page} does not exist.")
        print(f"[info]  Force-bypassing pipeline. Testing page index {force_page}.")
        return doc[force_page], force_page, doc

    print("\n[PIPELINE] Booting Production Cascade sequence...")
    extractor = PDFExtractor(str(pdf_path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        human_page = page_num + 1
        
        # --- STEP 1: PRE-FLIGHT ---
        health_status = run_pre_flight_check(page, human_page)
        if health_status != "CLEAN" and health_status != "VECTOR_BOMB":
            if health_status in ("RASTER_SCAN", "CORRUPT_FONT"):
                continue
            
        # --- STEP 2: PHASE 1 (EXTRACTOR VALIDATION) ---
        is_drawing = extractor.is_drawing_page(page, human_page, health_status)
        if not is_drawing:
            print(f"  -> [PHASE 1] Page {human_page} REJECTED: Not a recognized CAD drawing.")
            continue
            
        # --- STEP 3: PHASE 2 HAND-OFF ---
        print(f"  -> [PHASE 1] Page {human_page} APPROVED: Valid CAD geometry found.")
        print(f"  -> [PIPELINE] Queuing Page {human_page} to Phase 2 Vision Engine...\n")
        valid_pages.append((page, page_num))
        
    if not valid_pages:
        doc.close()
        sys.exit("[error] Pipeline failed to find any valid, clean CAD pages.")

    return valid_pages, doc


def _print_zones(tables: list[dict]) -> None:
    if not tables:
        print("  (none)")
        return
        
    col = "{:<6} {:>10} {:>10} {:>10} {:>10} {:>12} {:>10}"
    print(col.format("Zone", "Min X", "Min Y", "Max X", "Max Y", "Total Points", "Type"))
    print("  " + "─" * 78)
    
    for i, t in enumerate(tables, 1):
        # Handle both Bounding Box (legacy) and Polygon (new) formats
        if "vertices" in t:
            vertices = t["vertices"]
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            pts_count = len(vertices)
            zone_type = "polygon"
        else:
            # Legacy Bounding Box format
            x0, y0, x1, y1 = t["x0"], t["y0"], t["x1"], t["y1"]
            pts_count = 4
            zone_type = "box"
        
        print(col.format(
            f"  [{i}]",
            f"{x0:.1f}", f"{y0:.1f}",
            f"{x1:.1f}", f"{y1:.1f}",
            f"{pts_count} pts", 
            zone_type
        ))

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def test_vision_service() -> None:
    pdf_arg  = sys.argv[1] if len(sys.argv) > 1 else None
    page_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

    pdf_path = _resolve_pdf(pdf_arg)
    print(f"[info]  TARGET PDF  → {pdf_path.name}")

    # ── RUN THE CASCADE ───────────────────────────────────────────────────────
    valid_pages, doc = _find_drawing_page(pdf_path, page_arg)

    # ── RUN PHASE 2 ───────────────────────────────────────────────────────────
    print("═" * 70)
    print("  Phase 2 — Hierarchical Contour Analysis (VisionProcessor)")
    print("═" * 70)

    processor = VisionProcessor()
    zone_payload = {}

    try:
        for page, page_idx in valid_pages:
            human_page = page_idx + 1
            print(f"\n[info] Scanning Page {human_page} for Exclusion Zones...")
            
            tables = processor.process_page(page, str(pdf_path))
            zone_payload[f"page_{human_page}"] = tables
            
            # ── RESULTS ───────────────────────────────────────────────────────────────
            print(f"\n  Found {len(tables)} corporate table exclusion zone(s):\n")
            _print_zones(tables)
            
    finally:
        doc.close()
        
        
    # ── THE MICROSERVICE HANDOFF (Save to Temp File) ──────────────────────────
    temp_json_path = PROJECT_ROOT / "debug" / "zone_payloads" / f"temp_{pdf_path.stem}_zones.json"
    temp_json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_json_path, "w", encoding="utf-8") as f:
        json.dump(zone_payload, f, indent=4)
        
    print(f"\n[done] All co-ordinates safely dumped to → {temp_json_path.relative_to(PROJECT_ROOT)}")
        

    # ── DEBUG OUTPUT ──────────────────────────────────────────────────────────
    debug_dir = PROJECT_ROOT / "debug" / "overlay_mask"
    if debug_dir.is_dir():
        overlays = sorted(
            list(debug_dir.glob("*_overlay.jpg")),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if overlays:
            print(f"\n[info]  Debug overlay written to → debug/{overlays[0].name}")

    print("[done]  Verify mathematical isolation in the debug image.")

if __name__ == "__main__":
    test_vision_service()
import sys
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
#  IMPORTS (Phase 1)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import json
    import os
    import typing_extensions
except ImportError:
    sys.exit("[error] Cannot import required modules. Please install them first.")

try:
    from src.services.extractor import PDFExtractor
except ImportError as exc:
    sys.exit(f"[error] Architecture broken. Cannot import microservice: {exc}\n"
             f"Make sure extractor.py is at  src/services/extractor.py")


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
            print(f"[info]  Auto-selected PDF: {chosen.name}")
            return chosen
    
    sys.exit("[error] No PDF found. Pass a path:  python tests/test_phase1.py your.pdf")

def _print_parameters(parameters:list) -> None:
    """Formated the extracted test parameters into terminal grid."""
    if not parameters:
        print("[warning] No parameter found!")
        return

    col = "{:<6} | {:<35} | {:>10} | {:>10} | {:>10} | {:>10}"
    print(col.format("ID", "Extracted Data (Truncated)", "x0", "y0", "x1", "y1"))
    print("  " + "─" * 80)

    limit = min(10, len(parameters))
    for i, param in enumerate(parameters[:limit], 1):
        safe_text = (param.text[:32] + '...') if len(param.text) > 35 else param.text
        safe_text = safe_text.replace('\n', ' ').replace('\r', '')
        
        print(col.format(
            f"[{i:02d}]",
            safe_text,
            f"{param.x0:.1f}", f"{param.y0:.1f}",
            f"{param.x1:.1f}", f"{param.y1:.1f}"
        ))

    if len(parameters) > 15:
        print(f"  ... and {len(parameters) - 10} more records (Check JSON for full dump).")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_text_extraction() -> None:
    # -- CLI args (Enable running specific files from terminal)
    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else None
    pdf_path = _resolve_pdf(pdf_arg)
    print(f"\n[info] TARGET PDF → {pdf_path.name} ")

    # -- Setup Debug / Output Directory
    debug_dir = PROJECT_ROOT / "debug" 
    debug_dir.mkdir(exist_ok=True)
    output_file = debug_dir / "temp_extracted_data.json"
    
    # -- Wipe old data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([], f)
        print(f"[info] 🧹 Cleaned previous data from: debug\\{output_file.name}")
        
    # -- Run the extractor
    print("\n" + "═" * 70)
    print("  Phase 1 — PDF Parameter Extraction (PDFExtractor)")
    print("═" * 70)
    
    extractor = PDFExtractor(str(pdf_path))
    parameters = extractor.extract_text_parameters()
    
    # -- Results
    print(f"Successfully extracted {len(parameters)} text parameters.\n")
    if parameters:
        _print_parameters(parameters)
        
        # -- Save to JSON 
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in parameters], f, indent=4)
            
        print(f"\n[done]  All extracted data has been safely dumped to → {output_file.relative_to(PROJECT_ROOT)}")
    else:
        print("[warning] No text parameters extracted. The page might be raster scan or empty.")
    
    
if __name__ == "__main__":
    test_text_extraction()
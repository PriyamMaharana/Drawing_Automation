import fitz
import re

def run_pre_flight_check(page: fitz.Page, page_num: int) -> str:
    """
    Runs before the Matrix to catch Doomsday Scenarios from uncontrollable OEM PDFs.
    Returns: "CLEAN", "RASTER_SCAN", "CORRUPT_FONT", or "VECTOR_BOMB".
    """
    text_dict = page.get_text("dict")
    blocks = text_dict.get("blocks", [])
    paths = page.get_drawings()
    images = page.get_images()
    
    # 1. THE RASTER WRAPPER (Scanned PDF with no native data)
    if len(paths) == 0 and len(blocks) == 0 and len(images) > 0:
        print(f"  -> [PRE-FLIGHT] Page {page_num} ❌ FAULT: Scanned Image PDF detected. No native vector/text data.")
        return "RASTER_SCAN"

    # 2. THE VECTOR HATCHING BOMB (Memory Crash Preventer)
    if len(paths) > 50000:
        print(f"  -> [PRE-FLIGHT] Page {page_num} ⚠️ WARNING: Vector Bomb detected ({len(paths)} paths). Engaging Circuit Breaker.")
        return "VECTOR_BOMB"

    # 3. THE BROKEN FONT ENCODING (Gibberish Trap)
    raw_text = page.get_text("text").strip()
    if len(raw_text) > 100:
        # Count standard alphanumeric + common engineering punctuation
        standard_chars = len(re.findall(r'[a-zA-Z0-9\s\.\,\-\+\±\Ø\°\(\)\:\_]', raw_text))
        gibberish_ratio = 1.0 - (standard_chars / len(raw_text))
        
        # If >35% of the text is unreadable/corrupt Unicode symbols, halt extraction.
        if gibberish_ratio > 0.35:
            print(f"  -> [PRE-FLIGHT] Page {page_num} ❌ FAULT: Broken CAD Font Encoding ({gibberish_ratio*100:.1f}% Gibberish).")
            return "CORRUPT_FONT"

    # 4. THE SHATTERED CAD WARNING
    if len(paths) > 1000:
        # Do a blazing fast check to see if ANY curves exist
        has_curves = any(item[0] in ("c", "v", "y") for path in paths for item in path["items"])
        if not has_curves:
            print(f"  -> [PRE-FLIGHT] Page {page_num} ⚠️ WARNING: Shattered CAD detected (0 curves, {len(paths)} lines). Export quality degraded.")
            # We still return CLEAN because our Matrix is strong enough to rescue it!
            return "CLEAN"

    # THE FIX: We must actually tell the terminal that the page passed!
    print(f"  -> [PRE-FLIGHT] - [CLEAN] Page {page_num} CLEAN: Health check passed.")
    return "CLEAN"
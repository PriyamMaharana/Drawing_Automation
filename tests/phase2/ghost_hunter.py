import sys
import fitz
from pathlib import Path

# --- INJECT PROJECT ROOT ---
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def hunt_ghosts(pdf_filename: str):
    print("=" * 60)
    print(f"  PHASE 2 DIAGNOSTIC: HUNTING GHOSTS IN {pdf_filename}")
    print("=" * 60)

    pdf_path = PROJECT_ROOT / "resources" / "sample_data" / pdf_filename
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    doc = fitz.open(str(pdf_path))
    page = doc[0] # Scanning Page 1

    # 1. Hunt for 3D Models & Specialized Annotations
    print("\n▶ HUNTING ANNOTATIONS (3D Models, Stamps, CAD Layers)...")
    annots = list(page.annots())
    if not annots:
        print("   None found.")
    else:
        for a in annots:
            print(f"   - Found: {a.type[1]} | Bounding Box: {a.rect}")

    # 2. Hunt for Deep Exhaustive Images (Bypassing get_image_info)
    print("\n▶ HUNTING RAW/INLINE IMAGES...")
    raw_images = page.get_images(full=True)
    if not raw_images:
        print("   None found.")
    else:
        print(f"   - Found {len(raw_images)} raw image objects embedded in the binary.")

    # 3. Hunt for PDF Layers (Optional Content Groups)
    print("\n▶ HUNTING HIDDEN CAD LAYERS (OCGs)...")
    layers = doc.get_ocgs()
    if not layers:
        print("   No hidden CAD layers found.")
    else:
        for layer in layers.values():
            print(f"   - Layer Name: {layer.get('name', 'Unknown')} | State: {layer.get('on', True)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Change this to ch2.pdf or ch3.pdf to find out what's missing!
    hunt_ghosts("1.pdf")


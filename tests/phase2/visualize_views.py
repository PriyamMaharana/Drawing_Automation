import sys
import json
import cv2
import numpy as np
import fitz
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def visualize_phase2_views(pdf_path: Path):
    p2_json_path = PROJECT_ROOT / "debug" / "results" / "phase2" / f"{pdf_path.stem}_phase2.json"
    output_dir = PROJECT_ROOT / "debug" / "crops"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not p2_json_path.exists():
        print(f"❌ Error: {p2_json_path.name} not found. Run the pipeline first.")
        return

    with open(p2_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)["output"]
        isolated_views = data.get("isolated_views", [])
        page_num = data.get("page_number", 1)

    if not isolated_views:
        print("⚠️ Warning: No isolated views found in JSON.")
        return

    doc = fitz.open(str(pdf_path))
    page = doc[page_num - 1]
    
    render_dpi = 400
    scale = render_dpi / 72.0
    pix = page.get_pixmap(dpi=render_dpi, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    
    if pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    for idx, view in enumerate(isolated_views):
        bbox = view.get("bounding_box")
        name = view.get("view_name", f"View {idx}")
        if not bbox: continue
        
        x0 = int(bbox[0] * scale)
        y0 = int(bbox[1] * scale)
        x1 = int(bbox[2] * scale)
        y1 = int(bbox[3] * scale)

        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 4)
        
        label_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
        cv2.rectangle(img, (x0, y0 - 40), (x0 + label_size[0] + 10, y0), (0, 255, 0), -1)
        cv2.putText(img, name, (x0 + 5, y0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

    output_file = output_dir / f"{pdf_path.stem}_PHASE2_VIEWS.jpg"
    cv2.imwrite(str(output_file), img)
    print(f"✅ Success! Tracker image saved to: {output_file}")
    
if __name__ == "__main__":
    sample_dir = PROJECT_ROOT / "resources" / "sample_data"
    test_pdfs = list(sample_dir.glob("*.pdf"))
    
    for pdf in test_pdfs: visualize_phase2_views(pdf)
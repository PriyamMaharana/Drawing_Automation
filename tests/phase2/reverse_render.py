import sys
import json
import cv2
import numpy as np
from pathlib import Path

# --- INJECT PROJECT ROOT ---
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
def compute_bezier_points(p0, p1, p2, p3, scale, num_points=20):
    pts = []
    for t in np.linspace(0, 1, num_points):
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        pts.append([int(x * scale), int(y * scale)])
    return np.array(pts, dtype=np.int32)

def run_reverse_render(json_filename: str):
    print("=" * 60)
    print(f"  PHASE 2: REVERSE RENDER VISUALIZER ({json_filename})")
    print("=" * 60)

    json_path = PROJECT_ROOT / "debug" / "results" / "phase2" / json_filename
    output_path = PROJECT_ROOT / "debug" / "results" / "phase2" / f"RENDERED_{json_path.stem}.png"

    if not json_path.exists():
        print(f"❌ Error: Could not find {json_filename}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)["output"]
        
    scale = 1.0
    
    # 1. USE EXACT PAGE DIMENSIONS FROM JSON
    page_dims = data.get("page_dimensions", {})
    raw_w = page_dims.get("width", 2000) 
    raw_h = page_dims.get("height", 1500)
    
    canvas_w = int(raw_w * scale)
    canvas_h = int(raw_h * scale)
    canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 255

    print(f"▶ Canvas Locked to Absolute PDF Size: {canvas_w} x {canvas_h}")

    print("▶ Rendering High-Fidelity Geometry...")
    paths = data.get("path_elements", [])
    for path in paths:
        is_fill = path.get("path_type") in ("fill", "both")
        color = (230, 230, 230) if is_fill else (255, 0, 0)
        thickness = -1 if is_fill else 1
        
        for item in path["items"]:
            op = item[0]
            if op == "l":
                coords = item[1]
                pt1 = (int(coords[0][0] * scale), int(coords[0][1] * scale))
                pt2 = (int(coords[1][0] * scale), int(coords[1][1] * scale))
                cv2.line(canvas, pt1, pt2, color, 1)
            elif op == "re":
                r = item[1]
                pt1 = (int(r[0] * scale), int(r[1] * scale))
                pt2 = (int(r[2] * scale), int(r[3] * scale))
                cv2.rectangle(canvas, pt1, pt2, color, thickness)
            elif op == "qu":
                coords = item[1]
                pts = np.array([[int(c[0]*scale), int(c[1]*scale)] for c in coords], dtype=np.int32)
                if is_fill: cv2.fillPoly(canvas, [pts], color)
                else: cv2.polylines(canvas, [pts], True, color, 1)
            elif op == "c":
                coords = item[1]
                if len(coords) == 4:
                    pts = compute_bezier_points(coords[0], coords[1], coords[2], coords[3], scale)
                    if is_fill: cv2.fillPoly(canvas, [pts], color)
                    else: cv2.polylines(canvas, [pts], False, color, 1)

    print("▶ Printing Actual Text Strings...")
    texts = data.get("raw_characters", [])
    for text in texts:
        bx = text["bbox"]
        txt_str = text["text"]
        
        x = int(bx[0] * scale)
        y = int(bx[3] * scale) 
        
        extracted_font_size = text.get("font_size", 10)
        cv2_font_scale = (extracted_font_size * scale) * 0.035

        cv2.putText(canvas, txt_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, cv2_font_scale, (0, 100, 0), 1, cv2.LINE_AA)

    
    print("▶ Rendering Image Fallback Zones & OCR Text...") 
    images = data.get("image_elements", [])
    for img in images:
        bx = img["bbox"]
        pt1 = (int(bx[0] * scale), int(bx[1] * scale))
        pt2 = (int(bx[2] * scale), int(bx[3] * scale))
        
        cv2.rectangle(canvas, pt1, pt2, (255, 0, 255), 2)
        
        ocr_text = img.get("ocr_text", [])
        for ocr in ocr_text:
            obx = ocr["bbox"]
            txt_str = ocr["text"]
            
            x = int(obx[0] * scale)
            y = int(obx[3] * scale)
            
            box_height = obx[3] - obx[1]
            cv2_font_scale = box_height * 0.04
            
            cv2.putText(canvas, txt_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, max(0.3, cv2_font_scale), (0, 128, 255), 1, cv2.LINE_AA)
    
    cv2.imwrite(str(output_path), canvas)
    print(f"✅ Render Complete! Open: {output_path.name}")
    

if __name__ == "__main__":
    run_reverse_render("ch3_phase2.json")
    
    
    
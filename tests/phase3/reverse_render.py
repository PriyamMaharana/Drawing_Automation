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

def run_phase3_render(json_filename: str):
    print("=" * 60)
    print(f"  PHASE 3: SEMANTIC REVERSE RENDERER ({json_filename})")
    print("=" * 60)

    output_path = json_path.parent / f"RENDERED_{json_path.stem}.png"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    data = data.get("output", data)
        
    scale = 1.5
    
    page_dims = data.get("page_dimensions", {})
    raw_w = page_dims.get("width", 2000) 
    raw_h = page_dims.get("height", 1500)
    
    canvas_w = int(raw_w * scale)
    canvas_h = int(raw_h * scale)
    canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 255

    print("▶ Rendering High-Fidelity Geometry...")
    paths = data.get("path_elements", data.get("paths", []))
    print(f"▶▶ Found {len(paths)} CAD geometry paths.")
    
    for path in paths:
        is_fill = path.get("path_type") in ("fill", "both")
        color = (220, 220, 220) if is_fill else (255, 0, 0)
        
        shape_thickness = -1 if is_fill else 1
        line_thickness = 1
        
        for item in path.get("items", []):
            op = item[0]
            if op == "l": # straight lines
                coords = item[1]
                pt1 = (int(coords[0][0] * scale), int(coords[0][1] * scale))
                pt2 = (int(coords[1][0] * scale), int(coords[1][1] * scale))
                cv2.line(canvas, pt1, pt2, color, line_thickness)
            elif op == "re": # rectangle
                r = item[1]
                pt1 = (int(r[0] * scale), int(r[1] * scale))
                pt2 = (int(r[2] * scale), int(r[3] * scale))
                cv2.rectangle(canvas, pt1, pt2, color, shape_thickness)
            elif op == "c": # curves & circle
                coords = item[1]
                if len(coords) == 4:                
                    p0, p1, p2, p3 = coords[0], coords[1], coords[2], coords[3]
                    pts = compute_bezier_points(p0, p1, p2, p3, scale)
                    cv2.polylines(canvas, [pts], False, color, line_thickness)
                else:
                    pts = np.array([[int(c[0]*scale), int(c[1]*scale)] for c in coords], dtype=np.int32)
                    cv2.polylines(canvas, [pts], False, color, line_thickness)
            elif op == "qu": # quadilaterals / filled polygons / arrowheads
                coords = item[1]
                pts = np.array([[int(c[0]*scale), int(c[1]*scale)] for c in coords], dtype=np.int32)
                if is_fill: 
                    cv2.fillPoly(canvas, [pts], color)
                else: 
                    cv2.polylines(canvas, [pts], True, color, line_thickness)
            

    print("▶ Rendering Clean Semantic Lines...")
    semantic_lines = data.get("semantic_lines", [])
    print(f"▶▶ Found {len(semantic_lines)} clean text rows.")
    
    for line in semantic_lines:
        bx = line["bbox"]
        txt_str = line["text"]
        
        # Draw a nice clean box around the entire glued sentence
        pt1 = (int(bx[0] * scale), int(bx[1] * scale))
        pt2 = (int(bx[2] * scale), int(bx[3] * scale))
        cv2.rectangle(canvas, pt1, pt2, (200, 200, 200), 1) 
        
        x = int(bx[0] * scale)
        y = int(bx[3] * scale) 
        
        # FORCE uniform, readable text sizing so giant bounding boxes don't ruin the image
        cv2_font_scale = 0.4 * scale 
        
        # Print the cleaned text in Dark Blue
        cv2.putText(canvas, txt_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, cv2_font_scale, (150, 0, 0), 1, cv2.LINE_AA)
        
    cv2.imwrite(str(output_path), canvas)
    print(f"✅ Render Complete! Open: {output_path.name}")
    
if __name__ == "__main__":
    phase3_results_dir = PROJECT_ROOT / "debug" / "results" / "phase3"
    json_targets = list(phase3_results_dir.glob("*_phase3.json"))
    if not json_targets:
        print(f"❌ Error: No validation payloads found in {phase3_results_dir}")
    else:
        for json_path in json_targets:
            run_phase3_render(json_path)
    
    
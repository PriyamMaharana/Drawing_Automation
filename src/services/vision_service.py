import os
import cv2
import numpy as np
import fitz  # PyMuPDF
import re
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  TUNABLE CONSTANTS (Semantic Text Masking)
# ─────────────────────────────────────────────────────────────────────────────
RENDER_DPI = 300
BLEND_ALPHA_ORIG = 0.80
BLEND_ALPHA_MASK = 0.40

MIN_AREA_FRAC = 0.01  
MAX_AREA_FRAC = 0.60  

class VisionProcessor:
    """
    Enterprise Semantic Vision backend. 
    Uses 'Semantic Text Classification' and outputs Polygonal Contours 
    to perfectly 'shrink-wrap' complex L-shaped corporate tables without 
    boxing in adjacent CAD geometry.
    """

    def _is_corporate_text(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False 

        upper_text = text.upper()
        
        keywords = [
            "MATERIAL", "NOTE", "DETAIL", "TOLERANCE", "ASSY", "SHAFT", 
            "DRAWING", "WEIGHT", "SCALE", "PART", "DATE", "SHEET", 
            "PROJECTION", "TITLE", "NAME", "REVISION", "DESCRIPTION", 
            "QTY", "TATA", "ASHOK", "LEYLAND", "EICHER", "BILL OF", 
            "VEHICLE", "MODEL", "STD", "REF", "SIGN", "APP", "FORMAT",
            "REV", "CHKD", "DRAWN", "APPD", "NO.", "UNBALANCE", "FINISH"
        ]
        if any(k in upper_text for k in keywords):
            return True

        cad_dim_pattern = re.compile(
            r'^\s*[\(\[]?'                
            r'([A-Z]{1,2}|[\Ø\±\°])?'     
            r'\s*\d+(\.\d+)?'             
            r'(\s*[xX\*]\s*\d+(\.\d+)?)?' 
            r'[\°]?'                      
            r'[\)\]]?\s*$'                
        )
        
        if cad_dim_pattern.match(upper_text):
            return False
            
        cad_tol_pattern = re.compile(r'^\s*[\±\+\-]\s*\d+(\.\d+)?\s*$')
        if cad_tol_pattern.match(upper_text):
            return False 
            
        if len(text) <= 3 and not any(c.isalpha() for c in text):
            return False

        return True

    def process_page(
        self,
        page: fitz.Page,
        source_filename: str,
    ) -> List[Dict[str, Any]]:
        
        gray = self._render_page(page)
        h, w = gray.shape
        scale = RENDER_DPI / 72.0
        page_area = h * w
        
        semantic_map = np.zeros((h, w), dtype=np.uint8)
        
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  
                block_text = "".join(
                    span.get("text", " ") + " "
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                )
                
                if self._is_corporate_text(block_text):
                    bx0, by0, bx1, by1 = block["bbox"]
                    px0, py0 = int(bx0 * scale), int(by0 * scale)
                    px1, py1 = int(bx1 * scale), int(by1 * scale)
                    cv2.rectangle(semantic_map, (px0, py0), (px1, py1), 255, -1)
            
        melt_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 60))
        dense_text_zones = cv2.dilate(semantic_map, melt_kernel, iterations=1)
        
        contours, _ = cv2.findContours(dense_text_zones, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        inv_scale = 72.0 / RENDER_DPI
        table_coordinates = []
        debug_mask = np.zeros_like(gray)
        
        for c in contours:
            area = cv2.contourArea(c)
            
            if area < (page_area * MIN_AREA_FRAC): continue
            if area > (page_area * MAX_AREA_FRAC): continue
            
            # THE POLYGONAL SHRINK-WRAP
            # This simplifies the jagged edge of the contour into clean, straight lines
            # without forcing it into a strict rectangle.
            epsilon = 0.005 * cv2.arcLength(c, True)
            approx_polygon = cv2.approxPolyDP(c, epsilon, True)
            
            poly_points = []
            for pt in approx_polygon:
                px, py = pt[0]
                # Scale back to PDF points and safely clamp
                x_pdf = min(max(0, px * inv_scale), page.rect.width)
                y_pdf = min(max(0, py * inv_scale), page.rect.height)
                poly_points.append([float(x_pdf), float(y_pdf)])
                
            table_coordinates.append({
                "type": "polygon",
                "vertices": poly_points
            })
            
            # Draw the exact polygon shape onto the debug mask
            cv2.drawContours(debug_mask, [approx_polygon], -1, 255, -1)
            
        # THE CORPORATE ANCHOR (Converted to a Polygon)
        anchored_x0 = float(page.rect.width * 0.70)
        anchored_y0 = float(page.rect.height * 0.85)
        w_pdf = float(page.rect.width)
        h_pdf = float(page.rect.height)
        
        anchor_vertices = [
            [anchored_x0, anchored_y0],
            [w_pdf, anchored_y0],
            [w_pdf, h_pdf],
            [anchored_x0, h_pdf]
        ]
        
        table_coordinates.append({
            "type": "polygon", 
            "vertices": anchor_vertices
        })
        
        cv2.rectangle(
            debug_mask,
            (int(anchored_x0 * scale), int(anchored_y0 * scale)),
            (int(w_pdf * scale), int(h_pdf * scale)),
            255, -1
        )
        
        self._write_debug_overlay(gray, debug_mask, source_filename)
        del gray, semantic_map, dense_text_zones
        return table_coordinates

    @staticmethod
    def _render_page(page: fitz.Page) -> np.ndarray:
        zoom = RENDER_DPI / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 3: return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        if pix.n == 4: return cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        return img

    @staticmethod
    def _write_debug_overlay(gray: np.ndarray, debug_mask: np.ndarray, source_filename: str) -> str:
        project_root = Path(__file__).resolve().parent.parent.parent
        debug_dir = project_root / "debug" / "overlay_mask"
        debug_dir.mkdir(exist_ok=True, parents=True)

        original_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        red_layer = np.zeros_like(original_bgr)
        red_layer[debug_mask == 255] = (0, 0, 255)

        blended = cv2.addWeighted(original_bgr, BLEND_ALPHA_ORIG, red_layer, BLEND_ALPHA_MASK, 0)
        
        basename = os.path.splitext(os.path.basename(source_filename))[0]
        timestamp = datetime.now().strftime("%m%d_%H%M")
        out_path = os.path.join(debug_dir, f"{basename}_{timestamp}_overlay.jpg")
        cv2.imwrite(out_path, blended)
        return out_path

def process_pdf(pdf_path: str) -> List[List[Dict[str, Any]]]:
    processor = VisionProcessor()
    results: List[List[Dict[str, Any]]] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            zones = processor.process_page(page, pdf_path)
            results.append(zones)
    return results


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry-point  (python src/services/vision_service.py drawing.pdf)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python vision_service.py <path/to/drawing.pdf>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    print(f"\nProcessing: {pdf_file}")
    all_zones = process_pdf(pdf_file)

    print("\n── Results (PDF points at 72 DPI) ──────────────────────────────")
    for i, zones in enumerate(all_zones):
        print(f"Page {i + 1}:")
        for z in zones:
            print(f"  {json.dumps(z)}")

    print("\nDebug overlays written to <project_root>/debug/overlay_mask/")


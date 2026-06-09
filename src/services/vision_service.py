import os
import cv2
import numpy as np
import fitz  # PyMuPDF
import re
import math
import json
import logging
from scipy.spatial import cKDTree
from typing import Any, List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ─────────────────────────────────────────────────────────────────────────────
#  DATA STRUCTURES (JSON SCHEMA)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class Point:
    x: float
    y: float

@dataclass
class Tolerance:
    symmetric: Optional[str] = None
    upper: Optional[str] = None
    lower: Optional[str] = None

@dataclass
class DimensionEntity:
    id: str
    page: int
    type: str
    specification: str
    tolerance: Optional[Tolerance]
    reference_dimension: bool
    raw_text: str
    bbox: BoundingBox
    center: Point
    
    # Internal routing variables (Not exported to JSON)
    _base_token: tuple = None
    _tol_tokens: List[tuple] = None

# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC EXTRACTOR ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class VisionProcessor:
    def __init__(self, render_dpi: int = 600, debug: bool = True):
        self.render_dpi = render_dpi
        self.debug = debug
        self.scale = self.render_dpi / 72.0
        self.inv_scale = 72.0 / self.render_dpi
        
        # Spatial clustering threshold (Max distance a tolerance can be from a base dim)
        self.merge_radius_px = 15.0 * (self.render_dpi / 25.4) 
        
        # 1. Base Dimensions (Strict Whitelist)
        # Matches: 14.5, Ø153, R10, M12X1.5, 25°, (445), 4XØ13
        self.base_dim_re = re.compile(
            r'^[\(\[]?(?:[0-9]+\s*[xX]\s*)?(?:SR|R|M|S\u2205)?([A-Za-z]{1,2})?[\Ø\ø\Φ\φ\⌀]?[0-9]*\.?[0-9]+(?:\s*[xX\*×]\s*[0-9]*\.?[0-9]+)?[\°]?[\)\]]?$'
        )
        
        # 2. Tolerances
        self.tol_re = re.compile(r'^(?:\+|\-|±)[0-9]*\.?[0-9]+$')
        
        # 3. GD&T Symbols
        self.gdt_re = re.compile(r'^[⌖⌯⌒⌔⏥⟂∥∠⌭⌮⌢⌓]$')
        
        # 4. Units & Keywords to Reject (Blacklist)
        units = r'Kg|kg|Gram|g|Nm\.?|RPM|rpm|MPa|Bar|psi|Litre|Liter|mm|cm|in'
        kws = r'VIEW|SECTION|DETAIL|NOTE|NOTES|TECHNICAL|DETAILS|MATERIAL|DESCRIPTION|APPROVED|DRAWING|REMARKS|CUSTOMER|PART|NUMBER|VEHICLE|MODEL|SURFACE|FINISH|HOLES|THRU|PCD|REF|TYP|EQ\s*SP|ASSY|BORE|DEPTH'
        self.reject_re = re.compile(rf'^(?:{units}|{kws})$', re.IGNORECASE)
        
        self.shield_re = re.compile(r'^\(.*\)$')

    def process_page(self, page: fitz.Page, source_filename: str, page_idx: int) -> List[Dict[str, Any]]:
        if page.rotation != 0:
            page.set_rotation(0)

        # Stage 1: High Res Rendering
        gray = self._render_page(page)
        page_h, page_w = gray.shape  
        
        # Stage 2: Raw OCR Token Extraction
        raw_words = list(page.get_text("words"))
        
        # Metrics for HUD
        m_total = len(raw_words)
        m_rejected = 0
        
        # Stage 3: Token Classification
        base_dims, tolerances, gdts, rejected = [], [], [], []
        
        for w in raw_words:
            text = w[4].strip()
            
            # Reject single-digit balloons (e.g. '1', '2', '3')
            if len(text) == 1 and text.isdigit():
                rejected.append(w)
                m_rejected += 1
                continue
            
            # Reject long serial/part numbers (e.g. '508841120406')
            if len(text) > 6 and text.isdigit():
                rejected.append(w)
                m_rejected += 1
                continue
            
            # Rule 3, 4, 5: Reject units, keywords, and text
            if self.reject_re.match(text) or text.isalpha():
                rejected.append(w)
                m_rejected += 1
                continue
                
            if self.base_dim_re.match(text):
                base_dims.append(w)
            elif self.tol_re.match(text):
                tolerances.append(w)
            elif self.gdt_re.match(text):
                gdts.append(w)
            else:
                rejected.append(w)
                m_rejected += 1

        # Stage 4: Dimension Reconstruction (Clustering)
        entities = self._reconstruct_dimensions(base_dims, tolerances, page_idx + 1)
        
        # Stage 5: Semantic Parsing
        export_payload = []
        for entity in entities:
            self._parse_semantics(entity)
            export_payload.append(self._to_json_dict(entity))

        # Stage 6: Debug Image Generation
        if self.debug:
            self._generate_audit_image(
                gray, entities, rejected, 
                source_filename, page_idx, 
                m_total, m_rejected
            )
            
        return export_payload

    # ─────────────────────────────────────────────────────────
    # STAGE 4: CLUSTERING ALGORITHM
    # ─────────────────────────────────────────────────────────
    def _reconstruct_dimensions(self, base_dims: list, tolerances: list, page_num: int) -> List[DimensionEntity]:
        entities = []
        dim_counter = 1
        
        # Initialize an entity for every base dimension
        for w in base_dims:
            bx0, by0, bx1, by1 = [coord * self.scale for coord in w[:4]]
            
            ent = DimensionEntity(
                id=f"DIM_{dim_counter:04d}",
                page=page_num,
                type="linear_dimension", # Default, overridden in parsing
                specification="",
                tolerance=None,
                reference_dimension=False,
                raw_text="",
                bbox=BoundingBox(bx0, by0, bx1, by1),
                center=Point((bx0+bx1)/2, (by0+by1)/2),
                _base_token=w,
                _tol_tokens=[]
            )
            entities.append(ent)
            dim_counter += 1

        # Nearest Neighbor Search for Tolerances
        if entities and tolerances:
            # We look for dimensions that are to the LEFT of the tolerance
            # Anchor point for base dim = Right-Center edge
            base_anchors = np.array([
                [e.bbox.x2, e.center.y] for e in entities
            ], dtype=np.float64)
            tree = cKDTree(base_anchors)

            for t in tolerances:
                tx0, ty0, tx1, ty1 = [coord * self.scale for coord in t[:4]]
                t_anchor = [tx0, (ty0+ty1)/2] # Left-Center edge of tolerance
                
                distances, indices = tree.query(t_anchor, k=1, distance_upper_bound=self.merge_radius_px)
                
                if distances != float('inf'):
                    target_entity = entities[indices]
                    target_entity._tol_tokens.append(t)
                    
                    # Expand the bounding box of the group
                    target_entity.bbox.x1 = min(target_entity.bbox.x1, tx0)
                    target_entity.bbox.y1 = min(target_entity.bbox.y1, ty0)
                    target_entity.bbox.x2 = max(target_entity.bbox.x2, tx1)
                    target_entity.bbox.y2 = max(target_entity.bbox.y2, ty1)
                    target_entity.center = Point(
                        (target_entity.bbox.x1 + target_entity.bbox.x2)/2,
                        (target_entity.bbox.y1 + target_entity.bbox.y2)/2
                    )

        return entities

    # ─────────────────────────────────────────────────────────
    # STAGE 5: SEMANTIC PARSING
    # ─────────────────────────────────────────────────────────
    def _parse_semantics(self, entity: DimensionEntity) -> None:
        base_text = entity._base_token[4].strip()
        
        # 1. Rule 2: Brackets
        if self.shield_re.match(base_text):
            entity.reference_dimension = True
            base_text = base_text[1:-1] # Strip brackets
            
        # 2. Type Classification
        if 'M' in base_text.upper() and 'X' in base_text.upper():
            entity.type = "thread"
        elif 'R' in base_text.upper():
            entity.type = "radius"
        elif 'Ø' in base_text or '⌀' in base_text:
            entity.type = "diameter"
        elif '°' in base_text:
            entity.type = "angle"
            
        entity.specification = base_text
        entity.raw_text = base_text
        
        # 3. Tolerance Parsing
        if entity._tol_tokens:
            entity.tolerance = Tolerance()
            for t in entity._tol_tokens:
                tol_str = t[4].strip()
                entity.raw_text += f" {tol_str}"
                
                if '±' in tol_str:
                    entity.tolerance.symmetric = tol_str
                elif tol_str.startswith('+'):
                    entity.tolerance.upper = tol_str
                elif tol_str.startswith('-'):
                    entity.tolerance.lower = tol_str

    def _to_json_dict(self, entity: DimensionEntity) -> Dict[str, Any]:
        # Convert internal units back to PDF space (72 DPI) for JSON
        return {
            "id": entity.id,
            "page": entity.page,
            "type": entity.type,
            "specification": entity.specification,
            "tolerance": asdict(entity.tolerance) if entity.tolerance else None,
            "reference_dimension": entity.reference_dimension,
            "raw_text": entity.raw_text,
            "bbox": {
                "x1": round(entity.bbox.x1 * self.inv_scale, 2),
                "y1": round(entity.bbox.y1 * self.inv_scale, 2),
                "x2": round(entity.bbox.x2 * self.inv_scale, 2),
                "y2": round(entity.bbox.y2 * self.inv_scale, 2)
            },
            "center": {
                "x": round(entity.center.x * self.inv_scale, 2),
                "y": round(entity.center.y * self.inv_scale, 2)
            }
        }

    # ─────────────────────────────────────────────────────────
    # STAGE 6: DEBUG AUDIT RENDERING
    # ─────────────────────────────────────────────────────────
    def _generate_audit_image(self, gray: np.ndarray, entities: List[DimensionEntity], rejected: list, filename: str, page_idx: int, m_total: int, m_rejected: int):
        img_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        overlay = img_bgr.copy()
        
        # 1. RED ZONES (Rejected Tokens)
        for r in rejected:
            x0, y0, x1, y1 = [int(coord * self.scale) for coord in r[:4]]
            cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 0, 255), -1)
            
        # Blend Red zones with 25% opacity
        cv2.addWeighted(overlay, 0.25, img_bgr, 0.75, 0, img_bgr)
        
        # 2. DRAW ENTITIES
        for ent in entities:
            # Yellow Box: Group Bounding Box
            gx0, gy0, gx1, gy1 = int(ent.bbox.x1), int(ent.bbox.y1), int(ent.bbox.x2), int(ent.bbox.y2)
            cv2.rectangle(img_bgr, (gx0, gy0), (gx1, gy1), (0, 255, 255), 2)
            
            # Green Box: Base Specification
            bx0, by0, bx1, by1 = [int(coord * self.scale) for coord in ent._base_token[:4]]
            cv2.rectangle(img_bgr, (bx0, by0), (bx1, by1), (0, 255, 0), 2)
            
            # Blue Boxes: Tolerances
            for t in ent._tol_tokens:
                tx0, ty0, tx1, ty1 = [int(coord * self.scale) for coord in t[:4]]
                cv2.rectangle(img_bgr, (tx0, ty0), (tx1, ty1), (255, 0, 0), 2)
                
            # Text Label
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0 * (self.render_dpi / 300)
            thickness = max(1, int(2 * (self.render_dpi / 300)))
            cv2.putText(img_bgr, ent.id, (gx0, gy0 - 10), font, font_scale, (0, 0, 0), thickness + 2) # Black outline
            cv2.putText(img_bgr, ent.id, (gx0, gy0 - 10), font, font_scale, (0, 255, 255), thickness) # Yellow text

        # 3. LEGEND HUD
        self._draw_hud(img_bgr, m_total, m_rejected, len(entities), sum(1 for e in entities if e._tol_tokens))

        # Save
        out_dir = Path(os.environ.get("VISION_DEBUG_DIR", Path.cwd() / "debug")) / "audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        basename = os.path.splitext(os.path.basename(filename))[0]
        out_path = out_dir / f"{basename}_page_{page_idx+1:03d}_audit.png"
        cv2.imwrite(str(out_path), img_bgr)
        logging.info(f"Audit Image generated: {out_path}")

    def _draw_hud(self, img: np.ndarray, total: int, rejected: int, dims: int, groups: int):
        h, w = img.shape[:2]
        hud_w, hud_h = int(w * 0.20), int(h * 0.15)
        margin = int(w * 0.02)
        x0, y0 = w - hud_w - margin, margin
        
        # HUD Background
        cv2.rectangle(img, (x0, y0), (x0 + hud_w, y0 + hud_h), (240, 240, 240), -1)
        cv2.rectangle(img, (x0, y0), (x0 + hud_w, y0 + hud_h), (0, 0, 0), 2)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.0 * (self.render_dpi / 300)
        th = max(1, int(2 * (self.render_dpi / 300)))
        line_spacing = int(40 * (self.render_dpi / 300))
        
        cv2.putText(img, "PAGE AUDIT", (x0 + 20, y0 + line_spacing), font, scale*1.2, (0,0,0), th+1)
        cv2.putText(img, f"OCR Tokens      : {total}", (x0 + 20, y0 + line_spacing*3), font, scale, (0,0,0), th)
        cv2.putText(img, f"Rejected Tokens : {rejected}", (x0 + 20, y0 + line_spacing*4), font, scale, (0,0,255), th)
        cv2.putText(img, f"Dimensions      : {dims}", (x0 + 20, y0 + line_spacing*5), font, scale, (0,200,0), th)
        cv2.putText(img, f"Groups          : {groups}", (x0 + 20, y0 + line_spacing*6), font, scale, (0,200,200), th)

    def _render_page(self, page: fitz.Page) -> np.ndarray:
        zoom = self.render_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        
        if pix.n == 1: return img.squeeze()
        elif pix.n == 2: return img[:, :, 0]
        elif pix.n == 3: return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        elif pix.n == 4: return cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        raise ValueError(f"Unexpected channel count: {pix.n}")

# ─────────────────────────────────────────────────────────
# CLI RUNNER
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("Usage: python semantic_extractor.py <path/to/drawing.pdf>")

    pdf_file = sys.argv[1]
    processor = VisionProcessor(render_dpi=600, debug=True)
    
    final_payload = {}
    with fitz.open(pdf_file) as doc:
        for page_index, page in enumerate(doc):
            entities = processor.process_page(page, pdf_file, page_idx=page_index)
            final_payload[f"page_{page_index+1}"] = entities

    out_json = Path(os.environ.get("VISION_DEBUG_DIR", Path.cwd() / "debug")) / f"{Path(pdf_file).stem}_dimensions.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=4, ensure_ascii=False)
        
    logging.info(f"Phase 2 Complete. JSON Schema saved to: {out_json}")
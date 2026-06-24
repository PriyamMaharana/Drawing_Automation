import fitz
import logging
import numpy as np
import cv2
import re
from typing import List, Dict

logger = logging.getLogger(__name__) 

try:
    from core.utils.settings import PlatformSettings
except ImportError as e:
    logger.error(f"Microservices import failure: {e}")

class HybridEngine:
    def __init__(self, y_tolerance: float = 4.0, x_tolerance: float = 10.0):
        self.y_tolerance = y_tolerance
        self.x_tolerance = x_tolerance

    def extract_unified_text(self, page: fitz.Page, clip_rect: fitz.Rect, image_processor=None, ocr_engine=None, debug_path: str = None) -> list:
        logger.info("Igniting Hybrid Extraction (Vector + OCR)...")
        
        vector_blocks = self._extract_vector_text(page, clip_rect)
        
        ocr_blocks = []
        if ocr_engine:
            ocr_blocks = self._extract_ocr_text(page, clip_rect, ocr_engine, image_processor, debug_path)

        unique_blocks = self._deduplicate_blocks(vector_blocks, ocr_blocks)
        unified_lines = self._spatial_merge(unique_blocks)
        
        return unified_lines

    def _extract_vector_text(self, page: fitz.Page, clip_rect: fitz.Rect) -> list:
        blocks = []
        raw_dict = page.get_text("dict", clip=clip_rect)
        
        for block in raw_dict.get("blocks", []):
            if block.get("type") == 0:  
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        bbox = span.get("bbox")
                        
                        # CRITICAL FIX: Removed the 'height >= 4.0' constraint. 
                        # Scaled PDFs compress native text coordinates to < 4.0 points, causing valid dimensions to drop.
                        if text:
                            blocks.append({"text": text, "bbox": bbox, "source": "vector"})
        return blocks

    def _extract_ocr_text(self, page: fitz.Page, clip_rect: fitz.Rect, ocr_engine, image_processor, debug_path: str) -> list:
        blocks = []
        zoom = getattr(PlatformSettings, 'OCR_EXTRACTION_DPI', 300) / getattr(PlatformSettings, 'PDF_BASE_DPI', 72)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
        
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4: img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        elif pix.n == 1: img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        if image_processor and hasattr(image_processor, 'enhance_for_ocr'):
            img_array = image_processor.enhance_for_ocr(img_array)

        ocr_results = ocr_engine.extract_text(img_array)
        scale_factor = getattr(PlatformSettings, 'PDF_BASE_DPI', 72) / getattr(PlatformSettings, 'OCR_EXTRACTION_DPI', 300)
        
        for res in ocr_results:
            text = res.get("text", "").strip()
            if text:
                obbox = res.get("bbox") 
                pdf_x0 = clip_rect.x0 + (obbox[0] * scale_factor)
                pdf_y0 = clip_rect.y0 + (obbox[1] * scale_factor)
                pdf_x1 = clip_rect.x0 + (obbox[2] * scale_factor)
                pdf_y1 = clip_rect.y0 + (obbox[3] * scale_factor)
                blocks.append({"text": text, "bbox": [pdf_x0, pdf_y0, pdf_x1, pdf_y1], "source": "ocr"})
        return blocks

    def _deduplicate_blocks(self, vector_blocks: list, ocr_blocks: list) -> list:
        try:
            from core.dictionaries.cad_dictionary import CADSignatures
            gdt_symbols = CADSignatures.GDT_SYMBOLS
        except ImportError:
            gdt_symbols = ['⌖', '⊥', '⟂', '//', '∥', '∠', '◎', '↗', '⌰', '⌭', '⌯', '▱', '⌓', '○', 'Ⓜ', 'Ⓛ', 'Ⓢ']

        final_blocks = []
        gdt_ocr_blocks = []
        standard_ocr_blocks = []
        
        # Phase 1: Separate OCR blocks into GD&T vs Standard
        for ob in ocr_blocks:
            text = ob["text"]
            # Identify FCF separators '|' and '│' or GD&T shapes that vector extraction misses
            if any(sym in text for sym in gdt_symbols) or '│' in text or '|' in text or '[' in text:
                gdt_ocr_blocks.append(ob)
            else:
                standard_ocr_blocks.append(ob)
                
        # Phase 2: Prioritize OCR for GD&T
        for vb in vector_blocks:
            v_center_x = (vb["bbox"][0] + vb["bbox"][2]) / 2
            v_center_y = (vb["bbox"][1] + vb["bbox"][3]) / 2
            
            is_inside_gdt = False
            # If native vector text falls inside an OCR GD&T frame, suppress the vector text
            for gob in gdt_ocr_blocks:
                gbox = gob["bbox"]
                if gbox[0]-5 <= v_center_x <= gbox[2]+5 and gbox[1]-5 <= v_center_y <= gbox[3]+5:
                    is_inside_gdt = True
                    break
            
            if not is_inside_gdt:
                final_blocks.append(vb)
                
        final_blocks.extend(gdt_ocr_blocks)
        
        # Phase 3: Dedup standard OCR against Vector
        for ob in standard_ocr_blocks:
            oc_x = (ob["bbox"][0] + ob["bbox"][2]) / 2
            oc_y = (ob["bbox"][1] + ob["bbox"][3]) / 2
            
            is_dup = False
            for vb in final_blocks:
                vbox = vb["bbox"]
                if vbox[0]-2 <= oc_x <= vbox[2]+2 and vbox[1]-2 <= oc_y <= vbox[3]+2:
                    is_dup = True
                    break
                    
            if not is_dup:
                final_blocks.append(ob)
                
        return final_blocks

    def _spatial_merge(self, blocks: list) -> list:
        if not blocks: return []
        blocks.sort(key=lambda b: b["bbox"][1])
        
        lines = []
        current_line = [blocks[0]]
        for i in range(1, len(blocks)):
            block = blocks[i]
            prev_block = current_line[-1]
            if abs(block["bbox"][1] - prev_block["bbox"][1]) <= self.y_tolerance:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
        lines.append(current_line)
        
        unified_output = []
        for line in lines:
            line.sort(key=lambda b: b["bbox"][0]) 
            
            entities = []
            current_entity = [line[0]]
            for i in range(1, len(line)):
                b = line[i]
                prev_b = current_entity[-1]
                gap = b["bbox"][0] - prev_b["bbox"][2]
                
                # Split text separated by large gaps > 0.5 inches
                if gap > 40.0:  
                    entities.append(current_entity)
                    current_entity = [b]
                else:
                    current_entity.append(b)
            entities.append(current_entity)

            for ent in entities:
                merged_text = ""
                min_x0, min_y0, max_x1, max_y1 = float('inf'), float('inf'), 0, 0
                for b in ent:
                    merged_text += b["text"] + " "
                    bbox = b["bbox"]
                    min_x0 = min(min_x0, bbox[0])
                    min_y0 = min(min_y0, bbox[1])
                    max_x1 = max(max_x1, bbox[2])
                    max_y1 = max(max_y1, bbox[3])
                    
                unified_output.append({
                    "text": re.sub(r'\s+', ' ', merged_text).strip(),
                    "bbox": [min_x0, min_y0, max_x1, max_y1]
                })
        return unified_output
    
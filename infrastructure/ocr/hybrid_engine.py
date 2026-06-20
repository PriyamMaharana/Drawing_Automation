import fitz
import logging
from typing import List, Dict

logger = logging.getLogger(__name__) 

try:
    from core.utils.settings import PlatformSettings
except ImportError as e:
    logger.error(f"Microservices import failure: {e}")

class HybridEngine:
    
    def extract_unified_text(self, page: fitz.Page, clip_rect: fitz.Rect, 
                             image_processor, ocr_engine, 
                             debug_path: str = None) -> List[Dict]:
        
        native_blocks = page.get_text("dict", clip=clip_rect).get("blocks", [])
        native_char_count = sum(len(span["text"].strip()) for b in native_blocks if b.get("type") == 0 for line in b.get("lines", []) for span in line.get("spans", []))

        is_raster_embedded = False
        for img in page.get_image_info():
            img_bbox = fitz.Rect(img["bbox"])
            intersection = img_bbox.intersect(clip_rect)
            if not intersection.is_empty:
                if (intersection.get_area() / clip_rect.get_area()) > 0.05:
                    is_raster_embedded = True
                    break

        if native_char_count > 3 and not is_raster_embedded:
            logger.info(f"   -> [HybridEngine] Path A: Pure Native Vector Region ({native_char_count} chars).")
            return self._parse_native_blocks(native_blocks)
        else:
            if is_raster_embedded:
                logger.info("   -> [HybridEngine] Path C: Hybrid Vector/Raster detected! Igniting OCR.")
            else:
                logger.info("   -> [HybridEngine] Path B: Flat Raster Region detected. Igniting OCR.")
            
            # --- USE CENTRAL SETTINGS HERE ---
            target_dpi = PlatformSettings.OCR_EXTRACTION_DPI
            
            high_res_pix = page.get_pixmap(dpi=target_dpi, clip=clip_rect, alpha=False)
            img_bytes = high_res_pix.tobytes("png")
            
            if image_processor and ocr_engine:
                clean_img = image_processor.standardize_for_ocr(img_bytes, debug_path=debug_path)
                ocr_lines = ocr_engine.extract_text(clean_img) 
                
                unified_lines = self._scale_ocr_lines(ocr_lines, clip_rect, target_dpi)
                logger.info(f"   -> [HybridEngine] OCR recovered {len(unified_lines)} text blocks.")
                return unified_lines
            return []

    def _parse_native_blocks(self, native_blocks: list) -> List[Dict]:
        unified = []
        for b in native_blocks:
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    text = "".join([span["text"] for span in line["spans"]])
                    if text.strip(): unified.append({"text": text.strip(), "bbox": line["bbox"]})
        return unified

    def _scale_ocr_lines(self, ocr_lines: list, clip_rect: fitz.Rect, ocr_dpi: int) -> List[Dict]:
        unified = []
        # --- USE CENTRAL SETTINGS HERE ---
        scale = PlatformSettings.PDF_BASE_DPI / ocr_dpi
        
        for line in ocr_lines:
            bx0 = clip_rect.x0 + (line["bbox"][0] * scale)
            by0 = clip_rect.y0 + (line["bbox"][1] * scale)
            bx1 = clip_rect.x0 + (line["bbox"][2] * scale)
            by1 = clip_rect.y0 + (line["bbox"][3] * scale)
            unified.append({"text": line["text"], "bbox": [bx0, by0, bx1, by1]})
        return unified
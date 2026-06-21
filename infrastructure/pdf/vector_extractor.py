import fitz
import logging
from pathlib import Path

try:
    from infrastructure.ocr.image_processor import ImageProcessor
    from infrastructure.ocr.tesseract_engine import TesseractEngine
    from core.entities.geometry import BoundingBox, PDFCharacter, PDFPath, VectorPage
    from core.utils.settings import PlatformSettings
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise
    
class PDFVectorExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.image_processor = ImageProcessor()
            self.ocr_engine = TesseractEngine()
        except Exception as e:
            self.logger.error(f"Failed to load OCR Engines: {e}")
        
    def extract_page_vectors(self, pdf_path: Path, drawing_package, clip_rect: fitz.Rect = None) -> VectorPage:
        doc = fitz.open(str(pdf_path))
        
        # Resolve target page (Handles both automated packages and manual integers)
        target_page_num = getattr(drawing_package, "primary_page", 1) if drawing_package else 1
        if isinstance(drawing_package, int): target_page_num = drawing_package
        
        page = doc[target_page_num - 1]
        zone = clip_rect if clip_rect else page.rect
        
        # ---------------------------------------------------------
        # HYBRID ROUTING INTELLIGENCE (Path A, B, C)
        # ---------------------------------------------------------
        native_blocks = page.get_text("dict", clip=zone).get("blocks", [])
        native_char_count = sum(len(s["text"].strip()) for b in native_blocks if b.get("type") == 0 for l in b.get("lines", []) for s in l.get("spans", []))
        
        is_raster_embedded = False
        for img in page.get_image_info():
            img_bbox = fitz.Rect(img["bbox"])
            intersection = img_bbox.intersect(zone)
            if not intersection.is_empty and (intersection.get_area() / zone.get_area()) > 0.05:
                is_raster_embedded = True
                break

        all_raw_tokens = []
        
        # PATH A: Pure Native Vector 
        if native_char_count > 3:
            self.logger.info(f"Extractor | Path A: Harvesting Native Vectors in zone ({native_char_count} chars).")
            all_raw_tokens.extend(self._extract_native_text(page, target_page_num, zone))
            
        # PATH B & C: Raster OCR & Hybrid
        if is_raster_embedded or native_char_count <= 3:
            mode = "Path C (Hybrid)" if is_raster_embedded and native_char_count > 3 else "Path B (Raster)"
            self.logger.info(f"Extractor | {mode}: Raster detected. Igniting 600 DPI OCR...")
            all_raw_tokens.extend(self._extract_and_ocr_zone(page, target_page_num, zone))

        # Harvest geometric lines/circles in the zone
        path_elements = self._extract_native_paths(page, target_page_num, zone) 

        doc.close()
        
        return VectorPage(
            page_number=target_page_num,
            page_width=float(page.rect.width),
            page_height=float(page.rect.height),
            raw_characters=all_raw_tokens, 
            path_elements=path_elements,
            image_elements=[] # No longer needed, handled via Path B
        )

    def _extract_native_text(self, page: fitz.Page, page_num: int, zone: fitz.Rect) -> list[PDFCharacter]:
        characters = []
        blocks = page.get_text("dict", clip=zone)["blocks"]
        for b in blocks:
            if b.get("type") == 0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"].strip()
                        if text:
                            bx = s["bbox"]
                            characters.append(PDFCharacter(
                                text=text,
                                bbox=BoundingBox(float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])),
                                font_name=s.get("font", "Unknown"),
                                font_size=float(s["size"]),
                                confidence=100.0,
                                page_number=page_num
                            ))
        return characters

    def _extract_and_ocr_zone(self, page: fitz.Page, page_num: int, zone: fitz.Rect) -> list[PDFCharacter]:
        target_dpi = PlatformSettings.OCR_EXTRACTION_DPI if hasattr(PlatformSettings, 'OCR_EXTRACTION_DPI') else 600
        pix = page.get_pixmap(clip=zone, dpi=target_dpi, alpha=False)
        
        ocr_tokens = []
        if hasattr(self, 'image_processor') and hasattr(self, 'ocr_engine'):
            clean_img = self.image_processor.standardize_for_ocr(pix.tobytes("png"))
            ocr_data = self.ocr_engine.extract_text(clean_img)
            
            # Scale coordinates back to Native PDF points
            scale = 72.0 / target_dpi
            
            for item in ocr_data:
                bx0 = zone.x0 + (item["bbox"][0] * scale)
                by0 = zone.y0 + (item["bbox"][1] * scale)
                bx1 = zone.x0 + (item["bbox"][2] * scale)
                by1 = zone.y0 + (item["bbox"][3] * scale)
                
                ocr_tokens.append(PDFCharacter(
                    text=item["text"],
                    bbox=BoundingBox(bx0, by0, bx1, by1),
                    font_size=by1 - by0,
                    font_name="OCR_Hybrid",
                    confidence=95.0,
                    page_number=page_num
                ))
        return ocr_tokens

    def _extract_native_paths(self, page: fitz.Page, page_num: int, zone: fitz.Rect) -> list[PDFPath]:
        elements = []
        paths = page.get_drawings(extended=True)
        for p in paths:
            bx = p.get("rect")
            if bx is None or not fitz.Rect(bx).intersects(zone):
                continue

            path_type = "stroke"
            if p.get("type") == "f": path_type = "fill"
            elif p.get("type") == "fs": path_type = "both"
            
            stroke_col = list(p.get("color")) if p.get("color") else None
            fill_col = list(p.get("fill")) if p.get("fill") else None
            
            serialized_items = []
            for item in p.get("items", []):
                op = item[0]                
                if op in ("l", "c", "v", "y"):
                    coords = [[float(pt.x), float(pt.y)] for pt in item[1:]]
                    serialized_items.append([op, coords])
                elif op == "re":
                    rect = item[1]
                    direction = int(item[2])
                    serialized_items.append([op, [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)], direction])
                elif op == "qu":
                    quad = item[1]
                    coords = [[float(pt.x), float(pt.y)] for pt in [quad.ul, quad.ur, quad.ll, quad.lr]]
                    serialized_items.append([op, coords])
                else:
                    serialized_items.append([op])
            
            raw_width = p.get("width")
            safe_width = float(raw_width) if raw_width is not None else 1.0

            elements.append(PDFPath(
                path_type=path_type,
                items=serialized_items,
                bbox=BoundingBox(float(bx.x0), float(bx.y0), float(bx.x1), float(bx.y1)),
                stroke_color=stroke_col,
                fill_color=fill_col,
                line_width=safe_width,
                page_number=page_num
            ))
        return elements
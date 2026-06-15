import sys
import subprocess
import logging
from pathlib import Path

def ensure_package(pip_name: str, import_name: str):
    """Attempts to import a package, and installs it via pip if missing."""
    try:
        __import__(import_name)
    except ImportError:
        logging.warning(f"Package '{import_name}' not found. Installing '{pip_name}'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            logging.info(f"Successfully installed {pip_name}.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install {pip_name}. Please install manually.", exc_info=True)
            sys.exit(1)

ensure_package("PyMuPDF", "fitz")
ensure_package("numpy", "numpy")

import fitz
import numpy as np

try:
    from infrastructure.ocr.engine import run_ocr
    from core.entities.geometry import BoundingBox, PDFCharacter, PDFPath, PDFImage, VectorPage
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    
    
class PDFVectorExtractor:
    """
    PHASE 2: Infrastructure layer responsible for harvesting raw native PDF vectors.
    Operates strictly on the primary drawing page identified by Phase 1.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_page_vectors(self, pdf_path: Path, drawing_package) -> VectorPage:
        doc = fitz.open(str(pdf_path))
        target_page_num = drawing_package.primary_page if drawing_package.primary_page else 1
        
        if not target_page_num:
            logging.error(f"Cannot extract vectors. Phase 1 did not find a primary page for {pdf_path.name}")
            raise ValueError("No primary page identified.")
        
        page = doc[target_page_num - 1]
        
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        
        # -- harvest vector and native text
        logging.info(f"Extractor | Harvesting native data from Page {target_page_num}")
        path_elements = self._extract_native_paths(page, target_page_num) 
        native_chars = self._extract_native_text(page, target_page_num)
        
        # -- harvest images & ocr fallback
        logging.info(f"Extractor | Deep scanning images for OCR fallback...")
        image_elements = self._extract_and_ocr_images(page, pdf_path.stem, target_page_num)
        
        all_raw_tokens = native_chars.copy()
        for img in image_elements:
            all_raw_tokens.extend(img.ocr_text)

        doc.close()
        
        return VectorPage(
            page_number=target_page_num,
            page_width=page_w,
            page_height=page_h,
            raw_characters=all_raw_tokens, 
            path_elements=path_elements,
            image_elements=image_elements
        )
        
    def _extract_and_ocr_images(self, page: fitz.Page, pdf_name: str, page_num: int) -> list[PDFImage]:
        image_elements = []
        raw_rects = []
        
        # 1. Surface Images
        for img in page.get_image_info():
            raw_rects.append(fitz.Rect(img["bbox"]))
            
        # 2. Deep Binary Images
        for img_tuple in page.get_images(full=True):
            xref = img_tuple[0]
            for rect in page.get_image_rects(xref):
                raw_rects.append(rect)

        # 3. Remove Duplicate Bounding Boxes
        unique_rects = [r for i, r in enumerate(raw_rects) if not any(abs(ur.x0 - r.x0) < 1.0 for ur in raw_rects[:i])]

        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        crops_dir = BASE_DIR / "debug" / "crops"
        crops_dir.mkdir(parents=True, exist_ok=True)
        
        # 4. Process Each Image Zone with OCR
        for idx, rect in enumerate(unique_rects):
            pix = page.get_pixmap(clip=rect, dpi=300)
            
            file_path = crops_dir / f"{pdf_name}_p{page_num}_img{idx}.png"
            pix.save(str(file_path))
            self.logger.debug(f" -> Saved Raw Crop: {file_path.name}")
            
            image_bytes = pix.tobytes("png")
            
            self.logger.debug(f" -> Found Image at {rect}. Initiating OpenCV & Tesseract...")
            debug_filename = f"{pdf_name}_p{page_num}_img{idx}_ocr_feed.png"
            ocr_data = run_ocr(image_bytes, debug_name=debug_filename)
            
            scale_x, scale_y = (rect.width / pix.width), (rect.height / pix.height)
            ocr_tokens = []
            
            if ocr_data and 'text' in ocr_data:
                for i in range(len(ocr_data['text'])):
                    text_str = ocr_data['text'][i].strip()
                    conf = float(ocr_data['conf'][i])
                    
                    if text_str and conf > 10:
                        bx0 = rect.x0 + (ocr_data['left'][i] * scale_x)
                        by0 = rect.y0 + (ocr_data['top'][i] * scale_y)
                        bx1 = bx0 + (ocr_data['width'][i] * scale_x)
                        by1 = by0 + (ocr_data['height'][i] * scale_y)
                        
                        ocr_tokens.append(PDFCharacter(
                            text=text_str,
                            bbox=BoundingBox(bx0, by0, bx1, by1),
                            font_size=by1 - by0,
                            font_name="OCR_Fallback",
                            confidence=conf,
                            page_number=page_num
                        ))
            
            image_elements.append(PDFImage(
                bbox=BoundingBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
                width=pix.width, 
                height=pix.height,
                ocr_text=ocr_tokens
            ))
        return image_elements
    
    def _extract_native_text(self, page: fitz.Page, page_num: int) -> list[PDFCharacter]:
        characters = []
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"].strip()
                        if text:
                            bx = s["bbox"]
                            extracted_font = s.get("font", "Unknown")
                            characters.append(PDFCharacter(
                                text=text,
                                bbox=BoundingBox(float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])),
                                font_name=extracted_font,
                                font_size=float(s["size"]),
                                confidence=100.0,
                                page_number=page_num
                            ))
        return characters

    def _extract_native_paths(self, page: fitz.Page, page_num: int) -> list[PDFPath]:
        elements = []
        paths = page.get_drawings(extended=True)
        
        for p in paths:
            bx = p.get("rect")
            if bx is None:
                continue

            path_type = "stroke"
            if p.get("type") == "f": path_type = "fill"
            elif p.get("type") == "fs": path_type = "both"
            
            # Safely extract colors (convert tuples to lists for JSON serialization)
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
            
            # --- Safely Extract Width ---
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
    
    
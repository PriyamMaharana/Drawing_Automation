import sys
import subprocess
import logging
import re
import fitz
import cv2
import numpy as np
from typing import Tuple, List, Dict, Any
from pathlib import Path

def ensure_package(pip_name: str, import_name: str):
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
ensure_package("opencv-python", "cv2")
ensure_package("numpy", "numpy")

try:
    from core.entities.document import DocumentProfile, PageProfile, DrawingPackage
    from rules.cad_dictionary import CADSignatures, OEMSignatures, PaperSizeSignatures
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")

logger = logging.getLogger(__name__)

class DocumentScout:
    """
    PHASE 1: Target Acquisition & Layout Segmentation.
    Executes Pre-Flight Health Checks, calculates Matrix Page Scores, 
    and utilizes OpenCV to map safe geometry zones.
    """
    def __init__(self):
        logging.debug("Initializing Phase 1: Synthesized DocumentScout Engine")
        self.max_search_pages = 5
        
    def analyze_document(self, pdf_path: Path) -> 'DrawingPackage':
        logging.info(f"Phase 1 | Initiating Pipeline for {pdf_path.name}")
        
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            return self._build_failed_package("FILE_NOT_FOUND")

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.critical(f"Failed to open PDF document {pdf_path.name}. File may be corrupted or encrypted: {e}", exc_info=True)
            return self._build_failed_package("CORRUPTED_FILE")

        total_pages = len(doc)
        page_profiles = []
        drawing_pages = []
        primary_page_idx = -1
        highest_score = -999
        
        try:
            for i in range(total_pages):
                try:
                    page = doc[i]
                    score, breakdown, metrics = self._evaluate_page_matrix(page)
                    is_drawing = score > 20
                    
                    status = "✅ ACCEPTED" if is_drawing else "❌ REJECTED"
                    logger.debug(f"  -> [MATRIX] Page {i+1} {status} | Score: {score} | Breakdown: {breakdown}")
                    
                    profile = PageProfile(
                        page_number=i + 1,
                        is_drawing=is_drawing,
                        confidence_score=score,
                        metrics=metrics
                    )
                    page_profiles.append(profile)
                    
                    if is_drawing:
                        drawing_pages.append(i + 1)
                        if score > highest_score:
                            highest_score = score
                            primary_page_idx = i
                            
                except Exception as e:
                    logger.error(f"Evaluation failed on page {i+1} of {pdf_path.name}: {e}", exc_info=True)
                    page_profiles.append(PageProfile(page_number=i+1, is_drawing=False, confidence_score=-999, metrics={}))

            if not drawing_pages:
                logger.warning(f"Pre-Flight Failed: No valid engineering drawing pages detected in {pdf_path.name}.")
                return self._build_failed_package("NO_DRAWINGS_FOUND", page_profiles)

            # 2. Extract Metadata from the Primary Drawing Page
            try:
                primary_page = doc[primary_page_idx]
                raw_text = primary_page.get_text()
                oem = self._detect_oem(raw_text)                
                recommended_dpi = self._calculate_optimal_dpi(primary_page.rect)
                paper_size = "DYNAMIC"   
            except Exception as e:
                logger.error(f"Failed to extract metadata from primary page {primary_page_idx + 1}: {e}", exc_info=True)
                oem, paper_size, recommended_dpi = "UNKNOWN", "UNKNOWN", 400

            logger.info(f"Phase 1 | Target Locked: Page {primary_page_idx + 1} (OEM: {oem}, Size: {paper_size}, DPI: {recommended_dpi}). Initiating OpenCV Mapping...")

            # 3. Perform Deep Spatial Mapping (Red Zones)
            zones = {"MAIN_CANVAS": None, "TITLE_BLOCK": None, "TABLES": []}
            try:
                zones = self._map_zones(primary_page, recommended_dpi)
            except Exception as e:
                logger.error(f"Spatial Mapping failed on page {primary_page_idx + 1}. Proceeding without Red Zone shielding: {e}", exc_info=True)
                
            # 4. Compile the final Drawing Package
            doc_profile = DocumentProfile(
                health_status="CLEAN",
                oem=oem,
                paper_size=paper_size,
                recommended_dpi=recommended_dpi,
                total_pages=total_pages
            )
            
            package = DrawingPackage(
                document_profile=doc_profile,
                primary_page=primary_page_idx + 1,
                drawing_pages=drawing_pages,
                pages=page_profiles,
                spatial_zones=zones
            )
            
            return package
            
        except Exception as e:
            logger.critical(f"Catastrophic failure during Pre-Flight of {pdf_path.name}: {e}", exc_info=True)
            return self._build_failed_package("SYSTEM_FAILURE", page_profiles)
            
        finally:
            doc.close()
            logger.debug(f"Successfully released file locks for {pdf_path.name}")

    def _build_failed_package(self, status: str, page_profiles: list = None) -> 'DrawingPackage':
        return DrawingPackage(
            document_profile=DocumentProfile(health_status=status),
            primary_page=None,
            drawing_pages=[],
            pages=page_profiles or []
        )

    def _evaluate_page_matrix(self, page: fitz.Page) -> Tuple[int, str, dict]:
        score = 0
        breakdown = []
        metrics = {"path_count": 0, "text_length": 0, "ink_ratio": 0.0, "extraction_mode": "NATIVE"}
        
        paths = page.get_drawings()
        text = page.get_text().strip()
        
        path_count = len(paths)
        text_len = len(text)
        
        metrics["path_count"] = path_count
        metrics["text_length"] = text_len
        
        try:            
            if path_count > 1000:
                score += 40
                breakdown.append("Massive Path Density (+40)")
            elif path_count > 100:
                score += 20
                breakdown.append("Standard Path Density (+20)")
            else:
                score -= 20
                breakdown.append("Low Path Density (-20)")
                
            if metrics["path_count"] < 50 and metrics["text_len"] > 1000:
                score -= 50
                breakdown.append("Heavy Text Ratio (-50)")
                
            if re.search(r"[⌖⊥∥◯◿∠⌭⌯⌰◎]", text):
                score += 20
                breakdown.append("CAD Symbols Detected (+20)")
            else:
                score -= 10
                breakdown.append("No CAD Symbols (-10)")
                
        except Exception as e:
            logger.warning(f"Vector/Text matrix evaluation partially failed: {e}")
            pass

        try:
            pix = page.get_pixmap(dpi=72, alpha=False)
            if pix and pix.w > 0 and pix.h > 0:
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                if pix.n == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img
                    
                ink_pixels = np.sum(gray < 250)
                total_pixels = gray.shape[0] * gray.shape[1]
                ink_ratio = ink_pixels / total_pixels
                metrics["ink_ratio"] = float(ink_ratio)
                
                if metrics["text_length"] < 50 and metrics["path_count"] < 10 and ink_ratio > 0.02:
                    metrics["extraction_mode"] = "OCR_FALLBACK"
                    score += 30
                elif metrics["path_count"] > 100:
                    metrics["extraction_mode"] = "NATIVE_VECTOR"
                    score += 40
            else:
                logger.warning("Empty pixmap generated during ink spread evaluation.")
        except Exception as e:
            logger.warning(f"Ink spread evaluation failed (potential raster image error): {e}")
            pass

        return score, ", ".join(breakdown), metrics

    def map_spatial_zones(self, page: fitz.Page, dpi: int = 400) -> Dict[str, Any]:
        return self._map_zones(page, dpi)

    def _map_zones(self, page: fitz.Page, dpi: int) -> Dict[str, Any]:
        zones = {"MAIN_CANVAS": None, "TITLE_BLOCK": None, "TABLES": []}
        scale = dpi / 72.0 
        
        try:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            if not pix or pix.w == 0 or pix.h == 0:
                raise ValueError("PyMuPDF failed to render a valid pixmap image.")
                
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if pix.n == 3: 
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else: 
                gray = img
        except Exception as e:
            logger.error(f"Image Buffer extraction failed in _map_zones: {e}")
            raise

        img_h, img_w = gray.shape
        page_area = img_h * img_w
        min_zone_area = page_area * 0.005

        best_score = -1
        best_contours = []
        
        threshold_methods = [
            ("adaptive", cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15)),
            ("otsu", cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]),
            ("fixed", cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)[1])
        ]

        try:
            for name, thresh in threshold_methods:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
                grid = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)                
                contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                score = sum(1 for cnt in contours if cv2.contourArea(cnt) > min_zone_area)
                if score > best_score:
                    best_score = score
                    best_contours = contours
                    
        except cv2.error as e:
            logger.error(f"OpenCV thresholding/contour logic failed: {e}")
            raise

        logger.debug(f"OpenCV settled on optimal contour grid. Massive structures found: {best_score}")

        if best_contours:
            largest_cnt = max(best_contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_cnt)
            zones["MAIN_CANVAS"] = {"rect_pdf": (x/scale, y/scale, w/scale, h/scale)}

        for cnt in best_contours:
            area = cv2.contourArea(cnt)
            if area < min_zone_area or area > page_area * 0.8: continue

            x, y, w, h = cv2.boundingRect(cnt)
            is_bottom_right = (x + w) > (img_w * 0.7) and (y + h) > (img_h * 0.7)
            if is_bottom_right and not zones["TITLE_BLOCK"]:
                zones["TITLE_BLOCK"] = {"rect_pdf": (x/scale, y/scale, w/scale, h/scale)}
            else:
                zones["TABLES"].append({"rect_pdf": (x/scale, y/scale, w/scale, h/scale)})

        return zones

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _detect_oem(self, text: str) -> str:
        try:
            for oem, patterns in OEMSignatures.PATTERNS.items():
                if any(re.search(pat, text) for pat in patterns): return oem
        except Exception as e:
            logger.warning(f"OEM Detection failed safely: {e}")
            pass
        return "UNKNOWN"

    def _calculate_optimal_dpi(self, rect: fitz.Rect) -> int:
        TARGET_PIXEL_WIDTH = 4000.0        
        width_inches = rect.width / 72.0        
        optimal_dpi = int(TARGET_PIXEL_WIDTH / width_inches)        
        safe_dpi = max(300, min(optimal_dpi, 600))
        
        logger.debug(f"Dynamic Scale: {rect.width}pts -> {safe_dpi} DPI (Targeting ~4000px)")
        return safe_dpi
        
        
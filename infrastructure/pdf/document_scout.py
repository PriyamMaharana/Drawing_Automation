import sys
import subprocess
import logging
import re
from typing import Tuple, List
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
ensure_package("opencv-python", "cv2")
ensure_package("numpy", "numpy")

import fitz
import cv2
import numpy as np

try:
    from core.entities.document import DocumentProfile, PageProfile, DrawingPackage
    from rules.cad_dictionary import CADSignatures, OEMSignatures, PaperSizeSignatures
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")

class DocumentScout:
    """
    PHASE 1: Target Acquisition & Layout Segmentation.
    Executes Pre-Flight Health Checks, calculates Matrix Page Scores, 
    and utilizes OpenCV to map safe geometry zones.
    """
    def __init__(self):
        logging.debug("Initializing Phase 1: Synthesized DocumentScout Engine")
        self.max_search_pages = 5

    def analyze_document(self, pdf_path: Path) -> DrawingPackage:
        logging.info(f"Phase 1 | Initiating Pipeline for {pdf_path.name}")
        
        try:
            doc = fitz.open(str(pdf_path))
        except Exception:
            logging.error(f"Fatal error opening PDF {pdf_path.name}", exc_info=True)
            raise

        pages: List[PageProfile] = []
        global_text = ""
        best_score = -9999
        target_page_idx = -1
        
        search_limit = min(len(doc), self.max_search_pages)
        
        # 1. Page Evaluation Loop
        for idx in range(search_limit):
            page = doc[idx]
            human_page = idx + 1
            global_text += page.get_text("text").upper() + " "
            
            try:
                # Run Health Check & Matrix Math
                profile = self._profile_page(page, human_page)
                pages.append(profile)
                
                if profile.health_status in ("RASTER_SCAN", "CORRUPT_FONT", "CORRUPT_DOCUMENT"):
                    logging.warning(f"  -> [SCOUT] Page {human_page} skipped (Health: {profile.health_status})")
                    continue

                status = "✅ ACCEPTED" if profile.score >= 40 else "⏩ REJECTED"
                logging.debug(f"  -> [MATRIX] Page {human_page} {status} | Score: {profile.score} | Breakdown: {', '.join(profile.diagnostics)}")

                if profile.score > best_score:
                    best_score = profile.score
                    target_page_idx = idx

            except Exception:
                logging.error(f"Failed to parse vectors on Page {human_page}. Data corruption possible.", exc_info=True)
                continue 
                
        # 2. Document Level Resolution
        oem = self._detect_oem(global_text)
        paper_size, rec_dpi = self._detect_paper_size_and_dpi(global_text, doc[0].rect if len(doc) > 0 else None)
        
        # Resolve global health
        doc_health = "CLEAN"
        if not pages: doc_health = "CORRUPT_DOCUMENT"
        elif any(p.health_status == "VECTOR_BOMB" for p in pages): doc_health = "VECTOR_BOMB"
        elif any(p.health_status == "RASTER_SCAN" for p in pages) and best_score < 40: doc_health = "RASTER_SCAN"

        doc_profile = DocumentProfile(oem=oem, paper_size=paper_size, recommended_dpi=rec_dpi, health_status=doc_health)
        drawing_pages = [p.page_number for p in pages if p.score >= 40]
        primary_page = target_page_idx + 1 if target_page_idx >= 0 and best_score >= 40 else None

        # 3. OpenCV Spatial Mapping (The Final Addition)
        spatial_zones = {}
        if primary_page:
            logging.info(f"Phase 1 | Target Locked: Page {primary_page}. Initiating OpenCV Spatial Mapping...")
            spatial_zones = self._map_zones(doc[target_page_idx], rec_dpi)
            
            debug = spatial_zones.get("_debug", {})
            logging.info(
                f"OpenCV Pass | "
                f"Contours={debug.get('contours_found')} | "
                f"Boxes={debug.get('boxes_after_filter')} | "
                f"Threshold={debug.get('threshold_method')}"
            )

        return DrawingPackage(
            document_profile=doc_profile,
            primary_page=primary_page,
            drawing_pages=drawing_pages,
            pages=pages,
            spatial_zones=spatial_zones
        )

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL ENGINES: YOUR MATRIX MATH
    # ─────────────────────────────────────────────────────────────────────────
    def _profile_page(self, page: fitz.Page, page_num: int) -> PageProfile:
        health_status = self._run_pre_flight_check(page, page_num)
        text = page.get_text("text").upper()
        is_vector = len(page.get_text("words")) > 20 and health_status != "RASTER_SCAN"
        
        score, diagnostics = -1000, ["Failed Health Check"]
        if health_status not in ("RASTER_SCAN", "CORRUPT_FONT"):
            score, diagnostics = self._calculate_matrix_score(page, health_status)
            
        return PageProfile(
            page_number=page_num, health_status=health_status, 
            is_vector=is_vector, score=score, diagnostics=diagnostics
        )

    def _run_pre_flight_check(self, page: fitz.Page, page_num: int) -> str:
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        paths = page.get_drawings()
        images = page.get_images()
        
        if len(paths) == 0 and len(blocks) == 0 and len(images) > 0:
            return "RASTER_SCAN"
        if len(paths) > 50000:
            return "VECTOR_BOMB"
            
        raw_text = page.get_text("text").strip()
        if len(raw_text) > 100:
            standard_chars = len(re.findall(r'[a-zA-Z0-9\s\.\,\-\+\±\Ø\°\(\)\:\_]', raw_text))
            gibberish_ratio = 1.0 - (standard_chars / len(raw_text))
            if gibberish_ratio > 0.35:
                return "CORRUPT_FONT"
                
        return "CLEAN"

    def _calculate_matrix_score(self, page: fitz.Page, health_status: str) -> Tuple[int, list]:
        score = 0
        diagnostics = []
        page_area = max((page.rect.width * page.rect.height), 1.0) 
        paths = page.get_drawings()
        total_paths = len(paths)
        blocks = page.get_text("dict").get("blocks", [])
        
        if total_paths == 0: return -1000, ["Absolute Terminator: No vector paths"]
        if total_paths < 20 and len(blocks) > 10: return -1000, ["Absolute Terminator: Pure text page"]
        
        curve_count = 0
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        for path in paths:
            if health_status != "VECTOR_BOMB":
                for item in path["items"]:
                    if item[0] in ("c", "v", "y"): curve_count += 1
                if curve_count > 505: break 
            r = path.get("rect")
            if r and r.is_valid:
                min_x, min_y = min(min_x, r.x0), min(min_y, r.y0)
                max_x, max_y = max(max_x, r.x1), max(max_y, r.y1)
        
        if total_paths > 2000: score += 40; diagnostics.append(f"Massive Path Density (+40)")
        elif total_paths > 500: score += 20; diagnostics.append(f"High Path Density (+20)")
        elif total_paths < 50: score -= 40; diagnostics.append(f"Low Path Density (-40)")

        if min_x < max_x and min_y < max_y:
            ink_spread = (((max_x - min_x) * (max_y - min_y)) / page_area) * 100
            if ink_spread > 75: score += 30; diagnostics.append(f"High Ink Spread ({ink_spread:.1f}%) (+30)")

        page_text = page.get_text("text").upper()
        char_count = len(page_text.strip())
        text_to_path_ratio = char_count / total_paths if total_paths > 0 else 0
        
        if text_to_path_ratio > 3.0: score -= 40; diagnostics.append(f"Text-Heavy Ratio (-40)")

        symbol_blocks = sum(1 for b in blocks if b.get("type") == 0 and (
            CADSignatures.SYMBOLS.search("".join([s.get("text", "") for l in b.get("lines", []) for s in l.get("spans", [])]).upper()) or
            CADSignatures.DIMENSIONS.search("".join([s.get("text", "") for l in b.get("lines", []) for s in l.get("spans", [])]).upper())
        ))
                    
        if symbol_blocks >= 2: score += 20; diagnostics.append(f"CAD Symbols Found (+20)")
        elif symbol_blocks == 0: score -= 10; diagnostics.append("No CAD Symbols (-10)")

        if "TRACK & TRACE" in page_text:
            score -= 40; diagnostics.append("Cover Keyword 'TRACK & TRACE' (-40)")
            
        if char_count > 2500 and (curve_count < 500 and health_status != "VECTOR_BOMB"):
            return -1000, ["Absolute Terminator: Table/Notes Signature"]
            
        return score, diagnostics 

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL ENGINES: THE MISSING OPENCV CAPABILITY
    # ─────────────────────────────────────────────────────────────────────────
    def _map_zones(self, page: fitz.Page, dpi: int) -> dict:
        """
        Robust engineering drawing zone detection.Strategy order:
        1. Dynamic threshold competition
        2. Border frame detection
        3. Contour-based zoning
        4. Vector extent fallback
        5. Text-anchor title block fallback
        """
        scale = dpi / 72.0 
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        
        if pix.n == 1: gray = img
        else: gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        img_h, img_w = gray.shape
        page_area = img_h * img_w
        
        zones = {
            "TITLE_BLOCK": None,
            "MAIN_CANVAS": None,
            "TABLES": [],
            "_scale": scale,
            "_debug": {}
        }
        
        # -- multi threshold 
        threshold_candidates = []
        
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        threshold_candidates.append(("otsu", otsu))
        
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 10)
        threshold_candidates.append(("adaptive", adaptive))
        
        _, fixed = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        threshold_candidates.append(("fixed", fixed))
        
        best_grid = None
        best_contours = []
        best_score = -1
        
        line_length = max(int(dpi/5), 50)
        
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))
        
        for method_name, thresh in threshold_candidates:
            h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
            v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)
        
            grid = cv2.add(h_lines, v_lines)
            grid = cv2.dilate(grid, cv2.getStructuringElement(
                        cv2.MORPH_RECT, (5,5)
                    ), iterations=2 )
            
            contours, _ = cv2.findContours(grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            score = len(contours)
            
            if score > best_score:
                best_score = score
                best_grid = grid
                best_contours = contours

                zones["_debug"]["threshold_method"] = method_name

        contours = best_contours
        zones["_debug"]["contours_found"] = len(contours)
        
        # -- contour harvest
        boxes = []
        
        min_area = page_area * 0.00005
        max_area = page_area * 0.99995
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            if area < min_area:
                continue

            if area > max_area:
                continue

            boxes.append({
                "rect": (x, y, w, h),
                "area": area,
                "cx": x + w / 2,
                "cy": y + h / 2
            })

        zones["_debug"]["boxes_after_filter"] = len(boxes)
        
        # -- normal contour mode
        if boxes:
            boxes.sort(key=lambda b: b["area"], reverse=True)  
            main = boxes[0]
            zones["MAIN_CANVAS"] = {"rect": main["rect"]}
            mx, my, mw, mh = main["rect"]
            
            candidates = []
            
            for b in boxes[1:]:
                if (b["cx"] > img_w * 0.5 and b["cy"] > img_h * 0.5):
                    candidates.append(b)
                    
            if candidates:
                candidates.sort(key=lambda b: b["area"], reverse=True)
                zones["TITLE_BLOCK"] = {"rect": candidates[0]["rect"]}
            
            for b in boxes[1:]:
                if (zones["TITLE_BLOCK"] and b["rect"] == zones["TITLE_BLOCK"]["rect"]):
                    continue
                zones["TABLES"].append({"rect": b["rect"]})

            return zones
        
        # -- vector fallback
        paths = page.get_drawings()
        
        rects = []
        
        for path in paths:
            r = path.get("rect")
            if r and r.is_valid:
                rects.append(r)
        
        if rects:
            xmin = min(r.x0 for r in rects)
            ymin = min(r.y0 for r in rects)
            
            xmax = max(r.x1 for r in rects)
            ymax = max(r.y1 for r in rects)
            
            zones["MAIN_CANVAS"] = {
                "rect": (
                    int(xmin * scale),
                    int(ymin * scale),
                    int((xmax - xmin) * scale),
                    int((ymax - ymin) * scale)
                )
            }
            
        # -- title block text fallback
        keywords = [
            "PART NUMBER", "DRAWING NO", "DRG", "SHEET", "REVISION",
            "SCALE", "MATERIAL"
        ]

        text_blocks = page.get_text("blocks")

        candidate_blocks = []

        for block in text_blocks:
            text = str(block[4]).upper()

            if any(k in text for k in keywords):
                candidate_blocks.append(block)

        if candidate_blocks:

            x0 = min(b[0] for b in candidate_blocks)
            y0 = min(b[1] for b in candidate_blocks)

            x1 = max(b[2] for b in candidate_blocks)
            y1 = max(b[3] for b in candidate_blocks)

            zones["TITLE_BLOCK"] = {
                "rect": (
                    int(x0 * scale),
                    int(y0 * scale),
                    int((x1 - x0) * scale),
                    int((y1 - y0) * scale)
                )
            }

        return zones
            

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _detect_oem(self, text: str) -> str:
        for oem, patterns in OEMSignatures.PATTERNS.items():
            if any(re.search(pat, text) for pat in patterns): return oem
        return "UNKNOWN"

    def _detect_paper_size_and_dpi(self, text: str, rect: fitz.Rect) -> Tuple[str, int]:
        size = "UNKNOWN"
        for s, pattern in PaperSizeSignatures.PATTERNS.items():
            if re.search(pattern, text):
                size = s
                break
                
        if size == "UNKNOWN" and rect:
            max_dim = max(rect.width, rect.height)
            if max_dim > 2300: size = "A0"
            elif max_dim > 1600: size = "A1"
            elif max_dim > 1100: size = "A2"
            elif max_dim > 800: size = "A3"
            else: size = "A4" 

        dpi_map = {"A0": 400, "A1": 400, "A2": 500, "A3": 600, "A4": 600}
        return size, dpi_map[size]
    
    
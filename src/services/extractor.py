import fitz
import re
from typing import List
from src.models.parameter import TextParameter
from src.services.health_checker import run_pre_flight_check

class PDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        
        self.cad_symbol_pattern = re.compile(r'[\Ø\±\°\⌀\⌖\↗\⌰\⟂\∥\∠\▱\⌭\⌓\⌒\Ⓜ\Ⓛ\Ⓢ\⌯\◎\─\○]')
        self.cad_keyword_pattern = re.compile(r'\b(PCD|THRU|TYP|CHAM|CBORE|CSK|REF|MAX|MIN|SPLINE|ASSY)\b')
        self.cad_dimension_pattern = re.compile(r'\b[RNMHhgkp]\d{1,3}\b')
        self.cad_tolerance_pattern = re.compile(r'[+-]\s?\d*\.\d+')

    def is_drawing_page(self, page: fitz.Page, page_num: int, health_status: str) -> bool:
        score = 0
        diagnostics = []
        
        page_area = max((page.rect.width * page.rect.height), 1.0) 

        paths = page.get_drawings()
        total_paths = len(paths)
        
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        
        if total_paths == 0:
            print(f"  -> [MATRIX] Page {page_num} ⏩ REJECTED | No vector paths found.")
            return False
            
        if total_paths < 20 and len(blocks) > 10:
            print(f"  -> [MATRIX] Page {page_num} ⏩ REJECTED | Geometry Gate: Pure text/notes page.")
            return False
        
        curve_count = 0
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for path in paths:
            if health_status != "VECTOR_BOMB":
                for item in path["items"]:
                    if item[0] in ("c", "v", "y"):
                        curve_count += 1
                
                if curve_count > 505:
                    break 
            
            r = path.get("rect")
            if r and r.is_valid:
                min_x = min(min_x, r.x0)
                min_y = min(min_y, r.y0)
                max_x = max(max_x, r.x1)
                max_y = max(max_y, r.y1)
        
        # A. Path Density Score
        if total_paths > 2000:
            score += 40
            diagnostics.append(f"Massive Path Density ({total_paths}) (+40)")
        elif total_paths > 500:
            score += 20
            diagnostics.append(f"High Path Density ({total_paths}) (+20)")
        elif total_paths < 50:
            score -= 40
            diagnostics.append(f"Low Path Density ({total_paths}) (-40)")

        # B. Morphology Score
        curve_ratio = (curve_count / total_paths) * 100 if total_paths > 0 else 0
        if health_status == "VECTOR_BOMB":
            diagnostics.append("Curve Check Bypassed (Vector Bomb)")
        elif curve_ratio > 5 or curve_count > 50:
            score += 30
            diagnostics.append(f"High Curves ({curve_count}) (+30)")
        elif curve_count == 0:
            score -= 10 
            diagnostics.append("Zero Curves (-10)")
            
        # C. Spread Score
        if min_x < max_x and min_y < max_y:
            ink_area = (max_x - min_x) * (max_y - min_y)
            ink_spread = (ink_area / page_area) * 100
            if ink_spread > 75:
                score += 30
                diagnostics.append(f"High Ink Spread ({ink_spread:.1f}%) (+30)")
            elif ink_spread < 30:
                score -= 20
                diagnostics.append(f"Low Ink Spread ({ink_spread:.1f}%) (-20)")

        # --- 2. THE "WORD SALAD" FILTER ---
        page_text = page.get_text("text").upper()
        char_count = len(page_text.strip())
        text_to_path_ratio = char_count / total_paths if total_paths > 0 else 0
        
        if total_paths > 0:            
            if curve_count == 0 and text_to_path_ratio > 1.5 and total_paths < 2000:
                score -= 60
                diagnostics.append(f"Zero Curves + Text-Heavy Ratio ({text_to_path_ratio:.1f}) (-60)")
            elif text_to_path_ratio > 3.0:
                score -= 40
                diagnostics.append(f"Text-Heavy Ratio ({text_to_path_ratio:.1f}) (-40)")
            elif text_to_path_ratio < 0.5 and total_paths > 100:
                score += 20
                diagnostics.append(f"Geometry-Heavy Ratio ({text_to_path_ratio:.1f}) (+20)")

        # --- 3. TYPOGRAPHICAL SIGNATURES & DISPERSION ---
        symbol_blocks_found = 0
        hard_math_symbols_found = 0
        
        sym_min_x, sym_min_y = float('inf'), float('inf')
        sym_max_x, sym_max_y = float('-inf'), float('-inf')

        for block in blocks:
            if block.get("type") == 0:
                block_text = "".join([span.get("text", "") for line in block.get("lines", []) for span in line.get("spans", [])]).upper()
                
                has_symbol = self.cad_symbol_pattern.search(block_text) 
                has_keyword = self.cad_keyword_pattern.search(block_text)
                has_dimension = self.cad_dimension_pattern.search(block_text)
                has_tolerance = self.cad_tolerance_pattern.search(block_text)
                
                weights = sum([bool(has_symbol), bool(has_keyword), bool(has_dimension), bool(has_tolerance)])
                
                if weights > 0:
                    symbol_blocks_found += weights
                    if has_symbol or has_tolerance:
                        hard_math_symbols_found += 1
                        
                    bx0, by0, bx1, by1 = block["bbox"]
                    sym_min_x = min(sym_min_x, bx0)
                    sym_min_y = min(sym_min_y, by0)
                    sym_max_x = max(sym_max_x, bx1)
                    sym_max_y = max(sym_max_y, by1)
                    
        # D. Signature Score
        if symbol_blocks_found >= 2:
            score += 20
            diagnostics.append(f"CAD Symbols Found ({symbol_blocks_found}) (+20)")
            
            sym_spread_area = (sym_max_x - sym_min_x) * (sym_max_y - sym_min_y)
            if (sym_spread_area / page_area) * 100 > 30:
                score += 20
                diagnostics.append("Symbols Widely Dispersed (+20)")
                
        elif symbol_blocks_found == 0:
            score -= 10
            diagnostics.append("No CAD Symbols (-10)")

        # --- 4. CONDITIONAL PENALTIES (THE TERMINATORS) ---
        if "TRACK & TRACE" in page_text:
            score -= 40
            diagnostics.append("Cover Keyword 'TRACK & TRACE' (-40)")
            
        symbol_density = (hard_math_symbols_found / char_count) * 1000 if char_count > 0 else 0
        
        is_table_grid = char_count > 2500 and symbol_density < 2.0 and (curve_count < 500 and health_status != "VECTOR_BOMB")
        
        if is_table_grid:
            print(f"  -> [MATRIX] Page {page_num} ⏩ REJECTED | Absolute Terminator: Table/Notes Signature (High Volume, Low GD&T)")
            return False
            
        if text_to_path_ratio > 1.5:
            print(f"  -> [MATRIX] Page {page_num} ⏩ REJECTED | Absolute Terminator: Document Signature (Text Ratio: {text_to_path_ratio:.1f})")
            return False
            
        if total_paths < 20:
            print(f"  -> [MATRIX] Page {page_num} ⏩ REJECTED | Absolute Terminator: Raster/Empty Signature")
            return False

        # --- FINAL DECISION ---
        is_drawing = score >= 40
        status = "✅ ACCEPTED" if is_drawing else "⏩ REJECTED"
        print(f"  -> [MATRIX] Page {page_num} {status} | Score: {score} | Breakdown: {', '.join(diagnostics)}")
        
        return is_drawing


    def extract_text_parameters(self) -> List[TextParameter]:
        """
        Extracts native text strings and their 72-DPI Bounding Boxes 
        from mathematically verified drawing pages.
        """
        parameters = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            human_page = page_num + 1
            
            # Phase 1.A: Pre-Flight Health Check (Using the external module)
            health_status = run_pre_flight_check(page, human_page)
            
            if health_status in ("RASTER_SCAN", "CORRUPT_FONT"):
                print(f"Skipping Page {human_page} due to critical Pre-Flight Failure.\n")
                continue
            
            # Phase 1.B: Intelligent Matrix Routing
            if not self.is_drawing_page(page, human_page, health_status):
                print(f"Skipping Page {human_page}...\n")
                continue
                
            print(f"Extracting geometry parameters from Page {human_page}...\n")
            
            # Phase 1.C: Native Dictionary Extraction
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            for block in blocks:
                if block.get("type") == 0:  # Ensure it is a text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox")
                                param = TextParameter(
                                    text=text,
                                    x0=bbox[0],
                                    y0=bbox[1],
                                    x1=bbox[2],
                                    y1=bbox[3],
                                    page_number=human_page,
                                    is_table_data=False 
                                )
                                parameters.append(param)
        
        return parameters
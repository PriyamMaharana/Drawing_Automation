import re
import logging
from core.dictionaries.cad_dictionary import CADSignatures

logger = logging.getLogger(__name__)

class CompoundParser:
    @classmethod
    def _is_engineering_data(cls, text: str) -> bool:
        text_upper = text.upper()
        if any(c.isdigit() for c in text): return True
        if any(sym in text for sym in CADSignatures.GDT_SYMBOLS): return True
        
        extra_keywords = ["SECTION", "DETAIL", "NOTE", "REV", "SCALE", "MATERIAL", "FINISH", "TOLERANCE"]
        if any(kw in text_upper for kw in CADSignatures.KEYWORDS_LIST + extra_keywords): return True
        
        alpha_only = re.sub(r'[^a-zA-Z]', '', text)
        if 0 < len(alpha_only) <= 3 and alpha_only.isupper():
            if len(text.split()) == 1 or len(text.split()) == len(alpha_only): return True
                
        return False

    @classmethod
    def parse_annotation(cls, raw_text: str) -> list:
        raw_text = raw_text.strip()
        
        if not cls._is_engineering_data(raw_text):
            return []
            
        try:
            # 1. Datums (e.g. "A", "[B]")
            datum_match = re.match(r'^\[?([A-Z]{1,2})\]?$', raw_text)
            if datum_match:
                return [{"entity_type": "Datum", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]
                
            # 2. Surface Finish (e.g. "N9", "Ra 3.2")
            sf_match = re.match(r'^(N\d{1,2}|Ra\s*\d+\.\d+)$', raw_text, re.IGNORECASE)
            if sf_match:
                return [{"entity_type": "Surface Finish", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]

            # 3. GD&T Features
            if any(sym in raw_text for sym in CADSignatures.GDT_SYMBOLS) or '│' in raw_text or '|' in raw_text or '[' in raw_text:
                return [{"entity_type": "GD&T", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]

            # 4. NEW: Threads (e.g., M12x1.75 - 6g, 1/4-20 UNC)
            if re.search(r'(?:^[M]\d+(?:[xX]\d+(?:\.\d+)?)?)|(?:(?:UNC|UNF|UNEF)\b)', raw_text, re.IGNORECASE):
                return [{"entity_type": "Thread", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]

            # 5. NEW: Complex Hole Features (Counterbore, Countersink, Depth)
            if any(sym in raw_text for sym in ['⌴', '⌵', '↧', 'CBORE', 'CSK', 'DP']):
                return [{"entity_type": "Hole Feature", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]
                
            # 6. NEW: Limits and Fits (e.g., Ø20 H7/g6)
            if re.search(r'([Ø⌀]?\s*\d+(?:\.\d+)?\s*[a-zA-Z]\d{1,2}(?:\s*/\s*[a-zA-Z]\d{1,2})?)', raw_text) and '/' in raw_text:
                return [{"entity_type": "Limits & Fits", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]
                
            suffix_pattern = '|'.join(CADSignatures.KEYWORDS_LIST)
            
            # 7. Standard Dimensions (Upgraded Prefix to catch '4 HOLES')
            regex = re.compile(
                r'(?P<prefix>(?:\d+\s*[xX-]\s*)|(?:\d+\s*(?:HOLES?|PLCS?|PLACES?)\s*))?'
                r'(?P<base>[\(\[]?(?:[Ø⌀R\u2300M]|Ra|N)?\s*(?:SØ|SR|SQ|□)?\s*\d+(?:\.\d+)?(?:[xX*\-\s]\d+(?:\.\d+)?)?\s*(?:°|mm)?[\)\]]?(?:\s*min)?)'
                r'\s*(?P<tol>(?:[±+-]\s*\d+(?:\.\d+)?(?:\s*(?:/|\s*)\s*[+-]?\d+(?:\.\d+)?)?)|(?:[a-zA-Z]{1,2}\d{1,2}(?:\s*(?:/|\s+)\s*[a-zA-Z]{1,2}\d{1,2})?))?'
                rf'\s*(?P<suffix>{suffix_pattern})?',
                re.IGNORECASE
            )
            
            matches = list(regex.finditer(raw_text))
            results = []
            
            if matches:
                for m in matches:
                    d = m.groupdict()
                    prefix = (d['prefix'] or '').strip()
                    base = (d['base'] or '').strip()
                    tol = (d['tol'] or '').strip()
                    suffix = (d['suffix'] or '').strip()
                    
                    if not base: continue
                        
                    ent_type = "Linear Dimension"
                    base_upper = base.upper()
                    if 'Ø' in base_upper or '⌀' in base_upper: ent_type = "Diameter"
                    elif 'R' in base_upper: ent_type = "Radius"
                    elif '°' in base: ent_type = "Angle"
                    
                    raw_parts = [p for p in [prefix, base, tol, suffix] if p]
                    spec_parts = [p for p in [prefix, base, suffix] if p]
                    
                    results.append({
                        "entity_type": ent_type,
                        "raw_balloon_text": " ".join(raw_parts),
                        "specification": " ".join(spec_parts),
                        "tolerance": tol
                    })
                    
            if results: return results

            # 8. Fallback: Captures complete General Notes as annotations
            return [{"entity_type": "Annotation", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]

        except Exception as e:
            logger.error(f"CRITICAL PARSE FAILURE: {e}")
            return [{"entity_type": "Annotation", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]

    @staticmethod
    def _build_fallback(raw_text: str) -> list:
        return [{"entity_type": "Annotation", "raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]
    
    
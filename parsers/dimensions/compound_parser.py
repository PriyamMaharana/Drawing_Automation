import re
import logging
from core.dictionaries.cad_dictionary import CADSignatures

logger = logging.getLogger(__name__)

class CompoundParser:
    @classmethod
    def _is_engineering_data(cls, text: str) -> bool:
        """Sanity filter to drop OCR noise (e.g. 'wow', 'b', 'NS) C')."""
        text_upper = text.upper()
        if any(c.isdigit() for c in text): return True
        if any(sym in text for sym in CADSignatures.GDT_SYMBOLS): return True
        
        extra_keywords = ["SECTION", "DETAIL", "NOTE", "REV", "SCALE"]
        if any(kw in text_upper for kw in CADSignatures.KEYWORDS_LIST + extra_keywords): return True
        
        alpha_only = re.sub(r'[^a-zA-Z]', '', text)
        if 0 < len(alpha_only) <= 2 and alpha_only.isupper():
            if len(text.split()) == 1: return True
                
        return False

    @classmethod
    def parse_annotation(cls, raw_text: str) -> list:
        raw_text = raw_text.strip()
        
        # Kill noise strings instantly
        if not cls._is_engineering_data(raw_text):
            return []
            
        try:
            # 1. GD&T Features (Leaves them totally intact)
            if any(sym in raw_text for sym in CADSignatures.GDT_SYMBOLS) or raw_text.startswith('[') or '│' in raw_text:
                return cls._build_fallback(raw_text)
                
            suffix_pattern = '|'.join(CADSignatures.KEYWORDS_LIST)
            
            # 2. UPGRADED REGEX (Supports N9, Ra, and X20°)
            regex = re.compile(
                r'(?P<prefix>(?:\d+[xX]\s*)|(?:\d+\s+PLACES?\s*))?'
                r'(?P<base>[\(\[]?(?:[Ø⌀R\u2300M]|Ra|N)?\s*(?:SØ|SR|SQ|□)?\s*\d+(?:\.\d+)?(?:[xX*\-\s]\d+(?:\.\d+)?)?\s*(?:°|mm)?[\)\]]?(?:\s*min)?)'
                r'\s*(?P<tol>(?:[±+-]\s*\d+(?:\.\d+)?(?:\s*(?:/|\s*)\s*[+-]?\d+(?:\.\d+)?)?)|(?:[a-zA-Z]{1,2}\d{1,2}(?:\s*(?:/|\s+)\s*[a-zA-Z]{1,2}\d{1,2})?))?'
                rf'\s*(?P<suffix>{suffix_pattern})?',
                re.IGNORECASE
            )
            
            matches = list(regex.finditer(raw_text))
            if not matches: return cls._build_fallback(raw_text)
                
            results = []
            for m in matches:
                d = m.groupdict()
                prefix = (d['prefix'] or '').strip()
                base = (d['base'] or '').strip()
                tol = (d['tol'] or '').strip()
                suffix = (d['suffix'] or '').strip()
                
                if not base: continue
                    
                raw_parts = [p for p in [prefix, base, tol, suffix] if p]
                spec_parts = [p for p in [prefix, base, suffix] if p]
                
                results.append({
                    "raw_balloon_text": " ".join(raw_parts),
                    "specification": " ".join(spec_parts),
                    "tolerance": tol
                })
                
            if not results: return cls._build_fallback(raw_text)
            return results

        except Exception as e:
            logger.error(f"CRITICAL PARSE FAILURE: {e}")
            return cls._build_fallback(raw_text)

    @staticmethod
    def _build_fallback(raw_text: str) -> list:
        return [{"raw_balloon_text": raw_text, "specification": raw_text, "tolerance": ""}]
    
    
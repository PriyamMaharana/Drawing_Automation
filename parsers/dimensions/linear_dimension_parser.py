import re
from typing import Dict, Optional, Any

class LinearDimensionParser:
    """
    Shatters standard length/width strings (No symbols).
    Utilizes strict Context Guards to prevent metadata false positives.
    """
    def __init__(self):
        # 1. The Exclusion Shield (Instantly reject if it belongs to another parser)
        self.forbidden_symbols = re.compile(r"(Ø|DIA|R|RAD|RADIUS|DEG|°|⌖|⊥|∥)", re.IGNORECASE)
        
        # 2. The Core Pattern
        self.pattern = re.compile(
            r"(?:(?P<qty>\d+)[xX]\s*)?"
            r"(?P<nominal>\d+\.?\d*)\s*"
            r"(?:[±\+]\s*(?P<tol_sym>\d+\.?\d*))?"
            r"(?:\+\s*(?P<upper>\d+\.?\d*)\s*-\s*(?P<lower>\d+\.?\d*))?",
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        # --- PRE-FLIGHT CONTEXT GUARDS ---
        if self.forbidden_symbols.search(text):
            return None
            
        clean = text.strip()
        
        # Guard 1: Reject bare single or double-digit numbers (e.g., Item #1, Page 12)
        if re.fullmatch(r'\d{1,2}', clean):
            return None
            
        # Guard 2: Reject scale ratios (e.g., 1:2, 1:5)
        if re.search(r'\d\s*:\s*\d', clean):
            return None
            
        # Guard 3: Reject known metadata keywords
        if re.search(r'\b(REV|SH|DWG|PG|QTY|ITEM|POS|NO\.?)\b', clean, re.IGNORECASE):
            return None

        # --- SAFE TO PARSE ---
        clean_text = re.sub(r'(?i)(?:THRU|TYP|REF|\s+)', '', clean)
        match = self.pattern.search(clean_text)
        
        if not match: 
            return None
            
        data = match.groupdict()
        nominal = float(data.get("nominal", 0))
        has_tolerance = bool(data.get("tol_sym") or data.get("upper"))
        
        # Guard 4: Strict numerical sanity check 
        # (Engineering dimensions under 5mm almost ALWAYS have tolerances attached)
        if nominal < 5.0 and not has_tolerance:
            return None
            
        result = {
            "feature_type": "Linear",
            "quantity": int(data["qty"]) if data["qty"] else 1,
            "nominal": nominal,
            "upper_tolerance": float(data["tol_sym"]) if data["tol_sym"] else (float(data["upper"]) if data["upper"] else 0.0),
            "lower_tolerance": -float(data["tol_sym"]) if data["tol_sym"] else (-float(data["lower"]) if data["lower"] else 0.0),
            "raw_text": text
        }
        
        return result
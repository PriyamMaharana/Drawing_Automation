import re
from typing import Dict, Optional, Any

class LinearDimensionParser:
    """Shatters standard length/width strings (No symbols)."""
    def __init__(self):
        self.forbidden_symbols = re.compile(r"(Ø|DIA|R|RAD|RADIUS|DEG|°|⌖|⊥|∥)", re.IGNORECASE)
        
        self.pattern = re.compile(
            r"(?:(?P<qty>\d+)[xX]\s*)?"
            r"(?P<nominal>\d+\.?\d*)\s*"
            r"(?:[±\+]\s*(?P<tol_sym>\d+\.?\d*))?"
            r"(?:\+\s*(?P<upper>\d+\.?\d*)\s*-\s*(?P<lower>\d+\.?\d*))?",
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        if self.forbidden_symbols.search(text):
            return None
        
        # Strip out random whitespace or notes before testing
        clean_text = re.sub(r'(?i)(?:THRU|TYP|REF|\s+)', '', text)
        match = self.pattern.search(clean_text)
        
        if not match: return None
            
        data = match.groupdict()
        result = {
            "feature_type": "Linear",
            "quantity": int(data["qty"]) if data["qty"] else 1,
            "nominal": float(data["nominal"]),
            "upper_tolerance": float(data["tol_sym"]) if data["tol_sym"] else (float(data["upper"]) if data["upper"] else 0.0),
            "lower_tolerance": -float(data["tol_sym"]) if data["tol_sym"] else (-float(data["lower"]) if data["lower"] else 0.0),
            "raw_text": text
        }
        
        return result
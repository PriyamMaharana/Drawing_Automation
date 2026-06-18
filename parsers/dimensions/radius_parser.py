import re
from typing import Dict, Optional, Any

class RadiusParser:
    """Shatters a raw Radius string into a structured mathematical dictionary."""
    def __init__(self):
        # Matches: [Qty X] [R] [Nominal] [+/- Tolerances]
        self.pattern = re.compile(
            r"(?:(?P<qty>\d+)[xX]\s*)?"                     
            r"(?:R|RAD|RADIUS)\s*"                                
            r"(?P<nominal>\d+\.?\d*)\s*"                     
            r"(?:[±\+]\s*(?P<tol_sym>\d+\.?\d*))?"           
            r"(?:\+\s*(?P<upper>\d+\.?\d*)\s*-\s*(?P<lower>\d+\.?\d*))?", 
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(text)
        if not match: return None
            
        data = match.groupdict()
        result = {
            "feature_type": "Radius",
            "quantity": int(data["qty"]) if data["qty"] else 1,
            "nominal": float(data["nominal"]),
            "upper_tolerance": float(data["tol_sym"]) if data["tol_sym"] else (float(data["upper"]) if data["upper"] else 0.0),
            "lower_tolerance": -float(data["tol_sym"]) if data["tol_sym"] else (-float(data["lower"]) if data["lower"] else 0.0),
            "raw_text": text
        }
        return result
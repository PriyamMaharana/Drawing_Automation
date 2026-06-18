import re
from typing import Dict, Optional, Any

class AngleParser:
    """Shatters a raw Angle string into a structured mathematical dictionary."""
    def __init__(self):
        # Matches: [Nominal] [° or DEG] [+/- Tolerances]
        self.pattern = re.compile(
            r"(?:(?P<qty>\d+)[xX]\s*)?" 
            r"(?P<nominal>\d+\.?\d*)\s*"
            r"(?:°|DEG|DEGREES)\s*"
            r"(?:[±\+]\s*(?P<tol_sym>\d+\.?\d*)\s*(?:°|DEG)?)?",
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(text)
        if not match: return None
            
        data = match.groupdict()
        result = {
            "feature_type": "Angle",
            "quantity": int(data["qty"]) if data["qty"] else 1,
            "nominal": float(data["nominal"]),
            "upper_tolerance": float(data["tol_sym"]) if data["tol_sym"] else 0.0,
            "lower_tolerance": -float(data["tol_sym"]) if data["tol_sym"] else 0.0,
            "raw_text": text
        }
        return result
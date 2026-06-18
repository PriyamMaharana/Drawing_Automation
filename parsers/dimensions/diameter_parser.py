import re
from typing import Dict, Optional, Any

class DiameterParser:
    """
    Shatters a raw diameter string into a structured mathematical dictionary.
    Handles quantities (e.g., '2X'), nominals, and plus/minus tolerances.
    """
    def __init__(self):
        # The Regex Engine
        # Matches: [Qty X] [Dia Symbol] [Nominal] [+/-] [Upper] [Lower]
        self.pattern = re.compile(
            r"(?:(?P<qty>\d+)[xX]\s*)?"                     # Optional Quantity: '2X '
            r"(?:Ø|DIA|D)\s*"                                # Diameter Symbol
            r"(?P<nominal>\d+\.?\d*)\s*"                     # Nominal Value: '45.00'
            r"(?:[±\+]\s*(?P<tol_sym>\d+\.?\d*))?"           # Symmetrical Tolerance: '±0.05'
            r"(?:\+\s*(?P<upper>\d+\.?\d*)\s*-\s*(?P<lower>\d+\.?\d*))?", # Asymmetrical: '+0.05 -0.01'
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Returns structured data if the string is a diameter, else None."""
        match = self.pattern.search(text)
        if not match:
            return None
            
        data = match.groupdict()
        
        # Base Structure
        result = {
            "feature_type": "Diameter",
            "quantity": int(data["qty"]) if data["qty"] else 1,
            "nominal": float(data["nominal"]),
            "upper_tolerance": 0.0,
            "lower_tolerance": 0.0,
            "raw_text": text
        }
        
        # Calculate Tolerances
        if data["tol_sym"]:
            result["upper_tolerance"] = float(data["tol_sym"])
            result["lower_tolerance"] = -float(data["tol_sym"])
        elif data["upper"] and data["lower"]:
            result["upper_tolerance"] = float(data["upper"])
            result["lower_tolerance"] = -float(data["lower"])
            
        return result
import re
from typing import Dict, Optional, Any

class GDTParser:
    """Parses Geometric Dimensioning and Tolerancing (GD&T) frames."""
    def __init__(self):
        # Matches: [Geometric Symbol] | [Tolerance Zone] | [Datums]
        # Includes unicode for Position, Flatness, Perpendicularity, etc.
        self.pattern = re.compile(
            r"(?P<symbol>[⌖⊥∥◯◿∠⌭⌯⌰◎])\s*\|?\s*"     # Symbol (e.g., Position ⌖)
            r"(?P<modifier>[ØM]\s*)?"                   # Optional modifier (e.g., Ø or (M))
            r"(?P<tolerance>\d+\.?\d*)\s*\|?\s*"        # Tolerance value (e.g., 0.05)
            r"(?P<datums>[A-Z](?:\s*\|?\s*[A-Z])*)?",   # Datums (e.g., A | B | C)
            re.IGNORECASE
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(text)
        if not match: return None
            
        data = match.groupdict()
        
        # Clean up the datums (turn "A | B" into ["A", "B"])
        datums_list = []
        if data["datums"]:
            datums_list = [d.strip() for d in data["datums"].replace("|", " ").split()]

        result = {
            "feature_type": "GD&T",
            "symbol": data["symbol"],
            "zone_modifier": data["modifier"].strip() if data["modifier"] else None,
            "tolerance_value": float(data["tolerance"]),
            "datums": datums_list,
            "raw_text": text
        }
        return result
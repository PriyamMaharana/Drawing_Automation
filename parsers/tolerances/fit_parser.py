import re
from typing import Dict, Optional, Any

class FitParser:
    """Parses ISO Hole/Shaft Fit classes."""
    def __init__(self):
        # Matches: [Nominal] [Hole Class(Upper)] / [Shaft Class(Lower)]
        self.pattern = re.compile(
            r"(?:Ø|DIA|D)?\s*(?P<nominal>\d+\.?\d*)\s*"
            r"(?P<hole>[A-Z]\d{1,2})\s*/?\s*(?P<shaft>[a-z]\d{1,2})?"
        )

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.search(text)
        if not match: return None
            
        data = match.groupdict()
        result = {
            "feature_type": "Fit_Class",
            "nominal": float(data["nominal"]),
            "hole_class": data["hole"],
            "shaft_class": data["shaft"],
            "raw_text": text
        }
        return result
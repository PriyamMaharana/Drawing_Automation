import re
import logging

logger = logging.getLogger(__name__)

class OntologyEngine:
    @staticmethod
    def classify(text: str) -> str:
        """
        Layer 6: Classifies text based on the CAD Engineering Ontology.
        Returns 'REJECTED' for noise, table headers, and meaningless fragments.
        """
        text_upper = text.upper().strip()
        
        if any(kw in text_upper for kw in ["NOTE", "NOTES:", "UNLESS OTHERWISE SPECIFIED", "MATERIAL", "FINISH", "HEAT TREAT"]):
            return "Manufacturing Note"
        
        noise_patterns = [
            r"PART DRAWING",
            r"REVISION",
            r"SCALE",
            r"DO NOT SCALE",
            r"^[A-Z]{1,3}$"  
        ]
        
        for pattern in noise_patterns:
            if re.search(pattern, text_upper):
                return "REJECTED"
                
        # 2. Accept Engineering Signatures
        if any(char.isdigit() for char in text):
            return "Dimension"
            
        if any(sym in text for sym in ['⌖', '⊥', '⟂', '//', '∥', '∠', '◎', '↗', '⌯', '⌴', '⌵', '↧']):
            return "GD&T"
            
        return "REJECTED"
    
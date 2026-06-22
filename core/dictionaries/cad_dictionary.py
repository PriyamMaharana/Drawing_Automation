import re

class CADSignatures:
    # Expanded GD&T Symbols, Material Modifiers, and Feature Symbols
    GDT_SYMBOLS = [
        '⌖', '⊥', '⟂', '//', '∥', '∠', '◎', '↗', '⌰', '⌭', '⌯', '▱', '⌓', '⌢', '⌒', '─', '○', '◯',
        'Ⓜ', 'Ⓛ', 'Ⓢ', 'Ⓟ', 'Ⓣ', 'Ⓕ', 'Ⓤ', 
        '⌴', '⌵', '↧'
    ]

    # Standard Engineering Callout Keywords (Suffixes & Modifiers)
    KEYWORDS_LIST = [
        r'THRU', r'TYP', r'MIN', r'MAX', r'REF', r'PCD', 
        r'EQL\s*SP', r'DP', r'DEEP', r'CSK', r'CBORE', 
        r'CHAM', r'SPLINE', r'ASSY', r'BSC'
    ]

    # Legacy compiled regexes (kept for compatibility with older extraction modules)
    SYMBOLS = re.compile(r'[' + re.escape(''.join(GDT_SYMBOLS)) + r']')
    KEYWORDS = re.compile(r'\b(' + '|'.join(KEYWORDS_LIST).replace(r'\s*', r'\s') + r')\b')
    DIMENSIONS = re.compile(r'\b[RNMHhgkp]\d{1,3}\b')
    TOLERANCES = re.compile(r'[+-]\s?\d*\.\d+')

class OEMSignatures:
    PATTERNS = {
        "ASHOK_LEYLAND": [r"ASHOK\s*LEYLAND", r"VELLIVOYALCHAVADI"],
        "TATA": [r"TATA\s*MOTORS", r"TATA\s*CUMMINS"],
        "VOLVO": [r"VOLVO\s*EICHER", r"VECV"],
        "CUMMINS": [r"CUMMINS\s*INC"],
        "EICHER": [r"EICHER\s*MOTORS"]
    }

class PaperSizeSignatures:
    PATTERNS = {
        "A0": r"size\s*A0", 
        "A1": r"size\s*A1", 
        "A2": r"size\s*A2"
    }
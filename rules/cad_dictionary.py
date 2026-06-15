import re

class CADSignatures:
    SYMBOLS = re.compile(r'[\Ø\±\°\⌀\⌖\↗\⌰\⟂\∥\∠\▱\⌭\⌓\⌒\Ⓜ\Ⓛ\Ⓢ\⌯\◎\─\○]')
    KEYWORDS = re.compile(r'\b(PCD|THRU|TYP|CHAM|CBORE|CSK|REF|MAX|MIN|SPLINE|ASSY)\b')
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
        "A2": r"size\s*A2",
        "A3": r"size\s*A3", 
        "A4": r"size\s*A4"
    }
    
    
import re

class OCRAutoCorrect:
    
    CORRECTIONS = {
        # ---------------------------------------------------------
        # 1. GD&T MODIFIERS (Material Conditions)
        # ---------------------------------------------------------
        r'\(\s*[Mm]\s*\)': 'Ⓜ',      
        r'\[\s*[Mm]\s*\]': 'Ⓜ',      
        r'\(\s*[Ll]\s*\)': 'Ⓛ',      
        r'\(\s*[Ss]\s*\)': 'Ⓢ', 
        
        # ---------------------------------------------------------
        # 2. GD&T CHARACTERISTICS (Form, Orientation, Location)
        # ---------------------------------------------------------
        r'//': '∥',                  # Parallelism
        r'_\|_': '⟂',                # Perpendicularity
        r'\(\+\)': '⌖',              # Position (Crosshairs)
        r'\(@\)': '◎',               # Concentricity
        r'\([Oo]\)': '◎',            # Concentricity
        r'<\s*>': '▱',               # Flatness
        r'-\|\|-': '⌯',              # Symmetry (Three lines)
        r'<\\': '∠',                 # Angularity
        r'/\>': '↗',                 # Circular Runout (Angled Arrow)
        r'->': '↗',                  # Circular Runout (Straight Arrow)
        r'/\\': '⌓',                 # Surface Profile (Arch)
        r'\(\^\)': '⌓',              # Surface Profile Alternative
        
        # ---------------------------------------------------------
        # 3. STANDARD ENGINEERING SYMBOLS
        # ---------------------------------------------------------
        r'\+\s*-': '±',              # "+ -" or "+-" -> ±
        r'-\s*\+': '±',              # "- +" or "-+" -> ±
        r'^[OQ0]/': 'Ø',             # "O/" or "0/" -> Ø
        r'^0\s+(?=\d)': 'Ø',         # "0 10.5" -> Ø10.5
        r'(?<=\d)\s*[o](?!\w)': '°', # "45 o" or "45O" -> 45°
        r'\+\s+(?=\d)': '+',
        r'-\s+(?=\d)': '-',
        
        # ---------------------------------------------------------
        # 4. PUNCTUATION & SPACING CLEANUP
        # ---------------------------------------------------------
        r'\s*\.\s*': '.',            # "10 . 5" -> "10.5"
        r'\.\.+': '.',               # "10..5" -> "10.5"
        r',(?=\d)': '.',             # European comma decimals "10,5" -> "10.5"
        r'^R\s*(?=\d)': 'R',         # "R 10" -> "R10"
                  
    }

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        if not raw_text:
            
            return ""
            
        cleaned = raw_text.strip()
        
        for pattern, replacement in cls.CORRECTIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned)
            
        return cleaned.strip()
    
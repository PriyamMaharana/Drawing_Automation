import re

class OCRAutoCorrect:
    
    CORRECTIONS = {
        # ---------------------------------------------------------
        # 1. GD&T MODIFIERS (Material Conditions)
        # ---------------------------------------------------------
        r'\(\s*[Mm]\s*\)': 'Ⓜ',      # Catches (M) or ( M ) -> Ⓜ
        r'\[\s*[Mm]\s*\]': 'Ⓜ',      # Catches [M] -> Ⓜ
        r'\(\s*[Ll]\s*\)': 'Ⓛ',      # Catches (L) or ( L ) -> Ⓛ
        r'\(\s*[Ss]\s*\)': 'Ⓢ',      # Catches (S) or ( S ) -> Ⓢ
        
        # ---------------------------------------------------------
        # 2. GD&T CHARACTERISTICS (Form, Orientation, Location)
        # ---------------------------------------------------------
        r'//': '∥',                  # Catches double slashes -> Parallelism
        r'_\|_': '⟂',                # Catches _|_ -> Perpendicularity
        r'\(\+\)': '⌖',              # Catches (+) -> Position
        r'\(@\)': '◎',               # Catches (@) -> Concentricity
        r'\([Oo]\)': '◎',            # Catches (O) -> Concentricity
        r'<\s*>': '▱',               # Catches < > -> Flatness
        r'/s*/s*': '▱',              # Catches / / -> Flatness
        r'-\|\|-': '⌯',              # Catches -||- -> Symmetry
        r'<\\': '∠',                 # Catches <\ -> Angularity
        
        # ---------------------------------------------------------
        # 3. STANDARD ENGINEERING SYMBOLS
        # ---------------------------------------------------------
        r'\+\s*-': '±',              # "+ -" or "+-" -> ±
        r'-\s*\+': '±',              # "- +" or "-+" -> ±
        r'^[OQ0]/': 'Ø',             # "O/" or "0/" -> Ø
        r'^0\s+(?=\d)': 'Ø',         # "0 10.5" -> Ø10.5
        
        # Catch Degrees (A number followed by a space and a lowercase 'o')
        r'(?<=\d)\s*[o](?!\w)': '°', # "45 o" or "45O" -> 45°
        
        # FIX: Close gaps in unilateral tolerances (e.g. "+ 0.2" -> "+0.2")
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
    
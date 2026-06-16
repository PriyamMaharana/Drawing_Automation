import re
import logging
from typing import List

try:
    from core.entities.geometry import PDFCharacter, PDFWord, PDFLine, BoundingBox
    from rules.cad_dictionary import CADSignatures
except ImportError as e:
    logging.exception(f"Microservices import failure: {e}")
    
    
def is_garbage(text: str) -> bool:
    if re.fullmatch(r'[?~|_\-]+', text):
        return True
    
    alpha = re.sub(r'[^a-zA-Z]', '', text)
    if len(alpha) >= 3 and not any(c in 'aeiouAEIOU' for c in alpha):
        return True
    
    if CADSignatures.SYMBOLS.match(text):
        return True
    
    return False

def clean_text(text: str) -> str:
    # Remove fragments, repeated dash-line artifacts, and common OCR noise
    cleaned = re.sub(r'^[^\w\s]{1,3}$', '', text) 
    cleaned = re.sub(r'(.)\1{2,}', '', cleaned)
    cleaned = cleaned.replace('???', '').replace('~', '').replace('|', '').replace('_', '')
    return cleaned.strip()

def build_semantic_hierarchy(raw_characters: List[PDFCharacter]) -> List[PDFLine]:
    """
    PHASE 3: Spatial Clustering Engine
    Mathematically reconstructs words and table rows from raw, floating characters.
    """
    if not raw_characters:
        return []

    valid_chars = []
    for c in raw_characters:
        c.text = clean_text(c.text)
        if c.text: valid_chars.append(c)
            
    if not valid_chars: return []
    valid_chars.sort(key=lambda c: (c.bbox.center_y, c.bbox.x0))
    
    # -- Pass 1 -- Strict word assembly --
    raw_words: List[PDFWord] = []
    if valid_chars:
        current_word_chars: List[PDFCharacter] = [valid_chars[0]]
        for i in range(1, len(valid_chars)):
            char, prev = valid_chars[i], current_word_chars[-1]
            
            # merge only if very close
            if abs(char.bbox.center_y - prev.bbox.center_y) < (char.font_size * 0.5) and \
                (char.bbox.x0 - prev.bbox.x1) < (char.bbox.width * 0.4):
                    current_word_chars.append(char)
            else:
                raw_words.append(_build_word(current_word_chars))
                current_word_chars = [char]
        
        raw_words.append(_build_word(current_word_chars))
        
    # -- Pass 2 -- the purge --
    clean_words = [w for w in raw_words if not is_garbage(w.text)]
    
    # -- Pass 3 -- forgiving line assembly --
    semantic_lines: List[PDFLine] = []
    if clean_words:
        clean_words.sort(key=lambda w: (w.bbox.center_y, w.bbox.x0))
        current_line: List[PDFWord] = [clean_words[0]]
        
        for i in range(1, len(clean_words)):
            word, prev = clean_words[i], current_line[-1]
            gap = word.bbox.x0 - prev.bbox.x1
            
            if abs(word.bbox.center_y - prev.bbox.center_y) < (word.bbox.height * 0.6) and gap < (word.bbox.height * 5.0):
                current_line.append(word)
            else:
                semantic_lines.append(_build_line(current_line))
                current_line = [word]
                
        semantic_lines.append(_build_line(current_line))
    
    return semantic_lines
    

def _build_word(chars: List[PDFCharacter]) -> PDFWord:
    word_text = "".join(c.text for c in chars)    
    word_bbox = BoundingBox(chars[0].bbox.x0, chars[0].bbox.y0, chars[0].bbox.x1, chars[0].bbox.y1)
    
    for c in chars[1:]:
        word_bbox.expand(c.bbox)
        
    return PDFWord(text=word_text, bbox=word_bbox, characters=chars)

def _build_line(words: List[PDFWord]) -> PDFLine:
    line_text = " ".join(w.text for w in words)
    line_bbox = BoundingBox(words[0].bbox.x0, words[0].bbox.y0, words[0].bbox.x1, words[0].bbox.y1)
    
    for w in words[1:]:
        line_bbox.expand(w.bbox)
        
    return PDFLine(text=line_text, bbox=line_bbox, words=words)


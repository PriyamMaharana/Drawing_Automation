import re
import logging
from typing import List

try:
    from core.entities.geometry import PDFCharacter, PDFWord, PDFLine, BoundingBox
except ImportError as e:
    logging.exception(f"Microservices import failure: {e}")

def clean_text(text: str) -> str:
    """Removes CAD hash line hallucinations and garbage OCR symbols."""
    cleaned = re.sub(r'^[^\w\s]{1,3}$', '', text) 
    cleaned = re.sub(r'[eEaAoOsS]{3,}', '', cleaned)
    cleaned = re.sub(r'(.)\1{3,}', '', cleaned)
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
        if c.text:  
            valid_chars.append(c)
            
    if not valid_chars:
        return []

    valid_chars.sort(key=lambda c: (c.bbox.center_y, c.bbox.x0))

    raw_lines: List[List[PDFCharacter]] = []
    current_line: List[PDFCharacter] = [valid_chars[0]]
    
    for i in range(1, len(valid_chars)):
        char = valid_chars[i]
        prev_char = current_line[-1]
        
        y_diff = abs(char.bbox.center_y - prev_char.bbox.center_y)
        
        y_tolerance = max(char.font_size, prev_char.font_size) * 0.6
        
        if y_diff <= y_tolerance:
            current_line.append(char)
        else:
            raw_lines.append(current_line)
            current_line = [char]
            
    if current_line:
        raw_lines.append(current_line)

    semantic_lines: List[PDFLine] = []
    
    for line_chars in raw_lines:
        line_chars.sort(key=lambda c: c.bbox.x0)
        
        words: List[PDFWord] = []
        current_word_chars: List[PDFCharacter] = [line_chars[0]]
        
        for i in range(1, len(line_chars)):
            char = line_chars[i]
            prev_char = current_word_chars[-1]
            
            x_gap = char.bbox.x0 - prev_char.bbox.x1
            
            x_tolerance = ((char.bbox.height + prev_char.bbox.height) / 2) * 0.45
            
            if x_gap <= x_tolerance:
                current_word_chars.append(char)
            else:
                words.append(_build_word(current_word_chars))
                current_word_chars = [char]
                
        if current_word_chars:
            words.append(_build_word(current_word_chars))
            
        if words:
            semantic_lines.append(_build_line(words))

    return semantic_lines

def _build_word(chars: List[PDFCharacter]) -> PDFWord:
    """Helper to stitch characters into a single PDFWord with a dynamic BBox."""
    word_text = "".join(c.text for c in chars)    
    word_bbox = BoundingBox(chars[0].bbox.x0, chars[0].bbox.y0, chars[0].bbox.x1, chars[0].bbox.y1)
    
    for c in chars[1:]:
        word_bbox.expand(c.bbox)
        
    return PDFWord(text=word_text, bbox=word_bbox, characters=chars)

def _build_line(words: List[PDFWord]) -> PDFLine:
    """Helper to stitch Words into a single PDFLine with a dynamic BBox."""
    line_text = " ".join(w.text for w in words)
    line_bbox = BoundingBox(words[0].bbox.x0, words[0].bbox.y0, words[0].bbox.x1, words[0].bbox.y1)
    
    for w in words[1:]:
        line_bbox.expand(w.bbox)
        
    return PDFLine(text=line_text, bbox=line_bbox, words=words)


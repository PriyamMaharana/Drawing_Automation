import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

class ConfidenceArbitrator:
    """
    Layer 4.2: Confidence Arbitration Engine
    Evaluates overlapping Native Vector text and OCR text, scoring them 
    to determine the absolute source of truth.
    """
    
    @classmethod
    def arbitrate(cls, vector_blocks: List[Dict], ocr_blocks: List[Dict]) -> List[Dict]:
        logger.info(f"Arbitrating {len(vector_blocks)} Vector blocks and {len(ocr_blocks)} OCR blocks.")
        resolved_blocks = []
        
        # 1. OCR is the primary baseline for visual layout
        for ocr_block in ocr_blocks:
            ocr_text = ocr_block.get("text", "").strip()
            ocr_box = ocr_block.get("bbox")
            
            # Find any overlapping vector text
            overlapping_vectors = cls._find_overlaps(ocr_box, vector_blocks)
            
            if not overlapping_vectors:
                # No conflict, OCR stands alone
                ocr_block["confidence"] = 0.85
                ocr_block["status"] = "RESOLVED"
                resolved_blocks.append(ocr_block)
                continue
                
            # 2. Conflict Detected: Score both candidates
            merged_vector_text = " ".join([v["text"] for v in overlapping_vectors]).strip()
            
            ocr_score = cls._calculate_score(ocr_text, source="ocr")
            vector_score = cls._calculate_score(merged_vector_text, source="vector")
            
            if vector_score > ocr_score:
                logger.debug(f"[ARBITRATION] Vector won: '{merged_vector_text}' over OCR: '{ocr_text}'")
                resolved_blocks.append({
                    "text": merged_vector_text,
                    "bbox": ocr_box, # Keep OCR bounding box for spatial accuracy
                    "source": "vector",
                    "confidence": min(1.0, vector_score),
                    "status": "RESOLVED"
                })
            else:
                logger.debug(f"[ARBITRATION] OCR won: '{ocr_text}' over Vector: '{merged_vector_text}'")
                ocr_block["confidence"] = min(1.0, ocr_score)
                ocr_block["status"] = "RESOLVED"
                resolved_blocks.append(ocr_block)
                
            # Remove processed vectors to avoid duplicates
            for v in overlapping_vectors:
                if v in vector_blocks:
                    vector_blocks.remove(v)

        # 3. Add any remaining standalone vector blocks
        for v in vector_blocks:
            v["confidence"] = cls._calculate_score(v.get("text", ""), source="vector")
            v["status"] = "RESOLVED" if v["confidence"] > 0.6 else "UNRESOLVED"
            resolved_blocks.append(v)
            
        return resolved_blocks

    @staticmethod
    def _find_overlaps(target_box: List[float], candidates: List[Dict], tolerance: float = 5.0) -> List[Dict]:
        """Finds blocks whose centers fall within the target bounding box (with tolerance)."""
        overlaps = []
        tx0, ty0, tx1, ty1 = target_box
        
        for cand in candidates:
            cbox = cand.get("bbox")
            cx = (cbox[0] + cbox[2]) / 2.0
            cy = (cbox[1] + cbox[3]) / 2.0
            
            if (tx0 - tolerance) <= cx <= (tx1 + tolerance) and (ty0 - tolerance) <= cy <= (ty1 + tolerance):
                overlaps.append(cand)
        return overlaps

    @staticmethod
    def _calculate_score(text: str, source: str) -> float:
        """
        Calculates a confidence score (0.0 to 1.0) based on pattern matching and completeness.
        """
        score = 0.5 if source == "ocr" else 0.6  # Vector inherently has a slightly higher base trust
        
        # Bonus for containing standard GD&T or Math symbols (Proves it's an engineering feature)
        if any(sym in text for sym in ['Ø', '⌀', '±', '°', '⌖', '⌯', 'R']):
            score += 0.25
            
        # Penalty for fragmented characters or likely OCR noise
        if re.search(r'[^a-zA-Z0-9\sØ⌀±°.,|⌖⌯]', text):
            score -= 0.15
            
        # Penalty for weird decimal spacing (Common OCR error: '0 . 5' instead of '0.5')
        if re.search(r'\d\s+\.\s+\d', text):
            score -= 0.20
            
        return max(0.0, min(1.0, score))
    
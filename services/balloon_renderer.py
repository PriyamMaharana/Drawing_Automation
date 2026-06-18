import cv2
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BalloonRenderer:
    """
    Draws the visual 'Ballooned Blueprint' for Quality Inspectors.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_fai_page(self, pdf_name: str, original_image_bytes: bytes, intelligence_data: List[Dict[str, Any]]):
        """
        Takes the raw image and the ballooned data, and physically draws the bubbles.
        """
        logger.info(f"Rendering Visual Balloon Page for {pdf_name}...")
        
        # Load the original image
        nparr = np.frombuffer(original_image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Failed to decode image for balloon rendering.")
            return

        # FAI Styling (Standard Quality Control Red)
        bubble_color = (0, 0, 255) # BGR: Red
        text_color = (255, 255, 255) # White
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for view in intelligence_data:
            for dim in view.get("dimensions", []):
                bbox = dim.get("bounding_box")
                balloon_id = str(dim.get("balloon_id", "?"))
                
                if not bbox: continue
                
                # Coordinates of the text box
                x0, y0, x1, y1 = [int(v) for v in bbox]
                
                # Calculate the center of the balloon (Place it just to the top-left of the dimension)
                radius = 25
                cx = max(radius, x0 - 15)
                cy = max(radius, y0 - 15)
                
                # 1. Draw the Bubble (Filled)
                cv2.circle(img, (cx, cy), radius, bubble_color, -1)
                # 2. Draw the Bubble Border (Black)
                cv2.circle(img, (cx, cy), radius, (0, 0, 0), 2)
                
                # 3. Center the Text inside the bubble
                text_size = cv2.getTextSize(balloon_id, font, 0.8, 2)[0]
                tx = cx - (text_size[0] // 2)
                ty = cy + (text_size[1] // 2)
                cv2.putText(img, balloon_id, (tx, ty), font, 0.8, text_color, 2, cv2.LINE_AA)
                
                # 4. Optional: Draw a subtle box around the text to highlight what is being inspected
                cv2.rectangle(img, (x0, y0), (x1, y1), (255, 0, 0), 1)

        # Save the rendered Balloon Page
        output_file = self.output_dir / f"{pdf_name.replace('.pdf', '')}_BALLOONED.jpg"
        cv2.imwrite(str(output_file), img)
        logger.info(f"🎨 Visual FAI Blueprint saved: {output_file.name}")
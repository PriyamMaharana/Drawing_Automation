import cv2
import logging
import math
import fitz
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class BalloonRenderer:
    def __init__(self, output_dir: Path, render_dpi: int = 400):
        self.output_dir = output_dir
        self.render_dpi = render_dpi

    def render_fai_page(self, filename: str, full_page_bytes: bytes, intelligence: list):
        logger.info(f"Rendering Visual Balloon Page for {filename}...")
        
        nparr = np.frombuffer(full_page_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: 
            logger.error(f"Failed to decode image buffer for {filename}")
            return

        scale = self.render_dpi / 72.0
        radius = 26 
        thickness = 3
                
        for view in intelligence:
            for dim in view.get("dimensions", []):
                b_id = str(dim.get("balloon_id", ""))
                bbox = dim.get("bounding_box_pdf", [0,0,0,0])
                
                # 1. Target Point & Balloon Center Offset
                target_x = int(bbox[0] * scale) - 5
                target_y = int(((bbox[1] + bbox[3]) / 2) * scale)

                center_x = target_x - 80 
                center_y = target_y - 60

                # Safety: Prevent the balloon from drawing off the edge of the paper
                center_x = max(center_x, radius + 5)
                center_y = max(center_y, radius + 5)

                # 2. Draw Transparent Balloon & Text
                cv2.circle(img, (center_x, center_y), radius, (0, 0, 255), thickness) 

                text_size = cv2.getTextSize(b_id, cv2.FONT_HERSHEY_SIMPLEX, 0.9, thickness)[0]
                text_x = center_x - (text_size[0] // 2)
                text_y = center_y + (text_size[1] // 2)
                cv2.putText(img, b_id, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), thickness)

                # 3. Trigonometry for the Leader Line Arrow
                if not (target_x == center_x and target_y == center_y):
                    angle = math.atan2(target_y - center_y, target_x - center_x)
                    arrow_start_x = int(center_x + radius * math.cos(angle))
                    arrow_start_y = int(center_y + radius * math.sin(angle))

                    cv2.arrowedLine(
                        img, 
                        (arrow_start_x, arrow_start_y), 
                        (target_x, target_y), 
                        (0, 0, 255), 
                        thickness, 
                        tipLength=0.15
                    )
                    
                logger.info(f"🎈 Placed Balloon #{b_id} for text '{dim.get('raw_text', '')}'")
                drawn_count += 1
                
        out_path = self.output_dir / f"{filename.replace('.pdf', '')}_BALLOONED.png"
        cv2.imwrite(str(out_path), img)
        logger.info(f"🎨 FAI Blueprint Rendered: {out_path.name}")
                
        # out_path = self.output_dir / f"{filename.replace('.pdf', '')}_BALLOONED.pdf"
        # success, buffer = cv2.imencode('.png', img)
        
        # if success:
        #     img_doc = fitz.open("png", buffer.tobytes())
        #     pdf_bytes = img_doc.convert_to_pdf()
        #     pdf_doc = fitz.open("pdf", pdf_bytes)
            
        #     pdf_doc.save(str(out_path))
        #     pdf_doc.close()
        #     img_doc.close()
            
        #     logger.info(f"🎨 FAI Blueprint Rendered: {out_path.name}")
        # else:
        #     logger.error("Failed to encode OpenCV canvas for PDF generation.")
        
        
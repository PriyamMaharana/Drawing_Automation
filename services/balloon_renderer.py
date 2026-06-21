import logging
import math
import fitz
from pathlib import Path

logger = logging.getLogger(__name__)

class BalloonRenderer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def render_fai_page(self, source_pdf_path: Path, page_num: int, intelligence: list):
        logger.info(f"Rendering Native Vector Balloon Page for {source_pdf_path.name}...")
        
        doc = fitz.open(str(source_pdf_path))
        page = doc[page_num - 1]
        
        # Native PDF points (72 per inch). No resolution scaling needed!
        radius = 12 
        drawn_count = 0
                
        for view in intelligence:
            for dim in view.get("dimensions", []):
                b_id = str(dim.get("balloon_id", ""))
                bbox = dim.get("bounding_box_pdf", [0,0,0,0])
                
                # 1. Target Point (Left center of the bounding box)
                target_x = bbox[0] - 2
                target_y = (bbox[1] + bbox[3]) / 2

                # 2. Balloon Center Offset (Push up and left by ~25 points)
                center_x = max(target_x - 25, radius + 2)
                center_y = max(target_y - 25, radius + 2)

                # 3. Draw Native Vector Circle Annotation
                rect = fitz.Rect(center_x - radius, center_y - radius, center_x + radius, center_y + radius)
                circle_annot = page.add_circle_annot(rect)
                circle_annot.set_colors(stroke=(1, 0, 0)) # Pure Red
                circle_annot.set_border(width=1.5)
                circle_annot.update()

                # 4. Draw Native Vector Text
                font_size = 10
                text_w = fitz.get_text_length(b_id, fontname="helv", fontsize=font_size)
                text_rect = fitz.Rect(center_x - text_w/2, center_y - font_size/2 - 1, center_x + text_w/2 + 2, center_y + font_size/2 + 1)
                
                text_annot = page.add_freetext_annot(text_rect, b_id, fontsize=font_size, fontname="helv", text_color=(1, 0, 0))
                text_annot.set_border(width=0) 
                text_annot.update()

                # 5. Draw Native Vector Leader Line (Arrow)
                if target_x != center_x or target_y != center_y:
                    angle = math.atan2(target_y - center_y, target_x - center_x)
                    start_x = center_x + radius * math.cos(angle)
                    start_y = center_y + radius * math.sin(angle)

                    line_annot = page.add_line_annot(fitz.Point(start_x, start_y), fitz.Point(target_x, target_y))
                    line_annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
                    line_annot.set_colors(stroke=(1, 0, 0))
                    line_annot.set_border(width=1.0)
                    line_annot.update()
                    
                logger.debug(f"🎈 Placed Vector Balloon #{b_id} for text '{dim.get('raw_text', '')}'")
                drawn_count += 1
        
        if drawn_count == 0:
            logger.warning("⚠️ Zero balloons were drawn! The extractor passed an empty list.")
                
        # Save as a brand new PDF file (A copy of the original)
        out_path = self.output_dir / f"{source_pdf_path.stem}_BALLOONED.pdf"
        doc.save(str(out_path))
        doc.close()
        
        logger.info(f"🎨 Native Vector FAI Blueprint Rendered: {out_path.name}")
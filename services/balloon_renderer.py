import logging
import math
import fitz
from pathlib import Path

try:
    from core.utils.settings import PlatformSettings
except ImportError:
    pass

logger = logging.getLogger(__name__)

class BalloonRenderer:
    def __init__(self, output_dir: Path, balloon_render: PlatformSettings.BALLOON_RENDER_DPI):
        self.output_dir = output_dir
        self.balloon_render = balloon_render

    def render_fai_page(self, source_pdf_path: Path, page_num: int, intelligence: list, debug_mode: bool = False) -> Path:
        logger.info(f"Rendering Page for {source_pdf_path.name} | Debug Mode: {debug_mode}")
        
        doc = fitz.open(str(source_pdf_path))
        page = doc[page_num - 1]
        radius = 14
        drawn_count = 0
        occupied_centers = []
        
        for view in intelligence:
            for dim in view.get("dimensions", []):
                b_id = str(dim.get("balloon_id", ""))
                bbox = dim.get("bounding_box_pdf", [0,0,0,0])
                
                if debug_mode:
                    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                    rect_annot = page.add_rect_annot(rect)
                    rect_annot.set_colors(stroke=(0, 0, 1)) # Solid Blue
                    rect_annot.set_border(width=0.5)        # Thin Line
                    rect_annot.update()
                    
                    logger.debug(f"🟦 Drew Debug Box for text '{dim.get('raw_text', '')}'")
                    drawn_count += 1
                    continue
                
                target_x = bbox[0] - 2
                target_y = (bbox[1] + bbox[3]) / 2
                
                angle_offset = -math.pi * 0.75  
                distance = 35                   
                placed = False
                center_x, center_y = target_x, target_y
                
                while not placed:
                    prop_x = target_x + distance * math.cos(angle_offset)
                    prop_y = target_y + distance * math.sin(angle_offset)

                    prop_x = max(prop_x, radius + 2)
                    prop_y = max(prop_y, radius + 2)

                    collision = False
                    for (ox, oy) in occupied_centers:
                        if math.hypot(prop_x - ox, prop_y - oy) < (radius * 2 + 5):
                            collision = True
                            break
                            
                    if not collision:
                        center_x, center_y = prop_x, prop_y
                        occupied_centers.append((center_x, center_y))
                        placed = True
                    else:
                        angle_offset += 0.4 
                        distance += 3 

                rect = fitz.Rect(center_x - radius, center_y - radius, center_x + radius, center_y + radius)
                circle_annot = page.add_circle_annot(rect)
                circle_annot.set_colors(stroke=(1, 0, 0)) 
                circle_annot.set_border(width=1.5)
                circle_annot.update()

                font_size = 10
                text_w = fitz.get_text_length(b_id, fontname="helv", fontsize=font_size)
                text_rect = fitz.Rect(center_x - text_w/2, center_y - font_size/2 - 1, center_x + text_w/2 + 2, center_y + font_size/2 + 1)
                
                text_annot = page.add_freetext_annot(text_rect, b_id, fontsize=font_size, fontname="helv", text_color=(1, 0, 0))
                text_annot.set_border(width=0) 
                text_annot.update()

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
                
        out_path = self.output_dir / f"PREVIEW.pdf"
        doc.save(str(out_path))
        doc.close()
        
        logger.info(f"🎨 Native Vector FAI Blueprint Rendered: {out_path.name}")
        return out_path
        
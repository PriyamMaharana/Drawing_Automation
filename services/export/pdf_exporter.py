import fitz
import logging
from pathlib import Path
from typing import List, Dict

try:
    from services.export.balloon_engine import AdaptiveBalloonEngine
except ImportError:
    pass

logger = logging.getLogger(__name__)

class LosslessPDFExporter:
    """
    Layer 11: Lossless PDF Exporter
    Takes coordinates from the AdaptiveBalloonEngine and injects clean, 
    vector-based PDF annotations (Red Circles & Text) into a copy of the CAD drawing.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Initialize Layer 10 Balloon Physics Engine
        self.balloon_engine = AdaptiveBalloonEngine(balloon_radius=12.0)

    def export_ballooned_pdf(self, source_pdf_path: Path, master_intelligence: List[Dict]) -> Path:
        logger.info(f"Injecting lossless vector balloons into {source_pdf_path.name}")
        
        output_path = self.output_dir / f"{source_pdf_path.stem}_Ballooned.pdf"
        
        try:
            # 1. Open Native PDF Copy
            doc = fitz.open(source_pdf_path)
            
            # 2. Iterate through extracted intelligence views
            for view in master_intelligence:
                page_idx = view.get("page_idx", 0)
                if page_idx >= doc.page_count:
                    continue
                    
                page = doc[page_idx]
                dimensions = view.get("dimensions", [])
                
                # 3. Run Layer 10 Convergence Solver for perfect coordinate placement
                self.balloon_engine.calculate_positions(dimensions)
                
                # 4. Inject Annotations based on calculated physics coordinates
                for dim in dimensions:
                    balloon_id = str(dim.get("balloon_id", ""))
                    if not balloon_id: continue
                        
                    bx = dim.get("balloon_x")
                    by = dim.get("balloon_y")
                    
                    if bx is None or by is None:
                        continue # Skip if solver failed
                        
                    radius = self.balloon_engine.radius
                    
                    # Create red circle vector annotation
                    rect = fitz.Rect(bx - radius, by - radius, bx + radius, by + radius)
                    circle_annot = page.add_circle_annot(rect)
                    circle_annot.set_colors(stroke=(1, 0, 0)) # Pure Red
                    circle_annot.set_border(width=1.5)
                    circle_annot.update()
                    
                    # Create text inside the circle
                    # Calculate center perfectly based on text length (1 vs 100)
                    font_size = 10 if len(balloon_id) < 3 else 8
                    text_rect = fitz.Rect(bx - radius, by - (font_size/1.5), bx + radius, by + radius)
                    
                    text_annot = page.add_freetext_annot(
                        text_rect, 
                        balloon_id,
                        fontsize=font_size,
                        fontname="helv",
                        text_color=(1, 0, 0),
                        align=fitz.TEXT_ALIGN_CENTER
                    )
                    text_annot.update()

            # 5. Save the final document, retaining all original vectors and text
            doc.save(output_path, garbage=3, deflate=True)
            doc.close()
            
            logger.info(f"Lossless PDF successfully exported to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate ballooned PDF: {e}")
            raise
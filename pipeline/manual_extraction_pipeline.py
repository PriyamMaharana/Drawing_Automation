import fitz
import json
import logging
from pathlib import Path
from typing import List
from core.utils.settings import PlatformSettings

logger = logging.getLogger(__name__)

try: 
    from infrastructure.ocr.image_processor import ImageProcessor2
    from infrastructure.ocr.hybrid_engine import HybridEngine
    from services.dimension_service import DimensionService
    from services.ballooning_service import BallooningService
    from services.balloon_renderer import BalloonRenderer
    from services.excel_export_service import ExcelExportService
    from infrastructure.ocr.tesseract_engine import TesseractEngine
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

class ManualExtractionPipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.res_dir = self.project_root / "debug" / "results" / "manual_extract"
        self.res_dir.mkdir(parents=True, exist_ok=True)
        
        self.image_processor = ImageProcessor2()
        self.tesseract = TesseractEngine()
        self.hybrid_engine = HybridEngine()
        self.dimension_service = DimensionService()
        self.balloon_service = BallooningService(start_index=1)
        self.render = BalloonRenderer(self.res_dir)
        template_path = self.project_root / "resources" / "excel_templates" / "Excel_Format.xlsx"
        self.excel_service = ExcelExportService(template_path, self.res_dir)

    def execute(self, pdf_path: Path, page_num: int, green_zone_px: List[List[int]]):
        logger.info(f"Igniting Manual Extraction for {len(green_zone_px)} zones on {pdf_path.name}...")
        
        doc = fitz.open(str(pdf_path))
        page = doc[page_num - 1]
        scale = PlatformSettings.PDF_BASE_DPI / PlatformSettings.UI_RENDER_DPI
        master_intelligence = []
        
        for idx, zone_px in enumerate(green_zone_px):
            logger.info(f"Processing Zone {idx + 1}/{len(green_zone_px)}...")
        
            clip_rect = fitz.Rect(
                zone_px[0] * scale, zone_px[1] * scale,
                zone_px[2] * scale, zone_px[3] * scale
            )
            debug_crop_path = str(self.res_dir / f"debug_crop_zone_{idx+1}.png")

            if hasattr(self, 'hybrid_engine'):
                unified_lines = self.hybrid_engine.extract_unified_text(
                    page=page, clip_rect=clip_rect, 
                    image_processor=getattr(self, 'image_processor', None),
                    ocr_engine=getattr(self, 'tesseract', None),
                    debug_path=debug_crop_path
                )
            else:
                continue

            try:
                from core.entities.drawing_view import DrawingView
                target_view = DrawingView(view_name=f"USER_ZONE_{idx + 1}", bounding_box=[clip_rect.x0, clip_rect.y0, clip_rect.x1, clip_rect.y1], contained_text=unified_lines)
            except ImportError:
                return logger.error("❌ Missing File: core/entities/drawing_view.py")
            
            if hasattr(self, 'dimension_service'):
                dimensions = self.dimension_service.extract_dimensions(target_view)
                master_intelligence.append({"view_name": f"USER_ZONE_{idx + 1}", "dimensions": dimensions})

        if hasattr(self, 'balloon_service'):
            self.balloon_service.apply_balloons(master_intelligence)
            
        if hasattr(self, 'renderer'):
            self.renderer.render_fai_page(pdf_path, page_num, master_intelligence)
            
        if hasattr(self, 'excel_service'):
            self.excel_service.generate_inspection_report(pdf_path.name, master_intelligence)
        
        with open(self.res_dir / f"temp_data_dump.json", "w") as f:
            json.dump(master_intelligence, f, indent=4)

        doc.close()
        return master_intelligence

    def _unify_text(self, native_blocks, ocr_lines, clip_rect, ocr_dpi):
        unified = []
        for b in native_blocks:
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    text = "".join([span["text"] for span in line["spans"]])
                    unified.append({"text": text.strip(), "bbox": line["bbox"]})
        
        scale = 72.0 / ocr_dpi
        for line in ocr_lines:
            bx0 = clip_rect.x0 + (line["bbox"][0] * scale)
            by0 = clip_rect.y0 + (line["bbox"][1] * scale)
            bx1 = clip_rect.x0 + (line["bbox"][2] * scale)
            by1 = clip_rect.y0 + (line["bbox"][3] * scale)
            unified.append({"text": line["text"], "bbox": [bx0, by0, bx1, by1]})
            
        return unified
    
    
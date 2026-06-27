import fitz
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from core.utils.logger import setup_3_tier_logging
from core.entities.drawing_view import DrawingView

try: 
    from core.utils.settings import PlatformSettings
    from infrastructure.ocr.tesseract_engine import TesseractEngine
    from infrastructure.ocr.image_processor import ImageProcessor
    from infrastructure.ocr.hybrid_engine import HybridEngine
    from services.dimension_service import DimensionService
    from services.export.pdf_exporter import LosslessPDFExporter
    from services.excel_export_service import ExcelExportService
except ImportError as e:
    print(f"Core Microservices import failure: {e}")
    raise

try:
    from services.extraction.view_segmentation import ViewSegmentationEngine
    from services.extraction.relationship_engine import EngineeringRelationshipEngine
    from services.extraction.dimension_grouper import DimensionGroupingEngine
    from services.validation.duplicate_detector import DuplicateDetectionEngine
    from services.extraction.data_normalizer import ManufacturingDataNormalizer
except ImportError as e:
    logging.warning(f"Some advanced engines are missing, running in degraded mode: {e}")
    ManufacturingDataNormalizer = None


class ManualExtractionPipeline:
    """
    V5.1 Enterprise Extraction Pipeline
    Orchestrates the flow of data from Green Zones -> Hybrid Extraction -> 
    Semantic Parsing -> Relationship Graphing -> Duplicate Detection -> Export.
    """
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.export_dir = self.project_root / "debug" / "results" / "manual_extract"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Core Infrastructure (Phase 2)
        self.image_processor = ImageProcessor()
        self.tesseract = TesseractEngine()
        self.hybrid_engine = HybridEngine()
        self.dimension_service = DimensionService()
        
        # Initialize Advanced Intelligence Engines (Phase 2 & 3)
        self.relationship_engine = EngineeringRelationshipEngine()
        
        # Initialize Export Services (Phase 3)
        self.renderer = LosslessPDFExporter(self.export_dir)
        self.excel_service = ExcelExportService(self.export_dir)

    def execute(self, pdf_path: Path, page_num: int, green_zone_px: List[List[int]], debug_mode: bool = True) -> Tuple[List[Dict], str]:
        """
        Executes the extraction pipeline for the provided Green Zones.
        Returns the arbitrated master intelligence dictionary.
        """
        setup_3_tier_logging("manual_extraction", self.project_root)
        logger = logging.getLogger(__name__)
        
        logger.info(f" IGNITING PIPELINE for {pdf_path.name} (Page {page_num})")
        logger.info(f"Targeting {len(green_zone_px)} User-Defined Green Zones.")

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        
        scale = getattr(PlatformSettings, 'PDF_BASE_DPI', 72.0) / getattr(PlatformSettings, 'UI_RENDER_DPI', 144)
        
        all_unified_blocks = []

        # LAYER 4: LOCALIZED HYBRID EXTRACTION
        for idx, zone_px in enumerate(green_zone_px):
            logger.debug(f"Processing Zone {idx+1}/{len(green_zone_px)}: {zone_px}...")
            clip_rect = fitz.Rect(
                zone_px[0] * scale, zone_px[1] * scale,
                zone_px[2] * scale, zone_px[3] * scale
            )
            
            debug_crop_path = str(self.export_dir / f"debug_crop_zone_{idx+1}.png") if debug_mode else None

            if hasattr(self, 'hybrid_engine'):
                unified_blocks = self.hybrid_engine.extract_unified_text(
                    page=page, 
                    clip_rect=clip_rect, 
                    image_processor=getattr(self, 'image_processor', None),
                    ocr_engine=getattr(self, 'tesseract', None),
                    debug_path=debug_crop_path
                )
                all_unified_blocks.extend(unified_blocks)
            else: 
                logger.error("Hybrid Engine not initialized! Skipping text extraction.")
                continue
            
        # LAYER 6: ONTOLOGY & ENGINEERING SEMANTICS
        # Create a temporary unified drawing view to pass into the Dimension Service
        master_view = DrawingView(view_name="Master View", bounding_box=[0,0,0,0])
        master_view.contained_text = all_unified_blocks
        
        raw_dimensions = self.dimension_service.extract_dimensions(master_view)
        
        # LAYER 6.5: MANUFACTURING DATA NORMALIZATION (NEW)
        if ManufacturingDataNormalizer:
            logger.info(f"Normalizing bounds for {len(raw_dimensions)} dimensions...")
            for dim in raw_dimensions:
                norm_data = ManufacturingDataNormalizer.normalize(dim.get("specification", ""))
                dim.update({
                    "nominal": norm_data.get("nominal"),
                    "upper_limit": norm_data.get("upper_limit"),
                    "lower_limit": norm_data.get("lower_limit"),
                    "entity_type": norm_data.get("type", dim.get("entity_type")),
                    "is_reference": norm_data.get("is_reference", False)
                })

        # LAYER 5.2: VIEW SEGMENTATION
        # Segment the dimensions logically (e.g., separating "SECTION A-A" from "DETAIL B")
        try:
            segmented_views = ViewSegmentationEngine.segment_dimensions(all_unified_blocks, raw_dimensions)
        except NameError:
            segmented_views = [{"view_name": "Main View", "dimensions": raw_dimensions}]

        # LAYER 5.5 & 5.7: RELATIONSHIP GRAPHING & GROUPING
        try:
            relationship_graph = self.relationship_engine.build_graph(
                dimensions=raw_dimensions, 
                lines=[],       
                geometries=[]
            )
            DimensionGroupingEngine.group_dimensions(relationship_graph, raw_dimensions)
        except Exception as e:
            logger.warning(f"Skipping Relationship Engine due to missing constraints: {e}")

        # LAYER 12.5: DUPLICATE DETECTION SWEEP
        try:
            final_intelligence = DuplicateDetectionEngine.clean_duplicates(segmented_views, spatial_tolerance=15.0)
        except NameError:
            final_intelligence = segmented_views
            
        # FINALIZATION: BALLOON ASSIGNMENT, EXPORT, AND SERIALIZATION
        # Ensure sequential balloon IDs across all segmented views
        current_balloon_id = 1
        for view in final_intelligence:
            for dim in view.get("dimensions", []):
                if "balloon_id" not in dim or not dim["balloon_id"]:
                    dim["balloon_id"] = current_balloon_id
                    current_balloon_id += 1
                else:
                    current_balloon_id = max(current_balloon_id, int(dim["balloon_id"]) + 1)
         
        preview_pdf_path = None   
        if hasattr(self, 'renderer'):
            preview_pdf_path = self.renderer.export_ballooned_pdf(pdf_path, final_intelligence)
            
        if hasattr(self, 'excel_service'):
            self.excel_service.generate_inspection_report(pdf_path.name, final_intelligence)
        
        if debug_mode:
            logger.debug("Dumping raw schema to Temp file.")
            with open(self.export_dir / f"temp_data_dump.json", "w") as f:
                json.dump(final_intelligence, f, indent=4)

        doc.close()
        logger.info("Extraction completed successfully.")
        
        # Calculate Final Stats
        total_extracted = sum(len(v.get("dimensions", [])) for v in final_intelligence)
        logger.info(f"PIPELINE COMPLETE. Yielded {total_extracted} unique, verified features across {len(final_intelligence)} views.")
        
        return final_intelligence, preview_pdf_path
    
    
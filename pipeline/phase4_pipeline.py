import logging
import json
from pathlib import Path

try:
    from services.view_isolation import ViewIsolationService
    from services.dimension_service import DimensionService
    from services.ballooning_service import BallooningService
    from services.balloon_renderer import BalloonRenderer
    from services.excel_export_service import ExcelExportService
    from core.entities.geometry import VectorPage
    from core.entities.drawing_view import DrawingView
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")

class Phase4Pipeline:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
        # Output Directories
        self.res_dir = self.project_root / "debug" / "results" / "phase4"
        self.excel_dir = self.res_dir / "reports"
        self.balloon_dir = self.res_dir / "balloons"
        
        self.res_dir.mkdir(parents=True, exist_ok=True)
        self.excel_dir.mkdir(parents=True, exist_ok=True)
        self.balloon_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Domain Services
        self.view_service = ViewIsolationService(cluster_tolerance=50.0)
        self.dimension_service = DimensionService()
        self.balloon_service = BallooningService(start_index=1)
        self.balloon_renderer = BalloonRenderer(self.balloon_dir)
        
        # Initialize Excel Exporter
        template_path = self.project_root / "resources" / "excel_templates" / "Excel_Format.xlsx"
        self.export_service = ExcelExportService(template_path, self.excel_dir)

    def execute(self, pdf_path: Path, vector_page: VectorPage, semantic_lines: list, raw_image_bytes: bytes):
        logging.info(f"Starting Phase 4 (Intelligence Layer) for: {pdf_path.name}")
        
        # 1. Spatial Partitioning: Carve the canvas into isolated views
        isolated_views = self.view_service.isolate_views(vector_page, semantic_lines)
        
        # 2. Lexical Parsing: Extract dimensions per view
        final_intelligence = []
        
        for view_dict in isolated_views:
            # Rehydrate into Entity
            view_entity = DrawingView(
                view_name=view_dict["view_name"],
                bounding_box=view_dict["bounding_box"],
                contained_text=view_dict["contained_text"],
                contained_paths=view_dict.get("contained_paths", [])
            )
            
            dimensions = self.dimension_service.extract_dimensions(view_entity)
            final_intelligence.append({
                "view_name": view_entity.view_name,
                "dimensions": dimensions
            })
            
        # 3. The Ballooning Layer: Assign sequential AS9102 IDs
        total_balloons = self.balloon_service.apply_balloons(final_intelligence)
        
        # 4. The Visual Render: Draw the red bubbles on the blueprint
        if raw_image_bytes:
            self.balloon_renderer.render_fai_page(pdf_path.name, raw_image_bytes, final_intelligence)
        
        # 5. Export JSON Payload
        self._export_json(pdf_path, final_intelligence)
        
        # 6. Generate the Final Client Excel Report
        self.export_service.generate_inspection_report(pdf_path.name, final_intelligence)
        
        return final_intelligence, total_balloons
    
    def _export_json(self, pdf_path: Path, intelligence_data: list):
        output_payload = {
            "phase": "intelligence_extraction",
            "input": pdf_path.name,
            "views": intelligence_data
        }
        
        result_file = self.res_dir / f"{pdf_path.stem}_phase4.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4)
            
            
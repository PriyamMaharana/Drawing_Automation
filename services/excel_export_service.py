import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ExcelExportService:
    """
    Takes structured intelligence from Phase 4 and maps it directly 
    into standard engineering Excel templates.
    """
    def __init__(self, template_path: Path, output_dir: Path):
        self.template_path = template_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_inspection_report(self, pdf_name: str, intelligence_data: List[Dict[str, Any]]):
        """Flattens the DrawingViews and generates the Excel sheet."""
        flattened_rows = []
        
        # Unpack the hierarchical JSON into flat rows for Excel
        for view in intelligence_data:
            view_name = view.get("view_name", "UNKNOWN")
            
            for dim in view.get("dimensions", []):
                flattened_rows.append({
                    "Drawing View": view_name,
                    "Feature Type": dim.get("feature_type", ""),
                    "Quantity": dim.get("quantity", 1),
                    "Nominal Value": dim.get("nominal", ""),
                    "Upper Tolerance": dim.get("upper_tolerance", ""),
                    "Lower Tolerance": dim.get("lower_tolerance", ""),
                    "Raw OCR Text": dim.get("raw_text", "")
                })
                
        if not flattened_rows:
            logger.warning(f"No dimensions extracted for {pdf_name}. Skipping Excel export.")
            return

        # Convert to Pandas DataFrame
        df = pd.DataFrame(flattened_rows)
        
        # Export to Excel
        output_file = self.output_dir / f"{pdf_name.replace('.pdf', '')}_Inspection_Report.xlsx"
        
        # If you have a strict template, you would use openpyxl to write to specific cells here.
        # For now, we will auto-generate a clean sheet.
        df.to_excel(output_file, index=False, sheet_name="Extracted Dimensions")
        logger.info(f"💾 Excel Report Generated: {output_file.name}")
        
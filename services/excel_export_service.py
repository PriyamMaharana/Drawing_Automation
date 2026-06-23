import logging
import re
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class ExcelExportService:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _smart_pad(self, text: str) -> str:
        """
        Only pads purely numeric strings (e.g. '308' -> '308.000').
        Leaves symbols, degrees, and radii alone (e.g. '6°', 'R10', 'Ø59.42').
        """
        if not text:
            return ""
        text = str(text).strip()
        
        # If the string consists ONLY of digits and an optional decimal
        if re.match(r'^\d+(?:\.\d+)?$', text):
            return f"{float(text):.3f}"
        return text

    def generate_inspection_report(self, pdf_filename: str, intelligence: list):
        logger.info(f"Generating Excel report for {pdf_filename}...")
        flattened_rows = []        
        for view in intelligence:           
            for dim in view.get("dimensions", []):
                spec = dim.get("specification", dim.get("raw_text", ""))
                tol = dim.get("tolerance", "")
                
                flattened_rows.append({
                    "Sl.No.": dim.get("balloon_id"),
                    "Parameter": "",
                    "Specification": self._smart_pad(spec),
                    "Tolerance": tol
                })
                
        if flattened_rows:
            df = pd.DataFrame(flattened_rows, columns=["Sl.No.", "Parameter", "Specification", "Tolerance"])
            
            output_file = self.output_dir / f"{pdf_filename.replace('.pdf', '')}_Report.xlsx"
            try:
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Extracted Dimensions")
                    workbook = writer.book
                    worksheet = writer.sheets['Extracted Dimensions']
                    
                    # Force Text format to prevent Excel from converting ranges into dates
                    text_format = workbook.add_format({'num_format': '@'})
                    worksheet.set_column('C:D', 20, text_format)
                    worksheet.set_column('A:B', 12)
                    
                logger.info(f"💾 Excel Report Generated: {output_file}")
            except Exception as e:
                logger.error(f"Excel export failed: {e}")
        else:
            logger.warning(f"No dimensions extracted for {pdf_filename}. Skipping Excel export.")
            
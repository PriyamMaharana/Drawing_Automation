import logging
import re
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class ExcelExportService:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_for_excel(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return text
            
        cleaned = re.sub(r'[()[\]{}]', '', text)
        cleaned = re.sub(r'\b[A-Za-z]{2,}\b', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def _split_specification_and_tolerance(self, raw_text: str):
        raw_text = str(raw_text).strip()
        
        if '±' in raw_text:
            parts = raw_text.split('±')
            return parts[0].strip(), '±' + parts[1].strip()
        
        match = re.search(r'^(.*?)([\+\-]\s*\d+\.?\d*.*)$', raw_text)
        if match:
            base = match.group(1).strip()
            tol = match.group(2).strip()
            if any(char.isdigit() for char in base) or "Ø" in base or "R" in base:
                return base, tol
        
        return raw_text, ""

    def generate_inspection_report(self, filename: str, intelligence: list):
        flattened_rows = []        
        for view in intelligence:           
            for dim in view.get("dimensions", []):
                raw_text = dim.get("raw_text", "")
                clean_raw_text = self._sanitize_for_excel(raw_text)
                for key in ["nominal", "upper_tolerance", "lower_tolerance"]:
                    if key in dim and isinstance(dim[key], str):
                        dim[key] = self._sanitize_for_excel(dim[key])
                spec, tol = self._split_specification_and_tolerance(clean_raw_text)
                
                flattened_rows.append({
                    "SL NO.": dim.get("balloon_id"),
                    "Product Parameter": "",
                    "Specification": spec,
                    "Tolerance": tol,
                    "Checking Method": "",
                    "Observation": "",
                    "Remarks": ""
                })
                
        if flattened_rows:
            df = pd.DataFrame(flattened_rows, columns=[
                "SL NO.", "Product Parameter", "Specification", 
                "Tolerance", "Checking Method", "Observation", "Remarks"
            ])
            
            output_file = self.output_dir / f"{filename.replace('.pdf', '')}_Report.xlsx"
            df.to_excel(output_file, index=False, sheet_name="Extracted Dimensions")
            logger.info(f"💾 Excel Report Generated: {output_file.name}")
        else:
            logger.warning(f"No dimensions extracted for {filename}. Skipping Excel export.")
            return


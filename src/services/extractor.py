import fitz
from typing import List
from src.models.parameter import TextParameter

class PDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def is_drawing_page(self, page: fitz.Page) -> bool:
        """
        Heuristic to determine if a page is a drawing page.
        Drawing pages typically have a large bounding box and contain engineering lines.
        """
        paths = page.get_drawings()
        # If there are a significant number of vector paths, it's likely a drawing
        if len(paths) > 10:
            return True
        return False

    def extract_text_parameters(self) -> List[TextParameter]:
        parameters = []
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            if not self.is_drawing_page(page):
                print(f"Page {page_num} seems to be a cover/text page, skipping extraction.")
                continue
                
            print(f"Extracting text from drawing page {page_num}...")
            
            # Extract text dictionary
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox")
                                param = TextParameter(
                                    text=text,
                                    x0=bbox[0],
                                    y0=bbox[1],
                                    x1=bbox[2],
                                    y1=bbox[3],
                                    page_number=page_num
                                )
                                parameters.append(param)
        
        return parameters

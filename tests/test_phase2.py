import os
import sys
import fitz

# Ensure the root directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.vision_service import VisionProcessor
from src.services.extractor import PDFExtractor

def test_vision_processor():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_pdf = os.path.join(root_dir, "resources", "sample_data", "4.pdf")
    
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return
        
    print(f"Starting Phase 2 Vision Processing on: {sample_pdf}")
    
    # 1. Identify a drawing page using our Phase 1 extractor logic
    extractor = PDFExtractor(sample_pdf)
    from src.services.health_checker import run_pre_flight_check
    
    drawing_page = None
    page_num_to_test = -1
    
    for page_num in range(len(extractor.doc)):
        page = extractor.doc[page_num]
        human_page = page_num + 1
        health_status = run_pre_flight_check(page, human_page)
        
        if health_status not in ("RASTER_SCAN", "CORRUPT_FONT"):
            if extractor.is_drawing_page(page, human_page, health_status):
                drawing_page = page
                page_num_to_test = page_num
                break
            
    if not drawing_page:
        print("Error: Could not find any drawing pages in the sample PDF.")
        return
        
    print(f"Found drawing page at index {page_num_to_test}. Processing...")
    
    # 2. Process with the VisionProcessor
    processor = VisionProcessor()
    tables = processor.process_page(drawing_page, sample_pdf)
    
    print(f"\nProcessing complete! Found {len(tables)} tables/dead-zones.")
    for i, table in enumerate(tables):
        print(f"Table {i+1}: x0={table['x0']:.2f}, y0={table['y0']:.2f}, x1={table['x1']:.2f}, y1={table['y1']:.2f}")
        
    print("\nPlease check 'debug_mask.png' in the project root to visually verify the table isolation.")

if __name__ == "__main__":
    test_vision_processor()

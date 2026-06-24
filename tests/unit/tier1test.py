import sys
import logging
from pathlib import Path

# =========================================================================
# DYNAMIC PATH INJECTION (From your Canvas selection)
# =========================================================================
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR
while not (PROJECT_ROOT / 'services').exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =========================================================================
# PIPELINE IMPORTS
# =========================================================================
from pipeline.manual_extraction_pipeline import ManualExtractionPipeline

# Setup basic console logging to see what the engine is doing
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_real_pdf_extraction(pdf_path: str):
    logger.info(f"--- Starting Real Data Extraction on: {pdf_path} ---")

    # 1. Initialize the Pipeline
    pipeline = ManualExtractionPipeline(PROJECT_ROOT)

    # 2. Define a massive mock "Green Zone" that covers an entire page
    # [x_min, y_min, x_max, y_max] in PDF points
    mock_green_zone_px = [[0, 0, 5000, 5000]] 

    try:
        # 3. Execute extraction on Page 1
        logger.info("Executing Hybrid Extraction Engine...")
        intelligence, _ = pipeline.execute(
            pdf_path=Path(pdf_path),
            page_num=1,
            green_zone_px=mock_green_zone_px,  # Fixed parameter name here!
            debug_mode=False
        )

        # 4. Output the results cleanly to the console
        print("\n" + "="*60)
        print(" 🎯 EXTRACTION RESULTS ")
        print("="*60)
        
        if not intelligence:
            print("No dimensions were found or extracted.")
            return

        for view in intelligence:
            print(f"\n📁 View/Region: {view.get('view_name', 'Unknown')}")
            print("-" * 60)
            
            for dim in view.get("dimensions", []):
                b_id = dim.get('balloon_id', '--')
                e_type = dim.get('entity_type', 'Unknown')
                spec = dim.get('specification', '')
                tol = dim.get('tolerance', dim.get('plus_tol', ''))
                raw = dim.get('raw_text', '')
                
                print(f"[{b_id}] TYPE: {e_type.ljust(15)} | SPEC: {spec.ljust(10)} | TOL: {tol.ljust(10)} | RAW: {raw}")
                
        print("\n" + "="*60)
        print("Test Complete.")

    except Exception as e:
        logger.exception(f"Pipeline failed during real data test: {e}")

if __name__ == "__main__":
    print("Welcome to the Real Data Extraction Tester!")
    
    # Prompt you to paste the path to your test PDF
    # Example: E:\RSB GLOBAL\Drawing_Automation\sample_drawing.pdf
    user_input_path = input("Enter the full path to your PDF drawing: ").strip()
    
    # Remove surrounding quotes if you copy-pasted a path with spaces
    if user_input_path.startswith('"') and user_input_path.endswith('"'):
        user_input_path = user_input_path[1:-1]

    if Path(user_input_path).exists():
        test_real_pdf_extraction(user_input_path)
    else:
        print("\n❌ Error: File does not exist. Please check the path and try again.")
        
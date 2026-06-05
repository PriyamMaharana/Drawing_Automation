import typing_extensions
import os
import sys

# Ensure the root directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.extractor import PDFExtractor

def main():
    # Use 1.pdf from the sample_data directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_pdf = os.path.join(root_dir, "resources", "sample_data", "1.pdf")
    
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        return
        
    print(f"Starting Phase 1 extraction on: {sample_pdf}")
    
    extractor = PDFExtractor(sample_pdf)
    parameters = extractor.extract_text_parameters()
    
    print(f"\nExtracted {len(parameters)} text parameters.")
    if parameters:
        print("Sample of extracted parameters (first 20):")
        for i, param in enumerate(parameters[:20]):
            print(f"{i+1:02d}: '{param.text}' at ({param.x0:.2f}, {param.y0:.2f}) -> ({param.x1:.2f}, {param.y1:.2f})")
            
        import json
        output_file = os.path.join(root_dir, "temp_extracted_data.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in parameters], f, indent=4)
        print(f"\nAll extracted data has been saved to: {output_file}")
    else:
        print("No text parameters extracted. It's possible no drawing pages were found.")

if __name__ == "__main__":
    main()

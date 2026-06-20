from pathlib import Path

class PlatformSettings:
    """
    Centralized Configuration Manager for the CAD Intelligence Platform.
    Single Source of Truth for all rendering and extraction resolutions.
    """
    PDF_BASE_DPI: float = 72.0 
    UI_RENDER_DPI: int = 300 
    OCR_EXTRACTION_DPI: int = 600 
    EXPORT_RENDER_DPI: int = 300 

    OCR_MIN_CONFIDENCE: int = 10
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TESSERACT_CMD: Path = BASE_DIR / "bin" / "Tesseract-OCR" / "tesseract.exe"
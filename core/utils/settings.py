from pathlib import Path

class PlatformSettings:
    """
    Centralized Configuration Manager for the CAD Intelligence Platform.
    Single Source of Truth for all rendering and extraction resolutions.
    """
    PDF_BASE_DPI: float = 72.0 
    UI_RENDER_DPI: int = 144
    NATIVE_EXTRACTION_DPI = 300
    OCR_EXTRACTION_DPI: int = 400 
    EXPORT_RENDER_DPI: int = 300 
    BALLOON_RENDER_DPI: int = 400
    OCR_MIN_CONFIDENCE: int = 30
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TESSERACT_CMD: Path = BASE_DIR / "bin" / "Tesseract-OCR" / "tesseract.exe"
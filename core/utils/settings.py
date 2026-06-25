import os
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PlatformSettingsManager:
    """
    Centralized Configuration Manager for the CAD Intelligence Platform.
    Single Source of Truth. Dynamically tied to the PySide6 UI Settings.
    """
    _instance = None
    _config = {}

    # 1. STATIC PATHS (These never change)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TESSERACT_CMD: Path = BASE_DIR / "bin" / "Tesseract-OCR" / "tesseract.exe"
    PDF_BASE_DPI: float = 72.0 

    def __new__(cls):
        # Singleton Pattern: Only one settings manager exists in memory
        if cls._instance is None:
            cls._instance = super(PlatformSettingsManager, cls).__new__(cls)
            cls._instance._config_path = cls._instance.BASE_DIR / "ui" / "desktop" / "config" / "user_config.yaml"
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        try:
            with open(self._config_path, 'r') as file:
                self._config = yaml.safe_load(file) or {}
            logger.info(f"Dynamic settings loaded from {self._config_path.name}")
        except FileNotFoundError:
            logger.warning("user_config.yaml not found. Using defaults.")
            self._config = self._get_safe_defaults()
            self.save_to_disk()

    # =========================================================================
    # DYNAMIC PROPERTIES (Replaces your old static variables)
    # Whenever the backend calls PlatformSettings.UI_RENDER_DPI, it fetches live!
    # =========================================================================

    @property
    def UI_RENDER_DPI(self) -> int:
        return self.get("extraction", "preview_dpi", 144)

    @property
    def NATIVE_EXTRACTION_DPI(self) -> int:
        return self.get("extraction", "raster_dpi", 300)

    @property
    def OCR_EXTRACTION_DPI(self) -> int:
        return self.get("extraction", "raster_dpi", 400)

    @property
    def EXPORT_RENDER_DPI(self) -> int:
        return self.get("extraction", "raster_dpi", 300)

    @property
    def BALLOON_RENDER_DPI(self) -> int:
        return self.get("extraction", "raster_dpi", 400)

    @property
    def OCR_MIN_CONFIDENCE(self) -> int:
        return self.get("extraction", "min_confidence", 80)

    # =========================================================================
    # GETTERS AND SETTERS FOR THE PYSIDE6 UI
    # =========================================================================

    def get(self, section: str, key: str, default=None):
        """Fetches a specific dynamic setting from memory."""
        return self._config.get(section, {}).get(key, default)

    def update_settings(self, new_config: dict):
        """Called by UI Settings Page to update memory and save to YAML."""
        for section, values in new_config.items():
            if section not in self._config:
                self._config[section] = {}
            self._config[section].update(values)
            
        self.save_to_disk()
        logger.info("Settings dynamically applied and written to YAML.")

    def save_to_disk(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, 'w') as file:
            yaml.dump(self._config, file, default_flow_style=False)

    def _get_safe_defaults(self):
        return {
            "appearance": {"font_size": 12, "theme": "light"},
            "ballooning": {"color": "red", "leader_line_color": "red", "radius": 20, "shape": "circle", "text_size": 12},
            "extraction": {"line_text_enhancement": True, "min_confidence": 80, "preview_dpi": 144, "raster_dpi": 300, "engine": "Tesseract"},
            "export": {"generate_excel": True, "generate_pdf": True, "output_directory": ""},
            "performance": {"hardware_acceleration": True, "memory_watchdog_limit": 85, "thread_count": 4}
        }

# Instantiate global settings
app_settings = PlatformSettingsManager()
PlatformSettings = app_settings
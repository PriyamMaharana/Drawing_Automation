import logging
from pathlib import Path
from PySide6.QtGui import QIcon

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ICON_DIR = PROJECT_ROOT / "resources" / "icons"

class IconLibrary:
    _cache = {}

    @classmethod
    def get(cls, icon_filename: str) -> QIcon:
        if not icon_filename.endswith(".svg"):
            icon_filename += ".svg"

        if icon_filename in cls._cache:
            return cls._cache[icon_filename]

        icon_path = ICON_DIR / icon_filename
        
        if not icon_path.exists():
            logging.warning(f"⚠️ Icon Missing: {icon_path.name}")
            return QIcon() 

        icon = QIcon(str(icon_path))
        cls._cache[icon_filename] = icon
        return icon
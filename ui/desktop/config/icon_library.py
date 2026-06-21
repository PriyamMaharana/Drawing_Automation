import logging
from pathlib import Path
from PySide6.QtGui import QIcon

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ICON_DIR = PROJECT_ROOT / "resources" / "icons"

class Ico:
    # --- Navigation & Dashboard ---
    LAYOUT_DASHBOARD = "layout-dashboard.svg"
    LAYOUT_PANEL_TOP = "layout-panel-top.svg"
    SETTINGS = "settings.svg"
    USER = "user.svg"
    
    # --- Files & Folders ---
    FOLDER = "folder.svg"
    NEW_FOLDER = "New-Folder--Streamline-Flex.svg"
    FILE_TEXT = "file-text.svg"
    FILE_TEXT_PURPLE = "file-text-purple.svg"
    FILE_CODE_CORNER = "file-code-corner.svg"
    FILE_REPORT = "File-Report--Streamline-Plump-Gradient.svg"
    FILE_CHART_COLUMN = "file-chart-column.svg"
    COMPRESS_PDF = "Compress-Pdf--Streamline-Plump-Gradient.svg"
    SCRIPT = "Script-2--Streamline-Plump-Gradient.svg"

    # --- Actions & Status ---
    CIRCLE_CHECK_BIG = "circle-check-big.svg"
    BADGE_CHECK = "badge-check.svg"
    SHIELD_CHECK = "shield-check.svg"
    FILE_X_GREEN = "file-x-green.svg"
    TRIANGLE_ALERT = "triangle-alert.svg"
    INFO = "info.svg"
    BELL = "bell.svg"
    CLOCK_YELLOW = "clock-yellow.svg"
    CLOUD_ADD = "Cloud-Add--Streamline-Core.svg"

    # --- Data & Graphics ---
    CHART_NO_AXES = "chart-no-axes-column.svg"
    LAYERS = "layers.svg"
    GRID_GREEN = "Grid-green--Streamline-Flex.svg"
    MUSIC_EQUALIZER = "Music-Equalizer--Streamline-Core.svg"

    # --- UI Elements & Toggles ---
    CHEVRON_DOWN = "chevron-down.svg"
    CHEVRON_LEFT = "chevron-left.svg"
    CHEVRON_RIGHT = "chevron-right.svg"
    DOT = "dot.svg"
    SUN_DIM = "sun-dim.svg"
    MOON = "moon.svg"


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
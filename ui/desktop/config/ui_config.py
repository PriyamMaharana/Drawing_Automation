import yaml
import logging
from pathlib import Path

# Resolve Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = Path(__file__).resolve().parent
THEME_DIR = CONFIG_DIR.parent / "theme"

APP_YAML_PATH = CONFIG_DIR / "app_config.yaml"
USER_YAML_PATH = CONFIG_DIR / "user_config.yaml"

class AppConfig:
    # --- LOAD APP SETTINGS (Static) ---
    with open(APP_YAML_PATH, "r") as f:
        _app_cfg = yaml.safe_load(f)

    APP_NAME = _app_cfg["app"]["name"]
    LOGO_PATH = str(PROJECT_ROOT / _app_cfg["resources"]["logo"])
    ICON_DASHBOARD = str(PROJECT_ROOT / _app_cfg["resources"]["icons"]["dashboard"])
    ICON_PROCESS = str(PROJECT_ROOT / _app_cfg["resources"]["icons"]["process"])
    ICON_REPORTS = str(PROJECT_ROOT / _app_cfg["resources"]["icons"]["reports"])
    ICON_SETTINGS = str(PROJECT_ROOT / _app_cfg["resources"]["icons"]["settings"])

    @classmethod
    def load_user_settings(cls):
        """Reads the latest user settings from YAML."""
        if not USER_YAML_PATH.exists():
            return {}
        with open(USER_YAML_PATH, "r") as f:
            return yaml.safe_load(f)

    @classmethod
    def save_user_settings(cls, new_settings_dict):
        """Writes updated user preferences back to the YAML file."""
        with open(USER_YAML_PATH, "w") as f:
            yaml.dump(new_settings_dict, f, default_flow_style=False)

    @classmethod
    def load_stylesheet(cls, theme_filename: str) -> str:
        """Reads a .qss file and returns it as a string for PySide6."""
        qss_path = THEME_DIR / theme_filename
        if qss_path.exists():
            with open(qss_path, "r") as f:
                return f.read()
        logging.error(f"Stylesheet not found: {qss_path}")
        return "" 
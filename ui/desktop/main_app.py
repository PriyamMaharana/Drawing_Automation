import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QPushButton, QLabel, QStackedWidget, 
                               QSpacerItem, QSizePolicy)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QSize

# Core Configuration
from config.ui_config import AppConfig
from config.icon_library import IconLibrary

# Import Application Pages
from pages.dashboard import DashboardPage
from pages.process_pdf import ExtractionPage
from pages.reports import ReportsPage
from pages.settings import SettingsPage

class MainShell(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. LOAD YAML SETTINGS & APPLY GLOBAL THEME
        user_cfg = AppConfig.load_user_settings()
        theme_file = user_cfg.get("appearance", {}).get("theme", "white_theme.qss")
        font_family = user_cfg.get("appearance", {}).get("font_family", "Segoe UI")
        font_size = int(user_cfg.get("appearance", {}).get("font_size", 10))

        app = QApplication.instance()
        if app:
            app.setFont(QFont(font_family, font_size))
            qss = AppConfig.load_stylesheet(theme_file)
            app.setStyleSheet(qss) 
            
        self.setWindowTitle(AppConfig.APP_NAME)
        self.setMinimumSize(1024, 768)

        # 2. BUILD MAIN LAYOUT
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_sidebar(main_layout)
        self._build_page_stack(main_layout)

        self.switch_page(0) 

    def _build_sidebar(self, parent_layout):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(10)

        # App Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(AppConfig.LOGO_PATH).scaled(200, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)

        # Navigation Buttons
        self.nav_buttons = []
        self.btn_dashboard = self._create_nav_button(" Dashboard", IconLibrary.get("layout-dashboard"), 0)
        self.btn_process = self._create_nav_button(" Process PDF", IconLibrary.get("file-text"), 1)
        self.btn_reports = self._create_nav_button(" Results / Reports", IconLibrary.get("file-chart-column"), 2)
        
        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_process)
        sidebar_layout.addWidget(self.btn_reports)

        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.btn_settings = self._create_nav_button(" Settings", IconLibrary.get("settings"), 3)
        sidebar_layout.addWidget(self.btn_settings)

        parent_layout.addWidget(self.sidebar)

    def _create_nav_button(self, text, q_icon, page_index):
        btn = QPushButton(text)
        btn.setProperty("class", "NavBtn") 
        btn.setIcon(q_icon) 
        btn.setIconSize(QSize(20, 20))
        btn.clicked.connect(lambda: self.switch_page(page_index))
        self.nav_buttons.append(btn)
        return btn

    def _build_page_stack(self, parent_layout):
        self.stack = QStackedWidget()
        
        # Instantiate Pages
        self.page0 = DashboardPage()
        self.page1 = ExtractionPage()
        self.page2 = ReportsPage()
        self.page3 = SettingsPage()

        self.stack.addWidget(self.page0) # Index 0
        self.stack.addWidget(self.page1) # Index 1
        self.stack.addWidget(self.page2) # Index 2
        self.stack.addWidget(self.page3) # Index 3
        
        parent_layout.addWidget(self.stack)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        
        # Update Sidebar Styling
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            
            btn.style().unpolish(btn)
            btn.style().polish(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainShell()
    window.showMaximized() 
    sys.exit(app.exec())
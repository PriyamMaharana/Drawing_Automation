from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QFileDialog, QLineEdit,
                               QGroupBox, QApplication, QGridLayout, QScrollArea, QCheckBox, QButtonGroup)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from config.ui_config import AppConfig

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Load Last Saved Settings from YAML
        self.user_cfg = AppConfig.load_user_settings()
        self.appearance = self.user_cfg.get("appearance", {})
        self.output_cfg = self.user_cfg.get("output", {})
        self.ocr_cfg = self.user_cfg.get("ocr", {})
        self.export_cfg = self.user_cfg.get("export", {})

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 28px; font-weight: bold; border: none; background: transparent; color: #F8FAFC;")
        subtitle = QLabel("Configure application preferences and system settings.")
        subtitle.setStyleSheet("font-size: 14px; color: #94A3B8; border: none; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addSpacing(10)
        main_layout.addLayout(header_layout)

        # --- Scrollable Content Grid ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.content_widget = QWidget()
        self.grid = QGridLayout(self.content_widget)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignTop)

        # Build Exactly 4 Cards Requested
        self._build_appearance_card()
        self._build_output_card()
        self._build_ocr_card()
        self._build_export_card()

        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area, stretch=1)

    # --- HELPER WIDGET BUILDER FOR EXACT MOCKUP ALIGNMENT ---
    def _build_row(self, title, subtitle, control_widget):
        row = QWidget()
        lyt = QHBoxLayout(row)
        lyt.setContentsMargins(0, 0, 0, 0)

        text_lyt = QVBoxLayout()
        text_lyt.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #E2E8F0; background: transparent;")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8; background: transparent;")

        text_lyt.addWidget(lbl_title)
        text_lyt.addWidget(lbl_sub)
        text_lyt.addStretch()

        lyt.addLayout(text_lyt)
        lyt.addStretch()
        lyt.addWidget(control_widget, alignment=Qt.AlignRight | Qt.AlignVCenter)
        return row

    # --- CARD 1: APPEARANCE ---
    def _build_appearance_card(self):
        grp = QGroupBox("Appearance")
        lyt = QVBoxLayout(grp)
        lyt.setSpacing(20)

        # Theme Block Selector
        theme_lyt = QHBoxLayout()
        self.btn_theme_dark = QPushButton("Dark Mode")
        self.btn_theme_light = QPushButton("Light Mode")
        self.btn_theme_dark.setProperty("class", "OptionBlock")
        self.btn_theme_light.setProperty("class", "OptionBlock")
        self.btn_theme_dark.setFixedSize(140, 80)
        self.btn_theme_light.setFixedSize(140, 80)
        
        self.btn_theme_dark.setCheckable(True)
        self.btn_theme_light.setCheckable(True)
        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.btn_theme_dark)
        self.theme_group.addButton(self.btn_theme_light)
        
        if "dark" in self.appearance.get("theme", "dark_theme.qss"):
            self.btn_theme_dark.setChecked(True)
        else:
            self.btn_theme_light.setChecked(True)
            
        self.theme_group.buttonClicked.connect(self._auto_save_and_apply)
        
        theme_lyt.addWidget(self.btn_theme_dark)
        theme_lyt.addWidget(self.btn_theme_light)
        theme_lyt.addStretch()
        lyt.addWidget(self._build_row("Theme", "Choose application theme", QWidget())) # Hack to align labels
        lyt.addLayout(theme_lyt)

        # Font Size Block Selector (8, 10, 12, 14 exact requirement)
        font_box_lyt = QHBoxLayout()
        self.size_group = QButtonGroup(self)
        sizes = [("Small\n8px", 8), ("Medium\n10px", 10), ("Large\n12px", 12), ("X-Large\n14px", 14)]
        
        saved_size = int(self.appearance.get("font_size", 10))
        self.size_buttons = {}
        
        for label, pt in sizes:
            btn = QPushButton(f"Aa\n{label}")
            btn.setProperty("class", "OptionBlock")
            btn.setFixedSize(80, 80)
            btn.setCheckable(True)
            if pt == saved_size: btn.setChecked(True)
            self.size_group.addButton(btn)
            self.size_buttons[btn] = pt
            font_box_lyt.addWidget(btn)
            
        font_box_lyt.addStretch()
        self.size_group.buttonClicked.connect(self._auto_save_and_apply)
        
        lyt.addWidget(self._build_row("Font Size", "Adjust global font size", QWidget()))
        lyt.addLayout(font_box_lyt)

        # Dropdowns
        self.cb_font = QComboBox()
        self.cb_font.addItems(["Segoe UI", "Arial", "Roboto", "Consolas"])
        self.cb_font.setCurrentText(self.appearance.get("font_family", "Segoe UI"))
        self.cb_font.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Font Family", "Choose application font", self.cb_font))

        self.cb_density = QComboBox()
        self.cb_density.addItems(["Compact", "Comfortable", "Spacious"])
        self.cb_density.setCurrentText(self.appearance.get("ui_density", "Comfortable"))
        self.cb_density.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("UI Density", "Adjust spacing between UI elements", self.cb_density))
        
        self.grid.addWidget(grp, 0, 0) # Top Left

    # --- CARD 2: OUTPUT SETTINGS ---
    def _build_output_card(self):
        grp = QGroupBox("Output Settings")
        lyt = QVBoxLayout(grp)
        lyt.setSpacing(15)

        lbl = QLabel("Default Output Folder\nWhere all reports and files will be saved")
        lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; background: transparent;")
        lyt.addWidget(lbl)

        row = QHBoxLayout()
        self.le_path = QLineEdit(self.output_cfg.get("default_path", str(Path.home())))
        self.le_path.textChanged.connect(self._auto_save_and_apply)
        
        btn_browse = QPushButton("Browse")
        btn_browse.setProperty("class", "Primary")
        btn_browse.clicked.connect(self._browse_folder)
        row.addWidget(self.le_path)
        row.addWidget(btn_browse)
        lyt.addLayout(row)

        self.chk_date_folder = QCheckBox("Create date folder")
        self.chk_date_folder.setChecked(self.output_cfg.get("create_date_folder", True))
        
        self.chk_open_after = QCheckBox("Open output folder after processing")
        self.chk_open_after.setChecked(self.output_cfg.get("open_after_processing", True))
        
        self.chk_keep_org = QCheckBox("Keep output files organized in subfolders")
        self.chk_keep_org.setChecked(self.output_cfg.get("keep_organized", True))

        for chk in [self.chk_date_folder, self.chk_open_after, self.chk_keep_org]:
            chk.toggled.connect(self._auto_save_and_apply)
            lyt.addWidget(chk)
            
        lyt.addSpacing(20)
        self.cb_export_fmt = QComboBox()
        self.cb_export_fmt.addItems(["Both (Excel + PDF)", "Excel Only", "PDF Only"])
        self.cb_export_fmt.setCurrentText(self.output_cfg.get("default_export_format", "Both (Excel + PDF)"))
        self.cb_export_fmt.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Default Export Format", "Choose default export format", self.cb_export_fmt))
        
        lyt.addStretch()
        self.grid.addWidget(grp, 0, 1) # Top Right

    # --- CARD 3: OCR SETTINGS ---
    def _build_ocr_card(self):
        grp = QGroupBox("OCR Settings (For Scanned PDFs)")
        lyt = QVBoxLayout(grp)
        lyt.setSpacing(15)

        self.chk_ocr_enable = QCheckBox()
        self.chk_ocr_enable.setProperty("class", "Toggle") # Turns it into a pill!
        self.chk_ocr_enable.setChecked(self.ocr_cfg.get("enable", True))
        self.chk_ocr_enable.toggled.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Enable OCR", "Enable OCR for scanned PDFs", self.chk_ocr_enable))
        
        self.cb_ocr_engine = QComboBox()
        self.cb_ocr_engine.addItems(["Tesseract (Recommended)", "EasyOCR", "PaddleOCR"])
        self.cb_ocr_engine.setCurrentText(self.ocr_cfg.get("engine", "Tesseract (Recommended)"))
        self.cb_ocr_engine.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("OCR Engine", "Select OCR engine", self.cb_ocr_engine))
        
        self.cb_dpi = QComboBox()
        self.cb_dpi.addItems(["150 DPI", "300 DPI", "600 DPI"])
        self.cb_dpi.setCurrentText(self.ocr_cfg.get("dpi", "300 DPI"))
        self.cb_dpi.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Image DPI", "DPI for converting PDF pages to images", self.cb_dpi))

        self.cb_conf = QComboBox()
        self.cb_conf.addItems(["70%", "80%", "85%", "90%", "95%"])
        self.cb_conf.setCurrentText(self.ocr_cfg.get("min_confidence", "85%"))
        self.cb_conf.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Minimum Confidence", "Minimum confidence to accept text", self.cb_conf))

        self.chk_auto_enhance = QCheckBox()
        self.chk_auto_enhance.setProperty("class", "Toggle")
        self.chk_auto_enhance.setChecked(self.ocr_cfg.get("auto_enhance", True))
        self.chk_auto_enhance.toggled.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Auto Enhance Image", "Automatically enhance image before OCR", self.chk_auto_enhance))
        
        lyt.addStretch()
        self.grid.addWidget(grp, 1, 0) # Bottom Left

    # --- CARD 4: EXPORT SETTINGS ---
    def _build_export_card(self):
        grp = QGroupBox("Export Settings")
        lyt = QVBoxLayout(grp)
        lyt.setSpacing(15)

        self.chk_gen_pdf = QCheckBox("Generate Ballooned PDF\nCreate ballooned drawing PDF")
        self.chk_gen_pdf.setChecked(self.export_cfg.get("generate_pdf", True))
        
        self.chk_gen_xl = QCheckBox("Generate Excel Inspection Sheet\nCreate inspection Excel sheet")
        self.chk_gen_xl.setChecked(self.export_cfg.get("generate_excel", True))

        self.chk_gen_sum = QCheckBox("Generate Summary Report\nCreate summary report (PDF)")
        self.chk_gen_sum.setChecked(self.export_cfg.get("generate_summary", True))

        for chk in [self.chk_gen_pdf, self.chk_gen_xl, self.chk_gen_sum]:
            chk.toggled.connect(self._auto_save_and_apply)
            lyt.addWidget(chk)

        lyt.addSpacing(10)
        self.cb_xl_temp = QComboBox()
        self.cb_xl_temp.addItems(["Default Template", "Custom Template 1"])
        self.cb_xl_temp.setCurrentText(self.export_cfg.get("excel_template", "Default Template"))
        self.cb_xl_temp.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Excel Template", "Choose inspection sheet template", self.cb_xl_temp))

        self.cb_xl_head = QComboBox()
        self.cb_xl_head.addItems(["Style 1", "Style 2", "Minimal"])
        self.cb_xl_head.setCurrentText(self.export_cfg.get("header_style", "Style 1"))
        self.cb_xl_head.currentIndexChanged.connect(self._auto_save_and_apply)
        lyt.addWidget(self._build_row("Excel Header Style", "Choose header style", self.cb_xl_head))
        
        lyt.addStretch()
        self.grid.addWidget(grp, 1, 1) # Bottom Right

    # --- BACKEND LOGIC ---
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination", self.le_path.text())
        if folder: 
            self.le_path.setText(folder)
            self._auto_save_and_apply() # Trigger save immediately

    def _auto_save_and_apply(self):
        """Silently gathers all data, saves to YAML, and applies Theme/Font dynamically."""
        
        # 1. Determine active Theme
        theme_file = "dark_theme.qss" if self.btn_theme_dark.isChecked() else "white_theme.qss"
        
        # 2. Determine active Font Size (8, 10, 12, or 14)
        active_font_size = 10
        for btn, size in self.size_buttons.items():
            if btn.isChecked():
                active_font_size = size
                break
                
        # 3. Build Backend Dictionary
        new_settings = {
            "appearance": {
                "theme": theme_file,
                "font_family": self.cb_font.currentText(),
                "font_size": active_font_size,
                "ui_density": self.cb_density.currentText()
            },
            "output": {
                "default_path": self.le_path.text(),
                "create_date_folder": self.chk_date_folder.isChecked(),
                "open_after_processing": self.chk_open_after.isChecked(),
                "keep_organized": self.chk_keep_org.isChecked(),
                "default_export_format": self.cb_export_fmt.currentText()
            },
            "ocr": {
                "enable": self.chk_ocr_enable.isChecked(),
                "engine": self.cb_ocr_engine.currentText(),
                "dpi": self.cb_dpi.currentText(),
                "min_confidence": self.cb_conf.currentText(),
                "auto_enhance": self.chk_auto_enhance.isChecked()
            },
            "export": {
                "generate_pdf": self.chk_gen_pdf.isChecked(),
                "generate_excel": self.chk_gen_xl.isChecked(),
                "generate_summary": self.chk_gen_sum.isChecked(),
                "excel_template": self.cb_xl_temp.currentText(),
                "header_style": self.cb_xl_head.currentText()
            }
        }
        
        # 4. Write to YAML (Offline Persistence)
        AppConfig.save_user_settings(new_settings)

        # 5. Apply Settings to App instantly
        app = QApplication.instance()
        if app:
            app.setFont(QFont(self.cb_font.currentText(), active_font_size))
            qss_content = AppConfig.load_stylesheet(theme_file)
            app.setStyleSheet(qss_content)
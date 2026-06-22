from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QComboBox, QFileDialog, QLineEdit,
                               QFrame, QApplication, QGridLayout, QScrollArea, 
                               QCheckBox, QButtonGroup, QSizePolicy, QSpacerItem)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QSize

from config.ui_config import AppConfig

# --- SURGICALLY PRECISE QSS TO MATCH THE EXACT ENTERPRISE MOCKUP ---
PIXEL_PERFECT_QSS = """
/* Master Backgrounds */
QWidget { background-color: #0B0F19; color: #F8FAFC; font-family: 'Segoe UI', Arial, sans-serif; }
QScrollArea, QScrollArea > QWidget > QWidget { background-color: transparent; border: none; }

/* Custom Card Frames (Replaces QGroupBox for precise margin control) */
QFrame.Card { background-color: #111827; border: 1px solid #1E293B; border-radius: 12px; }

/* Typography */
QLabel.CardTitle { font-size: 16px; font-weight: 700; color: #F8FAFC; background: transparent; border: none; }
QLabel.RowTitle { font-size: 13px; font-weight: 500; color: #E2E8F0; background: transparent; border: none; }
QLabel.RowDesc { font-size: 11px; font-weight: 400; color: #64748B; background: transparent; border: none; }

/* Inputs & Dropdowns */
QLineEdit, QComboBox { background-color: #0B0F19; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; color: #F8FAFC; font-size: 12px; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #4F46E5; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background-color: #111827; color: #F8FAFC; selection-background-color: #4F46E5; border: 1px solid #334155; border-radius: 6px; outline: none; }

/* Standard Buttons */
QPushButton { background-color: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 8px 16px; font-size: 12px; font-weight: 600; color: #F8FAFC; }
QPushButton:hover { background-color: #334155; }
QPushButton.Primary { background-color: #4F46E5; color: white; border: none; }
QPushButton.Primary:hover { background-color: #4338CA; }

/* Selectable Visual Blocks (Theme & Font Size) */
QPushButton.VisualBlock { background-color: #0B0F19; border: 1px solid #334155; border-radius: 8px; color: #94A3B8; text-align: center; }
QPushButton.VisualBlock:hover { border: 1px solid #4F46E5; }
QPushButton.VisualBlock:checked { background-color: #1E1B4B; border: 2px solid #4F46E5; color: white; }

/* Standard Checkboxes */
QCheckBox { spacing: 10px; font-size: 13px; color: #E2E8F0; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #4F46E5; background-color: #0B0F19; }
QCheckBox::indicator:checked { background-color: #4F46E5; image: url(resources/icons/check.svg); }

/* Custom Pill Toggles */
QCheckBox.Toggle { spacing: 0px; background: transparent; }
QCheckBox.Toggle::indicator { width: 34px; height: 18px; border-radius: 9px; border: none; background-color: #334155; }
QCheckBox.Toggle::indicator:checked { background-color: #4F46E5; }
"""

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(PIXEL_PERFECT_QSS)
        
        # Load Last Saved Settings from YAML
        self.user_cfg = AppConfig.load_user_settings()
        self.appearance = self.user_cfg.get("appearance", {})
        self.output_cfg = self.user_cfg.get("output", {})
        self.ocr_cfg = self.user_cfg.get("ocr", {})
        self.process_cfg = self.user_cfg.get("processing", {})
        self.export_cfg = self.user_cfg.get("export", {})

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)

        # --- HEADER ROW (Title + Status Icons mock) ---
        header_row = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 26px; font-weight: 700; background: transparent;")
        subtitle = QLabel("Configure application preferences and system settings.")
        subtitle.setProperty("class", "RowDesc")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        
        header_row.addLayout(header_text)
        header_row.addStretch()
        main_layout.addLayout(header_row)
        main_layout.addSpacing(15)

        # --- CONTENT GRID ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.grid = QGridLayout(self.content_widget)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignTop)

        # Build The 5 Specific Cards matching the Image Grid
        self._build_appearance_card(0, 0, 1, 2) # Row 0, Col 0, spans 2 columns
        self._build_output_card(0, 2, 1, 1)     # Row 0, Col 2, spans 1 column
        self._build_ocr_card(1, 0, 1, 1)        # Row 1, Col 0
        self._build_processing_card(1, 1, 1, 1) # Row 1, Col 1
        self._build_export_card(1, 2, 1, 1)     # Row 1, Col 2

        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area, stretch=1)

        # --- BOTTOM ACTION BAR ---
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        btn_reset = QPushButton("↺ Reset to Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        
        btn_save = QPushButton("💾 Save Settings")
        btn_save.setProperty("class", "Primary")
        btn_save.clicked.connect(self._auto_save_and_apply) # For manual force save
        
        action_layout.addWidget(btn_reset)
        action_layout.addWidget(btn_save)
        main_layout.addLayout(action_layout)

    # =========================================================================
    # EXACT UI COMPONENT BUILDERS
    # =========================================================================
    def _create_card(self, title):
        frame = QFrame()
        frame.setProperty("class", "Card")
        lyt = QVBoxLayout(frame)
        lyt.setContentsMargins(20, 20, 20, 20)
        lyt.setSpacing(15)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "CardTitle")
        lyt.addWidget(lbl_title)
        lyt.addSpacing(5)
        return frame, lyt

    def _create_row(self, title, desc, control):
        row = QWidget()
        lyt = QHBoxLayout(row)
        lyt.setContentsMargins(0, 0, 0, 0)
        
        text_lyt = QVBoxLayout()
        text_lyt.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "RowTitle")
        lbl_d = QLabel(desc)
        lbl_d.setProperty("class", "RowDesc")
        text_lyt.addWidget(lbl_t)
        text_lyt.addWidget(lbl_d)
        
        lyt.addLayout(text_lyt)
        lyt.addStretch()
        
        if control:
            if isinstance(control, QComboBox): control.setFixedWidth(180)
            lyt.addWidget(control, alignment=Qt.AlignRight | Qt.AlignVCenter)
        return row

    def _create_toggle(self, title, desc, key, cfg_dict, default):
        chk = QCheckBox()
        chk.setProperty("class", "Toggle")
        chk.setChecked(cfg_dict.get(key, default))
        chk.toggled.connect(self._auto_save_and_apply)
        self.__dict__[f"chk_{key}"] = chk 
        return self._create_row(title, desc, chk)

    def _create_combo(self, title, desc, items, key, cfg_dict, default):
        cb = QComboBox()
        cb.addItems(items)
        cb.setCurrentText(cfg_dict.get(key, default))
        cb.currentIndexChanged.connect(self._auto_save_and_apply)
        self.__dict__[f"cb_{key}"] = cb
        return self._create_row(title, desc, cb)

    # =========================================================================
    # THE 5 CARDS
    # =========================================================================
    def _build_appearance_card(self, r, c, rSpan, cSpan):
        card, lyt = self._create_card("Appearance")

        # Theme Section (Dropdown + Visual Buttons)
        lyt.addWidget(self._create_combo("Theme", "Choose application theme", ["Dark", "Light"], "theme_dd", self.appearance, "Dark"))
        
        theme_lyt = QHBoxLayout()
        self.btn_theme_dark = QPushButton("Dark")
        self.btn_theme_light = QPushButton("Light")
        self.btn_theme_dark.setProperty("class", "VisualBlock")
        self.btn_theme_light.setProperty("class", "VisualBlock")
        self.btn_theme_dark.setFixedSize(140, 80)
        self.btn_theme_light.setFixedSize(140, 80)
        
        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.btn_theme_dark)
        self.theme_group.addButton(self.btn_theme_light)
        for btn in [self.btn_theme_dark, self.btn_theme_light]:
            btn.setCheckable(True)
            theme_lyt.addWidget(btn)
            
        if "light" in self.appearance.get("theme", "dark_theme.qss"): self.btn_theme_light.setChecked(True)
        else: self.btn_theme_dark.setChecked(True)
        self.theme_group.buttonClicked.connect(self._auto_save_and_apply)
        
        theme_lyt.addStretch()
        lyt.addLayout(theme_lyt)
        lyt.addSpacing(10)

        # Font Size Section (Dropdown + Visual Buttons)
        lyt.addWidget(self._create_combo("Font Size", "Adjust global font size", ["Small (10px)", "Medium (12px)", "Large (14px)", "Extra Large (16px)"], "size_dd", self.appearance, "Medium (12px)"))
        
        font_lyt = QHBoxLayout()
        self.size_group = QButtonGroup(self)
        sizes = [("Small\n10px", 10), ("Medium\n12px", 12), ("Large\n14px", 14), ("Extra Large\n16px", 16)]
        
        saved_size = int(self.appearance.get("font_size", 12))
        self.size_buttons = {}
        
        for label, pt in sizes:
            btn = QPushButton(f"Aa\n{label}")
            btn.setProperty("class", "VisualBlock")
            btn.setFixedSize(90, 60)
            btn.setCheckable(True)
            if pt == saved_size: btn.setChecked(True)
            self.size_group.addButton(btn)
            self.size_buttons[btn] = pt
            font_lyt.addWidget(btn)
            
        font_lyt.addStretch()
        self.size_group.buttonClicked.connect(self._auto_save_and_apply)
        lyt.addLayout(font_lyt)
        lyt.addSpacing(10)

        # Bottom Dropdowns
        lyt.addWidget(self._create_combo("Font Family", "Choose application font", ["Segoe UI", "Arial", "Roboto"], "font_family", self.appearance, "Segoe UI"))
        lyt.addWidget(self._create_combo("UI Density", "Adjust spacing between UI elements", ["Compact", "Comfortable", "Spacious"], "ui_density", self.appearance, "Comfortable"))
        
        lyt.addStretch()
        self.grid.addWidget(card, r, c, rSpan, cSpan)

    def _build_output_card(self, r, c, rSpan, cSpan):
        card, lyt = self._create_card("Output Settings")

        lbl = QLabel("Default Output Folder\nWhere all reports and files will be saved")
        lbl.setProperty("class", "RowDesc")
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
        lyt.addSpacing(10)

        self.chk_date = QCheckBox("Create date folder (21-05-2024)")
        self.chk_open = QCheckBox("Open output folder after processing")
        self.chk_keep = QCheckBox("Keep output files organized in subfolders")

        self.chk_date.setChecked(self.output_cfg.get("create_date_folder", True))
        self.chk_open.setChecked(self.output_cfg.get("open_after_processing", True))
        self.chk_keep.setChecked(self.output_cfg.get("keep_organized", True))

        for chk in [self.chk_date, self.chk_open, self.chk_keep]:
            chk.toggled.connect(self._auto_save_and_apply)
            lyt.addWidget(chk)
            
        lyt.addSpacing(20)
        lyt.addWidget(self._create_combo("Default Export Format", "Choose default export format", ["Both (Excel + PDF)", "Excel Only", "PDF Only"], "default_export_format", self.output_cfg, "Both (Excel + PDF)"))
        
        lyt.addStretch()
        self.grid.addWidget(card, r, c, rSpan, cSpan)

    def _build_ocr_card(self, r, c, rSpan, cSpan):
        card, lyt = self._create_card("OCR Settings (For Scanned PDFs)")
        lyt.addWidget(self._create_toggle("Enable OCR", "Enable OCR for scanned PDFs", "enable", self.ocr_cfg, True))
        lyt.addWidget(self._create_combo("OCR Engine", "Select OCR engine", ["EasyOCR (Recommended)", "Tesseract"], "engine", self.ocr_cfg, "EasyOCR (Recommended)"))
        lyt.addWidget(self._create_combo("Image DPI", "DPI for converting PDF pages to images", ["150 DPI", "300 DPI", "600 DPI"], "dpi", self.ocr_cfg, "300 DPI"))
        lyt.addWidget(self._create_combo("Minimum Confidence", "Minimum confidence to accept text", ["70%", "80%", "85%", "90%"], "min_confidence", self.ocr_cfg, "85%"))
        lyt.addWidget(self._create_toggle("Auto Enhance Image", "Automatically enhance image before OCR", "auto_enhance", self.ocr_cfg, True))
        lyt.addStretch()
        self.grid.addWidget(card, r, c, rSpan, cSpan)

    def _build_processing_card(self, r, c, rSpan, cSpan):
        card, lyt = self._create_card("Processing Settings")
        lyt.addWidget(self._create_toggle("Extract Specifications", "Extract all dimensions and parameters", "extract_specifications", self.process_cfg, True))
        lyt.addWidget(self._create_toggle("Extract Tolerances", "Extract all tolerances", "extract_tolerances", self.process_cfg, True))
        lyt.addWidget(self._create_toggle("Extract Metadata", "Extract drawing metadata", "extract_metadata", self.process_cfg, True))
        lyt.addWidget(self._create_toggle("Extract Notes", "Extract general and manufacturing notes", "extract_notes", self.process_cfg, True))
        lyt.addWidget(self._create_toggle("Auto-open Results", "Open results page after processing", "auto_open_results", self.process_cfg, True))
        lyt.addStretch()
        self.grid.addWidget(card, r, c, rSpan, cSpan)

    def _build_export_card(self, r, c, rSpan, cSpan):
        card, lyt = self._create_card("Export Settings")
        
        self.chk_pdf = QCheckBox("Generate Ballooned PDF\nCreate ballooned drawing PDF")
        self.chk_xl = QCheckBox("Generate Excel Inspection Sheet\nCreate inspection Excel sheet")
        self.chk_sum = QCheckBox("Generate Summary Report\nCreate summary report (PDF)")

        self.chk_pdf.setChecked(self.export_cfg.get("generate_pdf", True))
        self.chk_xl.setChecked(self.export_cfg.get("generate_excel", True))
        self.chk_sum.setChecked(self.export_cfg.get("generate_summary", True))

        for chk in [self.chk_pdf, self.chk_xl, self.chk_sum]:
            chk.toggled.connect(self._auto_save_and_apply)
            lyt.addWidget(chk)
            lyt.addSpacing(5)

        lyt.addWidget(self._create_combo("Excel Template", "Choose inspection sheet template", ["Default Template", "Custom Template 1"], "excel_template", self.export_cfg, "Default Template"))
        lyt.addWidget(self._create_combo("Excel Header Style", "Choose header style", ["Style 1", "Style 2"], "header_style", self.export_cfg, "Style 1"))
        
        lyt.addStretch()
        self.grid.addWidget(card, r, c, rSpan, cSpan)

    # =========================================================================
    # BACKEND DATA SYNC
    # =========================================================================
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination", self.le_path.text())
        if folder: 
            self.le_path.setText(folder)
            self._auto_save_and_apply()

    def _reset_defaults(self):
        self.cb_theme_dd.setCurrentText("Dark")
        self.btn_theme_dark.setChecked(True)
        self.cb_size_dd.setCurrentText("Medium (12px)")
        for btn, size in self.size_buttons.items():
            if size == 12: btn.setChecked(True)
        self.cb_font_family.setCurrentText("Segoe UI")
        self._auto_save_and_apply()

    def _auto_save_and_apply(self):
        if not hasattr(self, 'size_buttons'): return
        
        # Resolve active Font Size from Visual Blocks
        active_font_size = 12
        for btn, size in self.size_buttons.items():
            if btn.isChecked():
                active_font_size = size
                break
                
        # Sync Dropdown visually with the Block
        size_map = {10: "Small (10px)", 12: "Medium (12px)", 14: "Large (14px)", 16: "Extra Large (16px)"}
        self.cb_size_dd.blockSignals(True)
        self.cb_size_dd.setCurrentText(size_map.get(active_font_size, "Medium (12px)"))
        self.cb_size_dd.blockSignals(False)
        
        # Build strict payload
        new_settings = {
            "appearance": {
                "theme": "dark_theme.qss" if self.btn_theme_dark.isChecked() else "white_theme.qss",
                "font_family": self.cb_font_family.currentText(),
                "font_size": active_font_size,
                "ui_density": self.cb_ui_density.currentText()
            },
            "output": {
                "default_path": self.le_path.text(),
                "create_date_folder": self.chk_date.isChecked(),
                "open_after_processing": self.chk_open.isChecked(),
                "keep_organized": self.chk_keep.isChecked(),
                "default_export_format": self.cb_default_export_format.currentText()
            },
            "ocr": {
                "enable": getattr(self, 'chk_enable', QCheckBox()).isChecked(),
                "engine": getattr(self, 'cb_engine', QComboBox()).currentText(),
                "dpi": getattr(self, 'cb_dpi', QComboBox()).currentText(),
                "min_confidence": getattr(self, 'cb_min_confidence', QComboBox()).currentText(),
                "auto_enhance": getattr(self, 'chk_auto_enhance', QCheckBox()).isChecked()
            },
            "processing": {
                "extract_specifications": getattr(self, 'chk_extract_specifications', QCheckBox()).isChecked(),
                "extract_tolerances": getattr(self, 'chk_extract_tolerances', QCheckBox()).isChecked(),
                "extract_metadata": getattr(self, 'chk_extract_metadata', QCheckBox()).isChecked(),
                "extract_notes": getattr(self, 'chk_extract_notes', QCheckBox()).isChecked(),
                "auto_open_results": getattr(self, 'chk_auto_open_results', QCheckBox()).isChecked()
            },
            "export": {
                "generate_pdf": self.chk_pdf.isChecked(),
                "generate_excel": self.chk_xl.isChecked(),
                "generate_summary": self.chk_sum.isChecked(),
                "excel_template": getattr(self, 'cb_excel_template', QComboBox()).currentText(),
                "header_style": getattr(self, 'cb_header_style', QComboBox()).currentText()
            }
        }
        
        # Save to File System
        AppConfig.save_user_settings(new_settings)

        # Apply Global Font Live
        app = QApplication.instance()
        if app:
            app.setFont(QFont(new_settings["appearance"]["font_family"], active_font_size))
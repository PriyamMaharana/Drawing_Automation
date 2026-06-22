import sys
import logging
import shutil
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
try: 
    from core.utils.logger import setup_3_tier_logging
    setup_3_tier_logging("manual_extraction", project_root)
except ImportError as e:
    print(f"Logger import failure: {e}")

import fitz
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                               QGraphicsScene, QGraphicsRectItem, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QWidget, QFileDialog, 
                               QLabel, QComboBox, QMessageBox, QMenu)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter, QFont, QAction
from PySide6.QtCore import Qt, QRectF, QTimer

try: 
    from core.utils.settings import PlatformSettings
    from infrastructure.pdf.document_scout import DocumentScout
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")

class GreenZoneCanvas(QGraphicsView):
    def __init__(self, scene, main_window):
        super().__init__(scene)
        self.main_window = main_window 
        self.setDragMode(QGraphicsView.NoDrag) 
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.rect_items = [] 
        self.active_rect_item = None
        self.start_point = None
        self.drawing_mode = False
        self.current_view_scale = 1.0
        self.zoom_timer = QTimer()
        self.zoom_timer.setSingleShot(True)
        self.zoom_timer.timeout.connect(self.trigger_high_res_render)

    def wheelEvent(self, event):
        # ---------------------------------------------------------
        # SCROLL TO ZOOM LOGIC (No SHIFT required in Preview Mode!)
        # ---------------------------------------------------------
        is_preview = getattr(self.main_window, 'is_preview_mode', False)
        
        if event.modifiers() == Qt.ShiftModifier or is_preview:
            zoom_in = 1.15
            zoom_out = 1.0 / zoom_in
            old_pos = self.mapToScene(event.position().toPoint())
            if event.angleDelta().y() > 0:
                self.scale(zoom_in, zoom_in)
                self.current_view_scale *= zoom_in
            else:
                self.scale(zoom_out, zoom_out)
                self.current_view_scale *= zoom_out
            delta = self.mapToScene(event.position().toPoint()) - old_pos
            self.translate(delta.x(), delta.y())
            self.zoom_timer.start(300) 
        else:
            super().wheelEvent(event)

    def trigger_high_res_render(self):
        self.main_window.re_render_hd_pdf(self.current_view_scale)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            is_preview = getattr(self.main_window, 'is_preview_mode', False)
            
            # In preview mode, default click becomes Pan (ScrollHandDrag)
            if event.modifiers() == Qt.ShiftModifier or is_preview:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                super().mousePressEvent(event)
            else:
                self.setDragMode(QGraphicsView.NoDrag)
                self.drawing_mode = True
                self.start_point = self.mapToScene(event.position().toPoint())
                self.active_rect_item = QGraphicsRectItem()
                pen = QPen(QColor(0, 200, 0)) 
                pen.setWidth(4) 
                pen.setCosmetic(True) 
                self.active_rect_item.setPen(pen)
                self.scene().addItem(self.active_rect_item)
                self.rect_items.append(self.active_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        try:
            if self.drawing_mode and self.start_point and self.active_rect_item:
                rect = QRectF(self.start_point, self.mapToScene(event.position().toPoint())).normalized()
                self.active_rect_item.setRect(rect)
            else:
                super().mouseMoveEvent(event)
        except RuntimeError:
            self.drawing_mode = False
            self.active_rect_item = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing_mode: self.drawing_mode, self.start_point = False, None
            else:
                super().mouseReleaseEvent(event)
                self.setDragMode(QGraphicsView.NoDrag)
        else:
            super().mouseReleaseEvent(event)

    def clear_all_zones(self):
        for item in self.rect_items:
            try: self.scene().removeItem(item)
            except RuntimeError: pass
        self.rect_items.clear()

    def get_selected_zones(self):
        zones = []
        for item in self.rect_items:
            try:
                rect = item.rect()
                if rect.width() > 10 and rect.height() > 10:
                    zones.append([int(rect.left()), int(rect.top()), int(rect.right()), int(rect.bottom())])
            except RuntimeError: continue
        return zones

# --- THE MAIN WINDOW UPGRADE ---
class CADIntelligenceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Intelligence Platform - Manual Extraction")
        self.setGeometry(100, 100, 1400, 900)

        # UI Mode Tracking
        self.is_preview_mode = False

        self.setStyleSheet("""
            QMainWindow { background-color: #FFFFFF; }
            QWidget { color: #212529; font-family: 'Segoe UI', Arial, sans-serif; }
            QPushButton { background-color: #F8F9FA; border: 1px solid #CED4DA; border-radius: 6px; padding: 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #E2E6EA; border: 1px solid #ADB5BD; }
            QGraphicsView { background-color: #F1F3F5; border: 2px solid #DEE2E6; border-radius: 6px; }
            
            /* White Theme Page Selector */
            QComboBox { 
                border: 1px solid #CED4DA; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 14px; 
                background-color: #FFFFFF; 
                color: #212529; 
            }
            QComboBox QAbstractItemView { 
                background-color: #FFFFFF; 
                color: #212529; 
                selection-background-color: #007BFF; 
                selection-color: white; 
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.primary_tools = QWidget()
        primary_layout = QHBoxLayout(self.primary_tools)
        primary_layout.setContentsMargins(0,0,0,0)

        self.btn_load = QPushButton("1. Load Engineering PDF")
        self.btn_load.clicked.connect(self.load_pdf)
        self.page_selector = QComboBox()
        self.page_selector.currentIndexChanged.connect(self.change_page)
        self.page_selector.hide() 
        
        # Red Clear Zones Button
        self.btn_clear = QPushButton("🗑️ Clear Zones")
        self.btn_clear.setStyleSheet("""
            QPushButton { background-color: #DC3545; color: white; border: none; }
            QPushButton:hover { background-color: #C82333; }
        """)
        self.btn_clear.clicked.connect(lambda: self.canvas.clear_all_zones())
        
        primary_layout.addWidget(self.btn_load, stretch=3)
        primary_layout.addWidget(self.page_selector, stretch=1)
        primary_layout.addWidget(self.btn_clear, stretch=1)
        layout.addWidget(self.primary_tools)

        self.btn_extract = QPushButton("2. Extract Selected Green Zones")
        self.btn_extract.setStyleSheet("background-color: #28A745; color: white; border: none;")
        self.btn_extract.clicked.connect(self.trigger_extraction)
        self.btn_extract.setEnabled(False)
        layout.addWidget(self.btn_extract)

        # --- PREVIEW AND EXPORT CONTROLS ---
        self.export_tools = QWidget()
        export_layout = QHBoxLayout(self.export_tools)
        export_layout.setContentsMargins(0,0,0,0)
        
        lbl_preview = QLabel("🔍 PREVIEW MODE: Scroll to Zoom. Left-Click to Pan.")
        lbl_preview.setStyleSheet("font-size: 15px; color: #D35400; font-weight: bold;")
        
        # Format Dropdown Menu
        self.btn_approve = QPushButton("💾 Export Report ▾")
        self.btn_approve.setStyleSheet("""
            QPushButton { background-color: #007BFF; color: white; border: none; }
            QPushButton:hover { background-color: #0069D9; }
            QPushButton::menu-indicator { image: none; width: 0px; }
        """)
        
        self.export_menu = QMenu(self)
        self.export_menu.setStyleSheet("""
            QMenu { background-color: #FFFFFF; border: 1px solid #CED4DA; border-radius: 4px; }
            QMenu::item { padding: 8px 24px; color: #212529; font-size: 14px; font-weight: bold; }
            QMenu::item:selected { background-color: #007BFF; color: white; }
        """)
        
        action_pdf = QAction("📄 Export as PDF", self)
        action_pdf.triggered.connect(lambda: self.export_drawing(".pdf"))
        action_jpg = QAction("🖼️ Export as JPEG", self)
        action_jpg.triggered.connect(lambda: self.export_drawing(".jpeg"))
        action_png = QAction("🖼️ Export as PNG", self)
        action_png.triggered.connect(lambda: self.export_drawing(".png"))
        
        self.export_menu.addAction(action_pdf)
        self.export_menu.addAction(action_jpg)
        self.export_menu.addAction(action_png)
        self.btn_approve.setMenu(self.export_menu)

        self.btn_discard = QPushButton("❌ Discard & Adjust Zones")
        self.btn_discard.setStyleSheet("""
            QPushButton { background-color: #DC3545; color: white; border: none; }
            QPushButton:hover { background-color: #C82333; }
        """)
        self.btn_discard.clicked.connect(self.discard_preview)

        export_layout.addWidget(lbl_preview, stretch=2)
        export_layout.addWidget(self.btn_approve, stretch=1)
        export_layout.addWidget(self.btn_discard, stretch=1)
        self.export_tools.hide()
        layout.addWidget(self.export_tools)

        self.scene = QGraphicsScene()
        self.canvas = GreenZoneCanvas(self.scene, self)
        layout.addWidget(self.canvas)

        self.original_pdf_path = None
        self.preview_pdf_path = None
        self.current_pdf_path = None
        self.current_page_idx = 0 
        self.scout_engine = DocumentScout()
        self.pdf_pixmap_item = None
        self.base_dpi = PlatformSettings.UI_RENDER_DPI

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Drawing", "", "PDF Files (*.pdf)")
        if file_path:
            self.original_pdf_path = file_path
            drawing_package = self.scout_engine.analyze_document(Path(file_path))
            drawing_pages = drawing_package.drawing_pages
            self.is_preview_mode = False
            
            self.page_selector.blockSignals(True)
            self.page_selector.clear()
            
            if not drawing_pages:
                self.current_page_idx = 0
                self.page_selector.addItem("Page 1 (Fallback)", userData=0)
            else:
                for p_num in drawing_pages:
                    self.page_selector.addItem(f"Page {p_num} (Drawing)", userData=p_num - 1)
                self.current_page_idx = (drawing_package.primary_page - 1) if drawing_package.primary_page else (drawing_pages[0] - 1)
                self.page_selector.setCurrentText(f"Page {self.current_page_idx + 1} (Drawing)")
            
            if fitz.open(file_path).page_count > 1: self.page_selector.show()
            else: self.page_selector.hide()
                
            self.page_selector.blockSignals(False)
            self.render_pdf_to_canvas(file_path, self.current_page_idx)
            self.btn_extract.setEnabled(True)

    def change_page(self, index):
        if index >= 0:
            self.current_page_idx = self.page_selector.currentData()
            self.render_pdf_to_canvas(self.current_pdf_path, self.current_page_idx)

    def render_pdf_to_canvas(self, path, page_idx):
        self.current_pdf_path = path
        self.current_page_idx = page_idx
        self.pdf_pixmap_item = None 
        self.canvas.resetTransform()
        self.canvas.current_view_scale = 1.0
        self.scene.clear()
        
        if path == self.original_pdf_path:
            self.canvas.rect_items.clear()
            
        self.canvas.active_rect_item, self.canvas.drawing_mode = None, False
        self.re_render_hd_pdf(1.0)
        self.canvas.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def re_render_hd_pdf(self, zoom_scale):
        if not self.current_pdf_path: return
        doc = fitz.open(self.current_pdf_path)
        page = doc[self.current_page_idx]
        target_dpi = max(min(int(self.base_dpi * zoom_scale), 800), self.base_dpi)

        pix = page.get_pixmap(dpi=target_dpi, colorspace=fitz.csRGB, alpha=False)
        img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
        new_pixmap = QPixmap.fromImage(img)

        if self.pdf_pixmap_item is None: self.pdf_pixmap_item = self.scene.addPixmap(new_pixmap)
        else: self.pdf_pixmap_item.setPixmap(new_pixmap)

        self.pdf_pixmap_item.setScale(self.base_dpi / target_dpi)
        doc.close()

    def trigger_extraction(self):
        zones = self.canvas.get_selected_zones()
        if not zones: return QMessageBox.warning(self, "No Zones", "Please draw at least one green zone first!")
            
        try:
            from pipeline.manual_extraction_pipeline import ManualExtractionPipeline
            pipeline = ManualExtractionPipeline(project_root)
            result, preview_path = pipeline.execute(Path(self.current_pdf_path), self.current_page_idx + 1, zones)
            
            self.preview_pdf_path = preview_path
            self.is_preview_mode = True

            # Swap UI Mode
            self.primary_tools.hide()
            self.btn_extract.hide()
            self.export_tools.show()

            # Render Balloon Preview
            self.render_pdf_to_canvas(str(self.preview_pdf_path), self.current_page_idx)
            
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))

    def discard_preview(self):
        self.is_preview_mode = False
        self.export_tools.hide()
        self.primary_tools.show()
        self.btn_extract.show()
        self.render_pdf_to_canvas(self.original_pdf_path, self.current_page_idx)

    def export_drawing(self, ext):
        default_name = f"{Path(self.original_pdf_path).stem}_BALLOONED{ext}"
        
        filter_str = ""
        if ext == ".pdf": filter_str = "PDF Document (*.pdf)"
        elif ext == ".jpeg": filter_str = "JPEG Image (*.jpeg)"
        elif ext == ".png": filter_str = "PNG Image (*.png)"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Ballooned Drawing", default_name, filter_str)

        if file_path:
            try:
                if file_path.endswith(".pdf"):
                    shutil.copy(self.preview_pdf_path, file_path)
                else:
                    doc = fitz.open(self.preview_pdf_path)
                    page = doc[self.current_page_idx]
                    pix = page.get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
                    if file_path.endswith(".jpeg") or file_path.endswith(".jpg"):
                        pix.save(file_path, "jpeg")
                    else:
                        pix.save(file_path, "png")
                    doc.close()

                QMessageBox.information(self, "Export Successful", f"File saved successfully to:\n{file_path}")
                self.discard_preview() 
                
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Could not save file: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    hardware_dpi = int(screen.logicalDotsPerInch())
    optimal_dpi = max(hardware_dpi, 144) 
    
    try:
        PlatformSettings.UI_RENDER_DPI = optimal_dpi
    except ImportError: pass
        
    app.setFont(QFont("Segoe UI", 10))
    window = CADIntelligenceApp()
    window.show()
    sys.exit(app.exec())
    
    
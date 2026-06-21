import sys
import logging
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
try: 
    from core.utils.logger import setup_3_tier_logging
    setup_3_tier_logging("manual_extraction", project_root)
except ImportError as e:
    print(f"Logger import failure: {e}")
    sys.exit(1)

import fitz
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                               QGraphicsScene, QGraphicsRectItem, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QWidget, QFileDialog, 
                               QLabel, QComboBox, QMessageBox)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter, QFont
from PySide6.QtCore import Qt, QRectF, QTimer

try: 
    from core.utils.settings import PlatformSettings
    from infrastructure.pdf.document_scout import DocumentScout
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

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
        if event.modifiers() == Qt.ShiftModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1.0 / zoom_in_factor
            old_pos = self.mapToScene(event.position().toPoint())
            
            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
                self.current_view_scale *= zoom_in_factor
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
                self.current_view_scale *= zoom_out_factor
                
            new_pos = self.mapToScene(event.position().toPoint())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
            self.zoom_timer.start(250)
        else:
            super().wheelEvent(event)
            
    def trigger_high_res_render(self):
        self.main_window.re_render_hd_pdf(self.current_view_scale)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.modifiers() == Qt.ShiftModifier:
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
                end_point = self.mapToScene(event.position().toPoint())
                rect = QRectF(self.start_point, end_point).normalized()
                self.active_rect_item.setRect(rect)
            else:
                super().mouseMoveEvent(event)
        except RuntimeError:
            self.drawing_mode = False
            self.active_rect_item = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing_mode:
                self.drawing_mode = False
                self.start_point = None
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

class CADIntelligenceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Intelligence Platform - Manual Extraction")
        self.setGeometry(100, 100, 1400, 900)

        # UI Styling (White Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #FFFFFF; }
            QWidget { color: #212529; font-family: 'Segoe UI', Arial, sans-serif; }
            QPushButton { background-color: #F8F9FA; border: 1px solid #CED4DA; border-radius: 6px; padding: 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #E2E6EA; border: 1px solid #ADB5BD; }
            QPushButton:disabled { background-color: #F1F3F5; color: #ADB5BD; border: 1px solid #DEE2E6; }
            QGraphicsView { background-color: #F1F3F5; border: 2px solid #DEE2E6; border-radius: 6px; }
            QComboBox { border: 1px solid #CED4DA; border-radius: 6px; padding: 8px; background-color: #FFFFFF; font-size: 14px; font-weight: bold; }
        """)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)        
        self.setCentralWidget(layout.parent())

        self.instruction_label = QLabel(
            "<b>Controls:</b> &nbsp;&nbsp;&nbsp; "
            "🟩 <b>Draw Zones:</b> Left Click & Drag (Draw as many as needed) &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; "
            "🖐️ <b>Pan Document:</b> Hold [SHIFT] + Left Click & Drag &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; "
            "🔍 <b>Zoom:</b> Hold [SHIFT] + Mouse Scroll Wheel"
        )
        self.instruction_label.setFont(QFont("Segoe UI", 10))
        self.instruction_label.setStyleSheet("padding: 12px; background-color: #F8F9FA; border: 1px solid #DEE2E6; border-radius: 6px; color: #495057;")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.instruction_label)

        top_controls = QHBoxLayout()
        self.btn_load = QPushButton("Load  PDF")
        self.btn_load.setMinimumHeight(45)
        self.btn_load.clicked.connect(self.load_pdf)
        top_controls.addWidget(self.btn_load, stretch=3)
        
        self.page_selector = QComboBox()
        self.page_selector.setMinimumHeight(45)
        self.page_selector.currentIndexChanged.connect(self.change_page)
        self.page_selector.hide() 
        top_controls.addWidget(self.page_selector, stretch=1)
        
        self.btn_clear = QPushButton("🗑️ Clear Zones")
        self.btn_clear.setMinimumHeight(45)
        self.btn_clear.setStyleSheet("QPushButton { background-color: #DC3545; color: white; border: none; } QPushButton:hover { background-color: #C82333; }")
        self.btn_clear.clicked.connect(lambda: self.canvas.clear_all_zones())
        top_controls.addWidget(self.btn_clear, stretch=1)
        layout.addLayout(top_controls)

        self.btn_extract = QPushButton("Extract Selected Green Zones")
        self.btn_extract.setMinimumHeight(45)
        self.btn_extract.setStyleSheet("""
            QPushButton { background-color: #28A745; color: white; border: none; }
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #A5D8AD; color: #F8F9FA; }
        """)
        self.btn_extract.clicked.connect(self.trigger_extraction)
        self.btn_extract.setEnabled(False)
        layout.addWidget(self.btn_extract)

        self.scene = QGraphicsScene()
        self.canvas = GreenZoneCanvas(self.scene, self)
        layout.addWidget(self.canvas)

        self.current_pdf_path = None
        self.current_page_idx = 0 
        self.scout_engine = DocumentScout()
        
        self.pdf_pixmap_item = None
        self.base_dpi = PlatformSettings.UI_RENDER_DPI

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Drawing", "", "PDF Files (*.pdf)")
        if file_path:
            self.current_pdf_path = file_path
            print(f"Pre-Flight Analysis on {Path(file_path).name}...")
            drawing_package = self.scout_engine.analyze_document(Path(file_path))
            drawing_pages = drawing_package.drawing_pages
            
            self.page_selector.blockSignals(True)
            self.page_selector.clear()
            
            if not drawing_pages:
                self.current_page_idx = 0
                self.page_selector.addItem("Page 1 (Fallback)", userData=0)
            else:
                for p_num in drawing_pages:
                    self.page_selector.addItem(f"Page {p_num} (Drawing)", userData=p_num - 1)
                primary_idx = drawing_package.primary_page - 1 if drawing_package.primary_page else drawing_pages[0] - 1
                self.current_page_idx = primary_idx
                self.page_selector.setCurrentText(f"Page {primary_idx + 1} (Drawing)")
            
            if fitz.open(file_path).page_count > 1: 
                self.page_selector.show()
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
        self.canvas.rect_items.clear()
        self.canvas.active_rect_item, self.canvas.drawing_mode = None, False

        self.re_render_hd_pdf(1.0)
        self.canvas.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def re_render_hd_pdf(self, zoom_scale):
        if not self.current_pdf_path: return

        doc = fitz.open(self.current_pdf_path)
        page = doc[self.current_page_idx]
        
        target_dpi = min(int(self.base_dpi * zoom_scale), 800)
        
        target_dpi = max(target_dpi, self.base_dpi)

        pix = page.get_pixmap(dpi=target_dpi, colorspace=fitz.csRGB, alpha=False)
        img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
        new_pixmap = QPixmap.fromImage(img)

        if self.pdf_pixmap_item is None:
            self.pdf_pixmap_item = self.scene.addPixmap(new_pixmap)
        else:
            self.pdf_pixmap_item.setPixmap(new_pixmap)

        self.pdf_pixmap_item.setScale(self.base_dpi / target_dpi)
        doc.close()

    def trigger_extraction(self):
        zones = self.canvas.get_selected_zones()
        if not zones:
            return QMessageBox.warning(self, "No Zones", "Please draw at least one green zone first!")
            
        print(f"Extracting {len(zones)} Zones from Page {self.current_page_idx + 1}")
        
        try:
            from pipeline.manual_extraction_pipeline import ManualExtractionPipeline
            pipeline = ManualExtractionPipeline(project_root)
            result = pipeline.execute(Path(self.current_pdf_path), self.current_page_idx + 1, zones)            
            total_dims = sum(len(view.get("dimensions", [])) for view in result)
            QMessageBox.information(self, "Success", f"Extracted {total_dims} dimensions across {len(zones)} zones!\nCheck debug/results/manual_extract/")   
        except Exception as e:
            print(f"❌ Execution Error: {e}")
            QMessageBox.critical(self, "Extraction Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    screen = app.primaryScreen()
    hardware_dpi = int(screen.logicalDotsPerInch())
    optimal_dpi = max(hardware_dpi, 144)
    
    try:
        from core.utils.settings import PlatformSettings
        PlatformSettings.UI_RENDER_DPI = optimal_dpi
        logging.info(f"🖥️ Monitor Calibrated: Rendering UI at {optimal_dpi} DPI")
    except ImportError:
        pass

    app.setFont(QFont("Segoe UI", 10))
    window = CADIntelligenceApp()
    window.show()
    sys.exit(app.exec())
    
    
import sys
import fitz
import shutil
import os
import logging
from pathlib import Path

try:
    from config.icon_library import Ico, IconLibrary
except ImportError as e:
    logging.error(f"Microservices import failure: {e}")
    raise

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                               QLabel, QComboBox, QMessageBox, QMenu, QApplication)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter, QAction
from PySide6.QtCore import Qt, QRectF, QTimer, QSize

class GreenZoneCanvas(QGraphicsView):
    def __init__(self, scene, parent_page):
        super().__init__(scene)
        logger.debug("Initializing GreenZoneCanvas...")
        self.parent_page = parent_page 
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
        logger.debug("GreenZoneCanvas initialization complete.")

    def explicit_zoom(self, factor):
        logger.debug(f"Explicit zoom triggered. Factor: {factor}")
        self.scale(factor, factor)
        self.current_view_scale *= factor
        self.zoom_timer.start(300) 

    def explicit_pan(self, dx, dy):
        logger.debug(f"Explicit pan triggered. DX: {dx}, DY: {dy}")
        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()
        h_bar.setValue(h_bar.value() + dx)
        v_bar.setValue(v_bar.value() + dy)

    def wheelEvent(self, event):
        is_preview = getattr(self.parent_page, 'is_preview_mode', False)
        if event.modifiers() == Qt.ShiftModifier or is_preview:
            zoom_in = 1.15
            zoom_out = 1.0 / zoom_in
            old_pos = self.mapToScene(event.position().toPoint())
            if event.angleDelta().y() > 0:
                self.scale(zoom_in, zoom_in)
                self.current_view_scale *= zoom_in
                logger.debug(f"Mouse wheel zoomed IN. Current scale: {self.current_view_scale}")
            else:
                self.scale(zoom_out, zoom_out)
                self.current_view_scale *= zoom_out
                logger.debug(f"Mouse wheel zoomed OUT. Current scale: {self.current_view_scale}")
            delta = self.mapToScene(event.position().toPoint()) - old_pos
            self.translate(delta.x(), delta.y())
            self.zoom_timer.start(300) 
            event.accept() # Prevent default vertical scrolling
        else:
            super().wheelEvent(event)

    def trigger_high_res_render(self):
        logger.debug("Zoom timer finished. Triggering high-res PyMuPDF render.")
        self.parent_page.re_render_hd_pdf(self.current_view_scale)

    def mousePressEvent(self, event):
        is_preview = getattr(self.parent_page, 'is_preview_mode', False)
        if event.button() == Qt.LeftButton:
            if event.modifiers() == Qt.ShiftModifier or is_preview:
                logger.debug("Mouse pressed: Initiating Hand Drag mode.")
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                super().mousePressEvent(event)
            else:
                logger.debug("Mouse pressed: Initiating Green Zone drawing mode.")
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
            logger.error(f"Runtime error during mouse move (Drawing Mode): {e}")
            self.drawing_mode = False
            self.active_rect_item = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing_mode: 
                logger.debug("Mouse released: Green Zone drawn.")
                self.drawing_mode, self.start_point = False, None
            else:
                super().mouseReleaseEvent(event)
                is_preview = getattr(self.parent_page, 'is_preview_mode', False)
                if not is_preview:
                    self.setDragMode(QGraphicsView.NoDrag)
        else:
            super().mouseReleaseEvent(event)

    def clear_all_zones(self):
        logger.info(f"Clearing {len(self.rect_items)} Green Zones from canvas.")
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
            except RuntimeError: 
                logger.error(f"Failed to read a rectangle item: {e}")
                continue
        logger.info(f"Captured {len(zones)} valid Green Zones for extraction.")
        return zones

class ExtractionPage(QWidget):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ExtractionPage UI Module...")
        self.is_preview_mode = False
        layout = QVBoxLayout(self)

        # Primary Tools
        self.primary_tools = QWidget()
        primary_layout = QHBoxLayout(self.primary_tools)
        primary_layout.setContentsMargins(0,0,0,0)

        self.btn_load = QPushButton(" Load Engineering PDF")
        self.btn_load.setIcon(IconLibrary.get(Ico.FOLDER))
        self.btn_load.clicked.connect(self.load_pdf)
        
        self.page_selector = QComboBox()
        self.page_selector.currentIndexChanged.connect(self.change_page)
        self.page_selector.hide() 
        
        self.btn_clear = QPushButton(" Clear Zones")
        self.btn_clear.setIcon(IconLibrary.get(Ico.CLEAR))
        self.btn_clear.setStyleSheet("QPushButton { background-color: #DC3545; color: white; border: none; } QPushButton:hover { background-color: #C82333; }")
        self.btn_clear.clicked.connect(lambda: self.canvas.clear_all_zones())
        
        primary_layout.addWidget(self.btn_load, stretch=3)
        primary_layout.addWidget(self.page_selector, stretch=1)
        primary_layout.addWidget(self.btn_clear, stretch=1)
        layout.addWidget(self.primary_tools)

        self.btn_extract = QPushButton(" Extract Selected Green Zones")
        self.btn_extract.setStyleSheet("background-color: #28A745; color: white; border: none;")
        self.btn_extract.clicked.connect(self.trigger_extraction)
        self.btn_extract.setEnabled(False)
        layout.addWidget(self.btn_extract)

        # Preview Tools
        self.export_tools = QWidget()
        export_layout = QVBoxLayout(self.export_tools)
        export_layout.setContentsMargins(0,0,0,0)
        
        nav_row = QWidget()
        nav_layout = QHBoxLayout(nav_row)
        nav_layout.setContentsMargins(0,0,0,0)
        
        lbl_preview = QLabel("🔍 PREVIEW MODE:")
        lbl_preview.setStyleSheet("font-size: 15px; color: #D35400; font-weight: bold;")
        nav_layout.addWidget(lbl_preview, stretch=1)
        
        nav_btn_style = "QPushButton { background-color: #E9ECEF; color: #212529; border: 1px solid #CED4DA; border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 13px;} QPushButton:hover { background-color: #DEE2E6; }"
        self.btn_z_in = QPushButton("➕ Zoom In")
        # self.btn_z_in.setIcon(IconLibrary.get(Ico.PLUS))
        self.btn_z_out = QPushButton("➖ Zoom Out")
        self.btn_up = QPushButton("⬆️ Up")
        self.btn_down = QPushButton("⬇️ Down")
        self.btn_left = QPushButton("⬅️ Left")
        self.btn_right = QPushButton("➡️ Right")

        for btn in [self.btn_z_in, self.btn_z_out, self.btn_up, self.btn_down, self.btn_left, self.btn_right]:
            btn.setStyleSheet(nav_btn_style)
            nav_layout.addWidget(btn)

        self.btn_z_in.clicked.connect(lambda: self.canvas.explicit_zoom(1.15))
        self.btn_z_out.clicked.connect(lambda: self.canvas.explicit_zoom(1/1.15))
        self.btn_up.clicked.connect(lambda: self.canvas.explicit_pan(0, -150))
        self.btn_down.clicked.connect(lambda: self.canvas.explicit_pan(0, 150))
        self.btn_left.clicked.connect(lambda: self.canvas.explicit_pan(-150, 0))
        self.btn_right.clicked.connect(lambda: self.canvas.explicit_pan(150, 0))

        action_row = QWidget()
        action_layout = QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 10, 0, 0)
        
        self.btn_approve = QPushButton(" Export Report ▾")
        self.btn_approve.setIcon(IconLibrary.get(Ico.CIRCLE_CHECK_BIG))
        self.btn_approve.setStyleSheet("QPushButton { background-color: #007BFF; color: white; border: none; } QPushButton:hover { background-color: #0069D9; } QPushButton::menu-indicator { image: none; width: 0px; }")
        
        self.export_menu = QMenu(self)
        self.export_menu.setStyleSheet("QMenu { background-color: #FFFFFF; border: 1px solid #CED4DA; border-radius: 4px; } QMenu::item { padding: 8px 24px; color: #212529; font-size: 14px; font-weight: bold; } QMenu::item:selected { background-color: #007BFF; color: white; }")
        
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

        self.btn_discard = QPushButton(" Discard & Adjust Zones")
        self.btn_discard.setIcon(IconLibrary.get(Ico.CLOSE))
        self.btn_discard.setStyleSheet("QPushButton { background-color: #DC3545; color: white; border: none; } QPushButton:hover { background-color: #C82333; }")
        self.btn_discard.clicked.connect(self.discard_preview)

        action_layout.addWidget(self.btn_approve, stretch=1)
        action_layout.addWidget(self.btn_discard, stretch=1)

        export_layout.addWidget(nav_row)
        export_layout.addWidget(action_row)
        self.export_tools.hide()
        layout.addWidget(self.export_tools)

        self.scene = QGraphicsScene()
        self.canvas = GreenZoneCanvas(self.scene, self)
        layout.addWidget(self.canvas)

        self.original_pdf_path = None
        self.preview_pdf_path = None
        self.current_pdf_path = None
        self.current_page_idx = 0 
        self.pdf_pixmap_item = None
        self.base_dpi = 144
        logger.info("ExtractionPage UI Module completely loaded.")

    def load_pdf(self):
        logger.info("User requested to load a PDF drawing.")
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Drawing", "", "PDF Files (*.pdf)")
        if file_path:
            self.original_pdf_path = file_path
            self.is_preview_mode = False
            self.page_selector.blockSignals(True)
            self.page_selector.clear()
            
            try:
                doc = fitz.open(file_path)
                logger.debug(f"PyMuPDF detected {doc.page_count} pages.")
                for i in range(doc.page_count):
                    self.page_selector.addItem(f"Page {i + 1}", userData=i)
                self.current_page_idx = 0
                
                if doc.page_count > 1: self.page_selector.show()
                else: self.page_selector.hide()
                    
                self.page_selector.blockSignals(False)
                self.render_pdf_to_canvas(file_path, self.current_page_idx)
                self.btn_extract.setEnabled(True)
            except Exception as e:
                logger.error(f"PyMuPDF crashed while attempting to load PDF: {e}")
                QMessageBox.critical(self, "PDF Load Error", str(e))

    def change_page(self, index):
        if index >= 0:
            self.current_page_idx = self.page_selector.currentData()
            logger.info(f"User changed view to Page Index: {self.current_page_idx}")
            self.render_pdf_to_canvas(self.current_pdf_path, self.current_page_idx)

    def render_pdf_to_canvas(self, path, page_idx):
        logger.info(f"Rendering Path: {path} | Page: {page_idx} to Graphics Canvas.")
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
        if not self.current_pdf_path:
            logger.warning("Attempted to render HD PDF but current_pdf_path is empty.")
            return
             
        try:
            doc = fitz.open(self.current_pdf_path)
            page = doc[self.current_page_idx]
            target_dpi = max(min(int(self.base_dpi * zoom_scale), 800), self.base_dpi)
            logger.debug(f"PyMuPDF rendering at {target_dpi} DPI")

            pix = page.get_pixmap(dpi=target_dpi, colorspace=fitz.csRGB, alpha=False)
            img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
            new_pixmap = QPixmap.fromImage(img)

            if self.pdf_pixmap_item is None: 
                self.pdf_pixmap_item = self.scene.addPixmap(new_pixmap)
            else: 
                self.pdf_pixmap_item.setPixmap(new_pixmap)
                
            self.pdf_pixmap_item.setScale(self.base_dpi / target_dpi)
            doc.close()
            logger.debug("HD PDF render cycle completed successfully.")
        except Exception as e:
            logger.error(f"Error during HD PDF Render: {e}")

    def trigger_extraction(self):
        logger.info("Extraction Process Triggered by User.")
        zones = self.canvas.get_selected_zones()
        if not zones:            
            logger.warning("Extraction aborted: No zones selected.")
            return QMessageBox.warning(self, "No Zones", "Please draw at least one green zone first!")
            
        try:
            # 1. Update UI to show processing state
            self.btn_extract.setText(" ⏳ Extracting & Ballooning... Please Wait")
            self.btn_extract.setEnabled(False)
            QApplication.processEvents()

            logger.info("Dynamically importing ManualExtractionPipeline...")
            try:
                from pipeline.manual_extraction_pipeline import ManualExtractionPipeline
            except ModuleNotFoundError as e:
                logger.critical(f"FATAL PATH ERROR: Python sys.path does not recognize the project root. Current sys.path: {sys.path}")
                raise e

            logger.info(f"Instantiating Pipeline with project_root: {PROJECT_ROOT}")
            pipeline = ManualExtractionPipeline(PROJECT_ROOT)
            
            logger.info(f"Executing pipeline on {Path(self.current_pdf_path).name} (Page {self.current_page_idx + 1})")
            result, preview_path = pipeline.execute(Path(self.current_pdf_path), self.current_page_idx + 1, zones)
            logger.info(f"Pipeline Execution Complete. Ballooned FAI saved to: {preview_path}")
            
            # 3. Transition to Preview Mode
            self.preview_pdf_path = preview_path
            self.is_preview_mode = True

            self.primary_tools.hide()
            self.btn_extract.hide()
            self.export_tools.show()

            # Reset Extract Button for future use
            self.btn_extract.setText(" Extract Selected Green Zones")
            self.btn_extract.setEnabled(True)

            # 4. Render the newly generated ballooned PDF (Always Page 0 of the preview)
            self.render_pdf_to_canvas(str(self.preview_pdf_path), 0)
            
        except Exception as e:
            logger.exception(f"Exception caught during trigger_extraction: {str(e)}")
            self.btn_extract.setText(" Extract Selected Green Zones")
            self.btn_extract.setEnabled(True)
            QMessageBox.critical(self, "Extraction Error", str(e))

    def discard_preview(self):
        logger.info("User discarded preview. Returning to standard canvas.")
        self.is_preview_mode = False
        self.export_tools.hide()
        self.primary_tools.show()
        self.btn_extract.show()
        self.render_pdf_to_canvas(self.original_pdf_path, self.current_page_idx)

    def export_drawing(self, ext):
        logger.info(f"User requested Export Format: {ext}")
        if not self.preview_pdf_path or not Path(self.preview_pdf_path).exists():
            logger.error("Export Failed: Preview file does not exist locally.")
            return QMessageBox.warning(self, "Error", "No ballooned preview found to export!")

        default_name = f"{Path(self.original_pdf_path).stem}_BALLOONED{ext}"
        
        filter_str = ""
        if ext == ".pdf": filter_str = "PDF Document (*.pdf)"
        elif ext == ".jpeg": filter_str = "JPEG Image (*.jpeg)"
        elif ext == ".png": filter_str = "PNG Image (*.png)"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Ballooned Drawing", default_name, filter_str)

        # 2. Execute Save if path was chosen
        if file_path:
            logger.info(f"User selected export path: {file_path}")
            try:
                if file_path.endswith(".pdf"):
                    logger.debug("Executing raw file copy for PDF Export.")
                    shutil.copy(self.preview_pdf_path, file_path)
                else:
                    logger.debug("Executing PyMuPDF rasterization for Image Export.")
                    doc = fitz.open(self.preview_pdf_path)
                    page = doc[0]
                    pix = page.get_pixmap(dpi=400, colorspace=fitz.csRGB, alpha=False)
                    if file_path.endswith(".jpeg") or file_path.endswith(".jpg"):
                        pix.save(file_path, "jpeg")
                    else:
                        pix.save(file_path, "png")
                    doc.close()

                logger.info("Export Successful!")
                QMessageBox.information(self, "Export Successful", f"Drawing saved successfully to:\n{file_path}")
                self.discard_preview() 
                
            except Exception as e:
                logger.error(f"File writing failed during export: {e}")
                QMessageBox.critical(self, "Export Failed", f"Could not save the file:\n{str(e)}")
                
        else:
            logger.info("User cancelled the export dialog.")
            
import fitz
import shutil
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                               QLabel, QComboBox, QMessageBox, QMenu)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter, QAction
from PySide6.QtCore import Qt, QRectF, QTimer, QSize

from config.icon_library import IconLibrary

class GreenZoneCanvas(QGraphicsView):
    def __init__(self, scene, parent_page):
        super().__init__(scene)
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

    def explicit_zoom(self, factor):
        self.scale(factor, factor)
        self.current_view_scale *= factor
        self.zoom_timer.start(300) 

    def explicit_pan(self, dx, dy):
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
            else:
                self.scale(zoom_out, zoom_out)
                self.current_view_scale *= zoom_out
            delta = self.mapToScene(event.position().toPoint()) - old_pos
            self.translate(delta.x(), delta.y())
            self.zoom_timer.start(300) 
        else:
            super().wheelEvent(event)

    def trigger_high_res_render(self):
        self.parent_page.re_render_hd_pdf(self.current_view_scale)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            is_preview = getattr(self.parent_page, 'is_preview_mode', False)
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

class ExtractionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.is_preview_mode = False
        layout = QVBoxLayout(self)

        # Primary Tools
        self.primary_tools = QWidget()
        primary_layout = QHBoxLayout(self.primary_tools)
        primary_layout.setContentsMargins(0,0,0,0)

        self.btn_load = QPushButton(" Load Engineering PDF")
        self.btn_load.setIcon(IconLibrary.get("folder"))
        self.btn_load.clicked.connect(self.load_pdf)
        
        self.page_selector = QComboBox()
        self.page_selector.currentIndexChanged.connect(self.change_page)
        self.page_selector.hide() 
        
        self.btn_clear = QPushButton(" Clear Zones")
        self.btn_clear.setIcon(IconLibrary.get("file-x"))
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
        self.btn_approve.setIcon(IconLibrary.get("circle-check-big"))
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
        self.btn_discard.setIcon(IconLibrary.get("x"))
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

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Drawing", "", "PDF Files (*.pdf)")
        if file_path:
            self.original_pdf_path = file_path
            self.is_preview_mode = False
            self.page_selector.blockSignals(True)
            self.page_selector.clear()
            
            doc = fitz.open(file_path)
            for i in range(doc.page_count):
                self.page_selector.addItem(f"Page {i + 1}", userData=i)
            self.current_page_idx = 0
            
            if doc.page_count > 1: self.page_selector.show()
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
            # Connect your actual Pipeline here!
            # For UI placeholder logic:
            QMessageBox.information(self, "Extraction", "Extraction pipeline triggered!")
            self.is_preview_mode = True
            self.primary_tools.hide()
            self.btn_extract.hide()
            self.export_tools.show()
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))

    def discard_preview(self):
        self.is_preview_mode = False
        self.export_tools.hide()
        self.primary_tools.show()
        self.btn_extract.show()
        self.render_pdf_to_canvas(self.original_pdf_path, self.current_page_idx)

    def export_drawing(self, ext):
        QMessageBox.information(self, "Export", f"Saving format {ext} logic execution...")
        self.discard_preview()
        
import sys
import fitz
import shutil
import os
import logging
import numpy as np
import cv2
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                               QLabel, QComboBox, QMessageBox, QApplication,
                               QTableWidget, QTableWidgetItem, QHeaderView, QFrame)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter
from PySide6.QtCore import Qt, QRectF

# --- V5.1 ARCHITECTURE IMPORTS ---
try:
    from infrastructure.pdf.virtual_document import VirtualDocument
    from core.utils.session_manager import SessionManager
    from services.extraction.zone_validator import ZoneHealthValidator
except ImportError as e:
    logger.warning(f"Backend modules pending implementation: {e}")

try:
    from config.icon_library import Ico, IconLibrary
except ImportError:
    pass

# =========================================================================
# 1. THE INTERACTIVE REVIEW PANEL (UPGRADED FOR MULTI-PAGE)
# =========================================================================
class ReviewPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        self.setStyleSheet("QFrame { background-color: #F8FAFC; border-left: 1px solid #DEE2E6; }")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("🔍 Interactive Data Review")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #007BFF; padding: 10px 0;")
        layout.addWidget(title)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Specification", "Tolerance"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 80)
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #DEE2E6; border-radius: 4px; }
            QHeaderView::section { background-color: #E9ECEF; font-weight: bold; border: none; }
        """)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_del = QPushButton("🗑️ Delete Selected Row")
        self.btn_del.setStyleSheet("background-color: #FFE1E1; color: #D32F2F; padding: 8px; border-radius: 4px;")
        btn_layout.addWidget(self.btn_del)
        layout.addLayout(btn_layout)
        
        helper = QLabel("Tip: Draw directly on the canvas to add missing data!")
        helper.setStyleSheet("color: #6C757D; font-size: 11px; font-style: italic;")
        helper.setAlignment(Qt.AlignCenter)
        layout.addWidget(helper)

        # --- MULTI-PAGE WORKFLOW BUTTONS ---
        self.btn_commit_next = QPushButton("⏭️ Commit & Next Page")
        self.btn_commit_next.setStyleSheet("""
            QPushButton { background-color: #17A2B8; color: white; font-weight: bold; padding: 10px; border-radius: 6px; }
            QPushButton:hover { background-color: #138496; }
        """)
        layout.addWidget(self.btn_commit_next)

        self.btn_finalize = QPushButton("✅ Finalize Entire Document")
        self.btn_finalize.setStyleSheet("""
            QPushButton { background-color: #28A745; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #218838; }
        """)
        layout.addWidget(self.btn_finalize)
        self.hide()


# =========================================================================
# 2. THE DYNAMIC CANVAS
# =========================================================================
class GreenZoneCanvas(QGraphicsView):
    def __init__(self, scene, parent_page):
        super().__init__(scene)
        self.parent_page = parent_page 
        self.setDragMode(QGraphicsView.NoDrag) 
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.rect_items = [] 
        self.current_rect = None
        self.start_pos = None
        self.is_preview_mode = False

    def get_selected_zones(self):
        zones = []
        for item in self.rect_items:
            rect = item.sceneBoundingRect()
            zones.append([int(rect.left()), int(rect.top()), int(rect.right()), int(rect.bottom())])
        return zones

    def clear_all_rects(self):
        for item in self.rect_items:
            self.scene().removeItem(item)
        self.rect_items.clear()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item and item.flags() & QGraphicsRectItem.ItemIsSelectable:
                super().mousePressEvent(event)
                return
            
            self.start_pos = self.mapToScene(event.position().toPoint())
            self.current_rect = QGraphicsRectItem()
            
            if self.is_preview_mode:
                pen_color, brush_color = QColor(0, 0, 255), QColor(0, 0, 255, 30) 
            else:
                pen_color, brush_color = QColor(0, 255, 0), QColor(0, 255, 0, 50) 
                
            self.current_rect.setPen(QPen(pen_color, 2, Qt.SolidLine))
            self.current_rect.setBrush(brush_color)
            self.scene().addItem(self.current_rect)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos and self.current_rect:
            end_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self.start_pos, end_pos).normalized()
            self.current_rect.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_rect:
            rect = self.current_rect.rect()
            if rect.width() > 10 and rect.height() > 10:
                self.rect_items.append(self.current_rect)
                if self.is_preview_mode:
                    self.current_rect.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
                    self.current_rect.setFlag(QGraphicsRectItem.ItemIsMovable, True)
                    self.parent_page.add_manual_box_to_table(self.current_rect)
            else:
                self.scene().removeItem(self.current_rect)
            self.current_rect = None
            self.start_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            for item in self.scene().selectedItems():
                if item in self.rect_items:
                    self.rect_items.remove(item)
                    self.scene().removeItem(item)
                    if self.is_preview_mode:
                        self.parent_page.remove_box_from_table(getattr(item, 'dim_ref', None))
        super().keyPressEvent(event)


# =========================================================================
# 3. THE MAIN PAGE CONTROLLER (V5.1 ENABLED)
# =========================================================================
class ExtractionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.original_pdf_path = None
        self.current_pdf_path = None
        self.current_page_idx = 0
        self.master_intelligence = []
        self.base_dpi = 144
        self.pdf_pixmap_item = None
        
        # --- PHASE 1: INITIALIZE SECURE STATE MANAGERS ---
        try:
            self.virtual_doc = VirtualDocument()
            workspace_dir = Path.home() / ".drawing_automation"
            self.session_manager = SessionManager(workspace_dir)
        except NameError:
            logger.warning("VirtualDocument/SessionManager missing. App will fail if backend not built.")
        # -------------------------------------------------
        
        master_layout = QHBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left Panel (Toolbar + Canvas)
        self.left_panel = QWidget()
        layout = QVBoxLayout(self.left_panel)

        # Primary Tools
        self.primary_tools = QWidget()
        tool_layout = QHBoxLayout(self.primary_tools)
        
        self.btn_load = QPushButton(" 📂 Load Blueprint")
        self.btn_load.clicked.connect(self.load_pdf)
        tool_layout.addWidget(self.btn_load)
        
        self.page_selector = QComboBox()
        self.page_selector.currentIndexChanged.connect(self.change_page)
        self.page_selector.hide()
        tool_layout.addWidget(self.page_selector)
        
        layout.addWidget(self.primary_tools)

        # Export Tools (Hidden by default)
        self.export_tools = QWidget()
        export_layout = QHBoxLayout(self.export_tools)
        self.btn_export = QPushButton(" 💾 Export Ballooned Drawing")
        self.btn_export.clicked.connect(lambda: self.export_drawing(".pdf"))
        self.btn_discard = QPushButton(" ❌ Discard & Rerun")
        self.btn_discard.clicked.connect(self.discard_preview)
        export_layout.addWidget(self.btn_export)
        export_layout.addWidget(self.btn_discard)
        self.export_tools.hide()
        layout.addWidget(self.export_tools)

        # Canvas
        self.scene = QGraphicsScene()
        self.canvas = GreenZoneCanvas(self.scene, self)
        layout.addWidget(self.canvas)

        # Bottom Extract Button
        self.btn_extract = QPushButton(" Extract Selected Green Zones")
        self.btn_extract.setStyleSheet("background-color: #28A745; color: white; font-weight: bold; padding: 12px;")
        self.btn_extract.clicked.connect(self.trigger_extraction)
        self.btn_extract.hide()
        layout.addWidget(self.btn_extract)

        master_layout.addWidget(self.left_panel, stretch=1)
        
        # Right Panel (Interactive Review)
        self.review_panel = ReviewPanel(self)
        master_layout.addWidget(self.review_panel)
        
        self.review_panel.btn_del.clicked.connect(self.delete_table_row)
        self.review_panel.btn_commit_next.clicked.connect(self.commit_and_next_page)
        self.review_panel.btn_finalize.clicked.connect(self.finalize_extraction)
        
        logger.info("ExtractionPage UI Module completely loaded.")

    def load_pdf(self):
        """Layer 1: Secure in-memory loading without freezing UI."""
        logger.info("User requested to load a PDF drawing.")
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Blueprint", "", "PDF Files (*.pdf)")
        
        if file_path:
            logger.info(f"PDF Selected: {file_path}")
            self.original_pdf_path = file_path
            self.current_pdf_path = file_path
            
            # Lock UI
            self.btn_load.setText(" ⏳ Loading Securely to RAM...")
            self.btn_load.setEnabled(False)
            self.btn_extract.setEnabled(False)
            QApplication.processEvents()

            if hasattr(self, 'virtual_doc') and self.virtual_doc.load_from_disk(Path(file_path)):
                # Initialize Secure Session (Layer 3.5)
                self.doc_hash = str(hash(file_path)) 
                self.session_manager.initialize_session(self.doc_hash)
                
                # Populate UI
                self.page_selector.blockSignals(True)
                self.page_selector.clear()
                for i in range(self.virtual_doc.page_count):
                    self.page_selector.addItem(f"Page {i + 1}", userData=i)
                
                self.current_page_idx = 0
                self.page_selector.setCurrentIndex(0)
                self.page_selector.setVisible(self.virtual_doc.page_count > 1)
                self.page_selector.blockSignals(False)
                
                # Trigger Async Render (Layer 2)
                self.render_pdf_to_canvas_async(self.current_page_idx)
            else:
                QMessageBox.critical(self, "Load Error", "Failed to load document into secure memory.")
                self.btn_load.setText(" Load Engineering PDF")
                self.btn_load.setEnabled(True)

    def render_pdf_to_canvas_async(self, page_idx):
        """Layer 2: Triggers QThread rendering."""
        logger.info(f"Requesting Async Render for Page: {page_idx}")
        self.current_page_idx = page_idx
        self.canvas.resetTransform()
        self.scene.clear()
        self.canvas.rect_items.clear()
        self.pdf_pixmap_item = None 
        
        if hasattr(self, 'virtual_doc'):
            worker = self.virtual_doc.request_page_render(page_idx, self.base_dpi)
            worker.finished.connect(self._on_render_complete)
            worker.error.connect(self._on_render_error)
            worker.start()

    def _on_render_complete(self, pixmap, scale_factor):
        logger.debug("Async render complete. Applying Pixmap to Canvas.")
        self.pdf_pixmap_item = self.scene.addPixmap(pixmap)
        self.pdf_pixmap_item.setScale(scale_factor)
        self.canvas.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
        self.btn_load.setText(" Load Engineering PDF")
        self.btn_load.setEnabled(True)
        self.btn_extract.show()
        self.btn_extract.setEnabled(True)

    def _on_render_error(self, err_msg):
        logger.error(f"Render failed: {err_msg}")
        QMessageBox.critical(self, "Render Error", f"Failed to render page: {err_msg}")
        self.btn_load.setText(" Load Engineering PDF")
        self.btn_load.setEnabled(True)

    def change_page(self, index):
        if index >= 0:
            new_page_idx = self.page_selector.itemData(index)
            if new_page_idx is not None and new_page_idx != self.current_page_idx:
                self.render_pdf_to_canvas_async(new_page_idx)

    def qimage_to_cv(self, qimage: QImage) -> np.ndarray:
        """Helper to convert QImage to OpenCV array for health check."""
        qimage = qimage.convertToFormat(QImage.Format_RGB888)
        width, height = qimage.width(), qimage.height()
        ptr = qimage.constBits()
        arr = np.array(ptr).reshape(height, width, 3)
        return arr

    def trigger_extraction(self):
        zones = self.canvas.get_selected_zones()
        if not zones: 
            return QMessageBox.warning(self, "No Zones", "Please draw at least one green zone first!")
            
        # --- LAYER 3.6: GREEN ZONE HEALTH VALIDATOR ---
        if self.pdf_pixmap_item and hasattr(self, 'ZoneHealthValidator'):
            try:
                img_arr = self.qimage_to_cv(self.pdf_pixmap_item.pixmap().toImage())
                for z in zones:
                    x1, y1, x2, y2 = z
                    crop = img_arr[y1:y2, x1:x2]
                    health = ZoneHealthValidator.evaluate_zone(crop)
                    
                    if health['status'] == 'REJECT':
                        QMessageBox.warning(self, "Zone Health Warning", f"A selected zone was rejected. Reason: {health['reason']}")
                        return
                    elif health['status'] == 'WARNING':
                        logger.warning(f"Zone Health Warning: {health['reason']}")
            except Exception as e:
                logger.error(f"Pre-extraction health check failed: {e}")
        # ----------------------------------------------

        try:
            self.btn_extract.setText(" ⏳ Extracting & Analyzing...")
            self.btn_extract.setEnabled(False)
            QApplication.processEvents()

            from pipeline.manual_extraction_pipeline import ManualExtractionPipeline
            self.pipeline = ManualExtractionPipeline(Path(PROJECT_ROOT))
            
            self.master_intelligence, _ = self.pipeline.execute(
                Path(self.current_pdf_path), 
                self.current_page_idx + 1, 
                zones,
                debug_mode=False 
            )
            
            self.canvas.clear_all_rects()
            self.canvas.is_preview_mode = True
            self.overlay_interactive_blue_boxes()
            self.populate_review_table()
            
            self.primary_tools.hide()
            self.btn_extract.hide()
            self.review_panel.show()
            
        except Exception as e:
            logger.exception(f"Extraction failed: {e}")
            self.btn_extract.setText(" Extract Selected Green Zones")
            self.btn_extract.setEnabled(True)
            QMessageBox.critical(self, "Extraction Error", str(e))

    def overlay_interactive_blue_boxes(self):
        scale = 2.0 
        for view in self.master_intelligence:
            for dim in view.get("dimensions", []):
                bbox = dim.get("bounding_box_pdf", [0,0,0,0])
                if bbox == [0,0,0,0]: continue
                
                rect = QRectF(bbox[0]*scale, bbox[1]*scale, (bbox[2]-bbox[0])*scale, (bbox[3]-bbox[1])*scale)
                rect_item = QGraphicsRectItem(rect)
                rect_item.setPen(QPen(QColor(0, 0, 255), 2, Qt.SolidLine))
                rect_item.setBrush(QColor(0, 0, 255, 30))
                rect_item.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
                rect_item.setFlag(QGraphicsRectItem.ItemIsMovable, True)
                rect_item.dim_ref = dim 
                
                self.canvas.scene().addItem(rect_item)
                self.canvas.rect_items.append(rect_item)

    def populate_review_table(self):
        self.review_panel.table.setRowCount(0)
        row_idx = 0
        for view in self.master_intelligence:
            for dim in view.get("dimensions", []):
                self.review_panel.table.insertRow(row_idx)
                
                id_item = QTableWidgetItem(str(dim.get("balloon_id", "")))
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable) 
                spec_item = QTableWidgetItem(dim.get("specification", ""))
                tol_item = QTableWidgetItem(dim.get("plus_tol", "")) # Show plus_tol as proxy for tolerance
                
                spec_item.setData(Qt.UserRole, dim) 
                
                # Layer 9: Risk-Based Color Coding (if confidence is mapped)
                if dim.get("confidence", 1.0) < 0.80:
                    spec_item.setBackground(QColor(255, 200, 200))
                    tol_item.setBackground(QColor(255, 200, 200))
                
                self.review_panel.table.setItem(row_idx, 0, id_item)
                self.review_panel.table.setItem(row_idx, 1, spec_item)
                self.review_panel.table.setItem(row_idx, 2, tol_item)
                row_idx += 1

    def add_manual_box_to_table(self, rect_item):
        scale = 0.5 
        rect = rect_item.sceneBoundingRect()
        pdf_bbox = [rect.left() * scale, rect.top() * scale, rect.right() * scale, rect.bottom() * scale]
        
        row_idx = self.review_panel.table.rowCount()
        self.review_panel.table.insertRow(row_idx)
        
        next_id = 1
        if row_idx > 0:
            prev_id_str = self.review_panel.table.item(row_idx - 1, 0).text()
            if prev_id_str.isdigit():
                next_id = int(prev_id_str) + 1
                
        new_dim = {
            "balloon_id": next_id,
            "specification": "MANUAL ENTRY",
            "plus_tol": "",
            "minus_tol": "",
            "bounding_box_pdf": pdf_bbox,
            "raw_text": "MANUAL ENTRY",
            "confidence": 1.0
        }
        
        rect_item.dim_ref = new_dim
        
        if self.master_intelligence:
            self.master_intelligence[0]["dimensions"].append(new_dim)
        else:
            self.master_intelligence.append({"view_name": "MANUAL_VIEW", "dimensions": [new_dim]})
            
        id_item = QTableWidgetItem(str(next_id))
        id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
        spec_item = QTableWidgetItem("MANUAL ENTRY")
        spec_item.setData(Qt.UserRole, new_dim)
        tol_item = QTableWidgetItem("")
        
        self.review_panel.table.setItem(row_idx, 0, id_item)
        self.review_panel.table.setItem(row_idx, 1, spec_item)
        self.review_panel.table.setItem(row_idx, 2, tol_item)
        self.review_panel.table.scrollToBottom()

    def remove_box_from_table(self, dim_dict):
        if not dim_dict: return
        for row in range(self.review_panel.table.rowCount()):
            spec_item = self.review_panel.table.item(row, 1)
            if spec_item and spec_item.data(Qt.UserRole) == dim_dict:
                self.review_panel.table.removeRow(row)
                break

    def delete_table_row(self):
        current_row = self.review_panel.table.currentRow()
        if current_row >= 0:
            spec_item = self.review_panel.table.item(current_row, 1)
            dim_dict = spec_item.data(Qt.UserRole)
            
            for item in self.canvas.rect_items:
                if getattr(item, 'dim_ref', None) == dim_dict:
                    self.canvas.scene().removeItem(item)
                    self.canvas.rect_items.remove(item)
                    break
                    
            self.review_panel.table.removeRow(current_row)

    def _sync_table_to_intelligence(self):
        """Scrapes edits from UI table back into the dictionary."""
        scale = 0.5
        active_dims = []
        for row in range(self.review_panel.table.rowCount()):
            spec_item = self.review_panel.table.item(row, 1)
            tol_item = self.review_panel.table.item(row, 2)
            
            dim_dict = spec_item.data(Qt.UserRole)
            if dim_dict:
                dim_dict["specification"] = spec_item.text()
                dim_dict["plus_tol"] = tol_item.text()
                dim_dict["minus_tol"] = tol_item.text() # Proxy for now
                dim_dict["raw_text"] = spec_item.text()
                
                for item in self.canvas.rect_items:
                    if getattr(item, 'dim_ref', None) == dim_dict:
                        rect = item.sceneBoundingRect()
                        dim_dict["bounding_box_pdf"] = [
                            rect.left() * scale, rect.top() * scale, 
                            rect.right() * scale, rect.bottom() * scale
                        ]
                        break
                        
                active_dims.append(id(dim_dict))

        for view in self.master_intelligence:
            view["dimensions"] = [d for d in view.get("dimensions", []) if id(d) in active_dims]

    def commit_and_next_page(self):
        """Layer 9.5: Multi-page state commitment"""
        logger.info(f"Committing data for Page {self.current_page_idx + 1}")
        self._sync_table_to_intelligence()
        
        if hasattr(self, 'session_manager'):
            self.session_manager.commit_page(self.doc_hash, self.current_page_idx, self.master_intelligence)
            
        next_idx = self.current_page_idx + 1
        if hasattr(self, 'virtual_doc') and next_idx < self.virtual_doc.page_count:
            self.discard_preview()
            self.page_selector.setCurrentIndex(next_idx)
        else:
            QMessageBox.information(self, "Document Complete", "All pages have been processed! Click 'Finalize Entire Document' to export.")

    def finalize_extraction(self):
        self.review_panel.btn_finalize.setText("⏳ Generating Export...")
        self.review_panel.btn_finalize.setEnabled(False)
        QApplication.processEvents()
        
        self._sync_table_to_intelligence()

        # If session manager is active, commit the final page too
        if hasattr(self, 'session_manager'):
            self.session_manager.commit_page(self.doc_hash, self.current_page_idx, self.master_intelligence)
            # Fetch ALL committed intelligence across all pages for export
            final_intelligence = self.session_manager.active_sessions[self.doc_hash].get("master_intelligence", [])
        else:
            final_intelligence = self.master_intelligence

        try:
            # Re-render with debug_mode=False to generate real Red Balloons
            final_pdf_path = self.pipeline.renderer.render_fai_page(
                Path(self.current_pdf_path), 
                self.current_page_idx + 1, 
                final_intelligence, 
                debug_mode=False
            )
            
            self.pipeline.excel_service.generate_inspection_report(
                Path(self.current_pdf_path).name, 
                final_intelligence
            )
            
            # Clear UI and Load the Final Result
            self.canvas.is_preview_mode = False
            self.canvas.clear_all_rects()
            self.preview_pdf_path = final_pdf_path
            
            # Use fitz fallback if virtual doc is not used for preview
            doc = fitz.open(self.preview_pdf_path)
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
            self.scene.clear()
            self.scene.addPixmap(QPixmap.fromImage(img))
            doc.close()
            
            self.review_panel.hide()
            self.export_tools.show()
            QMessageBox.information(self, "Success", "Drawing Ballooned and Enterprise Report Generated Successfully!")
            
        except Exception as e:
            logger.error(f"Finalize failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to finalize report:\n{e}")
            
        self.review_panel.btn_finalize.setText("✅ Finalize Entire Document")
        self.review_panel.btn_finalize.setEnabled(True)

    def discard_preview(self):
        logger.info("User discarded preview. Returning to standard canvas.")
        self.canvas.is_preview_mode = False
        self.canvas.clear_all_rects()
        self.export_tools.hide()
        self.primary_tools.show()
        self.btn_extract.show()
        self.btn_extract.setText(" Extract Selected Green Zones")
        self.btn_extract.setEnabled(True)
        self.review_panel.hide()
        self.render_pdf_to_canvas_async(self.current_page_idx)

    def export_drawing(self, ext):
        default_name = os.path.join(os.path.expanduser("~"), "Desktop", "Ballooned_Drawing.pdf")
        filter_str = "PDF Files (*.pdf)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Ballooned Drawing", default_name, filter_str)

        if file_path:
            try:
                shutil.copy(self.preview_pdf_path, file_path)
                QMessageBox.information(self, "Export Successful", f"Drawing saved to:\n{file_path}")
                self.discard_preview() 
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))
                
                
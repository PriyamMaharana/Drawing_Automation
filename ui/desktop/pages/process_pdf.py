import sys
import fitz
import shutil
import os
import logging
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

from PySide6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                               QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                               QLabel, QComboBox, QMessageBox, QMenu, QApplication,
                               QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame)
from PySide6.QtGui import QPixmap, QImage, QPen, QColor, QPainter, QAction
from PySide6.QtCore import Qt, QRectF, QTimer, QSize

try:
    from config.icon_library import Ico, IconLibrary
except ImportError:
    pass

# =========================================================================
# 1. THE INTERACTIVE REVIEW PANEL
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
        
        # Helper text for drawing manual boxes
        helper = QLabel("Tip: Draw directly on the canvas to add missing data!")
        helper.setStyleSheet("color: #6C757D; font-size: 11px; font-style: italic;")
        helper.setAlignment(Qt.AlignCenter)
        layout.addWidget(helper)

        self.btn_finalize = QPushButton("✅ Finalize & Export Report")
        self.btn_finalize.setStyleSheet("""
            QPushButton { background-color: #28A745; color: white; font-weight: bold; padding: 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #218838; }
        """)
        layout.addWidget(self.btn_finalize)
        self.hide()


# =========================================================================
# 2. THE DYNAMIC CANVAS (Supports Green Zones & Blue Debug Zones)
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
            # If clicking an existing movable item (like resizing a blue box), let the system handle it
            item = self.itemAt(event.pos())
            if item and item.flags() & QGraphicsRectItem.ItemIsSelectable:
                super().mousePressEvent(event)
                return
            
            # Otherwise, start drawing a new box
            self.start_pos = self.mapToScene(event.position().toPoint())
            self.current_rect = QGraphicsRectItem()
            
            if self.is_preview_mode:
                pen_color, brush_color = QColor(0, 0, 255), QColor(0, 0, 255, 30) # Blue Debug Box
            else:
                pen_color, brush_color = QColor(0, 255, 0), QColor(0, 255, 0, 50) # Green Extract Zone
                
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
                    # Automatically add this new box to the review table!
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
                        # Automatically delete from the review table!
                        self.parent_page.remove_box_from_table(getattr(item, 'dim_ref', None))
        super().keyPressEvent(event)


# =========================================================================
# 3. THE MAIN PAGE CONTROLLER
# =========================================================================
class ExtractionPage(QWidget):
    def __init__(self):
        super().__init__()
        self.original_pdf_path = None
        self.current_pdf_path = None
        self.current_page_idx = 0
        self.master_intelligence = []
        
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
        self.review_panel.btn_finalize.clicked.connect(self.finalize_extraction)

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Blueprint", "", "PDF Files (*.pdf)")
        if file_path:
            self.original_pdf_path = file_path
            self.current_pdf_path = file_path
            self.current_page_idx = 0
            self.btn_extract.show()
            self.render_pdf_to_canvas(file_path, 0)

    def render_pdf_to_canvas(self, pdf_path, page_num):
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        mat = fitz.Matrix(2.0, 2.0) # 144 DPI (Scale Factor = 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        doc.close()

    def trigger_extraction(self):
        zones = self.canvas.get_selected_zones()
        if not zones: 
            return QMessageBox.warning(self, "No Zones", "Please draw at least one green zone first!")
            
        try:
            self.btn_extract.setText(" ⏳ Extracting & Analyzing...")
            self.btn_extract.setEnabled(False)
            QApplication.processEvents()

            from pipeline.manual_extraction_pipeline import ManualExtractionPipeline
            self.pipeline = ManualExtractionPipeline(Path(PROJECT_ROOT))
            
            # Execute Backend WITHOUT rendering the baked Blue Box PDF
            self.master_intelligence, _ = self.pipeline.execute(
                Path(self.current_pdf_path), 
                self.current_page_idx + 1, 
                zones,
                debug_mode=False 
            )
            
            # Switch to UI Preview Mode
            self.canvas.clear_all_rects()
            self.canvas.is_preview_mode = True
            
            # Paint Native Interactive Blue Boxes on the UI Canvas
            self.overlay_interactive_blue_boxes()
            
            # Populate Side Table
            self.populate_review_table()
            
            # Adjust UI
            self.primary_tools.hide()
            self.btn_extract.hide()
            self.review_panel.show()
            
        except Exception as e:
            logger.exception(f"Extraction failed: {e}")
            self.btn_extract.setText(" Extract Selected Green Zones")
            self.btn_extract.setEnabled(True)
            QMessageBox.critical(self, "Extraction Error", str(e))

    def overlay_interactive_blue_boxes(self):
        """Translates backend dict coordinates into native PySide6 Blue Boxes."""
        scale = 2.0 # Converts PDF 72 DPI to Canvas 144 DPI
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
                
                rect_item.dim_ref = dim # Secretly link the box to the dictionary!
                
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
                tol_item = QTableWidgetItem(dim.get("tolerance", ""))
                
                spec_item.setData(Qt.UserRole, dim) 
                
                self.review_panel.table.setItem(row_idx, 0, id_item)
                self.review_panel.table.setItem(row_idx, 1, spec_item)
                self.review_panel.table.setItem(row_idx, 2, tol_item)
                row_idx += 1

    def add_manual_box_to_table(self, rect_item):
        """Fires automatically when the user draws a new blue box on the canvas."""
        scale = 0.5 # Converts Canvas 144 DPI back to PDF 72 DPI
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
            "tolerance": "",
            "bounding_box_pdf": pdf_bbox,
            "raw_text": "MANUAL ENTRY"
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
        """Fires automatically when the user presses DELETE on a canvas blue box."""
        if not dim_dict: return
        for row in range(self.review_panel.table.rowCount()):
            spec_item = self.review_panel.table.item(row, 1)
            if spec_item and spec_item.data(Qt.UserRole) == dim_dict:
                self.review_panel.table.removeRow(row)
                break

    def delete_table_row(self):
        """Fires if the user clicks the Delete Button inside the Review Panel."""
        current_row = self.review_panel.table.currentRow()
        if current_row >= 0:
            spec_item = self.review_panel.table.item(current_row, 1)
            dim_dict = spec_item.data(Qt.UserRole)
            
            # Wipe it from the canvas visually
            for item in self.canvas.rect_items:
                if getattr(item, 'dim_ref', None) == dim_dict:
                    self.canvas.scene().removeItem(item)
                    self.canvas.rect_items.remove(item)
                    break
                    
            self.review_panel.table.removeRow(current_row)

    def finalize_extraction(self):
        self.review_panel.btn_finalize.setText("⏳ Generating Export...")
        self.review_panel.btn_finalize.setEnabled(False)
        QApplication.processEvents()
        
        scale = 0.5
        active_dims = []
        
        # Scrape all edited text and adjusted box coordinates
        for row in range(self.review_panel.table.rowCount()):
            spec_item = self.review_panel.table.item(row, 1)
            tol_item = self.review_panel.table.item(row, 2)
            
            dim_dict = spec_item.data(Qt.UserRole)
            if dim_dict:
                dim_dict["specification"] = spec_item.text()
                dim_dict["tolerance"] = tol_item.text()
                dim_dict["raw_text"] = spec_item.text()
                
                # Fetch dynamically shifted coordinates from UI canvas
                for item in self.canvas.rect_items:
                    if getattr(item, 'dim_ref', None) == dim_dict:
                        rect = item.sceneBoundingRect()
                        dim_dict["bounding_box_pdf"] = [
                            rect.left() * scale, rect.top() * scale, 
                            rect.right() * scale, rect.bottom() * scale
                        ]
                        break
                        
                active_dims.append(id(dim_dict))

        # Prune deleted dimensions from Master Intelligence
        for view in self.master_intelligence:
            view["dimensions"] = [d for d in view.get("dimensions", []) if id(d) in active_dims]

        try:
            # Re-render with debug_mode=False to generate real Red Balloons!
            final_pdf_path = self.pipeline.renderer.render_fai_page(
                Path(self.current_pdf_path), 
                self.current_page_idx + 1, 
                self.master_intelligence, 
                debug_mode=False
            )
            
            self.pipeline.excel_service.generate_inspection_report(
                Path(self.current_pdf_path).name, 
                self.master_intelligence
            )
            
            # Clear UI and Load the Final Result
            self.canvas.is_preview_mode = False
            self.canvas.clear_all_rects()
            self.preview_pdf_path = final_pdf_path
            self.render_pdf_to_canvas(str(self.preview_pdf_path), 0)
            
            self.review_panel.hide()
            self.export_tools.show()
            QMessageBox.information(self, "Success", "Drawing Ballooned and Excel Report Generated Successfully!")
            
        except Exception as e:
            logger.error(f"Finalize failed: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to finalize report:\n{e}")
            
        self.review_panel.btn_finalize.setText("✅ Finalize & Export Report")
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
        self.render_pdf_to_canvas(self.original_pdf_path, self.current_page_idx)

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
                
                
import fitz
import psutil
import logging
import numpy as np
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QImage, QPixmap
from pathlib import Path

logger = logging.getLogger(__name__)

class RasterizationWorker(QThread):
    finished = Signal(QPixmap, float)  # Pixmap, Render Scale
    error = Signal(str)

    def __init__(self, doc_bytes: bytes, page_idx: int, base_dpi: int = 144):
        super().__init__()
        self.doc_bytes = doc_bytes
        self.page_idx = page_idx
        self.base_dpi = base_dpi

    def run(self):
        try:
            # Memory Watchdog: Check available system RAM
            mem = psutil.virtual_memory()
            target_dpi = self.base_dpi
            if mem.percent > 85.0:
                logger.warning(f"High RAM usage detected ({mem.percent}%). Downscaling rasterization to 100 DPI.")
                target_dpi = 100

            doc = fitz.open("pdf", stream=self.doc_bytes)
            page = doc[self.page_idx]
            
            logger.debug(f"Rasterizing page {self.page_idx} at {target_dpi} DPI in background.")
            pix = page.get_pixmap(dpi=target_dpi, colorspace=fitz.csRGB, alpha=False)
            
            img = QImage(pix.samples, pix.w, pix.h, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            
            scale_factor = self.base_dpi / target_dpi
            
            doc.close()
            self.finished.emit(pixmap, scale_factor)
            
        except Exception as e:
            logger.error(f"Rasterization failed: {e}")
            self.error.emit(str(e))


class VirtualDocument(QObject):
    def __init__(self):
        super().__init__()
        self.doc_bytes = None
        self.page_count = 0
        self.current_worker = None

    def load_from_disk(self, file_path: Path) -> bool:
        """Loads the document securely into RAM (State A)."""
        try:
            with open(file_path, "rb") as f:
                self.doc_bytes = f.read()
            
            # Temporary open just to get page count
            temp_doc = fitz.open("pdf", stream=self.doc_bytes)
            self.page_count = temp_doc.page_count
            temp_doc.close()
            
            logger.info("PDF securely loaded into RAM. File handle released.")
            return True
        except Exception as e:
            logger.error(f"Failed to load PDF to RAM: {e}")
            return False

    def request_page_render(self, page_idx: int, base_dpi: int = 144):
        """Triggers asynchronous rasterization (State B) for the UI."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.terminate()
            self.current_worker.wait()
            
        self.current_worker = RasterizationWorker(self.doc_bytes, page_idx, base_dpi)
        return self.current_worker
    
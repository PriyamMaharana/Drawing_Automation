import os
import cv2
import numpy as np
import fitz  # PyMuPDF
from typing import List, Dict

class VisionProcessor:
    """
    A read-only, in-memory backend service to mathematically isolate tabular grids
    (like Bill of Material tables) physically drawn onto a CAD canvas.
    """

    def process_page(self, page: fitz.Page, source_filename: str) -> List[Dict[str, float]]:
        """
        Process a single fitz.Page to find bounding boxes of table grids.
        
        Args:
            page: The PyMuPDF page object.
            source_filename: The full path to the source PDF file.
            
        Returns:
            A list of dictionaries containing the 72-DPI coordinates of the masked tables.
        """
        # 1. The 300-DPI Render
        # Native PDF space is 72 DPI. We render at 300 DPI for high-resolution analysis.
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        
        # Render page to a pixmap
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert fitz pixmap to an OpenCV numpy array (grayscale)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        elif pix.n == 4:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
        else:
            gray = img_np
            
        # 2. The Signal Inversion
        # Binary Inverse Threshold: Background (white paper) becomes 0, drawing lines (black) become 255
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 3. The Morphological Scan
        # Isolate continuous horizontal and vertical lines independently
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 100))
        
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        
        # 4. The Topological Failsafe
        # Find 90-degree intersection points between horizontal and vertical lines
        # Tables have dense intersections. Long stray lines (like drive shafts) do not.
        intersections = cv2.bitwise_and(horizontal_lines, vertical_lines)
        
        # 5. The Grid Melter
        # Dilate the intersection mask to melt the dense grid structure into solid rectangular blocks (Dead Zones)
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
        dilated_mask = cv2.dilate(intersections, dilate_kernel, iterations=3)
        
        # 6. Contour Extraction & Coordinate Translation
        # Find the bounding boxes of the solid white table blocks
        contours, _ = cv2.findContours(dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        total_area = gray.shape[0] * gray.shape[1]
        
        table_coordinates = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # Filter out small noise (ignore contours whose bounding box area is less than 1.5% of total image area)
            if area > 0.015 * total_area:
                # The coordinates are at 300 DPI. We must downscale them back to 72 DPI native space.
                scale_factor = 72 / 300
                x0 = x * scale_factor
                y0 = y * scale_factor
                x1 = (x + w) * scale_factor
                y1 = (y + h) * scale_factor
                
                table_coordinates.append({
                    "x0": float(x0),
                    "y0": float(y0),
                    "x1": float(x1),
                    "y1": float(y1)
                })
                
                # Fill the mask with a solid white rectangle for debug output
                cv2.rectangle(dilated_mask, (x, y), (x + w, y + h), 255, -1)
                
        # 7. The Dynamic Debug Output
        # Ensure the debug/ directory exists
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        debug_dir = os.path.join(project_root, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Extract the base name from the source filename
        basename = os.path.splitext(os.path.basename(source_filename))[0]
        
        # Save the dilated mask
        debug_mask_path = os.path.join(debug_dir, f"{basename}_mask.png")
        cv2.imwrite(debug_mask_path, dilated_mask)
        
        return table_coordinates

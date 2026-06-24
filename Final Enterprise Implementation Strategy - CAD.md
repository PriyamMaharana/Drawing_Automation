# **Comprehensive Enterprise Implementation & Security Strategy**

**System:** Hybrid Vector-OCR CAD Extraction Engine (Version 5.1 \- Production Ready)

**Deployment Target:** Air-Gapped, Offline Enterprise Desktop Application

**Architecture Type:** Engineering Relationship Reconstruction Platform

## **SECTION 1: Developer Guide (Implementation, Logging, & Monitoring)**

This section provides the strict technical blueprint for developers to build the 14-layer architecture.  
**Strict Logging & Configuration Standard:** \* All modules must route through a centralized core.utils.logger.

* **Security Rule:** *NEVER* log raw proprietary dimension values, customer OEM names, or file paths in plain text debug logs to disk. Mask them (e.g., Value: .).  
* **Configuration Rule:** No hardcoded thresholds. Read all tolerances, scaling factors, and UI colors from config/extraction.yaml, config/security.yaml, and config/export\_profiles/.

### **PHASE 1: Document Loading & Session Management**

**Layer 1: Virtual Matrix Mapping (The Virtual Copy)**

* **Implementation:** Initialize State A (Vector Model) and State B (Raster Model). Read the PDF byte stream into fitz.Document(stream=file\_bytes). Spawn a background process to generate a NumPy array matrix of the raster image at 300 DPI.  
* **Logging:** INFO: Document loaded securely to RAM. DEBUG: Rasterization generation time (ms).  
* **Debugging:** Monitor memory\_usage\_mb. Implement a watchdog: if system RAM is \< 15% available, dynamically downscale the raster to 200 DPI.

**Layer 2: Asynchronous UI Rendering**

* **Implementation:** Utilize QThread and QGraphicsScene. Convert the 300 DPI NumPy array into a 144 DPI QImage for viewport rendering.  
* **Logging:** INFO: UI Canvas Ready. DEBUG: render\_time\_ms.  
* **Debugging:** Max allowable UI blocking is 100ms. Use Qt's Signal/Slot mechanism to pass the rendered image back to the main thread to prevent "Not Responding" freezes.

**Layer 3: Non-Destructive Display**

* **Implementation:** Render all layers of the PDF. Do not apply OpenCV thresholds or masking to the UI QPixmap.  
* **Debugging:** Ensure the user sees the drawing exactly as it appears in Adobe Acrobat.

**Layer 3.5: Document Session Manager**

* **Implementation:** Build a SessionManager class. Maintain a local, encrypted dictionary tracking: {document\_id, current\_page, processed\_pages, committed\_pages, next\_balloon\_id, export\_status}.  
* **Logging:** INFO: Session Resumed for \[Doc\_ID\_Hash\].  
* **Debugging:** Write session saves to a .tmp file first, then use atomic OS rename to overwrite the actual session file to prevent corruption on sudden power loss.

**Layer 3.6: Green Zone Health Validator**

* **Implementation:** Calculate a Health Score (0-100). Extract contours (cv2.findContours) in the drawn QRectF. Compute: Geometry Density (ink to whitespace ratio), Text Density, and Boundary Intersections (do text boxes cross the green line?).  
* **Logging:** DEBUG: Zone Health Score metrics. WARNING: Zone Rejected (Score \< 50).

### **PHASE 2: Extraction & Engineering Intelligence**

**Layer 4: OCR Provider Engine**

* **Implementation:** Build the IOcrProvider Python Interface. Implement TesseractProvider wrapping local binaries. Execute multi-pass rotations (0°, 90°, 180°, 270°) using Tesseract \--psm 11 (Sparse Text).  
* **Logging:** INFO: Multi-pass OCR completed. DEBUG: ocr\_time\_ms.

**Layer 4.1: Table & Annotation Isolation**

* **Implementation:** Run OpenCV Hough Line Transform on the Green Zone to find intersecting perpendicular lines forming grids. Mask these grid boundaries out of the extraction array.  
* **Logging:** INFO: N Tables Isolated and Ignored.

**Layer 4.2: Confidence Arbitration**

* **Implementation:** Compare PyMuPDF get\_text("dict") strings vs OCR strings at the same coordinates. Score \= (OCR\_Conf \* 0.4) \+ (Regex\_Match \* 0.4) \+ (Length\_Sanity \* 0.2). Map to enum: RESOLVED, UNRESOLVED, REJECTED.  
* **Logging:** DEBUG: Arbitration conflict resolved. Winner: \[Provider\].

**Layer 5: Multi-Factor Spatial Clustering**

* **Implementation:** Build a KD-Tree. Cluster fragments if Euclidean Distance \< (font\_height \* 1.2) AND Y-Axis Alignment variance \< 5px.  
* **Debugging:** During development, draw red lines on the canvas between clustered fragments to visually verify logic.

**Layer 5.2: View Segmentation Engine**

* **Implementation:** Locate text like "SECTION A-A". Generate a virtual bounding box covering the geometry immediately above/below the text until hitting another view boundary or sheet border.  
* **Logging:** INFO: View \[Name\] segmented.

**Layer 5.5: Graph-Based Relationship Engine (Critical)**

* **Implementation:** Build a NetworkX directed graph.  
  1. Detect OpenCV Line contours (Leaders).  
  2. Ray-cast from Dimension text to the nearest Leader endpoint.  
  3. Ray-cast from the Leader's opposite endpoint to intersecting Geometry (Arcs, Lines).  
  4. Link: Dimension \-\> Leader \-\> Geometry.  
* **Logging:** DEBUG: Edge established in Relationship Graph.

**Layer 5.7: Dimension Grouping Engine**

* **Implementation:** Scan the Relationship Graph for Dimensions sharing the same collinear axis (Baseline/Ordinate routing). Tag them with a shared dimension\_group\_id.

**Layer 6, 6.2, 6.5: Ontology, GD\&T Parsing, & Normalizer**

* **Implementation:** Classify clustered strings using standard regex dictionaries. Split composite GD\&T frames by vertical line | characters. Calculate floating-point upper\_limit and lower\_limit from ± string values.  
* **Logging:** ERROR: Normalizer math failure on string (route to UNRESOLVED).

### **PHASE 3: Validation, Commitment, & Export**

**Layer 7 & 8: Overlay Validation & Dynamic Review Table**

* **Implementation:** Draw QGraphicsPolygonItem boxes using the normalized PDF coordinates. Populate a QTableWidget. Bind the UI row to the Graph Node ID.  
* **Debugging:** Ensure len(table\_rows) \== len(ui\_polygons).

**Layer 9 & 9.5: Risk-Based Review & Commit Manager**

* **Implementation:** Highlight rows red if Aggregate Confidence \< 80%. On "Commit Page" click, serialize the approved Graph Nodes to the SessionManager, lock the UI elements, and transition to the next PDF page index.

**Layer 10: Adaptive Balloon Engine**

* **Implementation:** Implement a Convergence-Based Solver (Force-Directed).  
  * *Nodes:* Balloon Circles (repel each other).  
  * *Edges:* Leader lines (act as rigid springs to their target).  
  * Stop loop when no collisions exist or delta\_movement \< 1px.  
* **Logging:** DEBUG: Physics convergence reached in N iterations.

**Layer 11, 12, 12.5: Lossless PDF, Schema Export, Duplicate Detection**

* **Implementation:** Use fitz.Page.add\_circle\_annot (Red, 2px stroke). Export using pandas and map columns based on config/export\_profiles/as9102.json. Compare Value \+ View\_ID \+ Target\_Geometry to prevent duplicates.

**Layer 13 & 14: Immutable Audit & Telemetry Engine**

* **Implementation:** Use Python's logging module configured to output JSON Lines (.jsonl). Record action, before, after, user\_hash, timestamp. Store layer times in memory and dump to telemetry upon session close.

## **SECTION 2: Tamper-Resistant Enterprise Delivery & Security Architecture**

Because this application operates in air-gapped defense, aerospace, and automotive environments, it must be completely resilient against decompilation, reverse engineering, and memory injection.

### **1\. What Exactly Must Be Encrypted / Obfuscated?**

| Asset Type | Location / Component | Security Strategy |
| :---- | :---- | :---- |
| **Core Intellectual Property** | L4/L5/L6 (Arbitrators, Clustering, Relationship Graph, Parsers) | **Cython Compilation.** Convert .py to C code, compile to .pyd (Windows) or .so (Linux). Destroys Python bytecode. |
| **UI & Application Routing** | main\_app.py, process\_pdf.py, Page Routers | **PyArmor Advanced Obfuscation.** Encrypts scripts with runtime decryption. |
| **Session State & WIP** | project\_session.json | **AES-256 (Fernet) Encryption** at rest. Decrypted only in RAM. |
| **Audit Logs** | audit\_log.jsonl | **HMAC Signed & AES-256 Encrypted.** Prevents users from manually altering compliance logs. |
| **Internal Databases** | Telemetry / Knowledge Graph | **SQLCipher (AES-256).** Encrypts the local SQLite database files. |
| **Dictionaries & Configs** | CADSignatures, .yaml files | Bundled as encrypted data blobs inside the PyInstaller executable. |

### **2\. Hack-Proof Build Pipeline (CI/CD)**

The build process must be fully automated to ensure human developers never leak unencrypted assets.

**Step A: Native C-Compilation (Cython)**

Create a setup.py that targets the core intelligence layers.

from setuptools import setup  
from Cython.Build import cythonize

setup(  
    ext\_modules \= cythonize(\[  
        "infrastructure/ocr/\*.py",   
        "parsers/dimensions/\*.py",  
        "services/relationship\_engine.py"  
    \])  
)

*Action:* Run compilation. Delete the original .py files from the staging build directory.

**Step B: Anti-Debugger & Bytecode Obfuscation (PyArmor)**

Run PyArmor on the UI and entry point scripts.

*Action:* Use PyArmor's \--restrict flag. This injects anti-tamper routines that detect if a hacker attaches a debugger (like x64dbg or Cheat Engine). If a debugger is detected, the app triggers a sys.exit() and wipes RAM.

**Step C: Hardware Fingerprint & Offline Licensing**

Do not use standard MAC addresses (they can be spoofed).

* **Generation:** Generate a unique MachineID using a SHA-256 hash of the CPU ID \+ Motherboard UUID (wmic csproduct get uuid).  
* **Enforcement:** The application reads an encrypted license.key file. If the decrypted hardware hash inside the key does not match the host's MachineID, the application refuses to boot.

**Step D: Secure Packing (PyInstaller)**

Package the .pyd files, PyArmor scripts, headless OpenCV, and local Tesseract binaries.

pyinstaller \--name "DrawingAutomation\_v5" \\  
            \--windowed \\  
            \--icon="assets/icon.ico" \\  
            \--add-data="vendor/tesseract;vendor/tesseract" \\  
            \--clean \\  
            ui/desktop/main\_app.py

*Security Note:* Apply a digital Code Signing Certificate (Authenticode) to the final .exe. This proves the executable was built by your organization and prevents Windows Defender from blocking it.

### **3\. Execution Security (Runtime Defense)**

To protect proprietary OEM CAD data while the application is running:

1. **Memory-Only Processing:** At no point should a temporary PDF, cropped TIFF, or unencrypted image be written to the local disk (e.g., C:\\Temp\\). All image processing (cv2, fitz.Pixmap) must remain in application heap memory.  
2. **Secure Memory Wiping:** Implement a Python atexit handler. Upon graceful exit or crash, the handler must explicitly overwrite sensitive memory arrays (e.g., numpy image matrices, session dictionary values) with 0x00 before garbage collection releases them back to the OS.  
3. **Audit Trail Sealing:** When an AS9102 inspection is exported, the final audit\_log.jsonl is cryptographically signed. If a QA manager attempts to open the log in Notepad and alter an approval, the system will flag the log as "Tampered" upon subsequent loads.

### **4\. Enterprise Testing Framework (6-Tier System)**

* **Tier 1 (Unit Tests):** Automated PyTest suite for C-compiled (.pyd) parsers. Verify normalizers split tolerances accurately.  
* **Tier 2 (Integration Tests):** Feed dummy PDF crops to the Relationship Graph to verify dimension-to-leader linking.  
* **Tier 3 (End-to-End Tests):** Full lifecycle (Load \-\> Zone \-\> Extract \-\> Commit \-\> Page 2 \-\> Export) via automated UI tools (e.g., pytest-qt).  
* **Tier 4 (Customer UAT):** Deploy to air-gapped OEM facilities (e.g., Cummins). Validate Force-Directed Ballooning on 500+ dimension drawings.  
* **Tier 5 (Security Testing \- Red Team):** Attempt to run pyinstxtractor on the executable (verify it yields obfuscated/compiled junk). Attempt to spoof the hardware lock.  
* **Tier 6 (Performance & Load Testing):** Stress test parameters: 500-page PDFs, 1000+ dimensions/page. Ensure peak RAM usage remains under 4GB to support legacy engineering workstations.
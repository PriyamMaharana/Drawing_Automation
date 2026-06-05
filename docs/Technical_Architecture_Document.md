# Technical Architecture Document (TAD)

# Architecture Overview

Application Type:

Desktop Application

Architecture:

Layered Modular Architecture

---

# High-Level Architecture

UI Layer
↓
Controller Layer
↓
Service Layer
↓
Extraction Engine
↓
Export Engine

---

# Folder Structure

```text
EngineeringDrawingAutomation/
│
├── main.py
│
├── ui/
├── controllers/
├── services/
├── parsers/
├── extractors/
├── ballooning/
├── exporters/
├── models/
├── config/
├── resources/
├── output/
├── logs/
└── tests/
```

---

# Module Breakdown

## UI Layer

Responsible For:

- Dashboard
- Process PDF
- Results
- Reports
- Settings

Technology:

PySide6

---

## Controller Layer

Responsible For:

- Workflow orchestration
- Event handling
- Navigation

Files:

app_controller.py
process_controller.py
export_controller.py

---

## Service Layer

Responsible For:

Business Logic

Files:

extraction_service.py
balloon_service.py
report_service.py
settings_service.py

---

## PDF Parsing Layer

Technology:

PyMuPDF

Responsibilities:

- Read text
- Extract coordinates
- Extract page information

---

## Extraction Layer

Modules:

specification_extractor.py
tolerance_extractor.py
metadata_extractor.py
notes_extractor.py

---

# Extraction Workflow

PDF
↓
Text Blocks
↓
Coordinate Extraction
↓
Specification Detection
↓
Tolerance Detection
↓
Balloon Assignment
↓
Excel Export

---

# Data Model

Parameter

```python
class Parameter:
    serial_no: int
    specification: str
    tolerance: str
    page_no: int
    x: float
    y: float
```

---

# Export Architecture

Input:

ExtractionResult

Output:

Excel
Ballooned PDF

Technology:

openpyxl

---

# Deployment Architecture

Source
↓
PyInstaller
↓
Single EXE

No external services.

No database.

No internet required.

---
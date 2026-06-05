# Product Requirements Document (PRD)

# Project Name

Engineering Drawing Automation System

Version: 2.0
Owner: RSB Global
Platform: Windows Desktop Application
Technology: Python + PySide6

---

# 1. Project Overview

Engineering Drawing Automation System is an offline desktop application designed to automate extraction of engineering drawing parameters from PDF drawings and generate inspection-ready Excel sheets.

The system targets:

- Automotive Manufacturing
- Precision Machining
- Fabrication Industry
- Quality Inspection Teams
- Production Engineering Teams

The primary goal is to reduce manual effort required to prepare inspection sheets from engineering drawings.

---

# 2. Business Problem

Current Process:

Engineer receives PDF drawing
↓
Engineer manually reads dimensions
↓
Engineer manually creates Excel inspection sheet
↓
Engineer manually numbers dimensions
↓
Engineer manually creates ballooned drawing

Problems:

- Time consuming
- Human errors
- Missed dimensions
- Inconsistent reports
- Poor traceability

---

# 3. Proposed Solution

System shall:

1. Load Engineering Drawing PDF
2. Extract specification (dimensions, thread, callout, etc..) and tolerances
3. Generate ballooned drawing
4. Generate inspection Excel sheet
5. Store notes and metadata
6. Export reports

Entire process must be completed automatically.

---

# 4. Core Functional Requirements

## FR-001 PDF Import

User shall be able to:

- Select PDF
- Drag & Drop PDF
- Process multiple PDFs

Supported:

- Native PDF Drawings
- Scanned PDFs

Not Supported (Phase 1):

- DWG
- DXF

---

## FR-002 Parameter Extraction

Extract all engineering specifications.

Examples:

91.4
75
308
0.03
Ø75
R12
R5
N9
A1
M10
0.5x20

All extracted values become:

Specification

---

## FR-003 Tolerance Extraction

Examples:

±0.015
±0.5
+0.2
-0.1

Stored separately.

---

## FR-004 Balloon Generation

Every extracted specification shall receive:

1
2
3
4
5

etc.

Balloon Number = Excel Serial Number

---

## FR-005 Excel Generation

Template:

| SL NO | Product Parameter | Specification | Tolerance | Checking Method | Observation | Remarks |
|---------|---------|---------|---------|---------|---------|---------|

Auto Fill:

- SL NO
- Specification
- Tolerance

Manual Fields:

- Product Parameter
- Checking Method
- Observation
- Remarks

---

## FR-006 Metadata Extraction

Extract:

- Drawing Number
- Part Number
- Revision
- Material
- Scale
- Date

---

## FR-007 Notes Extraction

Extract:

- General Notes
- Manufacturing Notes
- Surface Finish Notes

---

## FR-008 Report Export

Export:

- Excel
- Ballooned PDF

---

# 5. Non-Functional Requirements

Performance:

- <10 seconds for typical drawing

Availability:

- Offline

Security:

- Local Processing Only

Scalability:

- Batch PDF Support

Reliability:

- No data loss

---

# 6. Success Metrics

Dimension Detection Accuracy:

≥95%

Tolerance Detection Accuracy:

≥95%

Excel Generation Success:

100%

Application Startup:

<3 sec

Processing Time:

<10 sec/drawing

---
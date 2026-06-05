# Frontend Specification Document

# UI Framework

PySide6

Theme:

Dark (Default)

---

# Responsive Behavior

Application must:

- Maximize automatically
- Scale according to screen resolution
- Support High DPI

Supported:

1366x768
1920x1080
2560x1440
4K

---

# Main Pages

1 Dashboard
2 Process PDF
3 Results
4 Reports
5 Settings

---

# Dashboard

Purpose:

System overview

Components:

- Total Drawings
- Total Parameters
- Total Reports
- Recent Activity
- Last Processed Drawing
- Quick Actions

---

# Process PDF

Components:

Upload Area

File Queue

Processing Options

Process Button

Output Folder

---

# Results

Components:

Search

Filters

Parameter Table

Drawing Preview

Export Button

---

# Results Table

Columns:

| SL NO |
| Specification |
| Tolerance |
| Source PDF |
| Page |

---

# Reports

Components:

Generated Files

Export Actions

Open Folder

Statistics

---

# Settings

## Appearance

Theme

- Dark
- Light

Font Size

- Small
- Medium
- Large
- Extra Large

Font Family

- Segoe UI
- Arial
- Calibri
- Roboto

---

## Processing

Generate Balloon PDF

Generate Excel

Extract Metadata

Extract Notes

Auto Open Results

---

## Export

Output Folder

Create Date Folder

Open Output Folder

Export Format

- Excel
- PDF
- Both

---

# Theme Architecture

```text
ui/themes/
├── dark_theme.qss
├── light_theme.qss
└── theme_manager.py
```

---

# Global Settings

Applied application-wide.

Theme change:

Immediate

Font change:

Immediate

No restart required.

---
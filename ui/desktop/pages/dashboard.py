from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QSize
from config.icon_library import IconLibrary

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Dashboard Overview")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007BFF;")
        layout.addWidget(title)

        # KPI Cards Row
        kpi_layout = QHBoxLayout()
        kpi_layout.addWidget(self._build_kpi_card("Total Drawings", "1,204", "folder"))
        kpi_layout.addWidget(self._build_kpi_card("Dimensions Extracted", "45,892", "file-text"))
        kpi_layout.addWidget(self._build_kpi_card("Average Accuracy", "99.4%", "circle-check-big"))
        kpi_layout.addWidget(self._build_kpi_card("Hours Saved", "340 hrs", "settings"))
        layout.addLayout(kpi_layout)

        # Quick Actions Row
        actions_layout = QHBoxLayout()
        btn_new = QPushButton(" ➕ Start New Extraction")
        btn_new.setStyleSheet("background-color: #28A745; color: white; padding: 12px; font-size: 14px;")
        
        btn_recent = QPushButton(" 📂 Open Recent Report")
        btn_recent.setStyleSheet("background-color: #007BFF; color: white; padding: 12px; font-size: 14px;")
        
        actions_layout.addWidget(btn_new)
        actions_layout.addWidget(btn_recent)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Recent Activity Table
        lbl_recent = QLabel("Recent Activity")
        lbl_recent.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        layout.addWidget(lbl_recent)

        self.table = QTableWidget(5, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Drawing Number", "Dimensions", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: white; border: 1px solid #DEE2E6; border-radius: 6px; }")
        
        # Mock Data
        self.table.setItem(0, 0, QTableWidgetItem("2026-06-22"))
        self.table.setItem(0, 1, QTableWidgetItem("RSB-DWG-9021"))
        self.table.setItem(0, 2, QTableWidgetItem("42"))
        self.table.setItem(0, 3, QTableWidgetItem("Completed"))
        
        layout.addWidget(self.table)

    def _build_kpi_card(self, title_text, value_text, icon_name):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: white; border: 1px solid #DEE2E6; border-radius: 8px; padding: 15px; }")
        l = QVBoxLayout(card)
        
        title = QLabel(title_text)
        title.setStyleSheet("color: #6C757D; font-size: 14px; font-weight: bold; border: none;")
        
        val_layout = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(IconLibrary.get(icon_name).pixmap(24, 24))
        icon.setStyleSheet("border: none;")
        
        value = QLabel(value_text)
        value.setStyleSheet("font-size: 28px; font-weight: bold; color: #212529; border: none;")
        
        val_layout.addWidget(icon)
        val_layout.addWidget(value)
        val_layout.addStretch()
        
        l.addWidget(title)
        l.addLayout(val_layout)
        return card
    
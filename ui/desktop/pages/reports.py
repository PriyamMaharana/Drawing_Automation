from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QComboBox, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView)
from config.icon_library import IconLibrary
from PySide6.QtCore import QSize

class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Results & Reports Vault")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007BFF;")
        layout.addWidget(title)

        # Filters and Search
        filter_layout = QHBoxLayout()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by Drawing Number or Parameter...")
        self.search_bar.setStyleSheet("padding: 10px; font-size: 14px;")
        
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["All Dates", "Today", "Last 7 Days", "Last 30 Days"])
        self.combo_filter.setStyleSheet("padding: 10px; font-size: 14px;")
        
        filter_layout.addWidget(self.search_bar, stretch=3)
        filter_layout.addWidget(self.combo_filter, stretch=1)
        layout.addLayout(filter_layout)

        # Results Table
        self.table = QTableWidget(10, 6)
        self.table.setHorizontalHeaderLabels(["SL NO.", "Product Parameter", "Specification", "Tolerance", "Checking Method", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("QTableWidget { background-color: white; border: 1px solid #DEE2E6; border-radius: 6px; }")
        
        # Add Mock Data
        self.table.setItem(0, 0, QTableWidgetItem("1"))
        self.table.setItem(0, 1, QTableWidgetItem("Outer Diameter"))
        self.table.setItem(0, 2, QTableWidgetItem("Ø 30.5"))
        self.table.setItem(0, 3, QTableWidgetItem("±0.2"))
        self.table.setItem(0, 5, QTableWidgetItem("2026-06-22"))
        
        layout.addWidget(self.table)

        # Export Actions
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        btn_csv = QPushButton(" Export CSV")
        btn_csv.setIcon(IconLibrary.get("file-text"))
        
        btn_excel = QPushButton(" Export Excel")
        btn_excel.setIcon(IconLibrary.get("file-chart-column"))
        btn_excel.setStyleSheet("background-color: #28A745; color: white;")
        
        action_layout.addWidget(btn_csv)
        action_layout.addWidget(btn_excel)
        layout.addLayout(action_layout)
        
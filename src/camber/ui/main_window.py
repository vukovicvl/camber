"""Camber — main desktop window with dark monitoring theme."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTabWidget, QStatusBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor
from ..services.services import AssetService, SensorService, StatusService, ImportService, MeasurementService
from .theme import STYLESHEET, COLORS, STATUS_COLORS


def _icon_path():
    d = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(d, "..", "..", "..", "camber_icon.png"),
        os.path.join(d, "..", "..", "..", "camber_icon.ico"),
    ]:
        p = os.path.normpath(candidate)
        if os.path.exists(p):
            return p
    return None


class MainWindow(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.assets_svc = AssetService(engine)
        self.sensors_svc = SensorService(engine)
        self.status_svc = StatusService(engine)
        self.import_svc = ImportService(engine)
        self.measurement_svc = MeasurementService(engine)

        self.setWindowTitle("Camber")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        icon = _icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))

        self.setStyleSheet(STYLESHEET)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_dashboard_tab(), "  Dashboard")
        tabs.addTab(self._build_assets_tab(), "  Assets")
        tabs.addTab(self._build_status_tab(), "  Status")
        tabs.addTab(self._build_charts_tab(), "  Charts")
        tabs.addTab(self._build_map_tab(), "  Map")
        self.setCentralWidget(tabs)

        sb = QStatusBar()
        sb.showMessage("  Camber v0.1.0  |  API: 127.0.0.1:8765")
        self.setStatusBar(sb)

    def _build_dashboard_tab(self) -> QWidget:
        from .dashboard_panel import DashboardPanel
        return DashboardPanel(self.engine)

    def _build_assets_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("ASSET INVENTORY")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        top.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_assets)
        top.addWidget(btn_refresh)
        btn_import = QPushButton("Import CSV")
        btn_import.setObjectName("btnPrimary")
        btn_import.clicked.connect(self.import_csv)
        top.addWidget(btn_import)
        layout.addLayout(top)

        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(5)
        self.asset_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Latitude", "Longitude"])
        self.asset_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.verticalHeader().setVisible(False)
        layout.addWidget(self.asset_table)
        self.refresh_assets()
        return w

    def refresh_assets(self):
        assets = self.assets_svc.list_assets()
        self.asset_table.setRowCount(len(assets))
        for i, a in enumerate(assets):
            self.asset_table.setItem(i, 0, QTableWidgetItem(str(a["id"])))
            self.asset_table.setItem(i, 1, QTableWidgetItem(a["name"]))
            self.asset_table.setItem(i, 2, QTableWidgetItem(a["type"]))
            self.asset_table.setItem(i, 3, QTableWidgetItem(str(a.get("latitude", ""))))
            self.asset_table.setItem(i, 4, QTableWidgetItem(str(a.get("longitude", ""))))

    def _build_status_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("SENSOR STATUS")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        top.addStretch()
        btn = QPushButton("Evaluate Now")
        btn.setObjectName("btnPrimary")
        btn.clicked.connect(self.refresh_status)
        top.addWidget(btn)
        layout.addLayout(top)

        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["Sensor ID", "Asset ID", "Status"])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.status_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.status_table.verticalHeader().setVisible(False)
        layout.addWidget(self.status_table)
        self.refresh_status()
        return w

    def refresh_status(self):
        rows = self.status_svc.sensor_statuses()
        self.status_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.status_table.setItem(i, 0, QTableWidgetItem(str(r["sensor_id"])))
            self.status_table.setItem(i, 1, QTableWidgetItem(str(r["asset_id"])))
            item = QTableWidgetItem(r["status"].upper())
            color = QColor(STATUS_COLORS.get(r["status"], COLORS["unknown"]))
            item.setForeground(color)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self.status_table.setItem(i, 2, item)

    def _build_charts_tab(self) -> QWidget:
        try:
            from ..charts.chart_panel import ChartPanel
            return ChartPanel(self.engine)
        except ImportError:
            w = QWidget()
            lbl = QLabel("Chart panel requires pyqtgraph.\nInstall: pip install pyqtgraph")
            lbl.setObjectName("labelMuted")
            lbl.setAlignment(Qt.AlignCenter)
            QVBoxLayout(w).addWidget(lbl)
            return w

    def _build_map_tab(self) -> QWidget:
        try:
            from ..mapping.map_panel import MapPanel
            return MapPanel(self.engine)
        except ImportError:
            w = QWidget()
            lbl = QLabel("Map requires PySide6-Addons.\nInstall: pip install PySide6-Addons")
            lbl.setObjectName("labelMuted")
            lbl.setAlignment(Qt.AlignCenter)
            QVBoxLayout(w).addWidget(lbl)
            return w

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            n = self.import_svc.import_csv(path)
            QMessageBox.information(self, "Import Complete",
                                    f"Successfully imported {n} measurements.")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

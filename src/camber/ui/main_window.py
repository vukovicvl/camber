"""Camber — main desktop window with dark monitoring theme."""
from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTabWidget, QStatusBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QProgressDialog,
    QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor
from ..services.services import AssetService, SensorService, StatusService, ImportService, MeasurementService
from ..integrations import sensor_import
from .import_dialog import ImportPreviewDialog
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

        self.chart_panel = None  # set in _build_charts_tab when pyqtgraph is present

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_dashboard_tab(), "  Dashboard")
        tabs.addTab(self._build_assets_tab(), "  Assets")
        tabs.addTab(self._build_status_tab(), "  Status")
        tabs.addTab(self._build_charts_tab(), "  Charts")
        tabs.addTab(self._build_map_tab(), "  Map")
        # Reload the chart's sensor list whenever the Charts tab is opened, so
        # sensors created by an import (or via the ingest API) show up without
        # restarting the app.
        tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs = tabs
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
        btn_import.setToolTip("Import a tidy measurements CSV "
                              "(columns: sensor_id, timestamp, metric_type, value, unit) "
                              "into existing sensors.")
        btn_import.clicked.connect(self.import_csv)
        top.addWidget(btn_import)
        btn_sensor = QPushButton("Import sensor file…")
        btn_sensor.setObjectName("btnPrimary")
        btn_sensor.setToolTip("Import a raw sensor recording (wide multi-channel or tidy CSV). "
                              "Auto-detects the layout and creates the asset and sensors.")
        btn_sensor.clicked.connect(self.import_sensor_file)
        top.addWidget(btn_sensor)
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
            import pyqtgraph  # noqa: F401  — probe the optional dep, not the panel module
        except ImportError:
            return self._placeholder_tab("Chart panel requires pyqtgraph.\nInstall: pip install pyqtgraph")
        try:
            from ..charts.chart_panel import ChartPanel
            self.chart_panel = ChartPanel(self.engine)
            return self.chart_panel
        except Exception as e:
            return self._placeholder_tab(f"Chart panel failed to load:\n{type(e).__name__}: {e}")

    def _on_tab_changed(self, index: int):
        if self.chart_panel is not None and self.tabs.tabText(index).strip() == "Charts":
            self.chart_panel.reload_sensors()

    def _build_map_tab(self) -> QWidget:
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401  — probe the optional dep
        except ImportError:
            return self._placeholder_tab("Map requires PySide6-Addons.\nInstall: pip install PySide6-Addons")
        try:
            from ..mapping.map_panel import MapPanel
            return MapPanel(self.engine)
        except Exception as e:
            return self._placeholder_tab(f"Map failed to load:\n{type(e).__name__}: {e}")

    def _placeholder_tab(self, message: str) -> QWidget:
        w = QWidget()
        lbl = QLabel(message)
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
            hint = ""
            # A KeyError here means a required tidy column (e.g. 'sensor_id') is
            # absent -- typically because this is a raw sensor recording, not a
            # tidy measurements CSV. Point the user at the right button.
            if isinstance(e, KeyError) or "column" in str(e).lower():
                hint = ("\n\nThis looks like a raw sensor recording rather than a tidy "
                        "measurements CSV. Use “Import sensor file…”, which auto-detects "
                        "the layout (including multi-channel exports) and creates the "
                        "asset and sensors for you.")
            QMessageBox.critical(self, "Import Failed", f"{e}{hint}")

    def import_sensor_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select sensor recording", "",
            "CSV Files (*.csv);;All Files (*)")
        if not path:
            return

        try:
            preview = sensor_import.inspect(path)
        except Exception as e:
            QMessageBox.critical(self, "Cannot read file", f"{type(e).__name__}: {e}")
            return

        dlg = ImportPreviewDialog(preview, self.assets_svc.list_assets(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        target_asset_id, new_asset_name = dlg.selected_target()

        progress = QProgressDialog("Importing measurements…", "", 0, 0, self)
        progress.setWindowTitle("Importing")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        def on_progress(n: int):
            progress.setLabelText(f"Importing measurements… {n:,} so far")
            QApplication.processEvents()

        try:
            res = sensor_import.import_file(
                self.engine, path, profile=preview.profile_name,
                target_asset_id=target_asset_id, new_asset_name=new_asset_name,
                progress=on_progress)
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Import Failed", f"{type(e).__name__}: {e}")
            return

        progress.close()
        self.refresh_assets()
        if self.chart_panel is not None:
            self.chart_panel.reload_sensors()  # surface the new sensors in Charts
        QMessageBox.information(
            self, "Import Complete",
            f"Imported {res.measurements_imported:,} measurements into "
            f"“{res.asset_name}” across {res.sensors_created} sensor(s).")

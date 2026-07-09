"""Dashboard overview panel — landing screen showing asset health at a glance."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame,
    QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from sqlalchemy import select, func
from ..storage.db import session, AssetRow, SensorRow, MeasurementRow, ThresholdRow
from ..services.services import StatusService
from .theme import COLORS, STATUS_COLORS


class StatusDot(QWidget):
    """Tiny colored circle indicating status."""
    def __init__(self, status: str = "unknown", size: int = 12, parent=None):
        super().__init__(parent)
        self.status = status
        self._size = size
        self.setFixedSize(size + 4, size + 4)

    def set_status(self, status: str):
        self.status = status
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(STATUS_COLORS.get(self.status, COLORS["unknown"]))
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, self._size, self._size)
        # Glow
        color.setAlpha(50)
        p.setBrush(color)
        p.drawEllipse(0, 0, self._size + 4, self._size + 4)
        p.end()


class MetricCard(QFrame):
    """Big number card for the dashboard grid."""
    def __init__(self, title: str, value: str, subtitle: str = "",
                 accent: str = COLORS["accent"], parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            MetricCard {{
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; "
                                f"font-weight: bold; text-transform: uppercase; letter-spacing: 1px;")
        layout.addWidget(lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"color: {accent}; font-size: 32px; font-weight: bold;")
        layout.addWidget(self.lbl_value)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.lbl_sub)

    def set_value(self, value: str, subtitle: str = "", accent: str = None):
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)
        if accent:
            self.lbl_value.setStyleSheet(f"color: {accent}; font-size: 32px; font-weight: bold;")


class AssetStatusRow(QFrame):
    """Single row in the asset status list."""
    def __init__(self, name: str, type_: str, status: str, sensor_count: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            AssetStatusRow {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 10px 14px;
                margin-bottom: 4px;
            }}
            AssetStatusRow:hover {{
                background: {COLORS['bg_card']};
                border-color: {COLORS['border_light']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        dot = StatusDot(status, 10)
        layout.addWidget(dot)

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_name, 2)

        lbl_type = QLabel(type_)
        lbl_type.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(lbl_type, 1)

        lbl_sensors = QLabel(f"{sensor_count} sensors")
        lbl_sensors.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(lbl_sensors, 1)

        lbl_status = QLabel(status.upper())
        sc = STATUS_COLORS.get(status, COLORS["unknown"])
        lbl_status.setStyleSheet(f"color: {sc}; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        lbl_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(lbl_status, 1)


class DashboardPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.status_svc = StatusService(engine)
        self._build_ui()
        self.refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(15000)

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(16)
        main.setContentsMargins(24, 20, 24, 20)

        # Header
        header = QHBoxLayout()
        title = QLabel("SYSTEM OVERVIEW")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 20px; "
                            f"font-weight: bold; letter-spacing: 2px;")
        header.addWidget(title)
        header.addStretch()
        self.lbl_time = QLabel("")
        self.lbl_time.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        header.addWidget(self.lbl_time)
        main.addLayout(header)

        # Metric cards row
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(12)
        self.card_assets = MetricCard("Total Assets", "—")
        self.card_sensors = MetricCard("Sensors", "—")
        self.card_ok = MetricCard("Healthy", "—", accent=COLORS["ok"])
        self.card_warn = MetricCard("Warnings", "—", accent=COLORS["warning"])
        self.card_crit = MetricCard("Critical", "—", accent=COLORS["critical"])
        for c in [self.card_assets, self.card_sensors, self.card_ok, self.card_warn, self.card_crit]:
            self.cards_layout.addWidget(c)
        main.addLayout(self.cards_layout)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {COLORS['border']};")
        main.addWidget(div)

        # Asset list header
        list_header = QLabel("ASSET STATUS")
        list_header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; "
                                  f"font-weight: bold; letter-spacing: 1px; padding-top: 4px;")
        main.addWidget(list_header)

        # Scrollable asset rows — a QScrollArea so many assets stay reachable
        # instead of being squeezed/clipped by a bare layout.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        self.asset_list_layout = QVBoxLayout(container)
        self.asset_list_layout.setContentsMargins(0, 0, 0, 0)
        self.asset_list_layout.setSpacing(4)
        scroll.setWidget(container)
        main.addWidget(scroll, 1)

    def refresh(self):
        from datetime import datetime
        self.lbl_time.setText(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

        with session(self.engine) as s:
            assets = s.execute(select(AssetRow)).scalars().all()
            sensor_count = s.execute(select(func.count(SensorRow.id))).scalar() or 0
            asset_data = []
            for a in assets:
                sc = s.execute(select(func.count(SensorRow.id)).where(
                    SensorRow.asset_id == a.id)).scalar() or 0
                asset_data.append({"id": a.id, "name": a.name, "type": a.type, "sensors": sc})

        statuses = {r["asset_id"]: r["status"] for r in self.status_svc.asset_statuses()}
        for a in asset_data:
            a["status"] = statuses.get(a["id"], "unknown")

        n_ok = sum(1 for a in asset_data if a["status"] == "ok")
        n_warn = sum(1 for a in asset_data if a["status"] == "warning")
        n_crit = sum(1 for a in asset_data if a["status"] == "critical")

        self.card_assets.set_value(str(len(asset_data)))
        self.card_sensors.set_value(str(sensor_count))
        self.card_ok.set_value(str(n_ok), accent=COLORS["ok"])
        self.card_warn.set_value(str(n_warn), accent=COLORS["warning"])
        self.card_crit.set_value(str(n_crit), accent=COLORS["critical"])

        # Rebuild asset rows (clear old rows + any trailing stretch)
        while self.asset_list_layout.count():
            item = self.asset_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for a in asset_data:
            row = AssetStatusRow(a["name"], a["type"], a["status"], a["sensors"])
            self.asset_list_layout.addWidget(row)
        self.asset_list_layout.addStretch()  # keep rows top-aligned in the scroll area

"""Time-series chart panel — dark theme, threshold bands, status coloring."""
from __future__ import annotations
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
from sqlalchemy import select
from ..storage.db import session, SensorRow, MeasurementRow, ThresholdRow
from .theme import COLORS


class ChartPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("TIME-SERIES")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("Sensor:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.setMinimumWidth(250)
        self.sensor_combo.currentIndexChanged.connect(self.refresh_plot)
        top.addWidget(self.sensor_combo)
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh_plot)
        top.addWidget(btn)
        layout.addLayout(top)

        pg.setConfigOptions(antialias=True,
                            background=COLORS["bg_primary"],
                            foreground=COLORS["text_secondary"])
        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("bottom", "Time")
        self.plot.setLabel("left", "Value")
        self.plot.getAxis("bottom").setPen(pg.mkPen(COLORS["border"], width=1))
        self.plot.getAxis("left").setPen(pg.mkPen(COLORS["border"], width=1))
        layout.addWidget(self.plot)

        self.reload_sensors()

    def reload_sensors(self):
        self.sensor_combo.clear()
        with session(self.engine) as s:
            for r in s.execute(select(SensorRow)).scalars().all():
                label = f"#{r.id}  {r.sensor_type}  ({r.serial_number})"
                self.sensor_combo.addItem(label, r.id)

    def refresh_plot(self):
        sensor_id = self.sensor_combo.currentData()
        if sensor_id is None:
            return
        self.plot.clear()

        with session(self.engine) as s:
            rows = s.execute(
                select(MeasurementRow)
                .where(MeasurementRow.sensor_id == sensor_id)
                .order_by(MeasurementRow.timestamp.asc())
            ).scalars().all()
            if not rows:
                return

            xs = [r.timestamp.timestamp() for r in rows]
            ys = [r.value for r in rows]
            metric = rows[0].metric_type
            unit = rows[0].unit

            rule = s.execute(
                select(ThresholdRow).where(ThresholdRow.metric_type == metric)
            ).scalar_one_or_none()

        if rule:
            warn = pg.InfiniteLine(pos=rule.warning_value, angle=0,
                                    pen=pg.mkPen(COLORS["warning"], width=1, style=2))
            crit = pg.InfiniteLine(pos=rule.critical_value, angle=0,
                                    pen=pg.mkPen(COLORS["critical"], width=1, style=2))
            self.plot.addItem(warn)
            self.plot.addItem(crit)

            # Shaded bands
            if xs:
                x_min, x_max = min(xs), max(xs)
                warn_fill = pg.LinearRegionItem(
                    values=(rule.warning_value, rule.critical_value),
                    orientation="horizontal", movable=False,
                    brush=pg.mkBrush(241, 196, 15, 20))
                warn_fill.setZValue(-10)
                self.plot.addItem(warn_fill)

                crit_fill = pg.LinearRegionItem(
                    values=(rule.critical_value, rule.critical_value * 1.5),
                    orientation="horizontal", movable=False,
                    brush=pg.mkBrush(231, 76, 60, 20))
                crit_fill.setZValue(-10)
                self.plot.addItem(crit_fill)

        brushes = []
        for v in ys:
            if rule and v >= rule.critical_value:
                brushes.append(pg.mkBrush(COLORS["critical"]))
            elif rule and v >= rule.warning_value:
                brushes.append(pg.mkBrush(COLORS["warning"]))
            else:
                brushes.append(pg.mkBrush(COLORS["ok"]))

        self.plot.plot(xs, ys, pen=pg.mkPen(COLORS["accent"], width=1.5),
                       symbol="o", symbolSize=5, symbolBrush=brushes,
                       symbolPen=pg.mkPen(None))
        self.plot.setLabel("left", f"{metric} ({unit})")

        axis = pg.DateAxisItem(orientation="bottom")
        self.plot.setAxisItems({"bottom": axis})

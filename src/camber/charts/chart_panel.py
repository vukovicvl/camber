"""Time-series chart panel — dark theme, threshold bands, status coloring.

Two modes:
  * Manual  — plot a sensor's stored history; refresh on demand.
  * Live    — a timer re-queries on an interval and follows the latest window,
              so readings arriving from the ingest API (POST /measurements) or a
              real sensor gateway appear as they land. The "Demo feed" toggle
              synthesises readings for the selected sensor so Live mode can be
              seen and tested without hardware.
"""
from __future__ import annotations
import math
import random
import time
from datetime import datetime

import pyqtgraph as pg
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton, QCheckBox,
)
from sqlalchemy import select
from ..storage.db import session, SensorRow, MeasurementRow, ThresholdRow
from ..services.services import MeasurementService
from ..ui.theme import COLORS

LIVE_INTERVAL_MS = 1000       # how often the live view re-queries
LIVE_WINDOW_POINTS = 3000     # cap points loaded in live mode (keeps it fast)
LIVE_FOLLOW_SECONDS = 60      # x-axis window that follows the latest reading
DEMO_INTERVAL_MS = 400        # how often the demo feed emits a synthetic reading


class ChartPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.meas_svc = MeasurementService(engine)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("TIME-SERIES")
        title.setObjectName("labelHeader")
        top.addWidget(title)
        self.live_badge = QLabel("")
        self.live_badge.setStyleSheet("color: #2ecc71; font-weight: bold;")
        top.addWidget(self.live_badge)
        top.addStretch()

        top.addWidget(QLabel("Sensor:"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.setMinimumWidth(250)
        self.sensor_combo.currentIndexChanged.connect(self._on_sensor_changed)
        top.addWidget(self.sensor_combo)

        self.live_check = QCheckBox("Live")
        self.live_check.setToolTip("Auto-refresh and follow the latest readings "
                                   "as they arrive (from the ingest API or a gateway).")
        self.live_check.toggled.connect(self._toggle_live)
        top.addWidget(self.live_check)

        self.demo_btn = QPushButton("Demo feed")
        self.demo_btn.setCheckable(True)
        self.demo_btn.setToolTip("Emit synthetic readings for the selected sensor "
                                 "so Live mode can be seen without real hardware.")
        self.demo_btn.toggled.connect(self._toggle_demo)
        top.addWidget(self.demo_btn)

        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh_plot)
        top.addWidget(btn)
        layout.addLayout(top)

        pg.setConfigOptions(antialias=True,
                            background=COLORS["bg_primary"],
                            foreground=COLORS["text_secondary"])
        self.plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem(orientation="bottom")})
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel("bottom", "Time")
        self.plot.setLabel("left", "Value")
        self.plot.getAxis("bottom").setPen(pg.mkPen(COLORS["border"], width=1))
        self.plot.getAxis("left").setPen(pg.mkPen(COLORS["border"], width=1))
        # NOTE: clip-to-view / downsampling are toggled per-plot in refresh_plot,
        # not enabled globally here — they must stay OFF when per-point symbol
        # brushes are used (pyqtgraph does not clip the brush list with the data,
        # which raises "Number of brushes does not match number of points").
        layout.addWidget(self.plot)

        # Timers: one drives the live re-query, one drives the demo feed.
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(LIVE_INTERVAL_MS)
        self.live_timer.timeout.connect(lambda: self.refresh_plot(live=True))
        self.demo_timer = QTimer(self)
        self.demo_timer.setInterval(DEMO_INTERVAL_MS)
        self.demo_timer.timeout.connect(self._emit_demo_reading)

        self.reload_sensors()

    # ---- sensor list ----------------------------------------------------- #
    def reload_sensors(self):
        """Repopulate the sensor list from the DB, preserving the current
        selection. Called on startup, after an import, and when the Charts tab
        is opened, so newly-created sensors appear without a restart."""
        current = self.sensor_combo.currentData()
        self.sensor_combo.blockSignals(True)
        self.sensor_combo.clear()
        with session(self.engine) as s:
            for r in s.execute(select(SensorRow).order_by(SensorRow.id)).scalars().all():
                label = f"#{r.id}  {r.sensor_type}  ({r.serial_number})"
                self.sensor_combo.addItem(label, r.id)
        if current is not None:
            idx = self.sensor_combo.findData(current)
            if idx >= 0:
                self.sensor_combo.setCurrentIndex(idx)
        self.sensor_combo.blockSignals(False)
        self.refresh_plot(live=self.live_check.isChecked())

    # ---- live / demo toggles --------------------------------------------- #
    def _on_sensor_changed(self, *args):
        # Honour Live when the sensor is switched from the combo: otherwise the
        # combo's signal calls refresh_plot with live=False, loading the whole
        # unbounded history (the cost LIVE_WINDOW_POINTS exists to avoid) before
        # the timer snaps back to the follow window.
        self.refresh_plot(live=self.live_check.isChecked())

    def _toggle_live(self, on: bool):
        self.live_badge.setText("● LIVE" if on else "")
        if on:
            self.live_timer.start()
            self.refresh_plot(live=True)
        else:
            self.live_timer.stop()
            # A demo feed is meaningless without Live and would otherwise keep
            # writing synthetic rows into real data — stop it too.
            if self.demo_btn.isChecked():
                self.demo_btn.setChecked(False)

    def _toggle_demo(self, on: bool):
        if on:
            self.demo_timer.start()
            if not self.live_check.isChecked():
                self.live_check.setChecked(True)  # a feed is pointless unless live
        else:
            self.demo_timer.stop()

    def _emit_demo_reading(self):
        """Append one synthetic reading for the selected sensor: a slow sine
        around the sensor's current value plus a little noise."""
        sensor_id = self.sensor_combo.currentData()
        if sensor_id is None:
            return
        latest = self.meas_svc.latest(sensor_id)
        if latest is not None:
            base, metric, unit = latest["value"], latest["metric_type"], latest["unit"]
        else:
            with session(self.engine) as s:
                sr = s.get(SensorRow, sensor_id)
            base, metric, unit = 0.0, (sr.sensor_type if sr else "demo"), ""
        amp = max(abs(base) * 0.05, 0.5)
        value = base + amp * math.sin(time.time() * 1.5) + random.uniform(-0.3, 0.3) * amp
        try:
            self.meas_svc.append(sensor_id, value, metric, unit, datetime.utcnow())
        except Exception:
            # A transient DB error (e.g. lock contention during a large import)
            # must not crash the timer slot; just skip this tick.
            pass

    # ---- pause background work when this tab isn't visible ---------------- #
    def hideEvent(self, event):
        self.live_timer.stop()
        self.demo_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self.live_check.isChecked():
            self.live_timer.start()
        if self.demo_btn.isChecked():
            self.demo_timer.start()

    # ---- plotting -------------------------------------------------------- #
    def _load_points(self, sensor_id: int, live: bool):
        with session(self.engine) as s:
            # Select just the columns we plot (not full ORM rows) — a full
            # recording is tens of thousands of points and building ORM objects
            # for each is the main cost of switching/selecting.
            q = select(MeasurementRow.timestamp, MeasurementRow.value,
                       MeasurementRow.metric_type, MeasurementRow.unit
                       ).where(MeasurementRow.sensor_id == sensor_id)
            if live:
                rows = list(reversed(s.execute(
                    q.order_by(MeasurementRow.timestamp.desc()).limit(LIVE_WINDOW_POINTS)
                ).all()))
            else:
                rows = s.execute(q.order_by(MeasurementRow.timestamp.asc())).all()
            if not rows:
                return None
            # datetime.timestamp() calls the platform mktime, which on Windows
            # raises OSError for out-of-range dates (pre-1970 / epoch-zero in a
            # positive-UTC zone / far future). Skip such rows rather than letting
            # the exception escape into the Qt slot and crash the tab.
            xs, ys = [], []
            for r in rows:
                try:
                    t = r[0].timestamp()
                except (OSError, OverflowError, ValueError):
                    continue
                xs.append(t)
                ys.append(r[1])
            if not xs:
                return None
            metric, unit = rows[0][2], rows[0][3]
            rule = s.execute(
                select(ThresholdRow).where(ThresholdRow.metric_type == metric)
            ).scalar_one_or_none()
        return xs, ys, metric, unit, rule

    def refresh_plot(self, *args, live: bool = False):
        sensor_id = self.sensor_combo.currentData()
        if sensor_id is None:
            return
        self.plot.clear()
        loaded = self._load_points(sensor_id, live)
        if loaded is None:
            return
        xs, ys, metric, unit, rule = loaded

        if rule:
            dash = Qt.PenStyle.DashLine  # PySide6 enums no longer accept a bare int
            self.plot.addItem(pg.InfiniteLine(pos=rule.warning_value, angle=0,
                              pen=pg.mkPen(COLORS["warning"], width=1, style=dash)))
            self.plot.addItem(pg.InfiniteLine(pos=rule.critical_value, angle=0,
                              pen=pg.mkPen(COLORS["critical"], width=1, style=dash)))
            warn_fill = pg.LinearRegionItem(values=(rule.warning_value, rule.critical_value),
                                            orientation="horizontal", movable=False,
                                            brush=pg.mkBrush(241, 196, 15, 20))
            warn_fill.setZValue(-10)
            self.plot.addItem(warn_fill)
            # Critical zone spans from the critical line up to the data's peak
            # (thresholds are upper-bound: higher is worse). The old critical*1.5
            # was wrong for large values (band ended below the data) and for
            # negative thresholds.
            crit_top = max(rule.critical_value, max(ys)) if ys else rule.critical_value
            crit_fill = pg.LinearRegionItem(values=(rule.critical_value, crit_top),
                                            orientation="horizontal", movable=False,
                                            brush=pg.mkBrush(231, 76, 60, 20))
            crit_fill.setZValue(-10)
            self.plot.addItem(crit_fill)

        # Per-point coloured symbols are useful but slow; a full recording can be
        # tens of thousands of points. Above a threshold, draw a plain fast line
        # with clip-to-view + downsampling. Below it, draw coloured symbols — but
        # with clip/downsample OFF, since a per-point brush list is incompatible
        # with clip-to-view (the brushes are not clipped alongside the points).
        SYMBOL_LIMIT = 4000
        big = len(xs) > SYMBOL_LIMIT
        self.plot.setClipToView(big)
        self.plot.setDownsampling(mode="peak", auto=big)
        if not big:
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
        else:
            self.plot.plot(xs, ys, pen=pg.mkPen(COLORS["accent"], width=1.5))
        self.plot.setLabel("left", f"{metric} ({unit})")

        if live and xs:
            # follow the latest reading
            x_max = xs[-1]
            self.plot.setXRange(x_max - LIVE_FOLLOW_SECONDS, x_max, padding=0)

"""Regression: per-point symbol brushes + clip-to-view must not raise
"Number of brushes does not match number of points" when the view range
changes (live-follow / zoom). See charts/chart_panel.py refresh_plot.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtWidgets import QApplication  # noqa: E402
from camber.storage.db import init_db, session, AssetRow, SensorRow, MeasurementRow  # noqa: E402
from camber.charts.chart_panel import ChartPanel  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_symbols_survive_viewrange_change(app, tmp_path):
    engine = init_db(str(tmp_path / "camber.db"))
    with session(engine) as s:
        a = AssetRow(name="Clip", type="bridge"); s.add(a); s.flush()
        sensor = SensorRow(asset_id=a.id, sensor_type="accelerometer", serial_number="A1")
        s.add(sensor); s.flush(); sid = sensor.id
        base = datetime(2023, 2, 20, 3, 10, 0)
        # ~400 points over 400 s -> a 60 s window clips the visible count, which
        # used to mismatch the (unclipped) per-point brush list.
        s.execute(MeasurementRow.__table__.insert(), [
            {"sensor_id": sid, "timestamp": base + timedelta(seconds=i),
             "metric_type": "acceleration", "value": 0.5 + (i % 5) * 0.1, "unit": "m/s2"}
            for i in range(400)])
        s.commit()

    panel = ChartPanel(engine)
    panel.sensor_combo.setCurrentIndex(panel.sensor_combo.findData(sid))

    errors = []
    prev_hook = sys.excepthook
    sys.excepthook = lambda *a: errors.append(a[1])
    try:
        panel.refresh_plot(live=True)          # symbols + follow x-range
        panel.plot.setXRange(390, 400, padding=0)
        for _ in range(5):
            app.processEvents()
        panel.refresh_plot()
        panel.plot.setXRange(100, 130, padding=0)
        for _ in range(5):
            app.processEvents()
    finally:
        sys.excepthook = prev_hook
        engine.dispose()

    assert not errors, f"chart raised on view-range change: {errors[:1]}"

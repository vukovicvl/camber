"""Regression: out-of-range timestamps must not crash Charts or Analysis.

datetime.timestamp() calls the platform mktime, which on Windows raises OSError
for pre-1970 dates, epoch-zero in a positive-UTC zone, and far-future years. Such
a row is easily entered via a tidy CSV or the ingest API; the load paths now skip
un-representable timestamps instead of letting the exception crash the tab.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")
pytest.importorskip("numpy")

from PySide6.QtWidgets import QApplication
from camber.storage.db import init_db, session, AssetRow, SensorRow, MeasurementRow
from camber.charts.chart_panel import ChartPanel
from camber.charts.analysis_panel import AnalysisPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _make_sensor(engine, serial, t0):
    with session(engine) as s:
        a = AssetRow(name="TS", type="bridge"); s.add(a); s.flush()
        sr = SensorRow(asset_id=a.id, sensor_type="strain_gauge", serial_number=serial)
        s.add(sr); s.flush()
        s.execute(MeasurementRow.__table__.insert(), [
            {"sensor_id": sr.id, "timestamp": t0 + timedelta(seconds=i),
             "metric_type": "strain", "value": float(i % 50), "unit": "u"} for i in range(200)])
        s.commit()
        return sr.id


@pytest.mark.parametrize("t0", [datetime(1969, 1, 1), datetime(1970, 1, 1, 0, 0, 0), datetime(9999, 1, 1)])
def test_bad_timestamps_do_not_crash(app, tmp_path, t0):
    engine = init_db(str(tmp_path / f"c{t0.year}.db"))
    sid = _make_sensor(engine, f"S{t0.year}", t0)
    try:
        # Construction alone drives reload_sensors -> refresh_plot / analyse on the
        # only (bad-timestamp) sensor — the "tab becomes placeholder" path.
        cp = ChartPanel(engine)
        cp.sensor_combo.setCurrentIndex(cp.sensor_combo.findData(sid))
        cp.refresh_plot()
        cp.refresh_plot(live=True)
        ap = AnalysisPanel(engine)
        ap.sensor_combo.setCurrentIndex(ap.sensor_combo.findData(sid))
        ap.analyse()
    finally:
        engine.dispose()

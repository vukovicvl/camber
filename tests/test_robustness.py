"""Robustness fixes found by the drive-every-widget verification pass:
non-finite handling, import validation, sensor reuse, zero-data rejection,
and sampling-rate estimation from coarse timestamps.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from camber.domain.models import ThresholdRule, Status
from camber.storage.db import init_db, session, AssetRow, SensorRow
from camber.services.services import MeasurementService, ImportService

SAMPLE = Path(__file__).resolve().parents[1] / "src" / "camber" / "resources" / "sample" / "vanersborg_sample.csv"


def _sensor(engine, serial="S1"):
    with session(engine) as s:
        a = AssetRow(name="A", type="bridge"); s.add(a); s.flush()
        sr = SensorRow(asset_id=a.id, sensor_type="sg", serial_number=serial)
        s.add(sr); s.flush()
        sid = sr.id
        s.commit()
    return sid


# ---- domain: non-finite is not "healthy" ---------------------------------- #
def test_evaluate_nonfinite_is_unknown():
    r = ThresholdRule(1, "strain", 10.0, 20.0, "u")
    assert r.evaluate(float("nan")) is Status.UNKNOWN
    assert r.evaluate(float("inf")) is Status.UNKNOWN
    assert r.evaluate(-float("inf")) is Status.UNKNOWN
    assert r.evaluate(25) is Status.CRITICAL
    assert r.evaluate(15) is Status.WARNING
    assert r.evaluate(5) is Status.OK


# ---- append: drop non-finite (would violate NOT NULL) --------------------- #
def test_append_rejects_nonfinite(tmp_path):
    engine = init_db(str(tmp_path / "a.db"))
    sid = _sensor(engine)
    svc = MeasurementService(engine)
    try:
        assert svc.append(sid, float("nan"), "strain", "u") is None
        assert svc.append(sid, float("inf"), "strain", "u") is None
        assert svc.append(sid, 1.5, "strain", "u") is not None
    finally:
        engine.dispose()


# ---- tidy import: validate + skip bad/orphan rows ------------------------- #
def test_import_csv_validation_and_skipping(tmp_path):
    engine = init_db(str(tmp_path / "b.db"))
    sid = _sensor(engine)
    svc = ImportService(engine)
    try:
        empty = tmp_path / "empty.csv"; empty.write_text("")
        with pytest.raises(ValueError):
            svc.import_csv(str(empty))

        header_only = tmp_path / "hdr.csv"
        header_only.write_text("sensor_id,timestamp,metric_type,value,unit\n")
        with pytest.raises(ValueError):
            svc.import_csv(str(header_only))

        bad_cols = tmp_path / "cols.csv"; bad_cols.write_text("a,b\n1,2\n")
        with pytest.raises(KeyError):
            svc.import_csv(str(bad_cols))

        mixed = tmp_path / "mix.csv"
        mixed.write_text(
            "sensor_id,timestamp,metric_type,value,unit\n"
            f"{sid},2023-01-01T00:00:00,strain,1.0,u\n"      # valid
            "99999,2023-01-01T00:00:01,strain,2.0,u\n"        # orphan sensor_id -> skip
            f"{sid},2023-01-01T00:00:02,strain,nan,u\n")      # non-finite -> skip
        assert svc.import_csv(str(mixed)) == 1
    finally:
        engine.dispose()


# ---- sensor-file import: reuse on re-import, reject zero-data -------------- #
@pytest.mark.skipif(not SAMPLE.exists(), reason="bundled sample missing")
def test_import_file_reuses_sensors_on_reimport(tmp_path):
    import camber.integrations.sensor_import as si
    engine = init_db(str(tmp_path / "c.db"))
    try:
        r1 = si.import_file(engine, str(SAMPLE), new_asset_name="Bridge")
        assert r1.sensors_created > 0 and r1.measurements_imported > 0
        with session(engine) as s:
            n_before = len(s.execute(
                SensorRow.__table__.select().where(SensorRow.asset_id == r1.asset_id)).all())
        r2 = si.import_file(engine, str(SAMPLE), target_asset_id=r1.asset_id)
        assert r2.sensors_created == 0  # all reused by serial
        with session(engine) as s:
            n_after = len(s.execute(
                SensorRow.__table__.select().where(SensorRow.asset_id == r1.asset_id)).all())
        assert n_after == n_before  # no duplicates
    finally:
        engine.dispose()


@pytest.mark.skipif(not SAMPLE.exists(), reason="bundled sample missing")
def test_import_file_rejects_all_sentinel(tmp_path):
    import camber.integrations.sensor_import as si
    header = SAMPLE.read_text().splitlines()[0]
    cols = header.split(",")
    row = []
    for c in cols:
        if c == "ts":
            row.append("2023-02-20T03:10:53.000000")
        elif c.startswith("ch_"):
            row.append("-1000000.0")   # the dataset's no-data sentinel
        else:
            row.append("0")
    sentinel = tmp_path / "sentinel.csv"
    sentinel.write_text(header + "\n" + ",".join(row) + "\n" + ",".join(row) + "\n")
    engine = init_db(str(tmp_path / "d.db"))
    try:
        with pytest.raises(ValueError):        # no readings parsed -> raise, no phantom sensors
            si.import_file(engine, str(sentinel), new_asset_name="Empty")
        with session(engine) as s:
            assert s.execute(AssetRow.__table__.select()).first() is None  # rolled back
    finally:
        engine.dispose()


# ---- analysis: sampling rate from coarse (quantised) timestamps ----------- #
def test_estimate_fs_from_coarse_timestamps():
    pytest.importorskip("numpy"); pytest.importorskip("pyqtgraph")
    import numpy as np
    from camber.charts.analysis_panel import AnalysisPanel
    # 200 samples over 50 s but timestamps quantised to whole seconds (4 per second)
    ts = np.array([float(i // 4) for i in range(200)])
    fs = AnalysisPanel._estimate_fs(ts)
    assert fs is not None and 3.5 < fs < 4.5  # ~4 Hz recovered from the overall span

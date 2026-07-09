"""Application services - operations used by UI and the local API."""
from __future__ import annotations
import csv
import math
from datetime import datetime
from typing import Iterable
from sqlalchemy import select, delete
from ..storage.db import session, AssetRow, SensorRow, MeasurementRow, ThresholdRow
from ..domain.models import Status, ThresholdRule


class AssetService:
    def __init__(self, engine):
        self.engine = engine

    def list_assets(self) -> list[dict]:
        with session(self.engine) as s:
            rows = s.execute(select(AssetRow)).scalars().all()
            return [
                {"id": r.id, "name": r.name, "type": r.type,
                 "latitude": r.latitude, "longitude": r.longitude}
                for r in rows
            ]

    def create_asset(self, name: str, type_: str,
                     latitude: float | None = None,
                     longitude: float | None = None) -> int:
        with session(self.engine) as s:
            row = AssetRow(name=name, type=type_, latitude=latitude, longitude=longitude)
            s.add(row); s.commit(); s.refresh(row)
            return row.id

    def rename_asset(self, asset_id: int, name: str) -> bool:
        with session(self.engine) as s:
            row = s.get(AssetRow, asset_id)
            if row is None:
                return False
            row.name = name
            s.commit()
            return True

    def delete_asset(self, asset_id: int) -> bool:
        """Delete an asset and everything under it. Uses bulk Core deletes rather
        than ORM cascade so removing an asset with millions of measurements is
        fast and doesn't materialise them all."""
        with session(self.engine) as s:
            if s.get(AssetRow, asset_id) is None:
                return False
            sensor_ids = [sid for (sid,) in s.execute(
                select(SensorRow.id).where(SensorRow.asset_id == asset_id)).all()]
            if sensor_ids:
                s.execute(delete(MeasurementRow).where(MeasurementRow.sensor_id.in_(sensor_ids)))
                s.execute(delete(SensorRow).where(SensorRow.asset_id == asset_id))
            s.execute(delete(AssetRow).where(AssetRow.id == asset_id))
            s.commit()
            return True


class SensorService:
    def __init__(self, engine):
        self.engine = engine

    def list_for_asset(self, asset_id: int) -> list[dict]:
        with session(self.engine) as s:
            rows = s.execute(select(SensorRow).where(SensorRow.asset_id == asset_id)).scalars().all()
            return [{"id": r.id, "asset_id": r.asset_id, "sensor_type": r.sensor_type,
                     "serial_number": r.serial_number, "axis": r.axis} for r in rows]


class MeasurementService:
    def __init__(self, engine):
        self.engine = engine

    def for_sensor(self, sensor_id: int, limit: int = 1000) -> list[dict]:
        with session(self.engine) as s:
            rows = s.execute(
                select(MeasurementRow)
                .where(MeasurementRow.sensor_id == sensor_id)
                .order_by(MeasurementRow.timestamp.desc())
                .limit(limit)
            ).scalars().all()
            return [{"timestamp": r.timestamp.isoformat(), "metric_type": r.metric_type,
                     "value": r.value, "unit": r.unit} for r in rows]

    def latest(self, sensor_id: int) -> dict | None:
        """Most recent reading for a sensor, or None. Used by live charts to
        continue naturally from wherever the sensor currently is."""
        with session(self.engine) as s:
            r = s.execute(
                select(MeasurementRow)
                .where(MeasurementRow.sensor_id == sensor_id)
                .order_by(MeasurementRow.timestamp.desc())
                .limit(1)
            ).scalar_one_or_none()
            if r is None:
                return None
            return {"timestamp": r.timestamp, "metric_type": r.metric_type,
                    "value": r.value, "unit": r.unit}

    def append(self, sensor_id: int, value: float, metric_type: str, unit: str,
               timestamp: datetime | None = None) -> int | None:
        """Append one reading (the live-ingest path). Returns the new row id, or
        None if the value is non-finite. SQLite stores a float NaN as NULL, which
        violates the NOT NULL value column and would abort the insert; a NaN/inf
        reading is also meaningless, so it is dropped rather than raised (the demo
        feed and API both call this)."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(v):
            return None
        with session(self.engine) as s:
            row = MeasurementRow(
                sensor_id=sensor_id,
                timestamp=timestamp or datetime.utcnow(),
                metric_type=metric_type, value=v, unit=unit,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id


class ImportService:
    """CSV import. Expected columns: sensor_id,timestamp,metric_type,value,unit"""
    def __init__(self, engine):
        self.engine = engine

    REQUIRED = ("sensor_id", "timestamp", "metric_type", "value", "unit")

    def import_csv(self, path: str) -> int:
        """Import a tidy measurements CSV into existing sensors. Returns the number
        of rows imported. Rejects an empty / header-less / data-less file, and
        skips rows that can't be parsed, are non-finite, or reference a sensor_id
        that doesn't exist (SQLite has no FK enforcement, so those would otherwise
        be committed as invisible orphan rows) rather than aborting the whole import
        or reporting false success."""
        count = rows = 0
        with session(self.engine) as s, open(path, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV is empty or has no header row.")
            missing = [c for c in self.REQUIRED if c not in reader.fieldnames]
            if missing:
                raise KeyError(f"CSV is missing required column(s): {', '.join(missing)}")
            known = {sid for (sid,) in s.execute(select(SensorRow.id)).all()}
            for row in reader:
                rows += 1
                try:
                    sid = int(row["sensor_id"])
                    val = float(row["value"])
                    ts = datetime.fromisoformat(row["timestamp"])
                except (TypeError, ValueError):
                    continue  # unparseable cell — skip this row
                if sid not in known or not math.isfinite(val):
                    continue  # orphan sensor_id or NaN/inf value — skip
                s.add(MeasurementRow(sensor_id=sid, timestamp=ts,
                                     metric_type=row["metric_type"], value=val,
                                     unit=row["unit"]))
                count += 1
            if rows == 0:
                raise ValueError("CSV has a header but no data rows.")
            s.commit()
        return count


class StatusService:
    """Evaluates current status from latest measurements + thresholds."""
    def __init__(self, engine):
        self.engine = engine

    def _rules(self, s) -> dict[str, ThresholdRule]:
        return {
            r.metric_type: ThresholdRule(r.id, r.metric_type, r.warning_value, r.critical_value, r.unit)
            for r in s.execute(select(ThresholdRow)).scalars().all()
        }

    def sensor_statuses(self) -> list[dict]:
        with session(self.engine) as s:
            rules = self._rules(s)
            out = []
            for sensor in s.execute(select(SensorRow)).scalars().all():
                latest = s.execute(
                    select(MeasurementRow)
                    .where(MeasurementRow.sensor_id == sensor.id)
                    .order_by(MeasurementRow.timestamp.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if not latest:
                    status = Status.UNKNOWN
                else:
                    rule = rules.get(latest.metric_type)
                    status = rule.evaluate(latest.value) if rule else Status.UNKNOWN
                out.append({"sensor_id": sensor.id, "asset_id": sensor.asset_id,
                            "status": status.value})
            return out

    def asset_statuses(self) -> list[dict]:
        rank = {Status.UNKNOWN: 0, Status.OK: 1, Status.WARNING: 2, Status.CRITICAL: 3}
        worst: dict[int, Status] = {}
        for s in self.sensor_statuses():
            cur = worst.get(s["asset_id"], Status.UNKNOWN)
            new = Status(s["status"])
            if rank[new] > rank[cur]:
                worst[s["asset_id"]] = new
        return [{"asset_id": k, "status": v.value} for k, v in worst.items()]

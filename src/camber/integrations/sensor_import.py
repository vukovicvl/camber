"""Bridge between the MIT ``camber-convert`` library and Camber's own database.

``camber-convert`` reads a sensor recording (wide/multi-channel or tidy CSV, and
later TDMS/Dewesoft) into a neutral in-memory shape. This module maps that shape
into Camber's SQLAlchemy tables: it creates the asset (or reuses an existing
one), one sensor per channel, and streams the measurements in batches so a
multi-million-row recording imports without exhausting memory.

Keeping this here (in the AGPL app) rather than in camber-convert respects the
license split: format-reading logic stays in the MIT library; persistence into
Camber's schema is app code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path

from sqlalchemy import insert, select, text

from ..storage.db import AssetRow, MeasurementRow, SensorRow, session

import camber_convert as bc

# App-shipped import profiles (one JSON per known vendor layout). Auto-detection
# and the "add a layout = drop a JSON file" workflow both read from here.
PROFILES_DIR = str(Path(__file__).with_name("profiles"))


@dataclass
class ImportPreview:
    """A non-destructive description of what an import *would* do."""

    kind: str                       # "wide" | "tidy"
    profile_name: str | None
    delimiter: str
    decimal: str
    fieldnames: list[str]
    asset_name: str
    asset_type: str
    sensor_count: int
    preview_rows: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    asset_id: int
    asset_name: str
    sensors_created: int
    measurements_imported: int


def inspect(path: str, profile=None) -> ImportPreview:
    """Describe a file for the import preview dialog (reads only a few rows)."""
    info = bc.inspect_csv(path, profile=profile, user_dir=PROFILES_DIR)
    return ImportPreview(
        kind=info.kind,
        profile_name=info.profile_name,
        delimiter=info.dialect.delimiter,
        decimal=info.dialect.decimal,
        fieldnames=list(info.fieldnames),
        asset_name=info.asset.name,
        asset_type=info.asset.type or "bridge",
        sensor_count=len(info.sensors),
        preview_rows=[
            {
                "timestamp": m.timestamp.isoformat(),
                "sensor_id": m.sensor_id,
                "metric_type": m.metric_type,
                "value": m.value,
                "unit": m.unit,
            }
            for m in info.preview
        ],
        warnings=list(info.warnings),
    )


def _to_naive_utc(ts):
    """Camber stores naive-UTC datetimes (see seed/import). Normalise to that."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


def import_file(engine, path: str, profile=None, *,
                target_asset_id: int | None = None,
                new_asset_name: str | None = None,
                batch_size: int = 10_000,
                progress=None) -> ImportResult:
    """Import a recording into the DB.

    Creates a new asset unless ``target_asset_id`` is given, then one sensor per
    channel, then bulk-inserts measurements in ``batch_size`` chunks. ``progress``
    (if given) is called with the running measurement count after each batch.
    """
    info = bc.inspect_csv(path, profile=profile, user_dir=PROFILES_DIR)
    # Use the resolved profile name for streaming so the second pass maps
    # channels to the same sensor ids the inspect pass produced.
    stream_profile = profile if profile is not None else info.profile_name

    is_sqlite = engine.dialect.name == "sqlite"
    with session(engine) as s:
        # Bulk-load speedups for SQLite: skip fsync per commit and keep temp data
        # in memory. Scoped to this connection and restored below. journal_mode is
        # left on disk so a crash can still roll back the (single) import
        # transaction; only power-loss durability is traded for speed.
        if is_sqlite:
            s.execute(text("PRAGMA synchronous=OFF"))
            s.execute(text("PRAGMA temp_store=MEMORY"))

        existing: dict[str, int] = {}
        if target_asset_id is not None:
            asset = s.get(AssetRow, target_asset_id)
            if asset is None:
                raise ValueError(f"asset {target_asset_id} not found")
            asset_id, asset_name = asset.id, asset.name
            # Re-importing another recording of the same bridge should feed the
            # same sensors, not duplicate them (serial_number has no UNIQUE
            # constraint, so nothing else stops it). Reuse by serial.
            existing = {sr.serial_number: sr.id for sr in s.execute(
                select(SensorRow).where(SensorRow.asset_id == asset_id)).scalars()}
        else:
            asset = AssetRow(name=new_asset_name or info.asset.name,
                             type=info.asset.type or "bridge")
            s.add(asset)
            s.flush()
            asset_id, asset_name = asset.id, asset.name

        # One SensorRow per channel; map camber-convert's string id -> db int id.
        # Reuse an existing sensor with the same serial when importing into an
        # existing asset.
        sid_map: dict[str, int] = {}
        sensors_created = 0
        for sensor in info.sensors:
            serial = (sensor.serial_number or sensor.id)[:100]
            if serial in existing:
                sid_map[sensor.id] = existing[serial]
                continue
            row = SensorRow(
                asset_id=asset_id,
                sensor_type=(sensor.sensor_type or "unknown")[:100],
                serial_number=serial,
                axis=(sensor.axis or None),
            )
            s.add(row)
            s.flush()
            sid_map[sensor.id] = row.id
            existing[serial] = row.id
            sensors_created += 1

        # Core table insert (not the ORM class) is ~1.5x faster here: it skips
        # per-row ORM machinery while still going through SQLAlchemy's type
        # handling, so DateTime values serialise the way reads expect.
        meas_insert = insert(MeasurementRow.__table__)
        count = 0
        buf: list[dict] = []
        for m in bc.stream_measurements(path, profile=stream_profile, user_dir=PROFILES_DIR):
            db_sid = sid_map.get(m.sensor_id)
            if db_sid is None:
                continue
            # SQLite stores a float NaN as NULL, which violates the NOT NULL value
            # column and would abort the whole batch on one bad cell. Drop non-finite
            # readings (dropped samples / overflow) instead.
            if m.value is None or not math.isfinite(m.value):
                continue
            buf.append({
                "sensor_id": db_sid,
                "timestamp": _to_naive_utc(m.timestamp),
                "metric_type": m.metric_type[:50],
                "value": m.value,
                "unit": (m.unit or "")[:20],
            })
            if len(buf) >= batch_size:
                s.execute(meas_insert, buf)
                count += len(buf)
                buf.clear()
                if progress:
                    progress(count)
        if buf:
            s.execute(meas_insert, buf)
            count += len(buf)
            if progress:
                progress(count)

        if count == 0:
            # Nothing parsed -> don't commit phantom zero-row sensors or report a
            # misleading "imported 0" success. Raising rolls back the asset/sensors.
            raise ValueError(
                "No readings were parsed from the file — it may be empty, all "
                "no-data/sentinel values, or an unrecognised layout.")

        s.commit()

        if is_sqlite:  # restore default durability for the pooled connection
            try:
                s.execute(text("PRAGMA synchronous=FULL"))
            except Exception:  # pragma: no cover - best effort
                pass

    return ImportResult(asset_id=asset_id, asset_name=asset_name,
                        sensors_created=sensors_created, measurements_imported=count)

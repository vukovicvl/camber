"""Local HTTP API for external tooling and integrations.
Bind to 127.0.0.1 only - this is a local IPC layer, not a public service.
"""
from __future__ import annotations
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..services.services import (
    AssetService, SensorService, MeasurementService, StatusService, ImportService,
)


class MeasurementIn(BaseModel):
    """A live reading pushed in by a sensor gateway or simulator."""
    sensor_id: int
    value: float
    metric_type: str
    unit: str
    timestamp: datetime | None = None


def create_app(engine) -> FastAPI:
    app = FastAPI(title="Camber Local API", version="0.1.0")
    assets = AssetService(engine)
    sensors = SensorService(engine)
    meas = MeasurementService(engine)
    status = StatusService(engine)
    imports = ImportService(engine)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "camber"}

    @app.get("/projects/current")
    def current_project():
        return {"name": "default", "db": "camber.db"}

    @app.get("/assets")
    def list_assets():
        return assets.list_assets()

    @app.get("/assets/{asset_id}/sensors")
    def asset_sensors(asset_id: int):
        return sensors.list_for_asset(asset_id)

    @app.get("/sensors/{sensor_id}/measurements")
    def sensor_measurements(sensor_id: int, limit: int = 1000):
        return meas.for_sensor(sensor_id, limit)

    @app.get("/status/assets")
    def asset_status():
        return status.asset_statuses()

    @app.get("/status/sensors")
    def sensor_status():
        return status.sensor_statuses()

    @app.post("/imports/csv")
    def import_csv(path: str):
        try:
            n = imports.import_csv(path)
        except FileNotFoundError:
            raise HTTPException(404, "CSV not found")
        return {"imported": n}

    @app.post("/measurements")
    def add_measurement(m: MeasurementIn):
        """Live ingest: push a single reading. This is the endpoint a real
        sensor gateway (or the demo feed) posts to; the live chart shows it."""
        mid = meas.append(m.sensor_id, m.value, m.metric_type, m.unit, m.timestamp)
        if mid is None:  # non-finite value (JSON allows NaN/Infinity) — reject cleanly
            raise HTTPException(422, "value must be a finite number")
        return {"id": mid}

    @app.post("/measurements/batch")
    def add_measurements(items: list[MeasurementIn]):
        # Non-finite readings are dropped (append returns None) rather than
        # failing the whole batch; report how many were actually stored.
        ids = [mid for m in items
               if (mid := meas.append(m.sensor_id, m.value, m.metric_type, m.unit,
                                      m.timestamp)) is not None]
        return {"ingested": len(ids)}

    return app


def serve(engine, host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    # log_config=None: don't let uvicorn install its own dict-config logging. Its
    # default colour formatter calls sys.stdout.isatty() at construction, which
    # crashes in a windowed (console=False) build where sys.stdout is None. With
    # None, uvicorn's records propagate to the root logger we already configured,
    # so its logs land in camber.log too.
    uvicorn.run(create_app(engine), host=host, port=port, log_level="info",
                log_config=None)

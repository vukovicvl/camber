"""Local HTTP API for external tooling and integrations.
Bind to 127.0.0.1 only - this is a local IPC layer, not a public service.
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from ..services.services import (
    AssetService, SensorService, MeasurementService, StatusService, ImportService,
)


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

    return app


def serve(engine, host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(create_app(engine), host=host, port=port, log_level="info")

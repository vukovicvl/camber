"""Seed the local SQLite DB with demo assets, sensors, thresholds, and measurements."""
from datetime import datetime, timedelta
import random
from camber.storage.db import init_db, session, AssetRow, SensorRow, MeasurementRow, ThresholdRow

def main():
    engine = init_db("camber.db")
    with session(engine) as s:
        a1 = AssetRow(name="Sava Bridge", type="bridge", latitude=44.8125, longitude=20.4612)
        a2 = AssetRow(name="Danube Viaduct", type="viaduct", latitude=44.8700, longitude=20.5100)
        s.add_all([a1, a2]); s.flush()

        sensors = [
            SensorRow(asset_id=a1.id, sensor_type="accelerometer", serial_number="ACC-001", axis="Z"),
            SensorRow(asset_id=a1.id, sensor_type="strain", serial_number="STR-002"),
            SensorRow(asset_id=a2.id, sensor_type="tilt", serial_number="TLT-003", axis="X"),
        ]
        s.add_all(sensors); s.flush()

        s.add(ThresholdRow(metric_type="acceleration", warning_value=0.5, critical_value=1.0, unit="g"))
        s.add(ThresholdRow(metric_type="strain", warning_value=200, critical_value=400, unit="ue"))
        s.add(ThresholdRow(metric_type="tilt", warning_value=0.3, critical_value=0.6, unit="deg"))

        now = datetime.utcnow()
        metric_map = {"accelerometer": ("acceleration", "g", 0.6),
                      "strain": ("strain", "ue", 250),
                      "tilt": ("tilt", "deg", 0.35)}
        for sensor in sensors:
            metric, unit, peak = metric_map[sensor.sensor_type]
            for i in range(50):
                s.add(MeasurementRow(
                    sensor_id=sensor.id,
                    timestamp=now - timedelta(minutes=i),
                    metric_type=metric,
                    value=round(random.uniform(0, peak), 3),
                    unit=unit,
                ))
        s.commit()
    print("Seeded camber.db")

if __name__ == "__main__":
    main()

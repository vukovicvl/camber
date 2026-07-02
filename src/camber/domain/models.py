"""Pure business entities. No I/O, no framework dependencies."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Status(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class Asset:
    id: Optional[int]
    name: str
    type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Sensor:
    id: Optional[int]
    asset_id: int
    sensor_type: str
    serial_number: str
    axis: Optional[str] = None


@dataclass
class Measurement:
    id: Optional[int]
    sensor_id: int
    timestamp: datetime
    metric_type: str
    value: float
    unit: str


@dataclass
class ThresholdRule:
    id: Optional[int]
    metric_type: str
    warning_value: float
    critical_value: float
    unit: str

    def evaluate(self, value: float) -> Status:
        if value >= self.critical_value:
            return Status.CRITICAL
        if value >= self.warning_value:
            return Status.WARNING
        return Status.OK


@dataclass
class StatusSnapshot:
    id: Optional[int]
    entity_type: str  # "asset" | "sensor"
    entity_id: int
    status: Status
    timestamp: datetime
    reason: str = ""

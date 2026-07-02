"""SQLite storage with SQLAlchemy 2.x."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import create_engine, ForeignKey, String, Float, DateTime, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


class Base(DeclarativeBase):
    pass


class AssetRow(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    sensors: Mapped[list["SensorRow"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class SensorRow(Base):
    __tablename__ = "sensors"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    sensor_type: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(100))
    axis: Mapped[str | None] = mapped_column(String(10), nullable=True)
    asset: Mapped[AssetRow] = relationship(back_populates="sensors")
    measurements: Mapped[list["MeasurementRow"]] = relationship(back_populates="sensor", cascade="all, delete-orphan")


class MeasurementRow(Base):
    __tablename__ = "measurements"
    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    metric_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    sensor: Mapped[SensorRow] = relationship(back_populates="measurements")


class ThresholdRow(Base):
    __tablename__ = "thresholds"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_type: Mapped[str] = mapped_column(String(50), unique=True)
    warning_value: Mapped[float] = mapped_column(Float)
    critical_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))


def init_db(db_path: str = "camber.db"):
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    return engine


def session(engine) -> Session:
    return Session(engine, future=True)

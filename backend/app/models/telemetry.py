from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(16), ForeignKey("devices.device_id"), primary_key=True, nullable=False, index=True)
    sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_intensity: Mapped[float | None] = mapped_column(Float, nullable=True)
    pump_running: Mapped[bool] = mapped_column(Boolean, default=False)
    led_on: Mapped[bool] = mapped_column(Boolean, default=False)
    water_tank_level_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wifi_rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_heap_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uptime_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    device = relationship("Device", back_populates="telemetries")

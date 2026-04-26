from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    plant_type: Mapped[str | None] = mapped_column(ForeignKey("plant_types.plant_type"), nullable=True)
    bind_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    firmware_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    photo_schedule: Mapped[str | None] = mapped_column(nullable=True)
    telemetry_interval_s: Mapped[int] = mapped_column(Integer, default=300)
    watering_max_duration_ms: Mapped[int] = mapped_column(Integer, default=30000)
    soil_moisture_threshold: Mapped[float] = mapped_column(Float, default=30.0)
    bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="devices")
    plant_type_rel = relationship("PlantType")
    telemetries = relationship("Telemetry", back_populates="device", lazy="selectin")
    images = relationship("Image", back_populates="device", lazy="selectin")
    alerts = relationship("Alert", back_populates="device", lazy="selectin")
    commands = relationship("Command", back_populates="device", lazy="selectin")
    watering_events = relationship("WateringEvent", back_populates="device", lazy="selectin")

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Image(Base, TimestampMixin):
    __tablename__ = "images"

    image_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    photo_index: Mapped[int] = mapped_column(Integer, default=1)
    burst_total: Mapped[int] = mapped_column(Integer, default=1)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_condition: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(8), nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    annotated_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detection_status: Mapped[str] = mapped_column(String(32), default="pending_detection")
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disease_count: Mapped[int] = mapped_column(Integer, default=0)

    device = relationship("Device", back_populates="images")
    detections = relationship("Detection", back_populates="image", lazy="selectin")

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Detection(Base):
    __tablename__ = "detections"

    detection_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.image_id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disease_class: Mapped[str] = mapped_column(String(64), nullable=False)
    disease_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bbox: Mapped[str | None] = mapped_column(nullable=True)
    recommendation: Mapped[str | None] = mapped_column(nullable=True)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    image = relationship("Image", back_populates="detections")

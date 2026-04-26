from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlantType(Base):
    __tablename__ = "plant_types"

    plant_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_thresholds: Mapped[str] = mapped_column(nullable=False)
    watering_cfg: Mapped[str] = mapped_column(nullable=False)

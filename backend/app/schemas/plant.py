from __future__ import annotations

from pydantic import BaseModel


class PlantTypeItem(BaseModel):
    plant_type: str
    name: str
    category: str
    icon_url: str | None = None
    default_thresholds: dict = {}
    watering_cfg: dict = {}

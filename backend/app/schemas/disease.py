from __future__ import annotations

from pydantic import BaseModel


class DiseaseRecord(BaseModel):
    detection_id: str
    image_id: str
    timestamp: str
    disease_class: str
    disease_name: str
    confidence: float
    severity: str | None = None
    bbox: dict | None = None
    image_url: str | None = None

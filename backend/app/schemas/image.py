from __future__ import annotations

from pydantic import BaseModel


class ImageUploadMeta(BaseModel):
    timestamp: str
    photo_index: int = 1
    burst_total: int = 1
    quality_score: float | None = None
    light_condition: str | None = None
    resolution: str | None = None
    file_size_bytes: int | None = None
    format: str | None = None


class ImageUploadResponse(BaseModel):
    image_id: str
    url: str | None = None
    status: str = "pending_detection"


class ImageListItem(BaseModel):
    image_id: str
    url: str | None = None
    enhanced_url: str | None = None
    detection_source: str | None = None
    detection_image_url: str | None = None
    annotated_url: str | None = None
    timestamp: str
    photo_index: int = 1
    detection_status: str = "pending_detection"
    disease_count: int = 0
    health_score: int | None = None


class DetectionDetail(BaseModel):
    status: str
    completed_at: str | None = None
    diseases: list[dict] = []
    health_score: int | None = None


class ImageDetailResponse(BaseModel):
    image_id: str
    url: str | None = None
    enhanced_url: str | None = None
    detection_source: str | None = None
    detection_image_url: str | None = None
    annotated_url: str | None = None
    timestamp: str
    photo_index: int = 1
    quality_score: float | None = None
    light_condition: str | None = None
    detection: DetectionDetail | None = None

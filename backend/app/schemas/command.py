from __future__ import annotations

from pydantic import BaseModel, Field


class WaterRequest(BaseModel):
    duration_ms: int = Field(gt=0, le=30000)


class PhotoRequest(BaseModel):
    burst_count: int = Field(default=3, ge=1, le=5)


class ConfigRequest(BaseModel):
    photo_schedule: list[str] | None = None
    telemetry_interval_s: int | None = Field(default=None, ge=10, le=3600)
    watering_max_duration_ms: int | None = Field(default=None, ge=1000, le=60000)


class CommandSentResponse(BaseModel):
    cmd_id: str
    status: str
    timestamp: str


class CommandStatusResponse(BaseModel):
    cmd_id: str
    type: str
    status: str
    request: dict | None = None
    response: dict | None = None
    created_at: str
    completed_at: str | None = None

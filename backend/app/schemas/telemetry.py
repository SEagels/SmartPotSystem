from __future__ import annotations

from pydantic import BaseModel, Field


class LatestTelemetryResponse(BaseModel):
    device_id: str
    timestamp: str
    sensors: dict = Field(default_factory=dict)
    actuators: dict = Field(default_factory=dict)
    system: dict = Field(default_factory=dict)


class HistoryDataPoint(BaseModel):
    timestamp: str
    avg: float | None = None
    min: float | None = None
    max: float | None = None
    value: float | None = None


class HistoryResponse(BaseModel):
    metric: str
    unit: str
    interval: str
    data_points: list[HistoryDataPoint] = Field(default_factory=list)


class MetricSummary(BaseModel):
    avg: float
    min: float
    max: float


class SummaryResponse(BaseModel):
    device_id: str
    period: str
    date: str
    summary: dict = Field(default_factory=dict)
    watering_count: int = 0
    watering_total_ml: float = 0
    photo_count: int = 0
    disease_alerts: int = 0

from __future__ import annotations

from pydantic import BaseModel, Field


class LatestTelemetrySnippet(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    soil_moisture: float | None = None
    timestamp: str | None = None


class DeviceListItem(BaseModel):
    device_id: str
    name: str
    plant_type: str | None = None
    plant_type_name: str | None = None
    online: bool = False
    latest_telemetry: LatestTelemetrySnippet | None = None
    has_active_alert: bool = False
    bound_at: str | None = None


class Thresholds(BaseModel):
    temperature: dict | None = None
    humidity: dict | None = None
    soil_moisture: dict | None = None
    light_intensity: dict | None = None


class TodaySummary(BaseModel):
    watering_count: int = 0
    watering_total_ml: float = 0
    photo_count: int = 0
    disease_alerts: int = 0


class DeviceDetail(BaseModel):
    device_id: str
    name: str
    plant_type: str | None = None
    plant_type_name: str | None = None
    online: bool = False
    firmware_version: str | None = None
    latest_telemetry: dict | None = None
    thresholds: Thresholds | None = None
    photo_schedule: list[str] | None = None
    today_summary: TodaySummary | None = None


class BindDeviceRequest(BaseModel):
    device_id: str
    bind_code: str


class BindDeviceResponse(BaseModel):
    device_id: str
    name: str
    bound_at: str


class DeviceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    plant_type: str | None = None

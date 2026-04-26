from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TelemetrySensors(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    soil_moisture: float | None = None
    light_intensity: float | None = None


class TelemetryActuators(BaseModel):
    pump_running: bool = False
    led_on: bool = False
    water_tank_level_pct: float | None = None


class TelemetrySystem(BaseModel):
    wifi_rssi: int | None = None
    free_heap_kb: int | None = None
    uptime_s: int | None = None
    firmware_version: str | None = None


class TelemetryPayload(BaseModel):
    device_id: str
    timestamp: str
    sequence: int = 0
    sensors: TelemetrySensors = Field(default_factory=TelemetrySensors)
    actuators: TelemetryActuators = Field(default_factory=TelemetryActuators)
    system: TelemetrySystem = Field(default_factory=TelemetrySystem)


class ImageUploadedPayload(BaseModel):
    image_id: str
    timestamp: str
    url: str
    photo_index: int = 1


class DetectionResultItem(BaseModel):
    class_name: str = Field(alias="class")
    name_zh: str = ""
    confidence: float
    bbox: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class DetectionResultPayload(BaseModel):
    image_id: str
    timestamp: str
    detected: bool = False
    disease_count: int = 0
    diseases: list[DetectionResultItem] = Field(default_factory=list)
    health_score: int = 100


class WateringEventPayload(BaseModel):
    event_id: str
    timestamp: str
    trigger: str
    duration_ms: int
    water_pumped_ml: float | None = None
    reason: str = ""
    soil_moisture_before: float | None = None
    soil_moisture_after: float | None = None


class DeviceStatusPayload(BaseModel):
    online: bool
    timestamp: str
    firmware_version: str | None = None
    wifi_rssi: int | None = None
    free_heap: int | None = None
    battery_voltage: float | None = None


class WaterCommandPayload(BaseModel):
    cmd_id: str
    timestamp: str
    duration_ms: int = Field(gt=0, le=30000)
    source: str = "manual"


class WaterResponsePayload(BaseModel):
    cmd_id: str
    status: str
    timestamp: str
    actual_duration_ms: int = 0
    water_pumped_ml: float | None = None


class PhotoCommandPayload(BaseModel):
    cmd_id: str
    timestamp: str
    burst_count: int = Field(default=3, ge=1, le=5)
    source: str = "manual"


class PhotoResponsePayload(BaseModel):
    cmd_id: str
    status: str
    timestamp: str
    image_count: int = 0
    selected_index: int = 0


class ConfigCommandPayload(BaseModel):
    cmd_id: str
    timestamp: str
    changes: dict = Field(default_factory=dict)


class ConfigResponsePayload(BaseModel):
    cmd_id: str
    status: str
    timestamp: str

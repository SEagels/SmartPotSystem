from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models.device import Device
from app.models.user import User
from app.services import command_service

router = APIRouter(prefix="/devices/{device_id}")


class WaterBody(BaseModel):
    duration_ms: int = Field(default=5000, ge=1000, le=60000)


class PhotoBody(BaseModel):
    burst_count: int = Field(default=1, ge=1, le=5)


class ConfigBody(BaseModel):
    photo_schedule: list[str] | None = None
    telemetry_interval_s: int | None = Field(None, ge=60, le=3600)
    watering_max_duration_ms: int | None = Field(None, ge=5000, le=120000)


@router.post("/water")
async def water(
    body: WaterBody,
    device: Device = Depends(get_current_device),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not device.online:
        return {"code": 2002, "message": "设备离线", "data": None}
    result = await command_service.send_water_command(db, device.device_id, user.id, body.duration_ms)
    return {"code": 0, "message": "success", "data": result}


@router.post("/photo")
async def photo(
    body: PhotoBody,
    device: Device = Depends(get_current_device),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not device.online:
        return {"code": 2002, "message": "设备离线", "data": None}
    result = await command_service.send_photo_command(db, device.device_id, user.id, body.burst_count)
    return {"code": 0, "message": "success", "data": result}


@router.put("/config")
async def update_config(
    body: ConfigBody,
    device: Device = Depends(get_current_device),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not device.online:
        return {"code": 2002, "message": "设备离线", "data": None}
    config = body.model_dump(exclude_none=True)
    result = await command_service.send_config_command(db, device.device_id, user.id, config)

    if config.get("photo_schedule"):
        import json
        device.photo_schedule = json.dumps(config["photo_schedule"])
    if config.get("telemetry_interval_s"):
        device.telemetry_interval_s = config["telemetry_interval_s"]
    if config.get("watering_max_duration_ms"):
        device.watering_max_duration_ms = config["watering_max_duration_ms"]

    return {"code": 0, "message": "success", "data": result}


@router.get("/commands/{cmd_id}")
async def command_status(
    cmd_id: str,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    try:
        status = await command_service.get_command_status(db, device.device_id, cmd_id)
        return {"code": 0, "message": "success", "data": status}
    except ValueError as e:
        return {"code": 3001, "message": str(e), "data": None}

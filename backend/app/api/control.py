from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_write_lock, get_db, get_sessionmaker
from app.dependencies import get_current_device, get_current_device_ro, get_current_user, get_current_user_ro
from app.models.device import Device
from app.models.user import User
from app.services import command_service, telemetry_service
from app.services.device_service import _is_device_really_online

logger = logging.getLogger(__name__)

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
    if not await _is_device_really_online(db, device.device_id):
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
    if not await _is_device_really_online(db, device.device_id):
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
    if not await _is_device_really_online(db, device.device_id):
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


@router.post("/sync-sensors")
async def sync_sensors(
    device: Device = Depends(get_current_device_ro),
    user: User = Depends(get_current_user_ro),
):
    # 先用一个短暂锁定的会话获取同步前时间戳 + 发送指令
    sm = get_sessionmaker()
    async with db_write_lock:
        async with sm() as db:
            before = await telemetry_service.get_latest_telemetry(db, device.device_id)
            before_ts = before["timestamp"] if before else None
            result = await command_service.send_sync_command(db, device.device_id, user.id)
            await db.commit()

    logger.info(f"Sync command sent to {device.device_id}, waiting for telemetry response...")

    # 轮询等待设备上报新遥测（最多等待 8 秒）
    # 这里不持有 db_write_lock，MQTT handler 可以正常写入遥测数据
    for attempt in range(16):
        await asyncio.sleep(0.5)
        async with sm() as fresh_db:
            latest = await telemetry_service.get_latest_telemetry(fresh_db, device.device_id)
        if latest and (before_ts is None or latest["timestamp"] > before_ts):
            logger.info(f"Sync telemetry received from {device.device_id} after {attempt * 0.5:.1f}s")
            return {
                "code": 0,
                "message": "success",
                "data": {"cmd": result, "telemetry": latest["sensors"]},
            }

    logger.warning(f"Sync timeout for {device.device_id}: no telemetry received within 8s")
    return {
        "code": 0,
        "message": "指令已发送但设备未响应，请检查设备 MQTT 连接",
        "data": {"cmd": result, "telemetry": None},
    }


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

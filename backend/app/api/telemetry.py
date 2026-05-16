from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import parse_iso_datetime
from app.core.database import get_db
from app.dependencies import get_current_device
from app.models.device import Device
from app.services import telemetry_service

router = APIRouter(prefix="/devices/{device_id}/telemetry")


@router.get("/latest")
async def get_latest(device: Device = Depends(get_current_device), db: AsyncSession = Depends(get_db)):
    data = await telemetry_service.get_latest_telemetry(db, device.device_id)
    if not data:
        return {"code": 0, "message": "暂无数据", "data": None}
    return {"code": 0, "message": "success", "data": data}


@router.get("/history")
async def get_history(
    device: Device = Depends(get_current_device),
    metric: str = Query(..., description="temperature/humidity/soil_moisture/light_intensity"),
    start: str = Query(..., description="ISO8601"),
    end: str = Query(..., description="ISO8601"),
    interval: str = Query("1h", description="5m/15m/30m/1h/6h/1d"),
    db: AsyncSession = Depends(get_db),
):
    try:
        start_dt = parse_iso_datetime(start)
        end_dt = parse_iso_datetime(end)
        data = await telemetry_service.get_history(db, device.device_id, metric, start_dt, end_dt, interval)
        return {"code": 0, "message": "success", "data": data}
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.get("/summary")
async def get_summary(
    device: Device = Depends(get_current_device),
    date: str = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    date_str = date or datetime.now(UTC).strftime("%Y-%m-%d")
    data = await telemetry_service.get_daily_summary(db, device.device_id, date_str)
    return {"code": 0, "message": "success", "data": data}

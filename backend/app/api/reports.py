from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device
from app.models.device import Device
from app.services import report_service

router = APIRouter(prefix="/devices/{device_id}/reports")


@router.get("/daily")
async def daily_report(
    device: Device = Depends(get_current_device),
    date: str = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    date_str = date or datetime.now(UTC).strftime("%Y-%m-%d")
    data = await report_service.generate_daily_report(db, device.device_id, date_str)
    return {"code": 0, "message": "success", "data": data}


@router.get("/weekly")
async def weekly_report(
    device: Device = Depends(get_current_device),
    date: str = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    date_str = date or datetime.now(UTC).strftime("%Y-%m-%d")
    data = await report_service.generate_weekly_report(db, device.device_id, date_str)
    return {"code": 0, "message": "success", "data": data}


@router.post("/generate")
async def generate_report(
    device: Device = Depends(get_current_device),
    date: str = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    date_str = date or datetime.now(UTC).strftime("%Y-%m-%d")
    data = await report_service.generate_daily_report(db, device.device_id, date_str)
    return {"code": 0, "message": "养护报告已生成", "data": data}

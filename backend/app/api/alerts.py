from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models.device import Device
from app.models.user import User
from app.services import alert_service

router = APIRouter(prefix="")


@router.get("/devices/{device_id}/alerts")
async def list_alerts(
    device: Device = Depends(get_current_device),
    status: str | None = Query(None, description="unread / read"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    alerts, total = await alert_service.list_alerts(db, device.device_id, status, page, page_size)
    data = [
        {
            "alert_id": a.alert_id,
            "type": a.type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "image_id": a.image_id,
            "read": a.is_read,
            "created_at": a.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if a.created_at else None,
        }
        for a in alerts
    ]
    return {"code": 0, "message": "success", "data": data, "meta": {"page": page, "page_size": page_size, "total": total}}


@router.put("/alerts/{alert_id}/read")
async def mark_read(alert_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        await alert_service.mark_read(db, alert_id)
        return {"code": 0, "message": "success", "data": None}
    except ValueError as e:
        return {"code": 3001, "message": str(e), "data": None}


@router.put("/devices/{device_id}/alerts/read-all")
async def mark_all_read(device: Device = Depends(get_current_device), db: AsyncSession = Depends(get_db)):
    count = await alert_service.mark_all_read(db, device.device_id)
    return {"code": 0, "message": "success", "data": {"marked_read": count}}

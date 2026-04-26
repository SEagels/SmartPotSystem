from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device
from app.models.device import Device
from app.services import disease_service

router = APIRouter(prefix="/devices/{device_id}/diseases")


@router.get("")
async def list_diseases(
    device: Device = Depends(get_current_device),
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await disease_service.list_diseases(db, device.device_id, start, end)
    return {"code": 0, "message": "success", "data": data}

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models.device import Device
from app.models.user import User
from app.services import device_service, discovery_service

router = APIRouter(prefix="/devices")


class BindBody(BaseModel):
    device_id: str = Field(min_length=1, max_length=32)
    bind_code: str = Field(min_length=1, max_length=32)


class UpdateBody(BaseModel):
    name: str | None = None
    plant_type: str | None = None


class LanBindBody(BaseModel):
    device_id: str = Field(min_length=1, max_length=32)
    ip: str = Field(min_length=7, max_length=45)
    name: str | None = Field(default=None, max_length=128)


@router.get("")
async def list_devices(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    devices = await device_service.list_user_devices(db, user.id)
    return {"code": 0, "message": "success", "data": devices}


@router.post("/bind")
async def bind_device(body: BindBody, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        device = await device_service.bind_device(db, user.id, body.device_id, body.bind_code)
        return {
            "code": 0, "message": "success",
            "data": {
                "device_id": device.device_id,
                "name": device.name,
                "bound_at": device.bound_at.strftime("%Y-%m-%dT%H:%M:%SZ") if device.bound_at else None,
            },
        }
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.get("/lan-discover")
async def discover_lan_devices(
    cidr: str | None = None,
    user: User = Depends(get_current_user),
):
    try:
        devices = await discovery_service.discover_lan_devices(cidr)
        return {"code": 0, "message": "success", "data": devices}
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": []}


@router.post("/lan-bind")
async def bind_lan_device(
    body: LanBindBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        device = await discovery_service.bind_lan_device(db, user.id, body.device_id, body.ip, body.name)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "device_id": device.device_id,
                "name": device.name,
                "bound_at": device.bound_at.strftime("%Y-%m-%dT%H:%M:%SZ") if device.bound_at else None,
            },
        }
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.get("/{device_id}")
async def get_device(device: Device = Depends(get_current_device), db: AsyncSession = Depends(get_db)):
    detail = await device_service.get_device_detail(db, device.device_id, device.user_id)
    return {"code": 0, "message": "success", "data": detail}


@router.put("/{device_id}")
async def update_device(body: UpdateBody, device: Device = Depends(get_current_device), db: AsyncSession = Depends(get_db)):
    try:
        updated = await device_service.update_device(db, device.device_id, device.user_id, body.model_dump(exclude_none=True))
        return {"code": 0, "message": "success", "data": {"device_id": updated.device_id, "name": updated.name}}
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.delete("/{device_id}")
async def unbind_device(device: Device = Depends(get_current_device), db: AsyncSession = Depends(get_db)):
    await device_service.unbind_device(db, device.device_id, device.user_id)
    return {"code": 0, "message": "解绑成功", "data": None}

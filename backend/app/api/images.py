from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models.device import Device
from app.models.user import User
from app.services import image_service
from app.services.storage_service import get_storage

router = APIRouter(prefix="/devices/{device_id}/images")


@router.post("")
async def upload_image(
    device: Device = Depends(get_current_device),
    user: User = Depends(get_current_user),
    image: UploadFile = File(...),
    metadata: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await image.read()
    meta_dict = json.loads(metadata) if metadata else {}
    storage = get_storage()
    try:
        storage_path = await storage.upload(image.filename, content, device.device_id)
    except Exception:
        storage_path = None

    img = await image_service.create_image(db, device.device_id, str(user.id), meta_dict, storage_path)
    return {
        "code": 0, "message": "success",
        "data": {
            "image_id": img.image_id,
            "url": img.url or storage_path,
            "status": img.detection_status,
        },
    }


@router.get("")
async def list_images(
    device: Device = Depends(get_current_device),
    date: str | None = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    images = await image_service.list_images(db, device.device_id, date)
    data = [
        {
            "image_id": img.image_id,
            "url": img.url,
            "annotated_url": img.annotated_url,
            "timestamp": img.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if img.timestamp else None,
            "photo_index": img.photo_index,
            "detection_status": img.detection_status,
            "disease_count": img.disease_count,
            "health_score": img.health_score,
        }
        for img in images
    ]
    return {"code": 0, "message": "success", "data": data}


@router.get("/{image_id}")
async def get_image_detail(
    image_id: str,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    try:
        detail = await image_service.get_image_detail(db, device.device_id, image_id)
        return {"code": 0, "message": "success", "data": detail}
    except ValueError as e:
        return {"code": 3001, "message": str(e), "data": None}

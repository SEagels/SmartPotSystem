from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_device, get_device_for_upload
from app.models.device import Device
from app.services import image_service
from app.services.storage_service import generate_storage_path, get_storage

router = APIRouter(prefix="/devices/{device_id}/images")


@router.post("")
async def upload_image(
    device: Device = Depends(get_device_for_upload),
    image: UploadFile = File(...),
    metadata: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await image.read()
    meta_dict = json.loads(metadata) if metadata else {}
    storage = get_storage()
    try:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        ts = datetime.now(UTC).strftime("%H%M%S%f")
        unique_name = f"{ts}.jpg"
        path = generate_storage_path(device.device_id, date_str, unique_name)
        storage_path = await storage.upload(content, path)
    except Exception:
        storage_path = None

    user_id = str(device.user_id) if device.user_id else ""
    img = await image_service.create_image(db, device.device_id, user_id, meta_dict, storage_path)
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
            "url": img.url or img.storage_path,
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


@router.post("/re-detect")
async def re_detect_images(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    count = await image_service.reset_images_for_re_detection(db, device.device_id)
    await db.commit()
    return {"code": 0, "message": f"已重置 {count} 张图像的检测状态，正在重新推理", "data": {"count": count}}

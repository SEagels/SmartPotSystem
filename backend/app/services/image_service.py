from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.detection import Detection
from app.models.image import Image
from app.services.storage_service import STORAGE_DIR


async def create_image(
    db: AsyncSession,
    device_id: str,
    user_id: str,
    metadata: dict | None = None,
    storage_path: str | None = None,
) -> Image:
    now = datetime.now(UTC)
    ts_str = now.strftime("%Y%m%d-%H%M%S")
    image_id = f"IMG-{ts_str}-{device_id}"

    meta = metadata or {}
    image = Image(
        image_id=image_id,
        device_id=device_id,
        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        timestamp=meta.get("timestamp", now),
        photo_index=meta.get("photo_index", 1),
        burst_total=meta.get("burst_total", 1),
        quality_score=meta.get("quality_score"),
        light_condition=meta.get("light_condition"),
        resolution=meta.get("resolution"),
        file_size_bytes=meta.get("file_size_bytes"),
        format=meta.get("format"),
        storage_path=storage_path,
        detection_status="pending_detection",
    )
    db.add(image)
    await db.flush()
    return image


async def update_detection_result(
    db: AsyncSession,
    image_id: str,
    status: str,
    health_score: int | None = None,
    disease_count: int = 0,
    detections: list[dict] | None = None,
) -> Image:
    result = await db.execute(select(Image).where(Image.image_id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise ValueError("图片不存在")
    image.detection_status = status
    if health_score is not None:
        image.health_score = health_score
    if disease_count:
        image.disease_count = disease_count
    if detections:
        for i, det_data in enumerate(detections):
            det = Detection(
                detection_id=f"DET-{image_id}-{i+1}-{uuid.uuid4().hex[:8].upper()}",
                image_id=image_id,
                device_id=image.device_id,
                timestamp=datetime.now(UTC),
                disease_class=det_data.get("class", "unknown"),
                disease_name=det_data.get("name_zh", "未知"),
                confidence=det_data.get("confidence", 0.0),
                severity=det_data.get("severity"),
                bbox=json.dumps(det_data.get("bbox")) if det_data.get("bbox") else None,
                recommendation=det_data.get("recommendation"),
                health_score=health_score,
            )
            db.add(det)
    await db.flush()
    return image


async def reset_images_for_re_detection(db: AsyncSession, device_id: str) -> int:
    result = await db.execute(
        select(Image).where(
            Image.device_id == device_id,
            Image.detection_status.in_(["completed", "failed"]),
        )
    )
    images = list(result.scalars().all())
    if not images:
        return 0

    image_ids = [img.image_id for img in images]
    await db.execute(sql_delete(Detection).where(Detection.image_id.in_(image_ids)))

    for img in images:
        img.detection_status = "pending_detection"
        img.detection_source = None
        img.health_score = None
        img.disease_count = 0

    await db.flush()
    return len(images)


def _static_url_to_local_path(value: str | None) -> Path | None:
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return None
    rel = value.replace("/static/images/", "", 1)
    path = (STORAGE_DIR / rel).resolve()
    root = STORAGE_DIR.resolve()
    if path != root and root in path.parents:
        return path
    return None


def _delete_local_file(value: str | None) -> None:
    path = _static_url_to_local_path(value)
    if path and path.exists() and path.is_file():
        path.unlink()


async def delete_image(db: AsyncSession, device_id: str, image_id: str) -> None:
    result = await db.execute(
        select(Image).where(Image.image_id == image_id, Image.device_id == device_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise ValueError("图片不存在")

    paths = {image.url, image.storage_path, image.enhanced_url, image.annotated_url}
    await db.execute(sql_delete(Detection).where(Detection.image_id == image_id))
    await db.execute(sql_delete(Alert).where(Alert.image_id == image_id))
    await db.delete(image)
    await db.flush()

    for path in paths:
        _delete_local_file(path)


def get_detection_image_url(image: Image) -> str | None:
    original_url = image.url or image.storage_path
    if image.detection_source == "enhanced" and image.enhanced_url:
        return image.enhanced_url
    return original_url


async def list_images(
    db: AsyncSession, device_id: str, date_str: str | None = None, limit: int = 50
) -> list[Image]:
    q = select(Image).where(Image.device_id == device_id)
    if date_str:
        day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
        day_end = day_start.replace(hour=23, minute=59, second=59)
        q = q.where(Image.timestamp.between(day_start, day_end))
    q = q.order_by(Image.timestamp.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_image_detail(db: AsyncSession, device_id: str, image_id: str) -> dict:
    result = await db.execute(
        select(Image).where(Image.image_id == image_id, Image.device_id == device_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise ValueError("图片不存在")

    det_result = await db.execute(
        select(Detection).where(Detection.image_id == image_id)
    )
    dets = det_result.scalars().all()

    diseases = []
    for d in dets:
        diseases.append({
            "class": d.disease_class,
            "name_zh": d.disease_name,
            "confidence": d.confidence,
            "bbox": json.loads(d.bbox) if d.bbox else None,
            "severity": d.severity,
            "recommendation": d.recommendation,
        })

    detection_info = {
        "status": image.detection_status,
        "completed_at": dets[0].timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if dets else None,
        "diseases": diseases,
        "health_score": image.health_score,
    }

    return {
        "image_id": image.image_id,
        "url": image.url or image.storage_path,
        "enhanced_url": image.enhanced_url,
        "detection_source": image.detection_source,
        "detection_image_url": get_detection_image_url(image),
        "annotated_url": image.annotated_url,
        "timestamp": image.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if image.timestamp else None,
        "photo_index": image.photo_index,
        "quality_score": image.quality_score,
        "light_condition": image.light_condition,
        "resolution": image.resolution,
        "file_size_bytes": image.file_size_bytes,
        "format": image.format,
        "detection": detection_info,
    }

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import format_utc_datetime, parse_iso_datetime
from app.models.detection import Detection
from app.models.image import Image


async def list_diseases(
    db: AsyncSession,
    device_id: str,
    start: str | None = None,
    end: str | None = None,
    limit: int = 100,
) -> list[dict]:
    q = select(Detection).where(Detection.device_id == device_id)
    if start:
        q = q.where(Detection.timestamp >= parse_iso_datetime(start))
    if end:
        q = q.where(Detection.timestamp <= parse_iso_datetime(end))
    q = q.order_by(Detection.timestamp.desc()).limit(limit)
    result = await db.execute(q)
    dets = result.scalars().all()

    import json
    output = []
    for d in dets:
        image_url = None
        img_result = await db.execute(select(Image.url).where(Image.image_id == d.image_id))
        url_row = img_result.first()
        if url_row:
            image_url = url_row[0]
        output.append({
            "detection_id": d.detection_id,
            "image_id": d.image_id,
            "timestamp": format_utc_datetime(d.timestamp),
            "disease_class": d.disease_class,
            "disease_name": d.disease_name,
            "confidence": d.confidence,
            "severity": d.severity,
            "bbox": json.loads(d.bbox) if d.bbox else None,
            "image_url": image_url,
        })
    return output


async def get_disease_stats(db: AsyncSession, device_id: str) -> dict:
    from sqlalchemy import func
    result = await db.execute(
        select(Detection.disease_class, func.count(Detection.detection_id), func.avg(Detection.confidence))
        .where(Detection.device_id == device_id)
        .group_by(Detection.disease_class)
        .order_by(func.count(Detection.detection_id).desc())
    )
    by_type = [
        {"class": row[0], "count": row[1], "avg_confidence": round(float(row[2]), 3) if row[2] else 0}
        for row in result
    ]
    total_result = await db.execute(
        select(func.count(Detection.detection_id)).where(Detection.device_id == device_id)
    )
    total = total_result.scalar() or 0
    return {"total_detections": total, "by_disease_type": by_type}

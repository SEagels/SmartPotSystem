from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.database import get_sessionmaker
from app.models.image import Image
from app.services.detection_service import compute_health_score, run_detection

logger = logging.getLogger(__name__)
_PROCESSING = False
_MAX_RETRIES = 3


async def start_image_processor(interval_s: int = 10):
    global _PROCESSING
    _PROCESSING = True
    while _PROCESSING:
        try:
            await process_pending_images()
        except Exception:
            logger.exception("Image processor loop error")
        await asyncio.sleep(interval_s)


async def stop_image_processor():
    global _PROCESSING
    _PROCESSING = False


async def process_pending_images():
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        result = await db.execute(
            select(Image).where(Image.detection_status == "pending_detection").limit(5)
        )
        images = list(result.scalars().all())

    for image in images:
        if not image.storage_path:
            continue

        async with sessionmaker() as db:
            try:
                result = await db.execute(select(Image).where(Image.image_id == image.image_id))
                img = result.scalar_one_or_none()
                if not img or img.detection_status != "pending_detection":
                    continue

                img.detection_status = "processing"
                await db.flush()

                detections = await run_detection(image.storage_path)
                health_score = await compute_health_score(detections)
                disease_count = len([d for d in detections if d.get("class") != "healthy"])

                from app.services.image_service import update_detection_result
                await update_detection_result(db, img.image_id, "completed", health_score, disease_count, detections)

                if disease_count > 0 and img.user_id:
                    from app.services.alert_service import create_alert
                    diseases_str = "、".join(
                        f"{d.get('name_zh', d.get('class'))}(置信度{d.get('confidence', 0):.0%})"
                        for d in detections if d.get("class") != "healthy"
                    )
                    await create_alert(
                        db, img.device_id, img.user_id,
                        "disease_detected", "warning",
                        "检测到病害",
                        f"您的植株在{img.timestamp.strftime('%H:%M') if img.timestamp else '未知时间'}的叶片图像中检测到：{diseases_str}",
                        img.image_id,
                    )

                await db.commit()
            except Exception:
                logger.exception(f"Detection failed for image {image.image_id}")
                try:
                    await db.rollback()
                    result = await db.execute(select(Image).where(Image.image_id == image.image_id))
                    img = result.scalar_one_or_none()
                    if img:
                        img.detection_status = "failed"
                    await db.commit()
                except Exception:
                    logger.exception(f"Failed to mark image {image.image_id} as failed")

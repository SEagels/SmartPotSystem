from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.models.image import Image
from app.services.detection_service import compute_health_score, run_detection
from app.services.image_preprocess_service import ImagePreprocessResult, preprocess_image_for_detection
from app.services.storage_service import STORAGE_DIR

logger = logging.getLogger(__name__)
_PROCESSING = False
_MAX_RETRIES = 3


def _detection_score(detections: list[dict]) -> float:
    if not detections:
        return 0.0
    diseases = [d for d in detections if d.get("class") != "healthy"]
    target = diseases or detections
    max_conf = max(float(d.get("confidence", 0) or 0) for d in target)
    avg_conf = sum(float(d.get("confidence", 0) or 0) for d in target) / max(len(target), 1)
    disease_bonus = min(len(diseases), 3) * 0.03
    healthy_penalty = 0.12 if not diseases else 0.0
    return max_conf * 0.7 + avg_conf * 0.3 + disease_bonus - healthy_penalty


def _choose_detection_result(
    original: list[dict],
    enhanced: list[dict] | None,
) -> tuple[list[dict], str]:
    if enhanced is None:
        return original, "original"

    original_score = _detection_score(original)
    enhanced_score = _detection_score(enhanced)
    original_diseases = sum(1 for d in original if d.get("class") != "healthy")
    enhanced_diseases = sum(1 for d in enhanced if d.get("class") != "healthy")
    enhanced_max_conf = max([float(d.get("confidence", 0) or 0) for d in enhanced] or [0.0])

    # Enhanced images must clearly beat the original. This keeps color/texture artifacts
    # from creating low-confidence false positives after luminance correction.
    if enhanced_score >= original_score + 0.08:
        return enhanced, "enhanced"
    if original_score < 0.30 and enhanced_score > 0.45:
        return enhanced, "enhanced"
    if original_diseases == 0 and enhanced_diseases > 0 and enhanced_max_conf >= 0.60:
        return enhanced, "enhanced"
    return original, "original"


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

        # Step 1: mark as processing under lock
        async with db_write_lock:
            async with sessionmaker() as db:
                try:
                    result = await db.execute(select(Image).where(Image.image_id == image.image_id))
                    img = result.scalar_one_or_none()
                    if not img or img.detection_status != "pending_detection":
                        continue
                    img.detection_status = "processing"
                    await db.flush()
                    stored_user_id = img.user_id
                    stored_device_id = img.device_id
                    stored_timestamp = img.timestamp
                except Exception:
                    logger.exception(f"Failed to mark image {image.image_id} as processing")
                    continue

        stored_image_id = image.image_id
        stored_path = image.storage_path

        # Step 2: preprocess image and run YOLO detection outside the lock
        original_fs_path = str(STORAGE_DIR / stored_path.replace("/static/images/", "", 1))
        preprocess_result: ImagePreprocessResult | None = None
        try:
            preprocess_result = await preprocess_image_for_detection(stored_path)
        except Exception:
            logger.exception(f"Image preprocessing failed for image {stored_image_id}; using original image")

        detections: list[dict] | None = None
        detection_source = "original"
        try:
            original_detections = await run_detection(original_fs_path)
            enhanced_detections = None
            if preprocess_result and preprocess_result.enhanced:
                enhanced_detections = await run_detection(preprocess_result.detection_path)
            detections, detection_source = _choose_detection_result(original_detections, enhanced_detections)
        except Exception:
            logger.exception(f"Detection inference failed for image {stored_image_id}")

        if detections is None:
            # Detection failed entirely — mark image as failed
            async with db_write_lock:
                async with sessionmaker() as db:
                    try:
                        result = await db.execute(select(Image).where(Image.image_id == stored_image_id))
                        img = result.scalar_one_or_none()
                        if img:
                            if preprocess_result:
                                img.quality_score = preprocess_result.quality_score
                                img.light_condition = preprocess_result.light_condition
                                if preprocess_result.enhanced_url:
                                    img.enhanced_url = preprocess_result.enhanced_url
                            img.detection_source = detection_source
                            img.detection_status = "failed"
                        await db.commit()
                    except Exception:
                        logger.exception(f"Failed to mark image {stored_image_id} as failed")
            continue

        health_score = await compute_health_score(detections)
        disease_count = len([d for d in detections if d.get("class") != "healthy"])

        # Step 3: write results under lock
        async with db_write_lock:
            async with sessionmaker() as db:
                try:
                    from app.services.image_service import update_detection_result
                    result = await db.execute(select(Image).where(Image.image_id == stored_image_id))
                    img = result.scalar_one_or_none()
                    if img and preprocess_result:
                        img.quality_score = preprocess_result.quality_score
                        img.light_condition = preprocess_result.light_condition
                        if preprocess_result.enhanced_url:
                            img.enhanced_url = preprocess_result.enhanced_url
                    if img:
                        img.detection_source = detection_source

                    await update_detection_result(db, stored_image_id, "completed", health_score, disease_count, detections)

                    if disease_count > 0 and stored_user_id:
                        from app.services.alert_service import create_alert
                        diseases_str = "、".join(
                            f"{d.get('name_zh', d.get('class'))}(置信度{d.get('confidence', 0):.0%})"
                            for d in detections if d.get("class") != "healthy"
                        )
                        await create_alert(
                            db, stored_device_id, stored_user_id,
                            "disease_detected", "warning",
                            "检测到病害",
                            f"您的植株在{stored_timestamp.strftime('%H:%M') if stored_timestamp else '未知时间'}的叶片图像中检测到：{diseases_str}",
                            stored_image_id,
                        )

                    await db.commit()
                except Exception:
                    logger.exception(f"Detection persistence failed for image {stored_image_id}")
                    try:
                        await db.rollback()
                        result = await db.execute(select(Image).where(Image.image_id == stored_image_id))
                        img = result.scalar_one_or_none()
                        if img:
                            img.detection_status = "failed"
                        await db.commit()
                    except Exception:
                        logger.exception(f"Failed to mark image {stored_image_id} as failed")

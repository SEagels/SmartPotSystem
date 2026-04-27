"""将 data/ 中的病害图片导入后端存储并运行推理，结果关联到 demo_user 的 SP000001 设备"""
import asyncio
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "images"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_sessionmaker
from app.services.detection_service import run_detection, compute_health_score

USER_1_ID = "11111111-1111-1111-1111-111111111111"
DEVICE_ID = "SP000001"


async def ingest():
    sm = get_sessionmaker()

    image_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    )
    if not image_files:
        print("data/ 目录下未找到图片文件")
        return

    print(f"找到 {len(image_files)} 张病害图片")

    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    for i, filename in enumerate(image_files):
        src_path = DATA_DIR / filename
        safe_name = filename.replace(" ", "_").replace("'", "").replace('"', "")
        if safe_name != filename:
            new_src = DATA_DIR / safe_name
            shutil.copy2(src_path, new_src)
            src_path = new_src

        device_storage = STORAGE_DIR / DEVICE_ID / today_str
        device_storage.mkdir(parents=True, exist_ok=True)
        dest_path = device_storage / safe_name
        shutil.copy2(src_path, dest_path)

        storage_rel_path = f"{DEVICE_ID}/{today_str}/{safe_name}"
        file_size = os.path.getsize(src_path)

        print(f"\n[{i+1}/{len(image_files)}] {safe_name}")

        detections = await run_detection(str(src_path))
        health_score = await compute_health_score(detections)
        disease_count = len([d for d in detections if d.get("class") != "healthy"])

        disease_summary = "、".join(
            f"{d.get('name_zh', d.get('class'))}({d.get('confidence', 0):.0%})"
            for d in detections
            if d.get("class") != "healthy"
        ) or "健康"

        print(f"  检测结果: {disease_summary} | 评分: {health_score}")

        async with sm() as db:
            from app.models.image import Image
            from app.models.detection import Detection
            from app.models.alert import Alert
            import json
            import uuid

            now = datetime.now(UTC)
            ts_str = now.strftime("%Y%m%d-%H%M%S")
            image_id = f"IMG-DISEASE-{i+1:03d}-{ts_str}"

            from sqlalchemy import select
            r = await db.execute(select(Image).where(Image.image_id == image_id))
            if r.scalar_one_or_none():
                print(f"  已存在，跳过")
                continue

            image = Image(
                image_id=image_id,
                device_id=DEVICE_ID,
                user_id=uuid.UUID(USER_1_ID),
                timestamp=now,
                photo_index=i + 1,
                burst_total=len(image_files),
                quality_score=0.85,
                light_condition="natural",
                resolution="1600x1200",
                file_size_bytes=file_size,
                format=safe_name.rsplit(".", 1)[-1].lower(),
                storage_path=str(dest_path),
                url=f"/static/images/{storage_rel_path}",
                detection_status="completed",
                health_score=health_score,
                disease_count=disease_count,
            )
            db.add(image)
            await db.flush()

            for j, det_data in enumerate(detections):
                det = Detection(
                    detection_id=f"DET-DISEASE-{i+1:03d}-{j+1}-{uuid.uuid4().hex[:8].upper()}",
                    image_id=image_id,
                    device_id=DEVICE_ID,
                    timestamp=now,
                    disease_class=det_data.get("class", "unknown"),
                    disease_name=det_data.get("name_zh", "未知"),
                    confidence=det_data.get("confidence", 0.0),
                    severity=det_data.get("severity"),
                    bbox=json.dumps(det_data.get("bbox")) if det_data.get("bbox") else None,
                    recommendation=det_data.get("recommendation"),
                    health_score=health_score,
                )
                db.add(det)

            if disease_count > 0:
                alert = Alert(
                    alert_id=f"ALT-DISEASE-{i+1:03d}",
                    device_id=DEVICE_ID,
                    user_id=uuid.UUID(USER_1_ID),
                    type="disease_detected",
                    severity="warning" if health_score < 60 else "info",
                    title=f"检测到{disease_summary[:30]}",
                    message=f"您的龟背竹(客厅)在导入的叶片图像中检测到：{disease_summary}。"[:500],
                    image_id=image_id,
                    is_read=False,
                    created_at=now,
                )
                db.add(alert)

            await db.commit()
            print(f"  已导入: image_id={image_id}, {len(detections)}个检测, 评分{health_score}")

    print(f"\n导入完成！共 {len(image_files)} 张图片")


if __name__ == "__main__":
    asyncio.run(ingest())

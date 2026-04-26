from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def create_alert(
    db: AsyncSession,
    device_id: str,
    user_id: uuid.UUID,
    type_: str,
    severity: str,
    title: str,
    message: str,
    image_id: str | None = None,
) -> Alert:
    ts = datetime.now(UTC)
    alert_id = f"ALT-{ts.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    alert = Alert(
        alert_id=alert_id,
        device_id=device_id,
        user_id=user_id,
        type=type_,
        severity=severity,
        title=title,
        message=message,
        image_id=image_id,
    )
    db.add(alert)
    await db.flush()
    return alert


async def list_alerts(
    db: AsyncSession,
    device_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Alert], int]:
    q = select(Alert).where(Alert.device_id == device_id)
    if status == "unread":
        q = q.where(Alert.is_read == False)
    elif status == "read":
        q = q.where(Alert.is_read == True)

    count_q = select(func.count(Alert.alert_id)).where(Alert.device_id == device_id)
    if status == "unread":
        count_q = count_q.where(Alert.is_read == False)
    elif status == "read":
        count_q = count_q.where(Alert.is_read == True)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars().all()), total


async def mark_read(db: AsyncSession, alert_id: str) -> Alert:
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise ValueError("告警不存在")
    alert.is_read = True
    await db.flush()
    return alert


async def mark_all_read(db: AsyncSession, device_id: str) -> int:
    result = await db.execute(
        update(Alert)
        .where(Alert.device_id == device_id, Alert.is_read == False)
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount

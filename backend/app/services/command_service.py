from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sessionmaker
from app.core.mqtt import mqtt_manager
from app.models.command import Command


async def send_water_command(db: AsyncSession, device_id: str, user_id: uuid.UUID, duration_ms: int = 5000) -> dict:
    cmd_id = f"CMD-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-WATER"
    cmd = Command(
        cmd_id=cmd_id,
        device_id=device_id,
        user_id=user_id,
        type="water",
        status="sent",
        request=json.dumps({"duration_ms": duration_ms}),
    )
    db.add(cmd)
    await db.flush()

    mqtt_manager.publish(
        f"smartpot/{device_id}/command/water",
        {"cmd_id": cmd_id, "duration_ms": duration_ms, "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
        qos=1,
    )

    asyncio.create_task(_ack_timeout(cmd_id, timeout_s=30))
    return {
        "cmd_id": cmd_id,
        "status": "sent",
        "timestamp": cmd.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def send_photo_command(db: AsyncSession, device_id: str, user_id: uuid.UUID, burst_count: int = 1) -> dict:
    cmd_id = f"CMD-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-PHOTO"
    cmd = Command(
        cmd_id=cmd_id,
        device_id=device_id,
        user_id=user_id,
        type="photo",
        status="sent",
        request=json.dumps({"burst_count": burst_count}),
    )
    db.add(cmd)
    await db.flush()

    mqtt_manager.publish(
        f"smartpot/{device_id}/command/photo",
        {"cmd_id": cmd_id, "burst_count": burst_count, "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
        qos=1,
    )

    asyncio.create_task(_ack_timeout(cmd_id, timeout_s=30))
    return {
        "cmd_id": cmd_id,
        "status": "sent",
        "timestamp": cmd.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def send_config_command(
    db: AsyncSession,
    device_id: str,
    user_id: uuid.UUID,
    config: dict,
) -> dict:
    cmd_id = f"CMD-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-CONFIG"
    cmd = Command(
        cmd_id=cmd_id,
        device_id=device_id,
        user_id=user_id,
        type="config",
        status="sent",
        request=json.dumps(config),
    )
    db.add(cmd)
    await db.flush()

    mqtt_manager.publish(
        f"smartpot/{device_id}/command/config",
        {"cmd_id": cmd_id, **config, "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
        qos=1,
    )

    asyncio.create_task(_ack_timeout(cmd_id, timeout_s=30))
    return {
        "cmd_id": cmd_id,
        "status": "sent",
        "timestamp": cmd.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def get_command_status(db: AsyncSession, device_id: str, cmd_id: str) -> dict:
    result = await db.execute(
        select(Command).where(Command.cmd_id == cmd_id, Command.device_id == device_id)
    )
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise ValueError("指令不存在")
    return {
        "cmd_id": cmd.cmd_id,
        "type": cmd.type,
        "status": cmd.status,
        "request": json.loads(cmd.request) if cmd.request else None,
        "response": json.loads(cmd.response) if cmd.response else None,
        "created_at": cmd.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": cmd.completed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if cmd.completed_at else None,
    }


async def _ack_timeout(cmd_id: str, timeout_s: int = 30):
    await asyncio.sleep(timeout_s)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await session.execute(select(Command).where(Command.cmd_id == cmd_id))
        cmd = result.scalar_one_or_none()
        if cmd and cmd.status == "sent":
            cmd.status = "timeout"
            cmd.completed_at = datetime.now(UTC)
            await session.commit()

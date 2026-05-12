"""
Photo scheduler: triggers timed photo capture for disease detection based
on each device's photo_schedule (e.g. ["08:00", "12:00", "16:00"]).

Checks every 30s and sends MQTT photo commands to devices whose schedule
matches the current time window.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.core.mqtt import mqtt_manager
from app.models.device import Device

logger = logging.getLogger(__name__)
_RUNNING = False

SCHEDULE_WINDOW_MIN = 2
PHOTO_COOLDOWN_MIN = 30


async def start_photo_scheduler(interval_s: int = 30):
    global _RUNNING
    _RUNNING = True
    while _RUNNING:
        try:
            await _check_schedules()
        except Exception:
            logger.exception("Photo scheduler error")
        await asyncio.sleep(interval_s)


async def stop_photo_scheduler():
    global _RUNNING
    _RUNNING = False


async def _check_schedules():
    sessionmaker = get_sessionmaker()
    async with db_write_lock:
        async with sessionmaker() as db:
            result = await db.execute(
                select(Device).where(
                    Device.user_id.isnot(None),
                    Device.photo_schedule.isnot(None),
                )
            )
            devices = result.scalars().all()

            now = datetime.now(UTC)
            current_minutes = now.hour * 60 + now.minute

            for device in devices:
                try:
                    await _check_device_schedule(db, device, now, current_minutes)
                except Exception:
                    logger.exception(f"Photo schedule failed for {device.device_id}")


async def _check_device_schedule(db, device, now, current_minutes):
    if not device.online:
        return

    try:
        schedule = json.loads(device.photo_schedule) if device.photo_schedule else []
    except (json.JSONDecodeError, TypeError):
        return

    if not schedule:
        return

    matched = False
    for time_str in schedule:
        try:
            parts = time_str.split(":")
            h, m = int(parts[0]), int(parts[1])
            scheduled_minutes = h * 60 + m
            if abs(current_minutes - scheduled_minutes) <= SCHEDULE_WINDOW_MIN:
                matched = True
                break
        except (ValueError, IndexError):
            continue

    if not matched:
        return

    # Check cooldown
    from app.models.command import Command

    cutoff = now - timedelta(minutes=PHOTO_COOLDOWN_MIN)
    cmd_result = await db.execute(
        select(Command).where(
            Command.device_id == device.device_id,
            Command.type == "photo",
            Command.created_at >= cutoff,
        )
    )
    if cmd_result.first():
        return

    cmd_id = f"CMD-AUTO-{now.strftime('%Y%m%d-%H%M%S')}-PHOTO"
    from app.models.command import Command as Cmd

    cmd = Cmd(
        cmd_id=cmd_id,
        device_id=device.device_id,
        type="photo",
        request=json.dumps({"burst_count": 1, "source": "scheduled"}),
        status="pending",
        created_at=now,
    )
    db.add(cmd)
    await db.flush()

    topic = f"smartpot/{device.device_id}/command/photo"
    mqtt_manager.publish(topic, {
        "cmd_id": cmd_id,
        "burst_count": 1,
        "source": "scheduled",
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    logger.info(f"Scheduled photo for {device.device_id}")

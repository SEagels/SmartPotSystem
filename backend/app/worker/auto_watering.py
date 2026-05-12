"""
Auto-watering worker: periodically checks telemetry against plant-specific
soil moisture thresholds and sends MQTT water commands to devices.

Runs every 60s to avoid missing telemetry windows while still being responsive.
"""
from __future__ import annotations

import asyncio
import json
import logging

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.core.mqtt import mqtt_manager
from app.models.device import Device
from app.models.plant import PlantType
from app.models.telemetry import Telemetry

logger = logging.getLogger(__name__)
_RUNNING = False

AUTO_WATER_COOLDOWN_S = 600  # min seconds between auto-waters per device


async def start_auto_watering(interval_s: int = 60):
    global _RUNNING
    _RUNNING = True
    while _RUNNING:
        try:
            await _check_and_water_all()
        except Exception:
            logger.exception("Auto-watering check error")
        await asyncio.sleep(interval_s)


async def stop_auto_watering():
    global _RUNNING
    _RUNNING = False


async def _check_and_water_all():
    sessionmaker = get_sessionmaker()
    async with db_write_lock:
        async with sessionmaker() as db:
            result = await db.execute(
                select(Device).where(
                    Device.user_id.isnot(None),
                    Device.plant_type.isnot(None),
                )
            )
            devices = result.scalars().all()

            for device in devices:
                try:
                    await _check_device(db, device)
                except Exception:
                    logger.exception(f"Auto-water check failed for {device.device_id}")


async def _check_device(db, device):
    plant_result = await db.execute(
        select(PlantType).where(PlantType.plant_type == device.plant_type)
    )
    plant = plant_result.scalar_one_or_none()
    if not plant or not plant.watering_cfg:
        return

    try:
        watering_cfg = json.loads(plant.watering_cfg)
    except (json.JSONDecodeError, TypeError):
        return

    trigger_moisture = watering_cfg.get("trigger_soil_moisture")
    if trigger_moisture is None:
        return

    telemetry_result = await db.execute(
        select(Telemetry)
        .where(Telemetry.device_id == device.device_id)
        .order_by(Telemetry.time.desc())
        .limit(1)
    )
    telemetry = telemetry_result.scalar_one_or_none()
    if not telemetry or telemetry.soil_moisture is None:
        return

    soil = telemetry.soil_moisture
    if soil >= trigger_moisture:
        return

    # Avoid spamming water commands
    from app.models.command import Command
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(seconds=AUTO_WATER_COOLDOWN_S)
    cmd_result = await db.execute(
        select(Command).where(
            Command.device_id == device.device_id,
            Command.type == "water",
            Command.created_at >= cutoff,
        )
    )
    if cmd_result.first():
        return

    if not device.online:
        return

    duration_ms = watering_cfg.get("default_duration_ms", 5000)

    from datetime import UTC as _UTC, datetime as _datetime
    cmd_id = f"CMD-AUTO-{_datetime.now(_UTC).strftime('%Y%m%d-%H%M%S')}-WATER"
    cmd = Command(
        cmd_id=cmd_id,
        device_id=device.device_id,
        type="water",
        request=json.dumps({"duration_ms": duration_ms, "source": "auto_threshold"}),
        status="pending",
        created_at=_datetime.now(_UTC),
    )
    db.add(cmd)
    await db.flush()

    topic = f"smartpot/{device.device_id}/command/water"
    mqtt_manager.publish(topic, {
        "cmd_id": cmd_id,
        "duration_ms": duration_ms,
        "source": "auto_threshold",
        "timestamp": _datetime.now(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    logger.info(
        f"Auto-water: {device.device_id} soil={soil:.1f}% "
        f"< trigger={trigger_moisture:.1f}% -> {duration_ms}ms"
    )

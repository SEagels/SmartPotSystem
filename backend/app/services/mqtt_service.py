from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.core.mqtt import mqtt_manager
from app.core.websocket_manager import ws_manager
from app.models.device import Device
from app.models.watering import WateringEvent

logger = logging.getLogger(__name__)


def setup_mqtt_handlers():
    mqtt_manager.subscribe("smartpot/+/telemetry", qos=0)
    mqtt_manager.subscribe("smartpot/+/status", qos=0)
    mqtt_manager.subscribe("smartpot/+/event/watering", qos=0)
    mqtt_manager.subscribe("smartpot/+/response/+", qos=0)

    mqtt_manager.on_message("smartpot/+/telemetry", _handle_telemetry)
    mqtt_manager.on_message("smartpot/+/status", _handle_device_status)
    mqtt_manager.on_message("smartpot/+/event/watering", _handle_watering_event)
    mqtt_manager.on_message("smartpot/+/response/+", _handle_command_response)


async def _handle_telemetry(topic: str, payload: dict):
    from app.services.telemetry_service import ingest_telemetry

    parts = topic.split("/")
    device_id = parts[1]
    logger.info(f"Telemetry received from {device_id}: temp={payload.get('sensors',{}).get('temperature')}")

    sessionmaker = get_sessionmaker()
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                telemetry = await ingest_telemetry(db, device_id, payload)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

            if user_id:
                await ws_manager.send_to_user(user_id, {
                    "event": "telemetry_update",
                    "device_id": device_id,
                    "timestamp": telemetry.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "payload": {
                        "temperature": telemetry.temperature,
                        "humidity": telemetry.humidity,
                        "soil_moisture": telemetry.soil_moisture,
                        "light_intensity": telemetry.light_intensity,
                    },
                })
    except Exception:
        logger.exception(f"Failed to handle telemetry from {device_id}")


async def _handle_device_status(topic: str, payload: dict):
    parts = topic.split("/")
    device_id = parts[1]
    online = payload.get("online", False)

    sessionmaker = get_sessionmaker()
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                from app.services.device_service import update_online_status
                await update_online_status(db, device_id, online, payload)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

            if user_id:
                await ws_manager.send_to_user(user_id, {
                    "event": "device_status",
                    "device_id": device_id,
                    "payload": {"online": online, "firmware_version": payload.get("firmware_version")},
                })

            if not online:
                from app.services.alert_service import create_alert
                async with db_write_lock:
                    async with sessionmaker() as db2:
                        result = await db2.execute(select(Device).where(Device.device_id == device_id))
                        dev = result.scalar_one_or_none()
                        if dev and dev.user_id:
                            await create_alert(
                                db2, device_id, dev.user_id, "device_offline", "warning",
                                "设备离线", f"设备 {device_id} 已离线",
                            )
                            await db2.commit()
    except Exception:
        logger.exception(f"Failed to handle device status from {device_id}")


async def _handle_watering_event(topic: str, payload: dict):
    parts = topic.split("/")
    device_id = parts[1]

    sessionmaker = get_sessionmaker()
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                event = WateringEvent(
                    event_id=f"WEVT-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{device_id}",
                    device_id=device_id,
                    timestamp=datetime.now(UTC),
                    trigger=payload.get("trigger", "auto_threshold"),
                    duration_ms=payload.get("duration_ms", 0),
                    water_pumped_ml=payload.get("water_pumped_ml", 0),
                    reason=payload.get("trigger", payload.get("reason", "auto_threshold")),
                    soil_moisture_before=payload.get("soil_moisture_before"),
                    soil_moisture_after=payload.get("soil_moisture_after"),
                )
                db.add(event)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

            if user_id:
                await ws_manager.send_to_user(user_id, {
                    "event": "watering_complete",
                    "device_id": device_id,
                    "payload": {"trigger": event.trigger, "duration_ms": event.duration_ms, "water_pumped_ml": event.water_pumped_ml},
                })
    except Exception:
        logger.exception(f"Failed to handle watering event from {device_id}")


async def _handle_command_response(topic: str, payload: dict):
    parts = topic.split("/")
    device_id = parts[1]
    cmd_type = parts[3]
    cmd_id = payload.get("cmd_id")

    if not cmd_id:
        return

    sessionmaker = get_sessionmaker()
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                from app.models.command import Command
                result = await db.execute(select(Command).where(Command.cmd_id == cmd_id))
                cmd = result.scalar_one_or_none()
                if cmd:
                    cmd.status = payload.get("status", "executed")
                    cmd.response = json.dumps(payload)
                    cmd.completed_at = datetime.now(UTC)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

            if user_id:
                await ws_manager.send_to_user(user_id, {
                    "event": "command_update",
                    "device_id": device_id,
                    "payload": {
                        "cmd_id": cmd_id,
                        "type": cmd_type,
                        "status": cmd.status if cmd else "unknown",
                        "response": payload,
                    },
                })
    except Exception:
        logger.exception(f"Failed to handle command response for {cmd_id}")

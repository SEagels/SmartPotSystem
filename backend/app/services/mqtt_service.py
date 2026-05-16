from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.core.mqtt import mqtt_manager
from app.core.websocket_manager import ws_manager
from app.models.device import Device
from app.models.plant import PlantType
from app.models.watering import WateringEvent
from app.services import command_service

logger = logging.getLogger(__name__)
_LAST_CONFIG_SYNC: dict[str, datetime] = {}
CONFIG_SYNC_INTERVAL = timedelta(minutes=5)


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
    _user_id = None
    _telemetry = None
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                _telemetry = await ingest_telemetry(db, device_id, payload)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                if device:
                    device.online = True
                    device.last_seen_at = _telemetry.time
                    if _telemetry.firmware_version:
                        device.firmware_version = _telemetry.firmware_version
                _user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

        if _user_id and _telemetry:
            await ws_manager.send_to_user(_user_id, {
                "event": "telemetry_update",
                "device_id": device_id,
                "timestamp": _telemetry.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "payload": {
                    "temperature": _telemetry.temperature,
                    "humidity": _telemetry.humidity,
                    "soil_moisture": _telemetry.soil_moisture,
                    "light_intensity": _telemetry.light_intensity,
                },
            })
    except Exception:
        logger.exception(f"Failed to handle telemetry from {device_id}")


async def _handle_device_status(topic: str, payload: dict):
    parts = topic.split("/")
    device_id = parts[1]
    online = payload.get("online", False)

    sessionmaker = get_sessionmaker()
    _user_id = None
    _is_online = online
    _fw = payload.get("firmware_version")
    _pump_running = payload.get("pump_running")
    should_sync_config = False
    try:
        async with db_write_lock:
            async with sessionmaker() as db:
                from app.services.device_service import update_online_status
                await update_online_status(db, device_id, online, payload)

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                _user_id = str(device.user_id) if device and device.user_id else None
                should_sync_config = bool(online and device and device.user_id and device.plant_type)
                if should_sync_config:
                    await _sync_runtime_config_if_needed(db, device)

                await db.commit()

        if _user_id:
            await ws_manager.send_to_user(_user_id, {
                "event": "device_status",
                "device_id": device_id,
                "payload": {
                    "online": _is_online,
                    "firmware_version": _fw,
                    "pump_running": _pump_running if _pump_running is not None else False,
                },
            })

        if not online and _user_id:
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


def _runtime_config_from_plant(plant: PlantType | None) -> dict | None:
    if not plant or not plant.watering_cfg:
        return None
    try:
        watering_cfg = json.loads(plant.watering_cfg)
    except (TypeError, json.JSONDecodeError):
        return None

    trigger = watering_cfg.get("trigger_soil_moisture")
    duration = watering_cfg.get("default_duration_ms")
    if trigger is None:
        return None
    return {
        "auto_water_enabled": True,
        "auto_water_soil_moisture_min": float(trigger),
        "soil_moisture_threshold": float(trigger),
        "auto_water_duration_ms": int(duration or 5000),
        "default_duration_ms": int(duration or 5000),
    }


async def _sync_runtime_config_if_needed(db, device: Device) -> None:
    now = datetime.now(UTC)
    last_sync = _LAST_CONFIG_SYNC.get(device.device_id)
    if last_sync and now - last_sync < CONFIG_SYNC_INTERVAL:
        return

    plant_result = await db.execute(select(PlantType).where(PlantType.plant_type == device.plant_type))
    config = _runtime_config_from_plant(plant_result.scalar_one_or_none())
    if not config:
        return

    device.soil_moisture_threshold = config["soil_moisture_threshold"]
    device.watering_max_duration_ms = config["auto_water_duration_ms"]
    await command_service.send_config_command(db, device.device_id, device.user_id, config)
    _LAST_CONFIG_SYNC[device.device_id] = now


async def _handle_watering_event(topic: str, payload: dict):
    parts = topic.split("/")
    device_id = parts[1]

    sessionmaker = get_sessionmaker()
    _user_id = None
    _ws_payload = None
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
                _user_id = str(device.user_id) if device and device.user_id else None

                _ws_payload = {"trigger": event.trigger, "duration_ms": event.duration_ms, "water_pumped_ml": event.water_pumped_ml}

                await db.commit()

        if _user_id and _ws_payload:
            await ws_manager.send_to_user(_user_id, {
                "event": "watering_complete",
                "device_id": device_id,
                "payload": _ws_payload,
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
    _user_id = None
    _cmd_status = None
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
                _cmd_status = cmd.status if cmd else "unknown"

                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                _user_id = str(device.user_id) if device and device.user_id else None

                await db.commit()

        if _user_id:
            await ws_manager.send_to_user(_user_id, {
                "event": "command_update",
                "device_id": device_id,
                "payload": {
                    "cmd_id": cmd_id,
                    "type": cmd_type,
                    "status": _cmd_status,
                    "response": payload,
                },
            })
    except Exception:
        logger.exception(f"Failed to handle command response for {cmd_id}")

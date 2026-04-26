from __future__ import annotations

import asyncio

from app.core.mqtt import mqtt_manager
from app.services.mqtt_service import setup_mqtt_handlers


async def start_telemetry_consumer():
    setup_mqtt_handlers()
    mqtt_manager.connect()


async def stop_telemetry_consumer():
    mqtt_manager.disconnect()

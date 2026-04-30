"""内嵌 MQTT Broker — 基于 amqtt 的轻量级 MQTT 3.1.1 代理

开发模式下无需外部 MQTT broker（EMQX/Mosquitto），随 FastAPI 进程启动即可。
仅监听 1883 端口，无认证，适合本地开发和 MVP 阶段使用。
"""
from __future__ import annotations

import asyncio
import logging

from amqtt.broker import Broker

logger = logging.getLogger(__name__)

_broker: Broker | None = None
_task: asyncio.Task | None = None


async def start_local_broker(host: str = "0.0.0.0", port: int = 1883):
    global _broker, _task
    config = {
        "listeners": {
            "default": {
                "type": "tcp",
                "bind": f"{host}:{port}",
                "max_connections": 50,
            },
        },
        "plugins": {
            "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True,
            },
        },
    }
    _broker = Broker(config)
    logger.info(f"Local MQTT broker starting on {host}:{port}...")
    _task = asyncio.create_task(_broker.start())
    await asyncio.sleep(0.5)
    logger.info(f"Local MQTT broker ready on {host}:{port}")


async def stop_local_broker():
    global _broker, _task
    if _broker:
        logger.info("Shutting down local MQTT broker...")
        await _broker.shutdown()
        _broker = None
    if _task and not _task.done():
        _task.cancel()
        _task = None

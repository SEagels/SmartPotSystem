# MQTT客户端封装层 —— 桥接Paho同步库与FastAPI异步世界
# 核心挑战：Paho MQTT是同步回调的，但处理器是async函数
# 解决方案：on_message中用run_coroutine_threadsafe将消息派发到asyncio事件循环
# Topic模式：smartpot/{device_id}/telemetry/sensors 等，使用单层通配符+做动态路由
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from app.config import settings

logger = logging.getLogger(__name__)


class MQTTManager:
    """MQTT连接管理器：封装paho-mqtt的订阅/发布/回调，桥接同步回调到异步处理器"""
    def __init__(self):
        # 每次启动生成唯一Client ID，避免Broker端会话残留冲突
        self._client = mqtt.Client(
            client_id=f"smartpot-server-{uuid.uuid4().hex[:8]}",
            protocol=mqtt.MQTTv311,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        # handler注册表：topic → async回调函数
        self._handlers: dict[str, Callable] = {}
        self._loop = None  # 首次connect时延迟获取事件循环

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """连接成功后自动重新订阅所有已注册的Topic（断线重连时也生效）"""
        if rc == 0:
            logger.info(f"MQTT connected to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            for topic in self._handlers:
                client.subscribe(topic, qos=1)
                logger.info(f"MQTT subscribed: {topic}")
        else:
            logger.warning(f"MQTT connect failed: rc={rc}")

    def _match_topic(self, pattern: str, topic: str) -> bool:
        """MQTT topic 通配符匹配：+ 匹配单层，# 匹配多层"""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")
        for i, pp in enumerate(pattern_parts):
            if pp == "#":
                return True  # # 匹配剩余所有层级
            if pp == "+":
                if i >= len(topic_parts):
                    return False
                continue  # + 匹配任意单层
            if i >= len(topic_parts) or pp != topic_parts[i]:
                return False
        return len(topic_parts) == len(pattern_parts)

    def _on_message(self, client, userdata, msg):
        """收到消息时：通配符匹配handler → JSON解析 → 投递到asyncio事件循环"""
        handler = None
        for pattern, h in self._handlers.items():
            if h and self._match_topic(pattern, msg.topic):
                handler = h
                break
        if handler:
            if self._loop is None:
                self._loop = asyncio.get_event_loop()
            payload = json.loads(msg.payload.decode())
            logger.debug(f"MQTT << {msg.topic}: {json.dumps(payload, ensure_ascii=False)[:200]}")
            asyncio.run_coroutine_threadsafe(handler(msg.topic, payload), self._loop)
        else:
            logger.warning(f"MQTT << {msg.topic}: NO HANDLER (patterns={list(self._handlers.keys())})")

    def subscribe(self, topic: str, qos: int = 1):
        """订阅Topic：注册到handler表（不覆盖已绑定的处理器），若已连接则立即订阅"""
        self._handlers.setdefault(topic, None)
        if self._client.is_connected():
            self._client.subscribe(topic, qos=qos)

    def on_message(self, topic: str, handler: Callable):
        """注册topic的消息处理器（Coroutine函数）"""
        self._handlers[topic] = handler
        logger.info(f"MQTT handler registered: {topic}")

    def connect(self):
        """建立MQTT连接并启动消息循环（loop_start在后台线程中运行）"""
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        logger.info(f"MQTT connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
        self._client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT)
        self._client.loop_start()

    def disconnect(self):
        """优雅断开MQTT连接"""
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: dict[str, Any], qos: int = 1):
        """发布消息到指定Topic（JSON序列化后发送）"""
        self._client.publish(topic, json.dumps(payload), qos=qos)


# 全局单例：整个应用共享一个MQTT连接
mqtt_manager = MQTTManager()

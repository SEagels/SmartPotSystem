# MQTT客户端封装层 —— 桥接Paho同步库与FastAPI异步世界
# 核心挑战：Paho MQTT是同步回调的，但处理器是async函数
# 解决方案：on_message中用run_coroutine_threadsafe将消息派发到asyncio事件循环
# Topic模式：smartpot/{device_id}/telemetry/sensors 等，使用单层通配符+做动态路由
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from app.config import settings


class MQTTManager:
    """MQTT连接管理器：封装paho-mqtt的订阅/发布/回调，桥接同步回调到异步处理器"""
    def __init__(self):
        # 每次启动生成唯一Client ID，避免Broker端会话残留冲突
        self._client = mqtt.Client(
            client_id=f"smartpot-server-{uuid.uuid4().hex[:8]}",
            protocol=mqtt.MQTTv5,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        # handler注册表：topic → async回调函数
        self._handlers: dict[str, Callable] = {}
        # 保存事件循环引用，用于跨线程投递协程
        self._loop = asyncio.get_event_loop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """连接成功后自动重新订阅所有已注册的Topic（断线重连时也生效）"""
        if reason_code == 0:
            for topic in self._handlers:
                client.subscribe(topic, qos=1)

    def _on_message(self, client, userdata, msg):
        """收到消息时：JSON解析 → 查找handler → 线程安全投递到asyncio事件循环"""
        handler = self._handlers.get(msg.topic)
        if handler:
            payload = json.loads(msg.payload.decode())
            # 关键：paho回调在独立线程，必须用run_coroutine_threadsafe投递async函数
            asyncio.run_coroutine_threadsafe(handler(msg.topic, payload), self._loop)

    def subscribe(self, topic: str, qos: int = 1):
        """订阅Topic：先注册占位（handler稍后通过on_message绑定），若已连接则立即订阅"""
        self._handlers[topic] = None  # 占位，确保断线重连时自动续订
        if self._client.is_connected():
            self._client.subscribe(topic, qos=qos)

    def on_message(self, topic: str, handler: Callable):
        """注册topic的消息处理器（Coroutine函数）"""
        self._handlers[topic] = handler

    def connect(self):
        """建立MQTT连接并启动消息循环（loop_start在后台线程中运行）"""
        self._client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT)
        self._client.loop_start()  # 非阻塞网络循环

    def disconnect(self):
        """优雅断开MQTT连接"""
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: dict[str, Any], qos: int = 1):
        """发布消息到指定Topic（JSON序列化后发送）"""
        self._client.publish(topic, json.dumps(payload), qos=qos)


# 全局单例：整个应用共享一个MQTT连接
mqtt_manager = MQTTManager()

# WebSocket连接管理器 —— 基于用户ID的广播路由
# 设计：一个用户可多端连接（App+网页同时在线），消息按user_id广播到所有连接
# 数据流：MQTT收到设备数据 → 查device表获取user_id → send_to_user推送到该用户所有WS连接
from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """管理WebSocket连接：按用户ID分组，支持多端连接和广播推送"""
    def __init__(self):
        # user_id → [WebSocket, ...] 一个用户可同时持有多个连接
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        """接受WebSocket连接请求并注册到用户组"""
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        """移除断开连接，若用户无剩余连接则清理用户条目"""
        sockets = self._connections.get(user_id, [])
        if ws in sockets:
            sockets.remove(ws)
        if not sockets:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """向指定用户的所有连接广播消息；发送失败时自动清理断连"""
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id, ws)  # 客户端已断开，静默清理

    async def close_all(self) -> None:
        """应用关闭时优雅断开所有WebSocket连接"""
        for user_id in list(self._connections):
            for ws in self._connections.get(user_id, []):
                try:
                    await ws.close()
                except Exception:
                    pass  # 忽略已关闭连接的异常
        self._connections.clear()


# 全局单例：整个应用共享一个连接管理器实例
ws_manager = ConnectionManager()

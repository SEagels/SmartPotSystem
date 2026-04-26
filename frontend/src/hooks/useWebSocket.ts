import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';

type WsEventHandler = (event: string, deviceId: string, payload: unknown) => void;

// ── WebSocket 连接管理 Hook ──
// 设计意图：将 WebSocket 生命周期与 React 组件绑定，自动处理连接/重连/清理
//   认证方式：Token 通过 query string 传递（后端 WS 中间件解析验证）
//   重连策略：onclose 触发后 5 秒自动重连，避免服务端重启时洪水式重连
//   协议选择：根据页面 https/http 自动选 wss/ws（生产环境 HTTPS 需 wss）
//   注意事项：connect 依赖 onEvent 引用——调用方须用 useCallback 包裹，否则每次 render 都会重建 WS
export function useWebSocket(onEvent: WsEventHandler) {
  const { token } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (!token) return;
    // 根据页面协议自动选 wss/ws，HTTPS 页面用 ws:// 会被浏览器阻断
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const url = `${protocol}//${host}:8000/v1/ws?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {};

    // 后端推送统一格式 { event, device_id, payload }
    // 解析后委托给调用方——不同页面按需处理不同 event 类型
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        onEvent(msg.event, msg.device_id, msg.payload);
      } catch {
        // 忽略解析失败（如非 JSON 的控制帧或心跳包）
      }
    };

    ws.onclose = () => {
      // 断线 5 秒后重连，避免立即重连加重服务端压力
      reconnectRef.current = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      // onerror 后主动 close，触发 onclose 走统一重连流程
      ws.close();
    };
  }, [token, onEvent]);

  useEffect(() => {
    connect();
    // 清理函数：组件卸载时关闭连接 + 取消排队中的重连定时器
    // 防止内存泄漏和"幽灵连接"继续更新已卸载组件
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}

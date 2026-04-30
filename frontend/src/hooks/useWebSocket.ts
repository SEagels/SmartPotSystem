import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';

type WsEventHandler = (event: string, deviceId: string, payload: unknown) => void;

interface WsState {
  ws: WebSocket;
  refCount: number;
  listeners: Map<number, WsEventHandler>;
  reconnectTimer: ReturnType<typeof setTimeout> | null;
}

const _sockets = new Map<string, WsState>();
let _listenerId = 0;

function _buildUrl(token: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  return `${protocol}//${host}:8000/v1/ws?token=${token}`;
}

function _createConnection(token: string): WsState {
  const url = _buildUrl(token);
  const ws = new WebSocket(url);
  const state: WsState = { ws, refCount: 0, listeners: new Map(), reconnectTimer: null };

  const scheduleReconnect = () => {
    if (state.reconnectTimer) return;
    state.reconnectTimer = setTimeout(() => {
      state.reconnectTimer = null;
      if (state.refCount > 0) {
        const newState = _createConnection(token);
        newState.refCount = state.refCount;
        newState.listeners = state.listeners;
        _sockets.set(token, newState);
      }
    }, 5000);
  };

  ws.onopen = () => {};

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      state.listeners.forEach((fn) => fn(msg.event, msg.device_id, msg.payload));
    } catch {
      // ignore non-JSON frames
    }
  };

  ws.onclose = () => {
    if (state.refCount > 0) scheduleReconnect();
  };

  ws.onerror = () => {
    ws.close();
  };

  return state;
}

export function useWebSocket(onEvent: WsEventHandler) {
  const { token } = useAuth();
  const idRef = useRef(++_listenerId);
  const stateRef = useRef<WsState | null>(null);

  // connect / disconnect on token change
  useEffect(() => {
    if (!token) return;
    const id = idRef.current;

    let state = _sockets.get(token);
    if (!state) {
      state = _createConnection(token);
      _sockets.set(token, state);
    }

    state.refCount++;
    state.listeners.set(id, onEvent);
    stateRef.current = state;

    return () => {
      const s = stateRef.current;
      if (!s) return;
      s.listeners.delete(id);
      s.refCount--;
      if (s.refCount <= 0) {
        if (s.reconnectTimer) {
          clearTimeout(s.reconnectTimer);
          s.reconnectTimer = null;
        }
        s.ws.close();
        _sockets.delete(token);
      }
    };
  }, [token]);

  // update listener callback in-place without reconnecting
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  useEffect(() => {
    const state = stateRef.current;
    if (!state) return;
    state.listeners.set(idRef.current, onEvent);
  }, [onEvent]);
}

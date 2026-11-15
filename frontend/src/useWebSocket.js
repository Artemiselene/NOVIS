/**
 * ASTRA MIND — Real-Time WebSocket Telemetry Hook
 * ===============================================
 * Connects to /api/extension/ws/telemetry with authenticated credentials.
 * Handles channel subscriptions, auto-reconnection, and incoming telemetry updates.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { getApiKey, api } from "./api";

function resolveWsUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  const base = api.getBaseUrl();
  try {
    const url = new URL(base, window.location.origin);
    const protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${url.host}${url.pathname.replace(/\/+$/, "")}/ws/telemetry`;
  } catch (_) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/api/extension/ws/telemetry`;
  }
}

export function useWebSocket({ astronautId, missionId, onMessage }) {
  const [status, setStatus] = useState("disconnected"); // 'connecting' | 'connected' | 'disconnected' | 'unauthorized'
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const backoffRef = useRef(1000);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    const key = getApiKey();
    if (!key) {
      setStatus("disconnected");
      return;
    }

    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setStatus("connecting");
    const wsEndpoint = `${resolveWsUrl()}?token=${encodeURIComponent(key)}`;

    try {
      const ws = new WebSocket(wsEndpoint);
      socketRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) return;
        setStatus("connected");
        backoffRef.current = 1000;

        // Apply channel subscriptions
        if (astronautId) {
          ws.send(JSON.stringify({ action: "subscribe_astronaut", astronaut_id: Number(astronautId) }));
        }
        if (missionId) {
          ws.send(JSON.stringify({ action: "subscribe_mission", mission_id: Number(missionId) }));
        }
      };

      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          if (onMessage) onMessage(data);
        } catch (_) {}
      };

      ws.onclose = (event) => {
        if (unmountedRef.current) return;
        socketRef.current = null;
        if (event.code === 1008) {
          setStatus("unauthorized");
          return;
        }
        setStatus("disconnected");

        // Exponential backoff auto-reconnect
        const delay = Math.min(backoffRef.current * 1.5, 10000);
        backoffRef.current = delay;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        if (socketRef.current) {
          socketRef.current.close();
        }
      };
    } catch (_) {
      setStatus("disconnected");
    }
  }, [astronautId, missionId, onMessage]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  // Handle dynamic channel updates when astronautId changes on open socket
  useEffect(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN && astronautId) {
      socketRef.current.send(JSON.stringify({ action: "subscribe_astronaut", astronaut_id: Number(astronautId) }));
    }
  }, [astronautId]);

  return { status, lastMessage, reconnect: connect };
}

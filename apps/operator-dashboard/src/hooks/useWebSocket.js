import { useEffect, useState, useRef } from "react";
import { apiConfig } from "../api/operatorApi";

export function useWebSocket(path, options = {}) {
  const { enabled = true, reconnectIntervalMs = 3000 } = options;
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const reconnectTimer = useRef(null);

  useEffect(() => {
    if (!enabled || apiConfig.useMockApi) {
      return;
    }

    function connect() {
      // Determine ws protocol based on api url
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = new URL(apiConfig.apiBaseUrl).host;
      const wsUrl = `${protocol}//${host}${path}`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        ws.current = null;
        // Schedule reconnect
        reconnectTimer.current = setTimeout(connect, reconnectIntervalMs);
      };

      ws.current.onerror = (event) => {
        setError(event);
        ws.current?.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [path, enabled, reconnectIntervalMs]);

  return { data, isConnected, error };
}

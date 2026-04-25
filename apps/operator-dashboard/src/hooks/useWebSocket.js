import { useEffect, useState, useRef } from "react";
import { apiConfig } from "../api/operatorApi";

/**
 * WebSocket hook with connection status tracking.
 *
 * Returns:
 *   - data: last parsed message
 *   - isConnected: true when the socket is open
 *   - connectionStatus: "connected" | "polling" | "reconnecting"
 *   - error: last error event (if any)
 */
export function useWebSocket(path, options = {}) {
  const { enabled = true, reconnectIntervalMs = 3000 } = options;
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("polling"); // "connected" | "polling" | "reconnecting"
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const hasConnectedBefore = useRef(false);

  useEffect(() => {
    if (!enabled || apiConfig.useMockApi) {
      setConnectionStatus("polling");
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
        setConnectionStatus("connected");
        setError(null);
        hasConnectedBefore.current = true;
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
        // If we had a connection before, show "reconnecting", otherwise "polling"
        setConnectionStatus(hasConnectedBefore.current ? "reconnecting" : "polling");
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

  return { data, isConnected, connectionStatus, error };
}

import { useCallback, useEffect, useRef } from "react";

import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationFrame } from "@/types/simulation";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

export function useSimulationSocket() {
  const setFrame = useSimulationStore((state) => state.setFrame);
  const setConnected = useSimulationStore((state) => state.setConnected);

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    const baseUrl = process.env.NEXT_PUBLIC_FASTAPI_WS_URL;
    if (!baseUrl) {
      setConnected(false);
      return;
    }

    const socket = new WebSocket(`${baseUrl}/ws/simulation`);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as SimulationFrame;
        setFrame(payload);
      } catch {
        // Ignore malformed payloads.
      }
    };

    socket.onclose = () => {
      setConnected(false);

      if (!shouldReconnectRef.current) {
        return;
      }

      if (retryRef.current >= MAX_RETRIES) {
        return;
      }

      const delay = BASE_DELAY_MS * Math.pow(2, retryRef.current);
      retryRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, [setConnected, setFrame]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      socketRef.current?.close();
    };
  }, [connect]);

  const sendCommand = useCallback((command: Record<string, unknown>) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(command));
    }
  }, []);

  return { sendCommand };
}

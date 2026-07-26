import { useCallback, useEffect, useRef } from "react";

import { useSimulationStore } from "@/store/simulationStore";
import type { TrainingMetric } from "@/types/simulation";
import { getFastApiUrls } from "@/lib/utils";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

export function useTrainingSocket() {
  const addTrainingMetric = useSimulationStore(
    (state) => state.addTrainingMetric,
  );
  const setTraining = useSimulationStore(
    (state) => state.setTraining,
  );

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const shouldReconnectRef = useRef(true);
  const connectRef = useRef<(() => void) | null>(null);

  const connect = useCallback(() => {
    const { wsUrl: baseUrl } = getFastApiUrls();
    if (!baseUrl) {
      console.error("[TrainWS] Missing NEXT_PUBLIC_FASTAPI_WS_URL environment variable.");
      return;
    }

    console.log("[TrainWS] Connecting to:", `${baseUrl}/ws/training`);
    const socket = new WebSocket(`${baseUrl}/ws/training`);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = 0;
      console.log("%c[TrainWS] Connected", "color:#22c55e;font-weight:bold", {
        url: `${baseUrl}/ws/training`,
      });
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        // Filter out checkpoint notification payloads
        if (payload && typeof payload === "object" && "type" in payload && payload.type === "checkpoint_saved") {
          console.log("[TrainWS] Checkpoint saved:", payload);
          return;
        }

        // Handle initial status sync response
        if (payload && typeof payload === "object" && "is_training" in payload && !("total_reward" in payload)) {
          setTraining(payload.is_training);
          return;
        }

        // Log every training message — they arrive only once per episode
        console.log(
          "%c[TrainWS] message",
          "color:#a78bfa;font-weight:bold",
          payload,
        );

        addTrainingMetric(payload as TrainingMetric);
      } catch (err) {
        console.warn("[TrainWS] Failed to parse message:", event.data, err);
      }
    };

    socket.onclose = (ev) => {
      console.log("%c[TrainWS] Disconnected", "color:#f97316;font-weight:bold", {
        code: ev.code,
        reason: ev.reason || "(none)",
        wasClean: ev.wasClean,
        url: `${baseUrl}/ws/training`,
        hint: ev.code === 1006
          ? "Abnormal closure — backend unreachable or rejected the connection (check CORS_ORIGINS on Render)"
          : ev.code === 1015
          ? "TLS handshake failed — make sure you use wss:// not ws:// for production"
          : undefined,
      });
      if (!shouldReconnectRef.current) {
        return;
      }

      if (retryRef.current >= MAX_RETRIES) {
        return;
      }

      const delay = BASE_DELAY_MS * Math.pow(2, retryRef.current);
      retryRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        connectRef.current?.();
      }, delay);
    };

    socket.onerror = () => {
      console.error(
        "[TrainWS] Connection error — waiting for close event with details.",
        { url: `${baseUrl}/ws/training` },
      );
      socket.close();
    };
  }, [addTrainingMetric, setTraining]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

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
      console.log("%c[TrainWS] → SENDING COMMAND:", "color:#94a3b8;font-weight:bold", command);
      socketRef.current.send(JSON.stringify(command));
    } else {
      console.warn("[TrainWS] Cannot send command, socket not open. State:", socketRef.current?.readyState);
    }
  }, []);

  return { sendCommand };
}

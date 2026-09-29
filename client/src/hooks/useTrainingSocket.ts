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
  const setTrainingStatus = useSimulationStore(
    (state) => state.setTrainingStatus,
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
      setTrainingStatus("Training service connected");
      console.log("%c[TrainWS] Connected", "color:#22c55e;font-weight:bold", {
        url: `${baseUrl}/ws/training`,
      });
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        // Handle lifecycle/progress events separately from episode metrics.
        if (payload && typeof payload === "object" && "type" in payload) {
          console.log("[TrainWS] Notification:", payload);
          const message = typeof payload.message === "string" ? payload.message : null;
          if (payload.type === "training_error") {
            setTraining(Boolean(payload.is_training));
            setTrainingStatus(message, message ?? "Training failed");
          } else if (
            payload.type === "training_request_received" ||
            payload.type === "training_started" ||
            payload.type === "warmup_progress"
          ) {
            setTraining(true);
            setTrainingStatus(message);
          } else if (payload.type === "warmup_complete") {
            setTrainingStatus(message ?? "Warm-up complete; starting episode 1...");
          } else if (payload.type === "checkpoint_saved") {
            setTrainingStatus(`Checkpoint saved at episode ${payload.episode ?? "?"}`);
          }
          return;
        }

        // Handle initial status sync response
        if (payload && typeof payload === "object" && "is_training" in payload && !("total_reward" in payload)) {
          setTraining(payload.is_training);
          return;
        }

        // Only add valid training metrics
        if (payload && typeof payload === "object" && ("episode" in payload || "total_reward" in payload)) {
          console.log(
            "%c[TrainWS] metric",
            "color:#a78bfa;font-weight:bold",
            payload,
          );
          addTrainingMetric(payload as TrainingMetric);
          setTrainingStatus(`Training episode ${payload.episode}`);
        }
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
      setTrainingStatus("Training service disconnected", "WebSocket disconnected");

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
  }, [addTrainingMetric, setTraining, setTrainingStatus]);

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

  const sendCommand = useCallback((command: Record<string, unknown>): boolean => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      console.log("%c[TrainWS] → SENDING COMMAND:", "color:#94a3b8;font-weight:bold", command);
      socketRef.current.send(JSON.stringify(command));
      return true;
    } else {
      console.warn("[TrainWS] Cannot send command, socket not open. State:", socketRef.current?.readyState);
      setTraining(false);
      setTrainingStatus(
        "Training command was not sent",
        "The training WebSocket is not connected. Restart the backend and refresh this page.",
      );
      return false;
    }
  }, [setTraining, setTrainingStatus]);

  return { sendCommand };
}

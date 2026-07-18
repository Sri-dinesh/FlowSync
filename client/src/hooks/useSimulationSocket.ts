import { useCallback, useEffect, useRef } from "react";

import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationFrame } from "@/types/simulation";
import { getFastApiUrls } from "@/lib/utils";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

export function useSimulationSocket() {
  const setFrame = useSimulationStore((state) => state.setFrame);
  const setConnected = useSimulationStore((state) => state.setConnected);

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
      console.error("[SimWS] Missing NEXT_PUBLIC_FASTAPI_WS_URL environment variable.");
      setConnected(false);
      return;
    }

    console.log("[SimWS] Connecting to:", `${baseUrl}/ws/simulation`);
    const socket = new WebSocket(`${baseUrl}/ws/simulation`);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = 0;
      setConnected(true);
      console.log("%c[SimWS] Connected", "color:#22c55e;font-weight:bold", {
        url: `${baseUrl}/ws/simulation`,
      });
    };

    socket.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        if (!raw || typeof raw !== "object") {
          return;
        }

        // Extract queue lengths from the backend nested QueueState dictionary
        const queue_lengths: Record<string, number> = {};
        if (raw.queues && typeof raw.queues === "object") {
          Object.entries(raw.queues).forEach(([key, val]) => {
            if (val && typeof val === "object") {
              queue_lengths[key] = (val as Record<string, unknown>).length as number ?? 0;
            }
          });
        }

        // Determine the overall active signal color (green, yellow, or red)
        let signal_color: "green" | "yellow" | "red" = "red";
        if (raw.signal) {
          if (raw.signal.is_transitioning) {
            const hasYellow = Object.values(raw.signal.color_per_lane ?? {}).some(
              (c) => c === "yellow",
            );
            signal_color = hasYellow ? "yellow" : "red";
          } else {
            signal_color = "green";
          }
        }

        const payload: SimulationFrame = {
          ...raw,
          signal_phase: raw.signal?.current_phase ?? 0,
          signal_color: signal_color,
          queue_lengths: queue_lengths,
          avg_wait_time: raw.metrics?.avg_wait_time ?? 0,
          throughput: raw.metrics?.throughput_total ?? 0,
          reward: raw.rl?.reward ?? 0,
        };

        // Log all raw frames in development/local server environment
        if (process.env.NODE_ENV === "development") {
          console.log("[SimWS Received Data]:", payload);
        }

        // Log the very first frame received
        if (payload.timestep === 0) {
          console.log("%c[SimWS] First frame received", "color:#38bdf8;font-weight:bold", payload);
        }

        // Log every 20th frame so the console isn't flooded (10 Hz × 20 = every 2 s)
        if (payload.timestep % 20 === 0) {
          console.log(
            "%c[SimWS] frame",
            "color:#38bdf8;font-weight:bold",
            {
              timestep: payload.timestep,
              mode: payload.mode,
              signal_phase: payload.signal_phase,
              signal_color: payload.signal_color,
              vehicles: payload.vehicles.length,
              queue_lengths: payload.queue_lengths,
              avg_wait_time: payload.avg_wait_time,
              throughput: payload.throughput,
              reward: payload.reward,
              episode: payload.episode,
              _vehicles: payload.vehicles,
            },
          );
        }

        setFrame(payload);
      } catch (err) {
        console.warn("[SimWS] Failed to parse message:", event.data, err);
      }
    };

    socket.onclose = (ev) => {
      setConnected(false);
      console.log("%c[SimWS] Disconnected", "color:#f97316;font-weight:bold", {
        code: ev.code,
        reason: ev.reason || "(none)",
        wasClean: ev.wasClean,
        url: `${baseUrl}/ws/simulation`,
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
      // onerror always fires before onclose — the close event has the real code/reason.
      // Log the URL so it's easy to spot a misconfigured env var.
      console.error(
        "[SimWS] Connection error — waiting for close event with details.",
        { url: `${baseUrl}/ws/simulation` },
      );
      socket.close();
    };
  }, [setConnected, setFrame]);

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
      console.log("%c[SimWS] → SENDING COMMAND:", "color:#94a3b8;font-weight:bold", command);
      socketRef.current.send(JSON.stringify(command));
    } else {
      console.warn("[SimWS] Cannot send command, socket not open. State:", socketRef.current?.readyState);
    }
  }, []);

  return { sendCommand };
}

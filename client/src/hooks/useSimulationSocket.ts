import { useCallback, useEffect, useRef, useState } from "react";

import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationFrame } from "@/types/simulation";
import { getFastApiUrls } from "@/lib/utils";

export interface SimBenchmarkResult {
  total_passed: number;
  avg_wait_time: number;
  max_queue: number;
  duration_seconds: number;
}

export interface SimBenchmarkResultsData {
  duration_seconds: number;
  results: Record<string, SimBenchmarkResult>;
  winner: string | null;
  modes: string[];
  improvements?: Record<string, number>;
}

export interface SimBenchmarkProgress {
  current_mode: string;
  elapsed?: number;
  duration_seconds?: number;
  mode_index?: number;
  modes_total?: number;
  modes_done?: string[];
  completed_mode?: string;
  result?: SimBenchmarkResult;
}

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

export function useSimulationSocket() {
  const setFrame = useSimulationStore((state) => state.setFrame);
  const setConnected = useSimulationStore((state) => state.setConnected);

  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkProgress, setBenchmarkProgress] = useState<SimBenchmarkProgress | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<SimBenchmarkResultsData | null>(null);

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

        // Handle benchmark messages
        if (raw.type === "benchmark_progress") {
          setBenchmarkRunning(true);
          setBenchmarkProgress({
            current_mode: raw.current_mode,
            elapsed: raw.elapsed ?? 0,
            duration_seconds: raw.duration_seconds ?? 30,
            mode_index: raw.mode_index ?? 0,
            modes_total: raw.modes_total ?? 3,
            modes_done: raw.modes_done ?? [],
            completed_mode: raw.completed_mode,
            result: raw.result,
          });
          return;
        }

        if (raw.type === "benchmark_results") {
          setBenchmarkRunning(false);
          setBenchmarkProgress(null);
          setBenchmarkResults(raw as SimBenchmarkResultsData);
          return;
        }

        // Skip non-simulation-frame messages (errors, pipeline_status, etc.)
        const NON_FRAME_TYPES = new Set([
          "error",
          "pipeline_status",
          "video_progress",
          "cctv_frame",
        ]);
        if (raw.type && NON_FRAME_TYPES.has(raw.type)) {
          if (raw.code === "BENCHMARK_FAILED") {
            setBenchmarkRunning(false);
            setBenchmarkProgress(null);
          }
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
          rl: raw.rl ?? null,
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

  const startBenchmark = useCallback((durationSeconds: number = 30) => {
    setBenchmarkResults(null);
    setBenchmarkProgress(null);
    setBenchmarkRunning(true);
    sendCommand({
      command: "run_timed_benchmark",
      duration_seconds: durationSeconds,
      modes: ["fixed", "greedy", "ai"],
    });
  }, [sendCommand]);

  const stopBenchmark = useCallback(() => {
    setBenchmarkRunning(false);
    setBenchmarkProgress(null);
    sendCommand({ command: "stop" });
  }, [sendCommand]);

  const resetBenchmark = useCallback(() => {
    setBenchmarkResults(null);
    setBenchmarkProgress(null);
    setBenchmarkRunning(false);
  }, []);

  return {
    sendCommand,
    benchmarkRunning,
    benchmarkProgress,
    benchmarkResults,
    startBenchmark,
    stopBenchmark,
    resetBenchmark,
  };
}

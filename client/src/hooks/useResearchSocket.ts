"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useResearchStore } from "@/store/researchStore";
import { getFastApiUrls } from "@/lib/utils";
import type {
  ResearchTelemetryFrame,
  PairedTelemetryFrame,
  ExperimentSummary,
  NoisePresetKey,
} from "@/types/research";

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 500;

export function useResearchSocket() {
  const setFrame = useResearchStore((s) => s.setFrame);
  const setPairedFrame = useResearchStore((s) => s.setPairedFrame);
  const setRunStatus = useResearchStore((s) => s.setRunStatus);
  const setExperimentSummary = useResearchStore((s) => s.setExperimentSummary);
  const setPairedSummary = useResearchStore((s) => s.setPairedSummary);
  const speedMultiplier = useResearchStore((s) => s.speedMultiplier);

  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);
  const connectRef = useRef<(() => void) | null>(null);

  const connect = useCallback(() => {
    const { wsUrl: baseUrl } = getFastApiUrls();
    if (!baseUrl) {
      console.warn("[ResearchWS] Missing FASTAPI_WS_URL.");
      setIsConnected(false);
      return;
    }

    const wsUrl = `${baseUrl}/ws/research`;
    console.log("[ResearchWS] Connecting to:", wsUrl);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      retryRef.current = 0;
      setIsConnected(true);
      console.log("%c[ResearchWS] Connected", "color:#22c55e;font-weight:bold");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || typeof data !== "object") return;

        if (data.type === "research_frame") {
          setFrame(data as ResearchTelemetryFrame);
        } else if (data.type === "paired_telemetry") {
          setPairedFrame(data as PairedTelemetryFrame);
        } else if (data.type === "experiment_started" || data.type === "paired_started") {
          setRunStatus("running");
        } else if (data.type === "experiment_completed") {
          setRunStatus("completed");
          if (data.result) {
            setExperimentSummary(data.result as ExperimentSummary);
          }
        } else if (data.type === "paired_completed") {
          setRunStatus("completed");
          if (data.summary) {
            setPairedSummary(data.summary);
          }
        } else if (data.type === "experiment_paused") {
          setRunStatus("paused");
        } else if (data.type === "experiment_resumed") {
          setRunStatus("running");
        } else if (data.type === "experiment_stopped") {
          setRunStatus("idle");
        } else if (data.type === "experiment_error") {
          setRunStatus("error", data.error || "Experiment error occurred");
        }
      } catch (err) {
        console.warn("[ResearchWS] Failed to parse message:", event.data, err);
      }
    };

    socket.onclose = (ev) => {
      setIsConnected(false);
      console.log("%c[ResearchWS] Disconnected", "color:#f97316;font-weight:bold", ev.code);

      if (!shouldReconnectRef.current) return;
      if (retryRef.current >= MAX_RETRIES) return;

      const delay = BASE_DELAY_MS * Math.pow(2, retryRef.current);
      retryRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        connectRef.current?.();
      }, delay);
    };

    socket.onerror = (err) => {
      console.error("[ResearchWS] Error:", err);
      socket.close();
    };
  }, [setFrame, setPairedFrame, setRunStatus, setExperimentSummary, setPairedSummary]);

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

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(cmd));
    } else {
      console.warn("[ResearchWS] Cannot send command, socket closed.");
    }
  }, []);

  const startExperiment = useCallback(
    (
      scenarioId: string,
      controller: any,
      seed: number,
      noisePreset: NoisePresetKey = "clean",
      speed: number = speedMultiplier,
    ) => {
      const ctrlId =
        typeof controller === "object" && controller !== null
          ? controller.id || controller.name || "flowsync_uq"
          : controller || "flowsync_uq";
      setRunStatus("running");
      useResearchStore.getState().resetRun();
      sendCommand({
        command: "start_experiment",
        scenario_id: scenarioId,
        controller: ctrlId,
        seed,
        noise_preset: noisePreset,
        speed,
      });
    },
    [sendCommand, setRunStatus, speedMultiplier]
  );

  const startPairedComparison = useCallback(
    (
      scenarioId: string,
      controllerA: any = "d3qn",
      controllerB: any = "flowsync_uq",
      seed: number = 1101,
      noisePreset: NoisePresetKey = "miss_30",
      speed: number = speedMultiplier,
    ) => {
      const ctrlAId =
        typeof controllerA === "object" && controllerA !== null
          ? controllerA.id || controllerA.name || "d3qn"
          : controllerA || "d3qn";
      const ctrlBId =
        typeof controllerB === "object" && controllerB !== null
          ? controllerB.id || controllerB.name || "flowsync_uq"
          : controllerB || "flowsync_uq";
      setRunStatus("running");
      useResearchStore.getState().setPairedMode(true, ctrlAId, ctrlBId);
      useResearchStore.getState().resetRun();
      sendCommand({
        command: "start_paired_comparison",
        scenario_id: scenarioId,
        controller_a: ctrlAId,
        controller_b: ctrlBId,
        seed,
        noise_preset: noisePreset,
        speed,
      });
    },
    [sendCommand, setRunStatus, speedMultiplier]
  );

  const pause = useCallback(() => {
    sendCommand({ command: "pause" });
  }, [sendCommand]);

  const resume = useCallback(() => {
    sendCommand({ command: "resume" });
  }, [sendCommand]);

  const stop = useCallback(() => {
    sendCommand({ command: "stop" });
    setRunStatus("idle");
  }, [sendCommand, setRunStatus]);

  return {
    isConnected,
    startExperiment,
    startPairedComparison,
    pause,
    resume,
    stop,
    sendCommand,
  };
}

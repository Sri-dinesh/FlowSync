"use client";

import { useCallback, useEffect } from "react";
import { useResearchStore } from "@/store/researchStore";
import { getFastApiUrls } from "@/lib/utils";
import type {
  ResearchTelemetryFrame,
  PairedTelemetryFrame,
  ExperimentSummary,
  NoisePresetKey,
} from "@/types/research";

const MAX_RETRIES = 6;
const BASE_DELAY_MS = 600;

// Shared singleton WebSocket across all component consumers
let globalSocket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let retryCount = 0;
let isConnecting = false;
const messageQueue: string[] = [];
let activeListenersCount = 0;
let startTimeoutTimer: ReturnType<typeof setTimeout> | null = null;

function ensureResearchSocket() {
  if (typeof window === "undefined") return;

  if (globalSocket) {
    if (globalSocket.readyState === WebSocket.OPEN || globalSocket.readyState === WebSocket.CONNECTING) {
      return;
    }
  }

  if (isConnecting) return;
  isConnecting = true;

  const { wsUrl: baseUrl } = getFastApiUrls();
  if (!baseUrl) {
    console.warn("[ResearchWS] Missing base WebSocket URL.");
    useResearchStore.getState().setIsWsConnected(false);
    isConnecting = false;
    return;
  }

  const wsUrl = `${baseUrl}/ws/research`;
  console.log("[ResearchWS] Initializing shared singleton connection to:", wsUrl);

  try {
    const socket = new WebSocket(wsUrl);
    globalSocket = socket;

    socket.onopen = () => {
      isConnecting = false;
      retryCount = 0;
      useResearchStore.getState().setIsWsConnected(true);
      console.log("%c[ResearchWS] Connected (Singleton)", "color:#22c55e;font-weight:bold");

      // Flush queued messages
      if (messageQueue.length > 0) {
        console.log(`[ResearchWS] Flushing ${messageQueue.length} queued commands`);
        while (messageQueue.length > 0) {
          const msg = messageQueue.shift();
          if (msg) socket.send(msg);
        }
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || typeof data !== "object") return;

        const store = useResearchStore.getState();

        if (data.type === "research_frame" || data.type === "replay_frame") {
          store.setFrame(data as ResearchTelemetryFrame);
        } else if (data.type === "paired_telemetry") {
          store.setPairedFrame(data as PairedTelemetryFrame);
        } else if (
          data.type === "experiment_started" ||
          data.type === "paired_started" ||
          data.type === "replay_started"
        ) {
          if (startTimeoutTimer) {
            clearTimeout(startTimeoutTimer);
            startTimeoutTimer = null;
          }
          store.setRunStatus("running");
        } else if (data.type === "experiment_completed" || data.type === "replay_completed") {
          store.setRunStatus("completed");
          if (data.result) {
            store.setExperimentSummary(data.result as ExperimentSummary);
          }
        } else if (data.type === "paired_completed") {
          store.setRunStatus("completed");
          if (data.summary) {
            store.setPairedSummary(data.summary);
          }
        } else if (data.type === "experiment_paused") {
          store.setRunStatus("paused");
        } else if (data.type === "experiment_resumed") {
          store.setRunStatus("running");
        } else if (data.type === "experiment_stopped") {
          store.setRunStatus("idle");
        } else if (data.type === "experiment_error") {
          if (startTimeoutTimer) {
            clearTimeout(startTimeoutTimer);
            startTimeoutTimer = null;
          }
          store.setRunStatus("error", data.error || "Experiment execution error");
        }
      } catch (err) {
        console.warn("[ResearchWS] Failed to parse message:", event.data, err);
      }
    };

    socket.onclose = (ev) => {
      isConnecting = false;
      globalSocket = null;
      useResearchStore.getState().setIsWsConnected(false);
      console.log("%c[ResearchWS] Disconnected", "color:#f97316;font-weight:bold", ev.code);

      if (activeListenersCount > 0 && retryCount < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * Math.pow(1.5, retryCount);
        retryCount += 1;
        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
          ensureResearchSocket();
        }, delay);
      }
    };

    socket.onerror = (err) => {
      console.error("[ResearchWS] Socket Error:", err);
      isConnecting = false;
      try {
        socket.close();
      } catch {
        // ignore close error
      }
    };
  } catch (err) {
    isConnecting = false;
    console.error("[ResearchWS] Failed to create WebSocket:", err);
  }
}

function sendResearchCommand(cmd: Record<string, unknown>) {
  const payload = JSON.stringify(cmd);
  if (globalSocket?.readyState === WebSocket.OPEN) {
    globalSocket.send(payload);
  } else {
    console.log("[ResearchWS] Socket not yet ready, queueing command:", cmd.command);
    messageQueue.push(payload);
    ensureResearchSocket();
  }
}

export function useResearchSocket() {
  const isConnected = useResearchStore((s) => s.isWsConnected);
  const runStatus = useResearchStore((s) => s.runStatus);
  const speedMultiplier = useResearchStore((s) => s.speedMultiplier);

  useEffect(() => {
    activeListenersCount += 1;
    ensureResearchSocket();

    return () => {
      activeListenersCount = Math.max(0, activeListenersCount - 1);
      // We purposefully DO NOT close globalSocket here so sibling components
      // or subsequent route transitions preserve the stream without abrupt resets
    };
  }, []);

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    sendResearchCommand(cmd);
  }, []);

  const startExperiment = useCallback(
    (
      scenarioId: string,
      controller: string | { id?: string; name?: string } = "flowsync_uq",
      seed: number = 1101,
      noisePreset: NoisePresetKey = "clean",
      speed: number = speedMultiplier,
    ) => {
      const ctrlId =
        typeof controller === "object" && controller !== null
          ? controller.id || controller.name || "flowsync_uq"
          : controller || "flowsync_uq";

      // Reset previous run data and transition to starting state
      const store = useResearchStore.getState();
      store.resetRun();
      store.setRunStatus("starting");

      // Set fallback safeguard: if backend fails to respond within 5s, revert to idle
      if (startTimeoutTimer) clearTimeout(startTimeoutTimer);
      startTimeoutTimer = setTimeout(() => {
        if (useResearchStore.getState().runStatus === "starting") {
          console.warn("[ResearchWS] start_experiment timed out waiting for backend confirmation.");
          useResearchStore.getState().setRunStatus("error", "Simulation start timed out. Please check backend status.");
        }
      }, 5000);

      sendResearchCommand({
        command: "start_experiment",
        scenario_id: scenarioId,
        controller: ctrlId,
        seed,
        noise_preset: noisePreset,
        speed,
      });
    },
    [speedMultiplier]
  );

  const startPairedComparison = useCallback(
    (
      scenarioId: string,
      controllerA: string | { id?: string; name?: string } = "d3qn",
      controllerB: string | { id?: string; name?: string } = "flowsync_uq",
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

      const store = useResearchStore.getState();
      store.resetRun();
      store.setPairedMode(true, ctrlAId, ctrlBId);
      store.setRunStatus("starting");

      if (startTimeoutTimer) clearTimeout(startTimeoutTimer);
      startTimeoutTimer = setTimeout(() => {
        if (useResearchStore.getState().runStatus === "starting") {
          useResearchStore.getState().setRunStatus("error", "Paired comparison start timed out.");
        }
      }, 5000);

      sendResearchCommand({
        command: "start_paired_comparison",
        scenario_id: scenarioId,
        controller_a: ctrlAId,
        controller_b: ctrlBId,
        seed,
        noise_preset: noisePreset,
        speed,
      });
    },
    [speedMultiplier]
  );

  const pause = useCallback(() => {
    sendResearchCommand({ command: "pause" });
  }, []);

  const resume = useCallback(() => {
    sendResearchCommand({ command: "resume" });
  }, []);

  const stop = useCallback(() => {
    if (startTimeoutTimer) {
      clearTimeout(startTimeoutTimer);
      startTimeoutTimer = null;
    }
    sendResearchCommand({ command: "stop" });
    useResearchStore.getState().setRunStatus("idle");
  }, []);

  const replayRun = useCallback(
    (runId: string, speed: number = speedMultiplier) => {
      const store = useResearchStore.getState();
      store.resetRun();
      store.setExperimentId(runId);
      store.setRunStatus("starting");

      if (startTimeoutTimer) clearTimeout(startTimeoutTimer);
      startTimeoutTimer = setTimeout(() => {
        if (useResearchStore.getState().runStatus === "starting") {
          useResearchStore.getState().setRunStatus("error", "Replay start timed out. Please check backend status.");
        }
      }, 5000);

      sendResearchCommand({ command: "replay_run", run_id: runId, speed });
    },
    [speedMultiplier]
  );

  const setSpeed = useCallback((speed: number) => {
    sendResearchCommand({ command: "set_speed", speed });
  }, []);

  const seek = useCallback((step: number) => {
    sendResearchCommand({ command: "seek", step });
  }, []);

  const reset = useCallback(() => {
    stop();
    useResearchStore.getState().resetRun();
  }, [stop]);

  return {
    isConnected,
    runStatus,
    sendCommand,
    startExperiment,
    startPairedComparison,
    replayRun,
    setSpeed,
    seek,
    pause,
    resume,
    stop,
    reset,
  };
}

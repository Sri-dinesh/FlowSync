"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import BenchmarkResults, { BenchmarkResultsData } from "./BenchmarkResults";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationFrame } from "@/types/simulation";

const SimulationCanvas = dynamic(
  () => import("@/components/simulation/SimulationCanvas"),
  { ssr: false }
);

export interface VehicleArrivalEvent {
  vehicle_id: string;
  time_s: number;
  lane: string;
  turn: string;
  vehicle_type: string;
}

export interface TwinData {
  session_id: string;
  total_frames_processed: number;
  total_vehicles_detected: number;
  video_duration_s?: number;
  arrivals?: VehicleArrivalEvent[];
  aggregate_counts: Record<string, number>;
  peak_counts: Record<string, number>;
  avg_counts: Record<string, number>;
}

export interface RLModel {
  id: string;
  name: string;
  version: string;
  source?: string;
  episodes?: number;
}

interface DigitalTwinShowdownProps {
  twinData?: TwinData | null;
  initialCounts?: Record<string, number> | null;
  sessionId?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL || "http://127.0.0.1:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";

type BenchmarkState = "idle" | "running" | "done";

export default function DigitalTwinShowdown({
  twinData,
  initialCounts,
  sessionId,
}: DigitalTwinShowdownProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [injecting, setInjecting] = useState(false);
  const [benchmarkState, setBenchmarkState] = useState<BenchmarkState>("idle");
  const [benchmarkProgress, setBenchmarkProgress] = useState<{
    current_mode: string;
    modes_done: string[];
    modes_total: number;
    elapsed?: number;
    spawned_count?: number;
    total_vehicles?: number;
    passed_count?: number;
    is_realworld?: boolean;
  } | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResultsData | null>(null);
  const [scenarioCounts, setScenarioCounts] = useState<Record<string, number> | null>(null);

  // Model selection states
  const [models, setModels] = useState<RLModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [isLoadingModel, setIsLoadingModel] = useState<boolean>(false);
  const [loadedModelName, setLoadedModelName] = useState<string | null>(null);
  const [loadSuccess, setLoadSuccess] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fetch models list on mount
  useEffect(() => {
    async function fetchModels() {
      try {
        const res = await fetch(`${API_BASE}/training/models`);
        if (res.ok) {
          const payload = await res.json();
          const list: RLModel[] = payload.models ?? [];
          setModels(list);
          if (list.length > 0) {
            setSelectedModelId(list[0].id);
            setLoadedModelName(`${list[0].name} (ep ${list[0].version})`);
          }
        }
      } catch {
        // ignore
      }
    }
    fetchModels();
  }, []);

  const handleLoadModel = async (modelId: string) => {
    if (!modelId || modelId === "__none") return;
    setIsLoadingModel(true);
    setLoadError(null);
    setLoadSuccess(false);
    try {
      const res = await fetch(`${API_BASE}/training/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId }),
      });
      if (res.ok) {
        const target = models.find((m) => m.id === modelId);
        if (target) {
          setLoadedModelName(`${target.name} (ep ${target.version})`);
        }
        setLoadSuccess(true);
        setTimeout(() => setLoadSuccess(false), 3000);
      } else {
        const p = await res.json().catch(() => null);
        setLoadError(p?.detail ?? "Failed to load model.");
      }
    } catch {
      setLoadError("Unable to reach backend server.");
    } finally {
      setIsLoadingModel(false);
    }
  };

  // Access simulation store so this page feeds the 3-D canvas during benchmark
  const setStoreFrame = useSimulationStore((s) => s.setFrame);
  const setStoreConnected = useSimulationStore((s) => s.setConnected);
  const setStoreRunning = useSimulationStore((s) => s.setRunning);

  // Connect to simulation WebSocket
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/simulation`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsWsConnected(true);
      setStoreConnected(true);
    };
    ws.onclose = () => {
      setIsWsConnected(false);
      setStoreConnected(false);
      setStoreRunning(false);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || typeof data !== "object") return;

        if (data.type === "benchmark_progress") {
          setBenchmarkProgress({
            current_mode: data.current_mode,
            modes_done: data.modes_done ?? [],
            modes_total: data.modes_total ?? 3,
            elapsed: data.elapsed ?? 0,
            spawned_count: data.spawned_count ?? 0,
            total_vehicles: data.total_vehicles ?? 0,
            passed_count: data.passed_count ?? 0,
            is_realworld: data.is_realworld ?? false,
          });
        } else if (data.type === "benchmark_results") {
          setBenchmarkResults(data as BenchmarkResultsData);
          setBenchmarkState("done");
          setBenchmarkProgress(null);
          setStoreRunning(false);
        } else if (
          // Treat everything else with vehicles array as a simulation frame
          Array.isArray(data.vehicles)
        ) {
          // Build queue_lengths from nested QueueState objects
          const queue_lengths: Record<string, number> = {};
          if (data.queues && typeof data.queues === "object") {
            Object.entries(data.queues).forEach(([key, val]) => {
              if (val && typeof val === "object") {
                queue_lengths[key] = (val as Record<string, unknown>).length as number ?? 0;
              }
            });
          }
          let signal_color: "green" | "yellow" | "red" = "red";
          if (data.signal) {
            signal_color = data.signal.is_transitioning
              ? (Object.values(data.signal.color_per_lane ?? {}).some((c) => c === "yellow") ? "yellow" : "red")
              : "green";
          }
          const frame: SimulationFrame = {
            ...data,
            signal_phase: data.signal?.current_phase ?? 0,
            signal_color,
            queue_lengths,
            avg_wait_time: data.metrics?.avg_wait_time ?? 0,
            throughput: data.metrics?.throughput_total ?? 0,
            reward: data.rl?.reward ?? 0,
            rl: data.rl ?? null,
          };
          setStoreFrame(frame);
        }
      } catch {
        // ignore
      }
    };

    return () => {
      ws.close();
    };
  }, [setStoreFrame, setStoreConnected, setStoreRunning]);

  // Inject initial scenario when counts change
  useEffect(() => {
    if (!initialCounts) return;
    setScenarioCounts(initialCounts);
    injectScenario(initialCounts);
  }, [initialCounts]);

  const injectScenario = async (counts: Record<string, number>) => {
    setInjecting(true);
    try {
      await fetch(`${API_BASE}/simulation/scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ counts }),
      });
    } catch (err) {
      console.error("Failed to inject scenario", err);
    } finally {
      setInjecting(false);
    }
  };

  const sendWsCommand = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const handleRunBenchmark = useCallback(() => {
    if (benchmarkState === "running" || !isWsConnected) return;
    setBenchmarkState("running");
    setBenchmarkResults(null);
    setBenchmarkProgress(null);
    setStoreRunning(true);

    const arrivals = twinData?.arrivals && twinData.arrivals.length > 0 ? twinData.arrivals : null;

    sendWsCommand({
      command: "run_timed_benchmark",
      arrivals: arrivals,
      scenario_counts: !arrivals ? scenarioCounts : null,
      modes: ["fixed", "greedy", "ai"],
    });
  }, [twinData, scenarioCounts, benchmarkState, isWsConnected, sendWsCommand, setStoreRunning]);

  const handleRerun = useCallback(async () => {
    setBenchmarkState("idle");
    setBenchmarkResults(null);
    setBenchmarkProgress(null);
    if (scenarioCounts) {
      await injectScenario(scenarioCounts);
    }
  }, [scenarioCounts]);

  const handleStopBenchmark = useCallback(() => {
    sendWsCommand({ command: "stop" });
    setBenchmarkState("idle");
    setBenchmarkProgress(null);
    setStoreRunning(false);
  }, [sendWsCommand, setStoreRunning]);

  const arrivalsList = twinData?.arrivals ?? [];
  const hasArrivals = arrivalsList.length > 0;
  const totalVehicles = hasArrivals
    ? arrivalsList.length
    : Object.values(scenarioCounts ?? {}).reduce((a, b) => a + b, 0);

  const durationSpan = hasArrivals && arrivalsList.length > 0
    ? arrivalsList[arrivalsList.length - 1].time_s
    : twinData?.video_duration_s ?? 0;

  if (!initialCounts && !twinData) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-center gap-3 p-8">
        <div className="text-4xl mb-2">🎬</div>
        <p className="text-white/70 text-sm font-medium">No session loaded</p>
        <p className="text-white/30 text-xs max-w-xs leading-relaxed">
          Upload and process a video in the Live View tab. When processing completes,
          click "Open in Digital Twin" to load the vehicle data here.
        </p>
      </div>
    );
  }

  const MODE_LABELS: Record<string, string> = { fixed: "Fixed Timer", ai: "DQN AI", greedy: "Greedy" };
  const MODES_ORDER = ["fixed", "greedy", "ai"];

  return (
    <div className="flex flex-1 w-full h-full bg-[#0a0a0a] overflow-hidden">
      {/* ── Left Sidebar ── */}
      <div className="w-80 flex-shrink-0 border-r border-white/10 bg-black/40 flex flex-col overflow-y-auto">
        <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
          <h2 className="text-[11px] uppercase tracking-[0.14em] text-white/40 font-semibold">Digital Twin Replay</h2>
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-mono">
            {sessionId || twinData?.session_id || "Session"}
          </span>
        </div>

        <div className="p-4 flex flex-col gap-3.5 flex-1">
          {/* Traffic Profile Card */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Traffic Profile</span>
              <span className="text-[9px] text-emerald-400 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Chronological Influx
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.04]">
              <div className="bg-white/[0.03] border border-white/[0.05] rounded-lg p-2 flex flex-col">
                <span className="text-[8px] text-white/30 uppercase tracking-wider">Vehicles Logged</span>
                <span className="text-base font-bold font-mono text-white mt-0.5">{totalVehicles}</span>
              </div>
              <div className="bg-white/[0.03] border border-white/[0.05] rounded-lg p-2 flex flex-col">
                <span className="text-[8px] text-white/30 uppercase tracking-wider">Arrival Span</span>
                <span className="text-base font-bold font-mono text-indigo-300 mt-0.5">{durationSpan.toFixed(1)}s</span>
              </div>
            </div>

            <p className="text-[9.5px] text-white/40 leading-relaxed bg-white/[0.01] border border-white/[0.04] rounded-lg p-2">
              ℹ Replays vehicles dynamically at their exact recorded video timestamps. Simulation runs until <strong className="text-white/80">all {totalVehicles} vehicles clear the intersection</strong>.
            </p>
          </div>

          {/* Model Selector Card */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">DQN AI Controller</span>
              {loadedModelName ? (
                <span className="text-[9px] text-indigo-400 font-mono font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                  Loaded
                </span>
              ) : (
                <span className="text-[9px] text-amber-400 font-mono">Random Weights</span>
              )}
            </div>

            <div className="flex flex-col gap-1.5 pt-1 border-t border-white/[0.04]">
              <label className="text-[8.5px] text-white/30 uppercase tracking-wider">Select Checkpoint</label>
              <select
                value={selectedModelId}
                onChange={(e) => {
                  const id = e.target.value;
                  setSelectedModelId(id);
                  void handleLoadModel(id);
                }}
                disabled={benchmarkState === "running" || isLoadingModel}
                className="w-full bg-black/60 border border-white/15 rounded-lg px-2.5 py-1.5 text-xs text-white/90 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                {models.length === 0 ? (
                  <option value="">No trained models available</option>
                ) : (
                  models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} — ep {m.version} {m.source === "remote" ? "☁" : "💾"}
                    </option>
                  ))
                )}
              </select>
            </div>

            {isLoadingModel && (
              <span className="text-[9px] text-indigo-300 animate-pulse">Loading model checkpoint…</span>
            )}
            {loadSuccess && (
              <span className="text-[9px] text-emerald-400">✓ Model weights loaded successfully</span>
            )}
            {loadError && (
              <span className="text-[9px] text-rose-400">{loadError}</span>
            )}
          </div>

          {benchmarkState === "done" && benchmarkResults ? (
            <BenchmarkResults data={benchmarkResults} onRerun={handleRerun} />
          ) : (
            <>
              {/* Benchmark progress */}
              {benchmarkState === "running" && benchmarkProgress && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/[0.06] p-3.5 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-indigo-300 font-semibold uppercase tracking-wider">
                      Replaying: {MODE_LABELS[benchmarkProgress.current_mode] ?? benchmarkProgress.current_mode}
                    </span>
                    <span className="text-[10px] text-white/60 font-mono font-bold">
                      {benchmarkProgress.elapsed?.toFixed(1)}s
                    </span>
                  </div>

                  {/* Real-time clearance progress bar */}
                  {benchmarkProgress.total_vehicles && benchmarkProgress.total_vehicles > 0 ? (
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[9px] text-white/50">
                        <span>Cleared: {benchmarkProgress.passed_count ?? 0} / {benchmarkProgress.total_vehicles}</span>
                        <span className="font-mono text-indigo-300">
                          {Math.round(((benchmarkProgress.passed_count ?? 0) / benchmarkProgress.total_vehicles) * 100)}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/5">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300 rounded-full"
                          style={{
                            width: `${Math.min(100, Math.round(((benchmarkProgress.passed_count ?? 0) / benchmarkProgress.total_vehicles) * 100))}%`,
                          }}
                        />
                      </div>
                      <div className="flex justify-between text-[8px] text-white/30">
                        <span>Spawned: {benchmarkProgress.spawned_count ?? 0}</span>
                        <span>Waiting in queue: {Math.max(0, (benchmarkProgress.spawned_count ?? 0) - (benchmarkProgress.passed_count ?? 0))}</span>
                      </div>
                    </div>
                  ) : null}

                  {/* Mode Step indicators */}
                  <div className="space-y-1.5 pt-1 border-t border-white/[0.04]">
                    {MODES_ORDER.map((m) => {
                      const done = benchmarkProgress.modes_done.includes(m);
                      const active = m === benchmarkProgress.current_mode;
                      return (
                        <div key={m} className="flex items-center gap-2">
                          <div
                            className={`w-2 h-2 rounded-full flex-shrink-0 ${
                              done
                                ? "bg-emerald-400"
                                : active
                                ? "bg-indigo-400 animate-pulse"
                                : "bg-white/10"
                            }`}
                          />
                          <span
                            className={`text-[10px] ${
                              done ? "text-emerald-400" : active ? "text-white/90 font-semibold" : "text-white/30"
                            }`}
                          >
                            {MODE_LABELS[m] ?? m}
                          </span>
                          {done && <span className="text-emerald-400 text-[10px] ml-auto">✓</span>}
                          {active && <span className="text-indigo-400 text-[9px] ml-auto animate-pulse">Running…</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Run/Cancel benchmark button */}
              {benchmarkState === "running" ? (
                <div className="flex gap-2">
                  <div className="flex-1 py-2.5 px-3 rounded-xl text-xs uppercase tracking-wider font-bold bg-indigo-600/25 text-indigo-300 border border-indigo-500/30 flex items-center justify-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
                    <span>Replaying…</span>
                  </div>
                  <button
                    onClick={handleStopBenchmark}
                    className="px-3.5 py-2.5 rounded-xl text-xs uppercase tracking-wider font-bold bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition-all hover:scale-105 active:scale-95"
                    title="Stop and cancel replay"
                  >
                    ⏹ Stop
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleRunBenchmark}
                  disabled={injecting || !isWsConnected}
                  className={`w-full py-3 rounded-xl text-xs uppercase tracking-wider font-bold transition-all duration-200 ${
                    isWsConnected && !injecting
                      ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25 active:scale-[0.98]"
                      : "bg-white/[0.04] text-white/20 cursor-not-allowed border border-white/[0.06]"
                  }`}
                >
                  ▶ Run Full Comparison
                </button>
              )}

              {!isWsConnected && (
                <p className="text-[10px] text-rose-400/70 text-center">
                  ⚠ Simulation server disconnected
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Right Area (3D Canvas) ── */}
      <div className="flex-1 relative bg-[#111622]">
        {injecting && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <span className="text-white/70 text-sm animate-pulse">Synchronizing digital twin scenario…</span>
          </div>
        )}
        <SimulationCanvas />
      </div>
    </div>
  );
}


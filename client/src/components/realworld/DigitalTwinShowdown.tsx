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

interface DigitalTwinShowdownProps {
  initialCounts: Record<string, number> | null;
  sessionId?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL || "http://127.0.0.1:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";

type BenchmarkState = "idle" | "running" | "done";

export default function DigitalTwinShowdown({
  initialCounts,
  sessionId,
}: DigitalTwinShowdownProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [injecting, setInjecting] = useState(false);
  const [durationSeconds, setDurationSeconds] = useState(120);
  const [benchmarkState, setBenchmarkState] = useState<BenchmarkState>("idle");
  const [benchmarkProgress, setBenchmarkProgress] = useState<{
    current_mode: string;
    modes_done: string[];
    modes_total: number;
  } | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResultsData | null>(null);
  const [scenarioCounts, setScenarioCounts] = useState<Record<string, number> | null>(null);

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

  // Inject scenario when counts change
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
    if (!scenarioCounts || benchmarkState === "running" || !isWsConnected) return;
    setBenchmarkState("running");
    setBenchmarkResults(null);
    setBenchmarkProgress(null);
    sendWsCommand({
      command: "run_timed_benchmark",
      duration_seconds: durationSeconds,
      scenario_counts: scenarioCounts,
      modes: ["fixed", "ai", "greedy"],
    });
  }, [scenarioCounts, benchmarkState, isWsConnected, durationSeconds, sendWsCommand]);

  const handleRerun = useCallback(async () => {
    setBenchmarkState("idle");
    setBenchmarkResults(null);
    if (scenarioCounts) {
      await injectScenario(scenarioCounts);
    }
  }, [scenarioCounts]);

  if (!initialCounts) {
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

  const totalVehicles = Object.values(scenarioCounts ?? {}).reduce((a, b) => a + b, 0);
  const MODE_LABELS: Record<string, string> = { fixed: "Fixed Timer", ai: "DQN AI", greedy: "Greedy" };
  const MODES_ORDER = ["fixed", "ai", "greedy"];

  return (
    <div className="flex flex-1 w-full h-full bg-[#0a0a0a] overflow-hidden">
      {/* ── Left Sidebar ── */}
      <div className="w-72 flex-shrink-0 border-r border-white/10 bg-black/40 flex flex-col overflow-y-auto">
        <div className="p-4 border-b border-white/[0.06]">
          <h2 className="text-[11px] uppercase tracking-[0.14em] text-white/35 font-semibold">Digital Twin</h2>
        </div>

        <div className="p-4 flex flex-col gap-4 flex-1">
          {/* Scenario summary */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-white/35 uppercase tracking-wider font-medium">Loaded Scenario</span>
              {injecting && <span className="text-[9px] text-blue-400 animate-pulse">Injecting…</span>}
            </div>
            <div className="grid grid-cols-2 gap-1">
              {Object.entries(scenarioCounts ?? {})
                .filter(([, v]) => v > 0)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 8)
                .map(([lane, count]) => (
                  <div key={lane} className="flex justify-between text-[10px]">
                    <span className="text-white/30 truncate">{lane.replace("_", " ")}</span>
                    <span className="text-white/60 font-mono ml-1">{count}</span>
                  </div>
                ))}
            </div>
            <div className="mt-2 pt-2 border-t border-white/[0.06] flex justify-between text-[10px]">
              <span className="text-white/30">Total vehicles</span>
              <span className="text-white/80 font-bold font-mono">{totalVehicles}</span>
            </div>
          </div>

          {benchmarkState === "done" && benchmarkResults ? (
            <BenchmarkResults data={benchmarkResults} onRerun={handleRerun} />
          ) : (
            <>
              {/* Timer input */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <label className="text-[10px] text-white/35 uppercase tracking-wider font-medium block mb-2">
                  Simulation Duration
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={30}
                    max={300}
                    step={10}
                    value={durationSeconds}
                    onChange={(e) => setDurationSeconds(Number(e.target.value))}
                    className="flex-1 accent-indigo-500 h-1"
                    disabled={benchmarkState === "running"}
                  />
                  <span className="text-white/70 text-sm font-bold font-mono w-12 text-right">
                    {durationSeconds}s
                  </span>
                </div>
                <p className="text-[9px] text-white/20 mt-1">All 3 modes will run for this duration</p>
              </div>

              {/* Benchmark progress */}
              {benchmarkState === "running" && benchmarkProgress && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-3">
                  <p className="text-[10px] text-indigo-300 font-semibold mb-2">
                    Running: {MODE_LABELS[benchmarkProgress.current_mode] ?? benchmarkProgress.current_mode}
                  </p>
                  <div className="space-y-1">
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
                              done ? "text-emerald-400" : active ? "text-white/80" : "text-white/25"
                            }`}
                          >
                            {MODE_LABELS[m] ?? m}
                          </span>
                          {done && <span className="text-emerald-400 text-[10px] ml-auto">✓</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Run benchmark button */}
              <button
                onClick={handleRunBenchmark}
                disabled={injecting || benchmarkState === "running" || !isWsConnected || !scenarioCounts}
                className={`w-full py-3 rounded-xl text-sm font-bold transition-all duration-200 ${
                  benchmarkState === "running"
                    ? "bg-indigo-600/40 text-indigo-300 cursor-not-allowed animate-pulse"
                    : isWsConnected && scenarioCounts && !injecting
                    ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/30"
                    : "bg-white/[0.04] text-white/20 cursor-not-allowed border border-white/[0.06]"
                }`}
              >
                {benchmarkState === "running"
                  ? "⏳ Running benchmark…"
                  : "▶ Run Full Comparison"}
              </button>

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
            <span className="text-white/70 text-sm animate-pulse">Injecting traffic snapshot…</span>
          </div>
        )}
        <SimulationCanvas />
      </div>
    </div>
  );
}

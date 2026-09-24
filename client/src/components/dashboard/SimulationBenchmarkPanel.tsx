"use client";

import { useMemo, useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Trophy,
  Play,
  Square,
  RotateCcw,
  Clock,
  Target,
  Bot,
  Activity,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import type { SimBenchmarkProgress, SimBenchmarkResultsData } from "@/hooks/useSimulationSocket";

interface SimulationBenchmarkPanelProps {
  running: boolean;
  progress: SimBenchmarkProgress | null;
  results: SimBenchmarkResultsData | null;
  onStart: (durationSeconds: number, modes?: string[], modelId?: string, modelEpisode?: number) => void;
  onStop: () => void;
  onReset: () => void;
}

const PRESET_DURATIONS = [15, 30, 60, 120];

const BENCHMARK_MODES = ["ai", "fixed", "greedy"];

const MODE_CONFIG: Record<
  string,
  { label: string; shortLabel: string; icon: any; barColor: string }
> = {
  ai: {
    label: "FlowSync DQN AI",
    shortLabel: "DQN AI",
    icon: Bot,
    barColor: "#6366F1",
  },
  fixed: {
    label: "Fixed Timer",
    shortLabel: "FIXED",
    icon: Clock,
    barColor: "#64748B",
  },
  greedy: {
    label: "Greedy Policy",
    shortLabel: "GREEDY",
    icon: Target,
    barColor: "#10B981",
  },
};

interface RLModelOption {
  id: string;
  name: string;
  version: string;
  episodes?: number;
  source?: string;
}

export default function SimulationBenchmarkPanel({
  running,
  progress,
  results,
  onStart,
  onStop,
  onReset,
}: SimulationBenchmarkPanelProps) {
  const [duration, setDuration] = useState<number>(15);
  const [models, setModels] = useState<RLModelOption[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    async function fetchModels() {
      try {
        const res = await fetch(`${API_BASE}/training/models`);
        if (res.ok) {
          const payload = await res.json();
          const list: RLModelOption[] = payload.models ?? [];
          setModels(list);
          if (list.length > 0) {
            setSelectedModelId((prev) => prev || list[0].id);
          }
        }
      } catch (err) {
        console.warn("Failed to fetch models for benchmark:", err);
      }
    }
    fetchModels();
  }, [API_BASE]);

  const chartData = useMemo(() => {
    if (!results || !results.results) return [];
    return [
      {
        metric: "Vehicles Passed",
        ...Object.fromEntries(results.modes.map((m) => [m, results.results[m]?.total_passed ?? 0])),
      },
      {
        metric: "Avg Wait (s)",
        ...Object.fromEntries(results.modes.map((m) => [m, results.results[m]?.avg_wait_time ?? 0])),
      },
      {
        metric: "Max Queue",
        ...Object.fromEntries(results.modes.map((m) => [m, results.results[m]?.max_queue ?? 0])),
      },
    ];
  }, [results]);

  const winnerLabel = useMemo(() => {
    if (!results?.winner) return null;
    return MODE_CONFIG[results.winner]?.label ?? results.winner.toUpperCase();
  }, [results]);

  return (
    <div className="space-y-3.5 text-white">
      {/* 1. CONFIGURATION VIEW */}
      {!running && !results && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              <span className="text-[10px] font-medium text-neutral-400">
                Benchmark Configuration
              </span>
            </div>
            <span className="text-[9px] font-mono text-neutral-500 bg-neutral-800 border border-neutral-700 px-2 py-0.5 rounded-md font-medium">
              3 Policies • Sequential
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400 font-medium flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-neutral-500" />
                Duration per Mode
              </span>
              <span className="font-mono text-sm font-medium text-white tracking-tight">
                {duration}s <span className="text-neutral-500 text-[10px] font-normal font-sans">({duration * 3}s total)</span>
              </span>
            </div>

            <div className="grid grid-cols-4 gap-1.5 p-1 bg-neutral-900 rounded-lg border border-neutral-800">
              {PRESET_DURATIONS.map((preset) => {
                const isSelected = duration === preset;
                return (
                  <button
                    key={preset}
                    onClick={() => setDuration(preset)}
                    className={`py-1.5 rounded-md text-xs font-mono font-medium transition-all ${
                      isSelected
                        ? "bg-neutral-800 text-white shadow-sm"
                        : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
                    }`}
                  >
                    {preset}s
                  </button>
                );
              })}
            </div>

            <div className="pt-1 px-1">
              <Slider
                min={10}
                max={120}
                step={5}
                value={[duration]}
                onValueChange={(val) => setDuration(val[0] ?? 15)}
                className="w-full"
              />
              <div className="flex justify-between text-[9px] font-mono text-neutral-600 mt-1">
                <span>10s</span>
                <span>60s</span>
                <span>120s</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 space-y-2">
            <div className="text-[9px] uppercase tracking-wider text-neutral-500 font-medium flex items-center justify-between">
              <span>Benchmark Pipeline</span>
              <span className="font-mono text-neutral-400 font-normal">{BENCHMARK_MODES.length} × {duration}s = {duration * BENCHMARK_MODES.length}s</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {BENCHMARK_MODES.map((m) => {
                const cfg = MODE_CONFIG[m];
                const Icon = cfg.icon;
                return (
                  <div
                    key={m}
                    className="flex flex-col items-center justify-center p-2 rounded-lg bg-neutral-800/50 border border-neutral-700 text-center"
                  >
                    <Icon className="w-3.5 h-3.5 text-neutral-500 mb-1" />
                    <span className="text-[10px] font-medium text-neutral-300">{cfg.shortLabel}</span>
                    <span className="text-[9px] font-mono text-neutral-500 mt-0.5">{duration}s</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* DQN AI Model Checkpoint Selector */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5 text-indigo-400" />
                DQN AI Model Selection
              </span>
              {(() => {
                const selected = models.find((m) => m.id === selectedModelId);
                return selected ? (
                  <span className="font-mono text-[10px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full font-medium">
                    {selected.episodes ?? selected.version} eps
                  </span>
                ) : null;
              })()}
            </div>

            <select
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
              className="w-full rounded-lg bg-neutral-950 border border-neutral-800 px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors font-medium"
            >
              {models.length === 0 ? (
                <option value="">Default FlowSync DQN (1000 eps checkpoint)</option>
              ) : (
                models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} — {m.episodes ?? m.version} eps ({m.source === "remote" ? "Cloud" : "Local"})
                  </option>
                ))
              )}
            </select>
            <p className="text-[10px] text-neutral-500 leading-tight">
              Choose which trained policy checkpoint the DQN AI agent will execute in this benchmark.
            </p>
          </div>

          <Button
            className="w-full py-6 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2"
            onClick={() => {
              const selected = models.find((m) => m.id === selectedModelId);
              let epNum: number | undefined;
              if (selected?.episodes) {
                epNum = Number(selected.episodes);
              } else if (selected?.version) {
                const parsed = parseInt(selected.version, 10);
                if (!isNaN(parsed)) epNum = parsed;
              }
              onStart(duration, BENCHMARK_MODES, selectedModelId || undefined, epNum);
            }}
          >
            <Play className="w-3.5 h-3.5 fill-black" />
            Launch Benchmark ({duration * BENCHMARK_MODES.length}s)
          </Button>
        </div>
      )}

      {/* 2. LIVE RUNNING TELEMETRY HUD */}
      {running && progress && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
              </span>
              <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-300">
                Running Phase {(progress.mode_index ?? 0) + 1} of {progress.modes_total ?? 3}
              </span>
            </div>
            <span className="font-mono text-xs font-medium text-white bg-neutral-800 border border-neutral-700 px-2 py-0.5 rounded-md">
              {progress.elapsed?.toFixed(1)}s / {progress.duration_seconds ?? duration}.0s
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {BENCHMARK_MODES.map((m) => {
              const isDone = (progress.modes_done ?? []).includes(m);
              const isCurrent = progress.current_mode === m;
              const cfg = MODE_CONFIG[m];
              const Icon = cfg.icon;

              return (
                <div
                  key={m}
                  className={`p-2.5 rounded-lg border transition-all flex flex-col items-center justify-center text-center ${
                    isCurrent
                      ? "border-neutral-400 bg-neutral-800 text-white"
                      : isDone
                      ? "border-neutral-800 bg-neutral-900 text-neutral-500"
                      : "border-neutral-800 bg-neutral-900/50 text-neutral-600"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 mb-1 ${isCurrent ? "text-white" : "text-neutral-600"}`} />
                  <div className={`text-[10px] font-medium tracking-wider ${isCurrent ? "text-white" : ""}`}>
                    {cfg.shortLabel}
                  </div>
                  <div className="text-[9px] font-mono mt-0.5">
                    {isCurrent ? (
                      <span className="text-white font-medium">{progress.elapsed?.toFixed(0)}s</span>
                    ) : isDone ? (
                      <span className="text-neutral-500">✓ Done</span>
                    ) : (
                      <span className="text-neutral-600">{duration}s</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-[9px] font-mono uppercase tracking-wider text-neutral-500">
              <span>{MODE_CONFIG[progress.current_mode]?.label} Execution</span>
              <span className="text-neutral-300 font-medium">
                {Math.min(Math.round(((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration)) * 100), 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden p-0.5 border border-neutral-700">
              <div
                className="h-full bg-white rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min((((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration))) * 100, 100)}%`,
                }}
              />
            </div>
          </div>

          <div className="pt-1 flex items-center justify-between border-t border-neutral-800">
            <span className="text-[9px] text-neutral-600 font-mono">Real-time 10Hz Broadcast</span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-3 rounded-lg border-neutral-800 bg-neutral-900 text-red-400 hover:bg-neutral-800 hover:text-red-300 text-[10px] font-bold uppercase tracking-wider transition-all"
              onClick={onStop}
            >
              Abort Benchmark
            </Button>
          </div>
        </div>
      )}

      {/* 3. COMPREHENSIVE BENCHMARK RESULTS VIEW */}
      {!running && results && (
        <div className="space-y-3.5">
          {/* Victory Card */}
          {results.winner && (
            <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded-md bg-neutral-800 text-neutral-300 border border-neutral-700">
                      <Trophy className="w-3.5 h-3.5" />
                    </span>
                    <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
                      Top Performance Policy
                    </span>
                  </div>
                  <div className="text-base font-medium text-white tracking-tight">
                    {winnerLabel}
                  </div>
                  <p className="text-[11px] text-neutral-400 leading-relaxed pt-0.5">
                    {results.improvements?.ai_wait_pct && results.improvements.ai_wait_pct > 0 && results.winner === "ai"
                      ? `Achieved ${results.improvements.ai_wait_pct}% lower average wait time compared to Fixed Timer baseline.`
                      : results.improvements?.greedy_wait_pct && results.improvements.greedy_wait_pct > 0 && results.winner === "greedy"
                      ? `Achieved ${results.improvements.greedy_wait_pct}% lower average wait time compared to Fixed Timer baseline.`
                      : `Demonstrated optimal vehicle flow and minimal congestion throughout the ${results.duration_seconds}s benchmark.`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Mode Performance Rows */}
          <div className="space-y-2">
            <div className="text-[9px] font-medium uppercase tracking-wider text-neutral-500 px-1">
              Policy Metrics ({results.duration_seconds}s per mode)
            </div>

            {results.modes.map((mode) => {
              const res = results.results[mode];
              const cfg = MODE_CONFIG[mode] ?? {
                label: mode,
                shortLabel: mode.toUpperCase(),
                icon: Activity,
                barColor: "#fff",
              };
              const isWinner = mode === results.winner;
              const Icon = cfg.icon;

              return (
                <div
                  key={mode}
                  className={`rounded-xl border p-3 transition-all ${
                    isWinner
                      ? "border-neutral-400 bg-neutral-800 shadow-sm"
                      : "border-neutral-800 bg-neutral-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded-md bg-neutral-800 text-neutral-400 border border-neutral-700">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className={`text-xs font-medium ${isWinner ? "text-white" : "text-white/80"}`}>
                        {cfg.label}
                      </span>
                    </div>
                    {isWinner && (
                      <span className="text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white text-black shadow-sm font-mono">
                        WINNER
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-neutral-800">
                    <div className="bg-neutral-900 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Passed</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white" : "text-white/90"}`}>
                        {res?.total_passed ?? 0} <span className="text-[8px] font-normal text-neutral-600">veh</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Avg Wait</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white" : "text-white/90"}`}>
                        {res?.avg_wait_time ?? 0} <span className="text-[8px] font-normal text-neutral-600">s</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Max Queue</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white/90" : "text-white/90"}`}>
                        {res?.max_queue ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Comparison Bar Chart */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-3.5">
            <p className="text-[9px] uppercase tracking-wider text-neutral-500 font-medium mb-3">
              Comparative Analysis
            </p>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="metric" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#0a0a0a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "11px",
                  }}
                  itemStyle={{ color: "rgba(255,255,255,0.8)" }}
                  labelStyle={{ color: "rgba(255,255,255,0.5)" }}
                />
                <Legend wrapperStyle={{ fontSize: "10px", color: "rgba(255,255,255,0.5)" }} />
                {results.modes.map((mode) => (
                  <Bar
                    key={mode}
                    dataKey={mode}
                    fill={MODE_CONFIG[mode]?.barColor ?? "#fff"}
                    radius={[3, 3, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Action Row */}
          <div className="flex gap-2 pt-1">
            <Button
              className="flex-1 py-5 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 shadow-sm"
              onClick={() => {
                const selected = models.find((m) => m.id === selectedModelId);
                let epNum: number | undefined;
                if (selected?.episodes) {
                  epNum = Number(selected.episodes);
                } else if (selected?.version) {
                  const parsed = parseInt(selected.version, 10);
                  if (!isNaN(parsed)) epNum = parsed;
                }
                onStart(results.duration_seconds || duration, BENCHMARK_MODES, selectedModelId || undefined, epNum);
              }}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Rerun ({results.duration_seconds}s each)
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-10 border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-all flex items-center gap-1.5"
              onClick={onReset}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Adjust
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

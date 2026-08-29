"use client";

import { useMemo, useState } from "react";
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
  CheckCircle2,
  SlidersHorizontal,
  ChevronRight,
  TrendingUp,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react";
import type { SimBenchmarkProgress, SimBenchmarkResultsData } from "@/hooks/useSimulationSocket";

interface SimulationBenchmarkPanelProps {
  running: boolean;
  progress: SimBenchmarkProgress | null;
  results: SimBenchmarkResultsData | null;
  onStart: (durationSeconds: number) => void;
  onStop: () => void;
  onReset: () => void;
}

const PRESET_DURATIONS = [15, 30, 60, 120];

const MODE_CONFIG: Record<
  string,
  { label: string; shortLabel: string; icon: any; color: string; barColor: string; accentBg: string; textAccent: string }
> = {
  fixed: {
    label: "Fixed Timer",
    shortLabel: "FIXED",
    icon: Clock,
    color: "border-slate-700/60 bg-slate-900/40",
    barColor: "#94a3b8",
    accentBg: "bg-slate-500/20",
    textAccent: "text-slate-300",
  },
  greedy: {
    label: "Greedy Policy",
    shortLabel: "GREEDY",
    icon: Target,
    color: "border-amber-500/40 bg-amber-950/20",
    barColor: "#f59e0b",
    accentBg: "bg-amber-500/20",
    textAccent: "text-amber-400",
  },
  ai: {
    label: "DQN AI Agent",
    shortLabel: "DQN AI",
    icon: Bot,
    color: "border-emerald-500/50 bg-emerald-950/20",
    barColor: "#10b981",
    accentBg: "bg-emerald-500/20",
    textAccent: "text-emerald-400",
  },
};

const BENCHMARK_MODES = ["fixed", "greedy", "ai"];

export default function SimulationBenchmarkPanel({
  running,
  progress,
  results,
  onStart,
  onStop,
  onReset,
}: SimulationBenchmarkPanelProps) {
  const [duration, setDuration] = useState<number>(15);

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
      {/* ─────────────────────────────────────────────────────────────
          1. CONFIGURATION VIEW
      ───────────────────────────────────────────────────────────── */}
      {!running && !results && (
        <div className="rounded-2xl border border-white/[0.08] bg-[#090d14]/90 backdrop-blur-xl p-4 space-y-4 shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/70">
                Benchmark Configuration
              </span>
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded-md font-semibold">
              3 Policies • Sequential
            </span>
          </div>

          {/* Duration Selector Segmented Control */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-white/60 font-medium flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                Duration per Mode
              </span>
              <span className="font-mono text-sm font-bold text-white tracking-tight">
                {duration}s <span className="text-white/35 text-[10px] font-normal font-sans">({duration * 3}s total)</span>
              </span>
            </div>

            {/* Matrix Chips */}
            <div className="grid grid-cols-4 gap-1.5 p-1 bg-black/60 rounded-xl border border-white/[0.06]">
              {PRESET_DURATIONS.map((preset) => {
                const isSelected = duration === preset;
                return (
                  <button
                    key={preset}
                    onClick={() => setDuration(preset)}
                    className={`py-1.5 rounded-lg text-xs font-mono font-bold tracking-tight transition-all ${
                      isSelected
                        ? "bg-white text-black shadow-md shadow-white/10"
                        : "text-white/45 hover:text-white hover:bg-white/[0.04]"
                    }`}
                  >
                    {preset}s
                  </button>
                );
              })}
            </div>

            {/* Slider */}
            <div className="pt-1 px-1">
              <input
                type="range"
                min={10}
                max={120}
                step={5}
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value, 10))}
                className="w-full h-1 bg-white/10 rounded-lg accent-emerald-400 cursor-pointer"
              />
              <div className="flex justify-between text-[9px] font-mono text-white/30 mt-1">
                <span>10s</span>
                <span>60s</span>
                <span>120s</span>
              </div>
            </div>
          </div>

          {/* Sequential Execution Nodes */}
          <div className="rounded-xl border border-white/[0.06] bg-black/40 p-3 space-y-2">
            <div className="text-[9px] uppercase tracking-[0.14em] text-white/40 font-semibold flex items-center justify-between">
              <span>Benchmark Pipeline</span>
              <span className="font-mono text-white/60 font-normal">3 × {duration}s = {duration * 3}s</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {BENCHMARK_MODES.map((m, idx) => {
                const cfg = MODE_CONFIG[m];
                const Icon = cfg.icon;
                return (
                  <div
                    key={m}
                    className="flex flex-col items-center justify-center p-2 rounded-lg bg-white/[0.02] border border-white/[0.05] text-center"
                  >
                    <Icon className="w-3.5 h-3.5 text-white/50 mb-1" />
                    <span className="text-[10px] font-bold text-white/90">{cfg.shortLabel}</span>
                    <span className="text-[9px] font-mono text-emerald-400 font-semibold mt-0.5">{duration}s</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Trigger */}
          <button
            onClick={() => onStart(duration)}
            className="w-full py-3 rounded-xl bg-emerald-400 hover:bg-emerald-300 text-black font-extrabold text-xs uppercase tracking-[0.14em] shadow-[0_0_24px_rgba(52,211,153,0.3)] hover:shadow-[0_0_32px_rgba(52,211,153,0.45)] active:scale-[0.99] transition-all flex items-center justify-center gap-2"
          >
            <Play className="w-3.5 h-3.5 fill-black" />
            Launch Benchmark ({duration * 3}s)
          </button>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          2. LIVE RUNNING TELEMETRY HUD
      ───────────────────────────────────────────────────────────── */}
      {running && progress && (
        <div className="rounded-2xl border border-emerald-500/30 bg-[#090d14]/95 backdrop-blur-xl p-4 space-y-4 shadow-[0_0_32px_rgba(16,185,129,0.1)]">
          {/* Status Bar */}
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </span>
              <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-white">
                Running Phase {(progress.mode_index ?? 0) + 1} of {progress.modes_total ?? 3}
              </span>
            </div>
            <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-md">
              {progress.elapsed?.toFixed(1)}s / {progress.duration_seconds ?? duration}.0s
            </span>
          </div>

          {/* 3 Pipeline Step Cards */}
          <div className="grid grid-cols-3 gap-2">
            {BENCHMARK_MODES.map((m, idx) => {
              const isDone = (progress.modes_done ?? []).includes(m);
              const isCurrent = progress.current_mode === m;
              const cfg = MODE_CONFIG[m];
              const Icon = cfg.icon;

              return (
                <div
                  key={m}
                  className={`p-2.5 rounded-xl border transition-all flex flex-col items-center justify-center text-center ${
                    isCurrent
                      ? "border-emerald-400 bg-emerald-500/15 shadow-[0_0_16px_rgba(52,211,153,0.15)] ring-1 ring-emerald-400/40"
                      : isDone
                      ? "border-white/10 bg-white/[0.03] text-white/50"
                      : "border-white/[0.04] bg-black/40 text-white/25"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 mb-1 ${isCurrent ? "text-emerald-400" : isDone ? "text-white/60" : "text-white/20"}`} />
                  <div className={`text-[10px] font-extrabold tracking-wider ${isCurrent ? "text-white" : ""}`}>
                    {cfg.shortLabel}
                  </div>
                  <div className="text-[9px] font-mono mt-0.5">
                    {isCurrent ? (
                      <span className="text-emerald-300 font-bold">{progress.elapsed?.toFixed(0)}s</span>
                    ) : isDone ? (
                      <span className="text-white/40">✓ Done</span>
                    ) : (
                      <span>{duration}s</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Mode Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[9px] font-mono uppercase tracking-wider text-white/40">
              <span>{MODE_CONFIG[progress.current_mode]?.label} Execution</span>
              <span className="text-white/80 font-bold">
                {Math.min(Math.round(((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration)) * 100), 100)}%
              </span>
            </div>
            <div className="h-2 bg-black/60 rounded-full overflow-hidden p-0.5 border border-white/[0.06]">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-300 shadow-[0_0_10px_#10b981]"
                style={{
                  width: `${Math.min((((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration))) * 100, 100)}%`,
                }}
              />
            </div>
          </div>

          {/* Abort Control */}
          <div className="pt-1 flex items-center justify-between border-t border-white/[0.06]">
            <span className="text-[9px] text-white/30 font-mono">Real-time 10Hz Broadcast</span>
            <button
              onClick={onStop}
              className="px-3 py-1.5 rounded-lg border border-red-500/40 bg-red-950/30 hover:bg-red-950/60 text-red-300 text-[10px] font-bold uppercase tracking-wider transition-all"
            >
              Abort Benchmark
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          3. COMPREHENSIVE BENCHMARK RESULTS VIEW
      ───────────────────────────────────────────────────────────── */}
      {!running && results && (
        <div className="space-y-3.5">
          {/* Victory Card */}
          {results.winner && (
            <div className="relative overflow-hidden rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-950/40 via-[#0a0f16] to-[#080b10] p-4 shadow-[0_0_24px_rgba(16,185,129,0.15)]">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded-md bg-emerald-400/20 text-emerald-400 border border-emerald-400/30">
                      <Trophy className="w-3.5 h-3.5" />
                    </span>
                    <span className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-emerald-400">
                      Top Performance Policy
                    </span>
                  </div>
                  <div className="text-base font-extrabold text-white tracking-tight">
                    {winnerLabel}
                  </div>
                  <p className="text-[11px] text-white/70 leading-relaxed pt-0.5">
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
            <div className="text-[9px] font-bold uppercase tracking-[0.16em] text-white/40 px-1">
              Policy Metrics ({results.duration_seconds}s per mode)
            </div>

            {results.modes.map((mode) => {
              const res = results.results[mode];
              const cfg = MODE_CONFIG[mode] ?? {
                label: mode,
                shortLabel: mode.toUpperCase(),
                icon: Activity,
                color: "border-white/10 bg-white/5",
                barColor: "#fff",
                accentBg: "bg-white/10",
                textAccent: "text-white",
              };
              const isWinner = mode === results.winner;
              const Icon = cfg.icon;

              return (
                <div
                  key={mode}
                  className={`rounded-xl border p-3 transition-all ${
                    isWinner
                      ? "border-emerald-500/50 bg-emerald-950/20 shadow-[0_0_16px_rgba(16,185,129,0.08)] ring-1 ring-emerald-500/30"
                      : "border-white/[0.06] bg-[#090d14]/80"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`p-1 rounded-md ${cfg.accentBg} ${cfg.textAccent}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className={`text-xs font-bold ${isWinner ? "text-white" : "text-white/80"}`}>
                        {cfg.label}
                      </span>
                    </div>
                    {isWinner && (
                      <span className="text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-400 text-black shadow-sm font-mono">
                        WINNER
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-white/[0.04]">
                    <div className="bg-black/30 rounded-lg p-2 text-center border border-white/[0.03]">
                      <div className="text-[8px] uppercase tracking-wider text-white/40 font-semibold">Passed</div>
                      <div className={`text-xs font-mono font-bold mt-0.5 ${isWinner ? "text-emerald-400" : "text-white/90"}`}>
                        {res?.total_passed ?? 0} <span className="text-[8px] font-normal text-white/40">veh</span>
                      </div>
                    </div>

                    <div className="bg-black/30 rounded-lg p-2 text-center border border-white/[0.03]">
                      <div className="text-[8px] uppercase tracking-wider text-white/40 font-semibold">Avg Wait</div>
                      <div className={`text-xs font-mono font-bold mt-0.5 ${isWinner ? "text-emerald-400" : "text-white/90"}`}>
                        {res?.avg_wait_time ?? 0} <span className="text-[8px] font-normal text-white/40">s</span>
                      </div>
                    </div>

                    <div className="bg-black/30 rounded-lg p-2 text-center border border-white/[0.03]">
                      <div className="text-[8px] uppercase tracking-wider text-white/40 font-semibold">Max Queue</div>
                      <div className={`text-xs font-mono font-bold mt-0.5 ${isWinner ? "text-emerald-400" : "text-white/90"}`}>
                        {res?.max_queue ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Comparison Bar Chart */}
          <div className="rounded-xl border border-white/[0.08] bg-[#090d14]/90 p-3.5">
            <p className="text-[9px] uppercase tracking-[0.16em] text-white/40 font-bold mb-3">
              Comparative Analysis
            </p>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="metric" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#090d16",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "11px",
                  }}
                  itemStyle={{ color: "rgba(255,255,255,0.8)" }}
                />
                <Legend wrapperStyle={{ fontSize: "10px", color: "rgba(255,255,255,0.5)" }} />
                {results.modes.map((mode) => (
                  <Bar
                    key={mode}
                    dataKey={mode}
                    name={MODE_CONFIG[mode]?.label ?? mode}
                    fill={MODE_CONFIG[mode]?.barColor ?? "#fff"}
                    radius={[3, 3, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Action Row */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => onStart(results.duration_seconds || duration)}
              className="flex-1 py-2.5 rounded-xl bg-white text-black font-extrabold text-xs uppercase tracking-wider hover:bg-white/90 transition-all flex items-center justify-center gap-1.5 shadow-md"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Rerun ({results.duration_seconds}s each)
            </button>
            <button
              onClick={onReset}
              className="px-4 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-white/70 hover:text-white transition-all flex items-center gap-1.5"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Adjust
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
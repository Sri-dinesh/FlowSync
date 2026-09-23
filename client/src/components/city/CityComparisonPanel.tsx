"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Trophy,
  Play,
  Square,
  RotateCcw,
  Clock,
  Target,
  Bot,
  SlidersHorizontal,
  Activity,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import type { ComparisonResult, ComparisonProgress, ComparisonResultsFrame } from "@/types/city";

interface CityComparisonPanelProps {
  results: Record<string, ComparisonResult> | null;
  fullResults?: ComparisonResultsFrame | null;
  running: boolean;
  progress?: ComparisonProgress;
  onStart: (durationSeconds: number) => void;
  onStop?: () => void;
}

const PRESET_DURATIONS = [15, 30, 60, 120];

const MODE_CONFIG: Record<
  string,
  { label: string; shortLabel: string; icon: any; barColor: string }
> = {
  fixed: {
    label: "Fixed Timing",
    shortLabel: "FIXED",
    icon: Clock,
    barColor: "#404040",
  },
  greedy: {
    label: "Greedy Decentralized",
    shortLabel: "GREEDY",
    icon: Target,
    barColor: "#A3A3A3",
  },
  ai: {
    label: "Shared DQN AI Network",
    shortLabel: "SHARED AI",
    icon: Bot,
    barColor: "#FFFFFF",
  },
};

const BENCHMARK_MODES = ["fixed", "greedy", "ai"];

export default function CityComparisonPanel({
  results,
  fullResults,
  running,
  progress,
  onStart,
  onStop,
}: CityComparisonPanelProps) {
  const [duration, setDuration] = useState<number>(15);

  const modes = useMemo(() => ["fixed", "greedy", "ai"], []);

  const chartData = useMemo(() => {
    if (!results) return [];

    const waitData: Record<string, string | number> = { metric: "Avg Wait (s)" };
    const thruData: Record<string, string | number> = { metric: "Throughput" };
    const maxQData: Record<string, string | number> = { metric: "Peak Queue" };

    if (results.fixed) {
      waitData.fixed = parseFloat(results.fixed.avg_wait_time.toFixed(2));
      thruData.fixed = results.fixed.throughput;
      maxQData.fixed = results.fixed.max_queue ?? 0;
    }
    if (results.greedy) {
      waitData.greedy = parseFloat(results.greedy.avg_wait_time.toFixed(2));
      thruData.greedy = results.greedy.throughput;
      maxQData.greedy = results.greedy.max_queue ?? 0;
    }
    if (results.ai) {
      waitData.ai = parseFloat(results.ai.avg_wait_time.toFixed(2));
      thruData.ai = results.ai.throughput;
      maxQData.ai = results.ai.max_queue ?? 0;
    }

    return [thruData, waitData, maxQData];
  }, [results]);

  const winner = useMemo(() => {
    if (fullResults?.winner) return fullResults.winner;
    if (!results) return null;
    return Object.keys(results).sort((a, b) => {
      const wa = results[a]?.avg_wait_time ?? 999;
      const wb = results[b]?.avg_wait_time ?? 999;
      if (wa !== wb) return wa - wb;
      return (results[b]?.throughput ?? 0) - (results[a]?.throughput ?? 0);
    })[0] ?? null;
  }, [results, fullResults]);

  const improvements = useMemo(() => {
    if (fullResults?.improvements) return fullResults.improvements;
    if (!results?.fixed) return {};
    const fWait = results.fixed.avg_wait_time;
    if (fWait <= 0) return {};
    const imp: Record<string, number> = {};
    if (results.ai) {
      imp.ai_wait_pct = Number((((fWait - results.ai.avg_wait_time) / fWait) * 100).toFixed(1));
    }
    if (results.greedy) {
      imp.greedy_wait_pct = Number((((fWait - results.greedy.avg_wait_time) / fWait) * 100).toFixed(1));
    }
    return imp;
  }, [results, fullResults]);

  const winnerLabel = useMemo(() => {
    if (!winner) return null;
    return MODE_CONFIG[winner]?.label ?? winner.toUpperCase();
  }, [winner]);

  return (
    <div className="space-y-3.5 text-white">
      {/* 1. CONFIGURATION VIEW */}
      {!running && !results && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              <span className="text-[10px] font-medium text-neutral-400">
                City Grid Benchmark
              </span>
            </div>
            <span className="text-[9px] font-mono text-neutral-500 bg-neutral-800 border border-neutral-700 px-2 py-0.5 rounded-md font-medium">
              4 Intersections
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
                className="w-full h-1 bg-neutral-800"
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
              <span>City Evaluation Sequence</span>
              <span className="font-mono text-neutral-400 font-normal">3 × {duration}s = {duration * 3}s</span>
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

          <Button
            className="w-full py-6 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2"
            onClick={() => onStart(duration)}
          >
            <Play className="w-3.5 h-3.5 fill-black" />
            Launch City Benchmark ({duration * 3}s)
          </Button>
        </div>
      )}

      {/* 2. LIVE RUNNING TELEMETRY HUD */}
      {running && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
              </span>
              <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-300">
                City Phase {(progress?.mode_index ?? 0) + 1} of {progress?.total_modes ?? 3}
              </span>
            </div>
            <span className="font-mono text-xs font-medium text-white bg-neutral-800 border border-neutral-700 px-2 py-0.5 rounded-md">
              {progress?.elapsed?.toFixed(1) ?? "0.0"}s / {progress?.total ?? duration}.0s
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {BENCHMARK_MODES.map((m, idx) => {
              const currentIndex = progress?.mode_index ?? 0;
              const isDone = idx < currentIndex;
              const isCurrent = idx === currentIndex;
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
                      <span className="text-white font-medium">{progress?.elapsed?.toFixed(0) ?? 0}s</span>
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
              <span>{MODE_CONFIG[progress?.current_mode ?? "fixed"]?.label} Evaluation</span>
              <span className="text-neutral-300 font-medium">
                {Math.min(Math.round(((progress?.elapsed ?? 0) / (progress?.total ?? duration)) * 100), 100)}%
              </span>
            </div>
            <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden p-0.5 border border-neutral-700">
              <div
                className="h-full bg-white rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min((((progress?.elapsed ?? 0) / (progress?.total ?? duration))) * 100, 100)}%`,
                }}
              />
            </div>
          </div>

          <div className="pt-1 flex items-center justify-between border-t border-neutral-800">
            <span className="text-[9px] text-neutral-600 font-mono">2×2 Network Topology</span>
            {onStop && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 px-3 rounded-lg border-neutral-800 bg-neutral-900 text-red-400 hover:bg-neutral-800 hover:text-red-300 text-[10px] font-bold uppercase tracking-wider transition-all"
                onClick={onStop}
              >
                Abort Benchmark
              </Button>
            )}
          </div>
        </div>
      )}

      {/* 3. COMPREHENSIVE BENCHMARK RESULTS VIEW */}
      {!running && results && (
        <div className="space-y-3.5">
          {winner && (
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
                    {improvements?.ai_wait_pct && improvements.ai_wait_pct > 0 && winner === "ai"
                      ? `Achieved ${improvements.ai_wait_pct}% lower city-wide wait time compared to Fixed Timing.`
                      : improvements?.greedy_wait_pct && improvements.greedy_wait_pct > 0 && winner === "greedy"
                      ? `Achieved ${improvements.greedy_wait_pct}% lower city-wide wait time compared to Fixed Timing.`
                      : `Demonstrated optimal vehicle throughput and flow across all 4 intersections.`}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <div className="text-[9px] font-medium uppercase tracking-wider text-neutral-500 px-1">
              Network Metrics ({fullResults?.duration_seconds || duration}s per mode)
            </div>

            {modes.map((mode) => {
              const res = results[mode];
              const cfg = MODE_CONFIG[mode] ?? {
                label: mode,
                shortLabel: mode.toUpperCase(),
                icon: Activity,
                barColor: "#fff",
              };
              const isWinner = mode === winner;
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
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Throughput</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white" : "text-white/90"}`}>
                        {res?.throughput ?? 0} <span className="text-[8px] font-normal text-neutral-600">veh</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Avg Wait</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white" : "text-white/90"}`}>
                        {res?.avg_wait_time ?? 0} <span className="text-[8px] font-normal text-neutral-600">s</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-500 font-medium">Peak Queue</div>
                      <div className={`text-xs font-mono font-medium mt-0.5 ${isWinner ? "text-white" : "text-white/90"}`}>
                        {res?.max_queue ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-3.5">
            <p className="text-[9px] uppercase tracking-wider text-neutral-500 font-medium mb-3">
              City Network Comparison
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
                {modes.map((mode) => (
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

          <div className="flex gap-2 pt-1">
            <Button
              className="flex-1 py-5 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 shadow-sm"
              onClick={() => onStart(fullResults?.duration_seconds || duration)}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Rerun ({fullResults?.duration_seconds || duration}s each)
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-10 border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-all flex items-center gap-1.5"
              onClick={() => onStart(duration)}
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

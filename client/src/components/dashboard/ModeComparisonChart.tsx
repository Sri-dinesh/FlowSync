"use client";

import { useRouter } from "next/navigation";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Award, Zap, Clock, Play, BarChart2, Info, X } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

export interface ModeBenchmarks {
  fixed: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
    has_data?: boolean;
  };
  greedy: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
    has_data?: boolean;
  };
  ai: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
    has_data?: boolean;
  };
  comparison: {
    wait_reduction_pct: number | null;
    throughput_gain_pct: number | null;
    queue_reduction_pct: number | null;
    baseline_type?: string;
    leader?: string;
    leader_name?: string;
    kpi_source?: string;
  };
}

interface Props {
  data: ModeBenchmarks;
}

function InlinePopover({
  title,
  description,
  onClose,
}: {
  title: string;
  description: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className="absolute top-full mt-2 right-0 z-20 w-64">
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3 shadow-2xl">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium text-white leading-tight">{title}</p>
          <button
            onClick={onClose}
            className="shrink-0 flex h-5 w-5 items-center justify-center rounded-md text-neutral-500 hover:text-white hover:bg-neutral-800 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-neutral-400">{description}</p>
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!active || !payload || !payload.length) return null;

  const metric = label as string;
  const getUnit = (m: string) => {
    if (m === "Avg Wait (s)") return "s";
    if (m === "Max Queue") return " veh";
    if (m === "Efficiency Score") return "";
    return "";
  };
  const unit = getUnit(metric);
  const isWait = metric === "Avg Wait (s)";
  const isQueue = metric === "Max Queue";

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const values = payload.map((p: any) => p.value as number);
  const best = isWait || isQueue ? Math.min(...values) : Math.max(...values);

  const nameMap: Record<string, { label: string; color: string }> = {
    fixed: { label: "Fixed Timer", color: "#64748b" },
    greedy: { label: "Greedy", color: "#10b981" },
    ai: { label: "DQN AI", color: "#6366f1" },
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-3 shadow-2xl min-w-[210px]">
      <div className="text-xs font-medium text-white pb-2 border-b border-neutral-800">
        {metric}
      </div>
      <div className="mt-3 space-y-2.5">
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {payload.map((entry: any) => {
          const cfg = nameMap[entry.dataKey] || { label: entry.dataKey, color: entry.fill };
          const isBest = entry.value === best;
          return (
            <div key={entry.dataKey} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: cfg.color }} />
                <span className={`text-xs ${isBest ? "text-white font-medium" : "text-neutral-400"}`}>
                  {cfg.label}
                </span>
                {isBest && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white text-black font-medium leading-none">
                    best
                  </span>
                )}
              </div>
              <span className={`text-xs font-mono font-medium ${isBest ? "text-white" : "text-neutral-300"}`}>
                {typeof entry.value === "number" ? entry.value.toFixed(1) : entry.value}
                <span className="text-neutral-500 font-normal ml-0.5">{unit}</span>
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-3 pt-2.5 border-t border-neutral-800 text-xs text-neutral-500 leading-relaxed">
        {isWait && "Lower wait is better — DQN learns to minimize delay."}
        {isQueue && "Lower queue means less congestion."}
        {!isWait && !isQueue && "Higher efficiency = more throughput per wait."}
      </div>
    </div>
  );
}

export default function ModeComparisonChart({ data }: Props) {
  const router = useRouter();
  const [activePopover, setActivePopover] = useState<"wait" | "throughput" | null>(null);

  const hasData =
    (data.fixed?.avg_wait_time ?? 0) > 0 ||
    (data.greedy?.avg_wait_time ?? 0) > 0 ||
    (data.ai?.avg_wait_time ?? 0) > 0;

  if (!hasData) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-neutral-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-white">Controller Benchmark</h3>
              <span className="rounded-full bg-neutral-900 border border-neutral-800 px-2.5 py-0.5 text-xs text-neutral-500">
                Awaiting data
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              Multi-metric comparison across DQN, Greedy, and Fixed controllers
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => router.push("/simulation")}
            className="h-8 rounded-full bg-white text-black hover:bg-neutral-200 text-xs"
          >
            <Play className="h-3 w-3 mr-1.5" />
            Run Benchmark
          </Button>
        </div>
        <div className="mt-6 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/20 py-12 px-6 flex flex-col items-center justify-center text-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-neutral-900 border border-neutral-800 text-neutral-600">
            <BarChart2 className="h-4 w-4" />
          </div>
          <div className="max-w-md space-y-1">
            <h4 className="text-sm font-medium text-white">No benchmarks yet</h4>
            <p className="text-xs text-neutral-500 leading-relaxed">
              Run a benchmark in Simulation to see side-by-side comparison.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const leaderKey = data.comparison?.leader;
  const leaderName =
    data.comparison?.leader_name ||
    (leaderKey === "greedy"
      ? "Greedy Controller"
      : leaderKey === "fixed"
        ? "Fixed Timer"
        : leaderKey === "ai"
          ? "FlowSync DQN AI"
          : "Evaluated");
  const waitRed = data.comparison?.wait_reduction_pct;
  const thrGain = data.comparison?.throughput_gain_pct;

  const chartData = [
    {
      metric: "Avg Wait (s)",
      fixed: data.fixed.avg_wait_time,
      greedy: data.greedy.avg_wait_time,
      ai: data.ai.avg_wait_time,
    },
    {
      metric: "Max Queue",
      fixed: data.fixed.max_queue_avg,
      greedy: data.greedy.max_queue_avg,
      ai: data.ai.max_queue_avg,
    },
    {
      metric: "Efficiency Score",
      fixed: data.fixed.efficiency_score,
      greedy: data.greedy.efficiency_score,
      ai: data.ai.efficiency_score,
    },
  ];

  return (
    <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-6">
        {/* Header — ultra clean */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-neutral-800 pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-sm font-medium text-white">Controller Benchmark</h3>
              <span
                className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium border ${
                  leaderKey === "greedy"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
                    : leaderKey === "fixed"
                      ? "bg-slate-500/10 border-slate-500/20 text-slate-300"
                      : leaderKey === "ai"
                        ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-300"
                        : "bg-neutral-900 border-neutral-800 text-neutral-500"
                }`}
              >
                <Award className={`h-3 w-3 ${leaderKey === "ai" ? "text-indigo-400" : "text-emerald-400"}`} />
                {leaderName}
              </span>
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              Paired runs with identical seeds — lower wait & queue is better
            </p>
          </div>

          <div className="flex items-start gap-2">
            <div className="relative rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-2 min-w-[120px]">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-neutral-500">Wait Δ</span>
                <button
                  onClick={() => setActivePopover(activePopover === "wait" ? null : "wait")}
                  className={`flex h-4 w-4 items-center justify-center rounded-full border text-[10px] transition-colors ${
                    activePopover === "wait"
                      ? "bg-white text-black border-white"
                      : "border-neutral-700 bg-neutral-800 text-neutral-400 hover:bg-neutral-700 hover:text-white"
                  }`}
                >
                  <Info className="h-2.5 w-2.5" />
                </button>
              </div>
              <div
                className={`text-sm font-mono font-semibold mt-1 tracking-tight tabular-nums ${
                  waitRed == null ? "text-neutral-600" : waitRed > 0 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {waitRed == null ? "—" : `${waitRed > 0 ? "+" : ""}${waitRed}%`}
              </div>
              {activePopover === "wait" && (
                <InlinePopover
                  title="Wait Reduction"
                  description="DQN vs fixed baseline. Positive = faster. From paired runs with identical traffic seeds."
                  onClose={() => setActivePopover(null)}
                />
              )}
            </div>
            <div className="relative rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-2 min-w-[120px]">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-neutral-500">Throughput Δ</span>
                <button
                  onClick={() => setActivePopover(activePopover === "throughput" ? null : "throughput")}
                  className={`flex h-4 w-4 items-center justify-center rounded-full border text-[10px] transition-colors ${
                    activePopover === "throughput"
                      ? "bg-white text-black border-white"
                      : "border-neutral-700 bg-neutral-800 text-neutral-400 hover:bg-neutral-700 hover:text-white"
                  }`}
                >
                  <Info className="h-2.5 w-2.5" />
                </button>
              </div>
              <div
                className={`text-sm font-mono font-semibold mt-1 tracking-tight tabular-nums ${
                  thrGain == null ? "text-neutral-600" : thrGain >= 0 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {thrGain == null ? "—" : `${thrGain > 0 ? "+" : ""}${thrGain}%`}
              </div>
              {activePopover === "throughput" && (
                <InlinePopover
                  title="Throughput Delta"
                  description="DQN vs baseline throughput change. Positive = higher flow."
                  onClose={() => setActivePopover(null)}
                />
              )}
            </div>
          </div>
        </div>

        {/* Chart — clean, airy */}
        <div className="mt-4 h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="28%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="metric"
                stroke="#737373"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#a3a3a3", fontSize: 12 }}
              />
              <YAxis
                stroke="#737373"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#737373", fontSize: 11 }}
                width={32}
              />
              <Tooltip cursor={{ fill: "rgba(255,255,255,0.02)" }} content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: "12px", paddingTop: "16px", color: "#737373" }}
                iconType="circle"
                iconSize={8}
              />
              <Bar dataKey="fixed" name="Fixed Timer" fill="#64748b" radius={[6, 6, 0, 0]} barSize={28} />
              <Bar dataKey="greedy" name="Greedy" fill="#10b981" radius={[6, 6, 0, 0]} barSize={28} />
              <Bar dataKey="ai" name="DQN AI" fill="#6366f1" radius={[6, 6, 0, 0]} barSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 text-center text-xs text-neutral-500">Hover bars for exact values · Best performer highlighted</p>

        {/* Bottom Cards — minimal */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            {
              key: "fixed",
              title: "Fixed Timer",
              icon: Clock,
              data: data.fixed,
              isLeader: leaderKey === "fixed",
            },
            {
              key: "greedy",
              title: "Greedy",
              icon: Zap,
              data: data.greedy,
              isLeader: leaderKey === "greedy",
            },
            {
              key: "ai",
              title: "DQN AI",
              icon: Award,
              data: data.ai,
              isLeader: leaderKey === "ai",
            },
          ].map(({ key, title, icon: Icon, data: d, isLeader }) => {
            const cardStyles =
              key === "fixed"
                ? isLeader
                  ? "border-slate-400/30 bg-slate-500/5"
                  : "border-neutral-800 bg-neutral-900/50"
                : key === "greedy"
                  ? isLeader
                    ? "border-emerald-500/30 bg-emerald-500/5"
                    : "border-neutral-800 bg-neutral-900/50"
                  : isLeader
                    ? "border-indigo-500/30 bg-indigo-500/5"
                    : "border-neutral-800 bg-neutral-900/50";
            const titleColor =
              key === "fixed" ? "text-slate-300" : key === "greedy" ? "text-emerald-300" : "text-indigo-300";
            return (
              <div
                key={key}
                className={`rounded-xl border p-4 flex flex-col gap-3 ${cardStyles} ${isLeader ? "ring-1 ring-white/10" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-xs font-medium flex items-center gap-1.5 ${titleColor}`}>
                    <Icon className="h-3.5 w-3.5" />
                    {title}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium leading-5 ${
                      isLeader
                        ? "bg-white text-black border border-white"
                        : "bg-transparent text-neutral-600 border border-transparent"
                    }`}
                  >
                    {isLeader ? "Leader" : "—"}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-neutral-500">Avg Wait</span>
                    <span className="font-mono font-medium tabular-nums text-white">{d.avg_wait_time.toFixed(1)}s</span>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-neutral-500">Throughput</span>
                    <span className="font-mono tabular-nums text-white">{d.throughput_rate} veh/m</span>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-neutral-500">Max Queue</span>
                    <span className="font-mono tabular-nums text-white">{d.max_queue_avg}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
  );
}

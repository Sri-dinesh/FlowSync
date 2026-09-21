"use client";

import { motion } from "framer-motion";
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
import { Award, Zap, Clock, Play, BarChart2 } from "lucide-react";

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

export default function ModeComparisonChart({ data }: Props) {
  const router = useRouter();
  const hasData =
    (data.fixed?.avg_wait_time ?? 0) > 0 ||
    (data.greedy?.avg_wait_time ?? 0) > 0 ||
    (data.ai?.avg_wait_time ?? 0) > 0;

  if (!hasData) {
    return (
      <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold tracking-wider uppercase text-white">
                Controller Benchmark Showdown
              </h3>
              <span className="flex items-center gap-1 rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-[9px] font-semibold text-white/50">
                Awaiting Live Runs
              </span>
            </div>
            <p className="mt-1 text-xs text-white/40">
              Multi-metric performance comparison across DQN AI, Greedy, and Fixed-Timer controllers
            </p>
          </div>
          <button
            onClick={() => router.push("/simulation")}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all active:scale-95"
          >
            <Play className="h-3 w-3 fill-white" />
            <span>Run Benchmark in Simulation</span>
          </button>
        </div>

        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.01] py-10 px-6 flex flex-col items-center justify-center text-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <BarChart2 className="h-5 w-5" />
          </div>
          <div className="max-w-md">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              No Benchmark Showdowns Recorded Yet
            </h4>
            <p className="text-[11px] text-white/40 mt-1 leading-relaxed">
              Live side-by-side graphs comparing Wait Time, Throughput, and Queue Size between Fixed Timer, Greedy, and DQN AI will render here automatically as soon as a benchmark completes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const leaderKey = data.comparison?.leader;
  const leaderName = data.comparison?.leader_name || (
    leaderKey === "greedy" ? "Greedy Controller" :
    leaderKey === "fixed" ? "Fixed Timer" :
    leaderKey === "ai" ? "FlowSync DQN AI" :
    "Evaluated"
  );
  const isAiLeader = leaderKey === "ai";
  const waitRed = data.comparison?.wait_reduction_pct;
  const thrGain = data.comparison?.throughput_gain_pct;

  // Active chart rendering when benchmark data is present
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
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold tracking-wider uppercase text-white">
              Controller Benchmark Showdown
            </h3>
            <span className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[9px] font-semibold border ${
              leaderKey === "greedy"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : leaderKey === "fixed"
                ? "bg-slate-500/10 border-slate-500/30 text-slate-300"
                : leaderKey === "ai"
                ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"
                : "bg-white/5 border-white/10 text-white/50"
            }`}>
              <Award className={`h-3 w-3 ${leaderKey === "ai" ? "text-yellow-400" : "text-emerald-400"}`} />
              Leader: {leaderName}
            </span>
          </div>
          <p className="mt-1 text-xs text-white/40">
            Multi-metric performance comparison across paired benchmark evaluations
          </p>
        </div>

        {/* Advantage Highlights */}
        <div className="flex items-center gap-3">
          <div className={`rounded-lg px-3 py-1 text-right border ${
            waitRed === null || waitRed === undefined
              ? "bg-white/5 border-white/10"
              : waitRed > 0
              ? "bg-emerald-500/10 border-emerald-500/20"
              : "bg-rose-500/10 border-rose-500/20"
          }`}>
            <div className="text-[9px] text-white/50 uppercase">DQN vs Baseline Wait</div>
            <div className={`text-xs font-bold font-mono ${
              waitRed === null || waitRed === undefined
                ? "text-white/40"
                : waitRed > 0
                ? "text-emerald-300"
                : "text-rose-300"
            }`}>
              {waitRed === null || waitRed === undefined
                ? "Pending Paired Run"
                : waitRed > 0
                ? `+${waitRed}%`
                : `${waitRed}%`}
            </div>
          </div>
          <div className={`rounded-lg px-3 py-1 text-right border ${
            thrGain === null || thrGain === undefined
              ? "bg-white/5 border-white/10"
              : thrGain >= 0
              ? "bg-emerald-500/10 border-emerald-500/20"
              : "bg-rose-500/10 border-rose-500/20"
          }`}>
            <div className="text-[9px] text-white/50 uppercase">Throughput Delta</div>
            <div className={`text-xs font-bold font-mono ${
              thrGain === null || thrGain === undefined
                ? "text-white/40"
                : thrGain >= 0
                ? "text-emerald-300"
                : "text-rose-300"
            }`}>
              {thrGain === null || thrGain === undefined
                ? "Pending"
                : `${thrGain > 0 ? "+" : ""}${thrGain}%`}
            </div>
          </div>
        </div>
      </div>

      {/* Grouped Bar Chart */}
      <div className="h-72 w-full pt-2 min-w-0">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="metric"
              stroke="rgba(255,255,255,0.4)"
              fontSize={11}
              tickLine={false}
            />
            <YAxis
              stroke="rgba(255,255,255,0.4)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(10, 10, 10, 0.95)",
                borderColor: "rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                fontSize: "12px",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
              iconType="circle"
            />
            <Bar dataKey="fixed" name="⏱ Fixed Timer" fill="#64748b" radius={[4, 4, 0, 0]} />
            <Bar dataKey="greedy" name="🎯 Greedy" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="ai" name="🤖 FlowSync DQN AI" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Comparison Highlights Bottom Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        {/* Fixed Timer */}
        <div className={`rounded-xl border p-3.5 flex flex-col justify-between transition-all ${
          leaderKey === "fixed"
            ? "border-slate-400/40 bg-slate-500/10 shadow-lg shadow-slate-500/5 ring-1 ring-slate-400/30"
            : "border-white/[0.06] bg-white/[0.01]"
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white/70 flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              Fixed Timer
            </span>
            {leaderKey === "fixed" ? (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-slate-400/20 text-slate-200 px-2 py-0.5 rounded-full border border-slate-400/30">
                Top Ranked
              </span>
            ) : (
              <span className="text-[10px] font-mono text-white/40">Baseline</span>
            )}
          </div>
          <div className="mt-2.5 space-y-1.5 text-[11px]">
            <div className="flex justify-between text-white/50">
              <span>Avg Wait:</span>
              <span className="font-mono text-white/80">{data.fixed.avg_wait_time}s</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Throughput:</span>
              <span className="font-mono text-white/80">{data.fixed.throughput_rate} veh/m</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Max Queue:</span>
              <span className="font-mono text-white/80">{data.fixed.max_queue_avg}</span>
            </div>
          </div>
        </div>

        {/* Greedy */}
        <div className={`rounded-xl border p-3.5 flex flex-col justify-between transition-all ${
          leaderKey === "greedy"
            ? "border-emerald-500/40 bg-emerald-500/[0.08] shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-400/30"
            : "border-emerald-500/20 bg-emerald-500/[0.03]"
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 text-emerald-400" />
              Greedy Controller
            </span>
            {leaderKey === "greedy" ? (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-emerald-400/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-400/30">
                Top Ranked
              </span>
            ) : (
              <span className="text-[10px] font-mono text-emerald-400/80">Queue Reactive</span>
            )}
          </div>
          <div className="mt-2.5 space-y-1.5 text-[11px]">
            <div className="flex justify-between text-white/50">
              <span>Avg Wait:</span>
              <span className="font-mono text-emerald-300">{data.greedy.avg_wait_time}s</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Throughput:</span>
              <span className="font-mono text-emerald-300">{data.greedy.throughput_rate} veh/m</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Max Queue:</span>
              <span className="font-mono text-emerald-300">{data.greedy.max_queue_avg}</span>
            </div>
          </div>
        </div>

        {/* FlowSync DQN AI */}
        <div className={`rounded-xl border p-3.5 flex flex-col justify-between transition-all ${
          leaderKey === "ai"
            ? "border-indigo-500/50 bg-indigo-500/[0.09] shadow-lg shadow-indigo-500/15 ring-1 ring-indigo-400/30"
            : "border-indigo-500/20 bg-indigo-500/[0.03]"
        }`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5 text-indigo-400" />
              FlowSync DQN AI
            </span>
            {leaderKey === "ai" ? (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-indigo-400/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-400/30">
                Top Ranked
              </span>
            ) : (
              <span className="text-[9px] font-mono text-indigo-300/60 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                Adaptive RL
              </span>
            )}
          </div>
          <div className="mt-2.5 space-y-1.5 text-[11px]">
            <div className="flex justify-between text-white/50">
              <span>Avg Wait:</span>
              <span className="font-mono font-bold text-indigo-300">{data.ai.avg_wait_time}s</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Throughput:</span>
              <span className="font-mono font-bold text-indigo-300">{data.ai.throughput_rate} veh/m</span>
            </div>
            <div className="flex justify-between text-white/50">
              <span>Max Queue:</span>
              <span className="font-mono font-bold text-indigo-300">{data.ai.max_queue_avg}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

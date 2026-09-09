"use client";

import { motion } from "framer-motion";
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
import { Award, Zap, Clock, ShieldAlert } from "lucide-react";

export interface ModeBenchmarks {
  fixed: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
  };
  greedy: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
  };
  ai: {
    name: string;
    avg_wait_time: number;
    throughput_rate: number;
    max_queue_avg: number;
    efficiency_score: number;
    color: string;
  };
  comparison: {
    wait_reduction_pct: number;
    throughput_gain_pct: number;
    queue_reduction_pct: number;
  };
}

interface Props {
  data: ModeBenchmarks;
}

export default function ModeComparisonChart({ data }: Props) {
  const chartData = [
    {
      metric: "Avg Wait (s)",
      fixed: data.fixed.avg_wait_time,
      greedy: data.greedy.avg_wait_time,
      ai: data.ai.avg_wait_time,
    },
    {
      metric: "Throughput (veh/m)",
      fixed: data.fixed.throughput_rate,
      greedy: data.greedy.throughput_rate,
      ai: data.ai.throughput_rate,
    },
    {
      metric: "Max Queue",
      fixed: data.fixed.max_queue_avg,
      greedy: data.greedy.max_queue_avg,
      ai: data.ai.max_queue_avg,
    },
    {
      metric: "Efficiency (/100)",
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
            <span className="flex items-center gap-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[9px] font-semibold text-indigo-300">
              <Award className="h-3 w-3 text-yellow-400" />
              DQN AI Leads
            </span>
          </div>
          <p className="mt-1 text-xs text-white/40">
            Multi-metric performance comparison across real session replays
          </p>
        </div>

        {/* Advantage Highlights */}
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-right">
            <div className="text-[9px] text-indigo-300/70 uppercase">Wait Reduction</div>
            <div className="text-xs font-bold font-mono text-indigo-300">
              -{data.comparison.wait_reduction_pct}%
            </div>
          </div>
          <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-right">
            <div className="text-[9px] text-emerald-300/70 uppercase">Throughput Gain</div>
            <div className="text-xs font-bold font-mono text-emerald-300">
              +{data.comparison.throughput_gain_pct}%
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
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0d1117",
                borderColor: "rgba(255,255,255,0.15)",
                borderRadius: "10px",
                fontSize: "12px",
                color: "#ffffff",
              }}
              itemStyle={{ color: "#ffffff" }}
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
              formatter={(val: string) => {
                if (val === "fixed") return "⏱ Fixed Timer";
                if (val === "greedy") return "🎯 Greedy";
                if (val === "ai") return "🤖 FlowSync DQN AI";
                return val;
              }}
            />
            <Bar dataKey="fixed" fill="#64748b" radius={[4, 4, 0, 0]} name="fixed" />
            <Bar dataKey="greedy" fill="#10b981" radius={[4, 4, 0, 0]} name="greedy" />
            <Bar dataKey="ai" fill="#6366f1" radius={[4, 4, 0, 0]} name="ai" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Controller Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        {/* Fixed Timer */}
        <div className="rounded-xl border border-slate-700/40 bg-slate-800/10 p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              Fixed Timer
            </span>
            <span className="text-[10px] font-mono text-slate-400">Baseline</span>
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
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 text-emerald-400" />
              Greedy Controller
            </span>
            <span className="text-[10px] font-mono text-emerald-400/80">Queue Reactive</span>
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
        <div className="rounded-xl border border-indigo-500/40 bg-indigo-500/[0.07] p-3.5 flex flex-col justify-between shadow-lg shadow-indigo-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5 text-yellow-400" />
              FlowSync DQN AI
            </span>
            <span className="text-[9px] font-bold uppercase tracking-wider bg-yellow-400/20 text-yellow-300 px-2 py-0.5 rounded-full border border-yellow-400/30">
              Top Ranked
            </span>
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

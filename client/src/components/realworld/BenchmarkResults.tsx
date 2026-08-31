"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export interface ModeResult {
  total_passed: number;
  total_vehicles?: number;
  avg_wait_time: number;
  max_queue: number;
  duration_seconds: number;
  clearance_time?: number;
}

export interface BenchmarkResultsData {
  duration_seconds: number;
  results: Record<string, ModeResult>;
  winner: string | null;
  modes: string[];
  improvements?: {
    ai_wait_pct?: number;
    ai_clearance_pct?: number;
    greedy_wait_pct?: number;
    greedy_clearance_pct?: number;
  };
  is_realworld?: boolean;
  total_vehicles?: number;
}

interface Props {
  data: BenchmarkResultsData;
  onRerun: () => void;
}

const MODE_CONFIG: Record<string, { label: string; icon: string; accent: string; barColor: string; glow: string }> = {
  fixed:  { label: "Fixed Timer", icon: "T",  accent: "border-slate-500/40  bg-slate-500/[0.07]",    barColor: "#64748b", glow: "rgba(100,116,139,0.12)" },
  ai:     { label: "DQN AI",      icon: "AI", accent: "border-indigo-500/40 bg-indigo-500/[0.07]",   barColor: "#6366f1", glow: "rgba(99,102,241,0.12)"  },
  greedy: { label: "Greedy",      icon: "G",  accent: "border-emerald-500/40 bg-emerald-500/[0.07]", barColor: "#10b981", glow: "rgba(16,185,129,0.12)"  },
};

export default function BenchmarkResults({ data, onRerun }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 80);
    return () => clearTimeout(t);
  }, []);

  const isRealworld = Boolean(data.is_realworld);

  const chartData = isRealworld
    ? [
        { metric: "Clear Time (s)", ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.clearance_time ?? data.results[m]?.duration_seconds ?? 0])) },
        { metric: "Avg Wait (s)",   ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.avg_wait_time ?? 0])) },
        { metric: "Max Queue",      ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.max_queue ?? 0])) },
      ]
    : [
        { metric: "Vehicles Passed", ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.total_passed ?? 0])) },
        { metric: "Avg Wait (s)",    ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.avg_wait_time ?? 0])) },
        { metric: "Max Queue",       ...Object.fromEntries(data.modes.map((m) => [m, data.results[m]?.max_queue ?? 0])) },
      ];

  const aiImprovement = data.improvements?.ai_wait_pct ?? 0;
  const aiClearanceImprovement = data.improvements?.ai_clearance_pct ?? 0;

  return (
    <div className={`flex flex-col gap-3 transition-all duration-500 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"}`}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[11px] font-bold text-white tracking-wide uppercase">
            {isRealworld ? "Replay Showdown Results" : "Benchmark Results"}
          </h3>
          <p className="text-[10px] text-white/35 mt-0.5">
            {isRealworld
              ? `Cleared all ${data.total_vehicles ?? "recorded"} vehicles`
              : `${data.duration_seconds}s per mode`}
          </p>
        </div>
        <button
          onClick={onRerun}
          className="px-2.5 py-1.5 text-[10px] font-semibold rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-white/60 hover:text-white transition-all"
        >
          Run Again
        </button>
      </div>

      {/* AI Improvement Badge */}
      {isRealworld && (aiImprovement > 0 || aiClearanceImprovement > 0) && (
        <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-2.5 flex items-center gap-2">
          <span className="text-base">⚡</span>
          <div className="text-[10px] leading-tight">
            <span className="font-bold text-indigo-300">DQN AI Efficiency Gain:</span>{" "}
            <span className="text-white/80">
              {aiClearanceImprovement > 0 && `${aiClearanceImprovement}% faster clearance`}
              {aiClearanceImprovement > 0 && aiImprovement > 0 && " • "}
              {aiImprovement > 0 && `${aiImprovement}% lower wait time`} vs Fixed Timer.
            </span>
          </div>
        </div>
      )}

      {/* Vertical mode rows */}
      <div className="flex flex-col gap-2">
        {data.modes.map((mode, i) => {
          const result = data.results[mode];
          const cfg = MODE_CONFIG[mode] ?? { label: mode, icon: "?", accent: "border-white/15 bg-white/[0.03]", barColor: "#fff", glow: "rgba(255,255,255,0.05)" };
          const isWinner = mode === data.winner;
          const clearTime = result?.clearance_time ?? result?.duration_seconds ?? 0;
          return (
            <div
              key={mode}
              className={`relative rounded-xl border px-3 py-2.5 transition-all duration-500 ${isWinner ? "border-yellow-400/50 bg-yellow-400/[0.07]" : cfg.accent}`}
              style={{ transitionDelay: `${i * 80}ms`, boxShadow: isWinner ? "0 0 20px rgba(234,179,8,0.12)" : `0 0 12px ${cfg.glow}` }}
            >
              {isWinner && (
                <span className="absolute top-2 right-2 bg-yellow-400 text-black text-[8px] font-black px-1.5 py-0.5 rounded-full uppercase tracking-wider">
                  Winner
                </span>
              )}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 w-[72px] flex-shrink-0">
                  <span className={`text-[10px] font-semibold leading-tight ${isWinner ? "text-yellow-300" : "text-white/70"}`}>
                    {cfg.label}
                  </span>
                </div>
                <div className="flex gap-1.5 flex-1">
                  {isRealworld ? (
                    <>
                      <Pill label="Clear" value={clearTime} unit="s" winner={isWinner} />
                      <Pill label="Wait"  value={result?.avg_wait_time ?? 0} unit="s" winner={isWinner} />
                      <Pill label="Passed" value={result?.total_passed ?? 0} unit="veh" winner={isWinner} />
                      <Pill label="Max Q" value={result?.max_queue ?? 0} unit="" winner={isWinner} />
                    </>
                  ) : (
                    <>
                      <Pill label="Passed" value={result?.total_passed ?? 0} unit="veh" winner={isWinner} />
                      <Pill label="Wait"   value={result?.avg_wait_time ?? 0} unit="s"   winner={isWinner} />
                      <Pill label="Max Q"  value={result?.max_queue ?? 0}     unit=""    winner={isWinner} />
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart */}
      <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
        <p className="text-[9px] text-white/25 uppercase tracking-widest font-medium mb-2">Performance Comparison</p>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -22, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="metric" tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 8 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "rgba(255,255,255,0.25)", fontSize: 8 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#0f0f0f", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 10 }}
              labelStyle={{ color: "rgba(255,255,255,0.6)" }}
              itemStyle={{ color: "rgba(255,255,255,0.5)" }}
            />
            <Legend wrapperStyle={{ fontSize: 9, color: "rgba(255,255,255,0.4)" }} />
            {data.modes.map((mode) => (
              <Bar key={mode} dataKey={mode} name={MODE_CONFIG[mode]?.label ?? mode} fill={MODE_CONFIG[mode]?.barColor ?? "#fff"} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Pill({ label, value, unit, winner }: { label: string; value: number; unit: string; winner: boolean }) {
  return (
    <div className="flex flex-col items-center px-1.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06] flex-1 min-w-0">
      <span className="text-[7.5px] text-white/30 uppercase tracking-wider leading-none mb-0.5 w-full text-center truncate">{label}</span>
      <span className="text-[10px] font-bold font-mono leading-none" style={{ color: winner ? "#fbbf24" : "#94a3b8" }}>
        {typeof value === "number" ? value.toFixed(1) : value}
        {unit && <span className="text-[7.5px] font-normal ml-0.5 opacity-60">{unit}</span>}
      </span>
    </div>
  );
}
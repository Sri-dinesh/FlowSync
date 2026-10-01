"use client";

import { useMemo } from "react";
import { AlertTriangle, ShieldCheck, Activity, Eye, Clock, Layers } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

export default function UncertaintyPanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const history = useResearchStore((s) => s.history);

  const u = currentFrame?.uncertainty;

  // Timeline points for SVG rendering
  const timelineSvgPoints = useMemo(() => {
    if (!history.length) return "";
    const recent = history.slice(-60);
    const width = 100;
    const height = 100;
    
    return recent
      .map((f, i) => {
        const x = recent.length === 1 ? 0 : (i / (recent.length - 1)) * width;
        const score = f.uncertainty?.score ?? 0;
        const y = height - score * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [history]);

  if (!u) {
    return (
      <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl text-center text-xs text-white/30 font-mono">
        Awaiting perception uncertainty telemetry...
      </div>
    );
  }

  const isExceeded = u.score >= u.threshold_high;
  const isRecovering = u.score < u.threshold_high && u.score > u.threshold_low;
  const isNominal = u.score <= u.threshold_low;

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-xl flex flex-col gap-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-rose-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white">
            Perception Uncertainty & Health Engine
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span
            className={`px-2 py-0.5 rounded-full font-bold uppercase border ${
              isExceeded
                ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                : isRecovering
                ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
            }`}
          >
            {isExceeded ? "Threshold Exceeded (Fallback)" : isRecovering ? "Hysteresis Dwell" : "Nominal Visibility"}
          </span>
        </div>
      </div>

      {/* Main Composite Score Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        {/* Big Score Box */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider mb-1">
            Composite Uncertainty U(s_t)
          </span>
          <div
            className={`font-mono text-3xl font-extrabold tabular-nums ${
              isExceeded ? "text-rose-400" : isRecovering ? "text-amber-400" : "text-emerald-400"
            }`}
          >
            {u.score.toFixed(3)}
          </div>
          <span className="text-[10px] text-white/40 mt-1 font-mono">
            Range: [0.000, 1.000]
          </span>
        </div>

        {/* Timeline SVG Chart */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 md:col-span-2 flex flex-col justify-between h-28 relative overflow-hidden">
          <div className="flex items-center justify-between text-[9px] text-white/40 font-mono z-10">
            <span>U(s) History (Last 60 Steps)</span>
            <span className="text-rose-400">τ_high = {u.threshold_high.toFixed(2)}</span>
          </div>

          {/* SVG Chart with horizontal threshold lines */}
          <div className="relative w-full h-16 my-auto">
            {/* High Threshold Line (0.65) */}
            <div
              className="absolute left-0 right-0 border-t border-dashed border-rose-500/40 z-0"
              style={{ top: `${(1 - u.threshold_high) * 100}%` }}
            />
            {/* Low Threshold Line (0.50) */}
            <div
              className="absolute left-0 right-0 border-t border-dashed border-amber-500/30 z-0"
              style={{ top: `${(1 - u.threshold_low) * 100}%` }}
            />

            {/* Sparkline */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible z-10">
              <polyline
                fill="none"
                stroke={isExceeded ? "#f43f5e" : isRecovering ? "#f59e0b" : "#10b981"}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={timelineSvgPoints}
              />
            </svg>
          </div>

          <div className="flex items-center justify-between text-[8px] text-white/30 font-mono z-10">
            <span>t - 6.0s</span>
            <span className="text-amber-400">τ_low = {u.threshold_low.toFixed(2)}</span>
            <span>Current (t)</span>
          </div>
        </div>
      </div>

      {/* Multi-Feature Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Detector Var.</span>
          <span className="font-mono font-bold text-white tabular-nums">{u.detector.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-indigo-500" style={{ width: `${Math.min(100, u.detector * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Track Instab.</span>
          <span className="font-mono font-bold text-white tabular-nums">{u.tracking.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-cyan-500" style={{ width: `${Math.min(100, u.tracking * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Temp. Flicker</span>
          <span className="font-mono font-bold text-white tabular-nums">{u.flicker.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-amber-500" style={{ width: `${Math.min(100, u.flicker * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Occlusion</span>
          <span className="font-mono font-bold text-white tabular-nums">{u.occlusion.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-rose-500" style={{ width: `${Math.min(100, u.occlusion * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5 flex flex-col gap-1 col-span-2 sm:col-span-1">
          <span className="text-[9px] text-white/40 uppercase">Obs. Age</span>
          <span className="font-mono font-bold text-white tabular-nums">{u.observation_age_s.toFixed(2)}s</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, u.observation_age_s * 50)}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}

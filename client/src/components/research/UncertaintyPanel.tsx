"use client";

import { useMemo } from "react";
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
      <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-xs text-neutral-500">
        Waiting for uncertainty telemetry — run a simulation to see the 𝒰 gauge.
      </div>
    );
  }

  const isExceeded = u.score >= u.threshold_high;
  const isRecovering = u.score < u.threshold_high && u.score > u.threshold_low;

  const stateTone = isExceeded
    ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
    : isRecovering
      ? "border-neutral-700 bg-white/[0.03] text-neutral-300"
      : "border-neutral-700 bg-white/[0.03] text-neutral-300";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="text-sm font-medium text-white">
          Camera uncertainty
        </h3>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${stateTone}`}>
          {isExceeded ? "Unreliable — fallback on" : isRecovering ? "Recovering" : "Cameras reliable"}
        </span>
      </div>

      {/* Main Composite Score Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
        {/* Big Score Box */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-4 flex flex-col items-center justify-center text-center">
          <span className="text-[11px] font-medium text-neutral-500 mb-1">
            Uncertainty 𝒰 (0 = clean, 1 = blind)
          </span>
          <div
            className={`font-mono text-3xl font-semibold tabular-nums ${
              isExceeded ? "text-amber-300" : isRecovering ? "text-neutral-200" : "text-emerald-300"
            }`}
          >
            {u.score.toFixed(3)}
          </div>
          <span className="text-[11px] text-neutral-600 mt-1 font-mono tabular-nums">
            fallback above {u.threshold_high.toFixed(2)}
          </span>
        </div>

        {/* Timeline SVG Chart */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-3 md:col-span-2 flex flex-col justify-between h-28 relative overflow-hidden">
          <div className="flex items-center justify-between text-[11px] text-neutral-500 font-mono tabular-nums z-10">
            <span>Last 60 steps</span>
            <span className="text-neutral-400">fallback line {u.threshold_high.toFixed(2)}</span>
          </div>

          {/* SVG Chart with horizontal threshold lines */}
          <div className="relative w-full h-16 my-auto">
            {/* High Threshold Line */}
            <div
              className="absolute left-0 right-0 border-t border-dashed border-neutral-600 z-0"
              style={{ top: `${(1 - u.threshold_high) * 100}%` }}
            />
            {/* Low Threshold Line */}
            <div
              className="absolute left-0 right-0 border-t border-dashed border-neutral-800 z-0"
              style={{ top: `${(1 - u.threshold_low) * 100}%` }}
            />

            {/* Sparkline */}
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full overflow-visible z-10">
              <polyline
                fill="none"
                stroke={isExceeded ? "#fbbf24" : isRecovering ? "#a3a3a3" : "#6ee7b7"}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={timelineSvgPoints}
              />
            </svg>
          </div>

          <div className="flex items-center justify-between text-[11px] text-neutral-600 font-mono tabular-nums z-10">
            <span>−6.0s</span>
            <span>now</span>
          </div>
        </div>
      </div>

      {/* Cue breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] text-neutral-500">Detector</span>
          <span className="font-mono font-semibold text-sm text-white tabular-nums">{u.detector.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-neutral-400" style={{ width: `${Math.min(100, u.detector * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] text-neutral-500">Tracking</span>
          <span className="font-mono font-semibold text-sm text-white tabular-nums">{u.tracking.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-neutral-400" style={{ width: `${Math.min(100, u.tracking * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] text-neutral-500">Flicker</span>
          <span className="font-mono font-semibold text-sm text-white tabular-nums">{u.flicker.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-neutral-400" style={{ width: `${Math.min(100, u.flicker * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] text-neutral-500">Occlusion</span>
          <span className="font-mono font-semibold text-sm text-white tabular-nums">{u.occlusion.toFixed(3)}</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-neutral-400" style={{ width: `${Math.min(100, u.occlusion * 100)}%` }} />
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1 col-span-2 sm:col-span-1">
          <span className="text-[11px] text-neutral-500">Frame age</span>
          <span className="font-mono font-semibold text-sm text-white tabular-nums">{u.observation_age_s.toFixed(2)}s</span>
          <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full bg-neutral-400" style={{ width: `${Math.min(100, u.observation_age_s * 50)}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}

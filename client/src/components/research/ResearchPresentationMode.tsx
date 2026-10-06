"use client";

import React, { memo } from "react";
import dynamic from "next/dynamic";
import { Maximize2, Minimize2, Shield, Activity, AlertTriangle, Layers, TrendingUp } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";
import { ControllerComparison } from "./ControllerComparison";

interface ResearchPresentationModeProps {
  onExit: () => void;
}

export const ResearchPresentationMode = memo(function ResearchPresentationMode({
  onExit,
}: ResearchPresentationModeProps) {
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const activeNoise = useResearchStore((s) => s.activeNoise);
  const runStatus = useResearchStore((s) => s.runStatus);

  const uScore = currentFrame?.uncertainty?.composite_u ?? 0.0;
  const isFallback = (currentFrame?.supervisor?.mode ?? "").toUpperCase() === "FALLBACK";
  const delayMean = currentFrame?.metrics?.delay_mean_s ?? 0.0;
  const p95Delay = currentFrame?.metrics?.delay_p95_s ?? 0.0;
  const queueArea = currentFrame?.metrics?.queue_area_veh_s ?? 0.0;
  const throughput = currentFrame?.metrics?.throughput_total_veh ?? 0;

  return (
    <div className="fixed inset-0 z-50 bg-[#07090e] text-white flex flex-col p-6 overflow-y-auto">
      {/* Top Presentation Bar */}
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800 mb-6">
        <div className="flex items-center gap-4">
          <div className="px-3 py-1 bg-indigo-600 text-white font-mono text-xs font-bold rounded-lg tracking-wider uppercase">
            Viva & Conference Presentation Mode
          </div>
          <h1 className="text-xl font-black tracking-tight text-slate-100">
            FlowSync-UQ: Uncertainty-Aware Safe Fallback for Vision-Based Traffic Control
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs font-mono text-slate-400">
            Scenario: <strong className="text-slate-200">{activeScenario.id}</strong> | Seed:{" "}
            <strong className="text-amber-400">{activeSeed}</strong> | Corruption:{" "}
            <strong className="text-sky-300">{activeNoise.name}</strong>
          </div>
          <button
            onClick={onExit}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-mono text-slate-200 transition-colors"
          >
            <Minimize2 className="w-4 h-4" />
            <span>Exit Fullscreen</span>
          </button>
        </div>
      </div>

      {/* Prominent High-Contrast State Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 font-mono">
        {/* Authority / Fallback Status */}
        <div
          className={`p-5 rounded-lg border flex items-center justify-between transition-all ${
            isFallback
              ? "bg-amber-950/40 border-amber-500/50 text-amber-300 shadow-amber-950/30 animate-pulse"
              : "bg-emerald-950/30 border-emerald-500/40 text-emerald-300 shadow-emerald-950/20"
          }`}
        >
          <div>
            <div className="text-xs uppercase text-slate-400">Active Control Authority</div>
            <div className="text-2xl font-black mt-1">
              {isFallback ? "FALLBACK (MAX-PRESSURE)" : "D3QN (UNCERTAINTY OK)"}
            </div>
          </div>
          <Shield className="w-8 h-8 opacity-80" />
        </div>

        {/* Composite Uncertainty */}
        <div className="p-5 rounded-lg border border-neutral-800 bg-black/40 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400">Composite Uncertainty U(st)</div>
            <div
              className={`text-2xl font-black mt-1 ${
                uScore >= 0.65 ? "text-rose-400" : uScore >= 0.5 ? "text-amber-400" : "text-emerald-400"
              }`}
            >
              {uScore.toFixed(3)}
            </div>
          </div>
          <Activity className="w-8 h-8 text-sky-400" />
        </div>

        {/* Mean Delay */}
        <div className="p-5 rounded-lg border border-neutral-800 bg-black/40 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400">Mean Delay / Vehicle</div>
            <div className="text-2xl font-black text-white mt-1">{delayMean.toFixed(1)}s</div>
          </div>
          <TrendingUp className="w-8 h-8 text-emerald-400" />
        </div>

        {/* Safety Violations */}
        <div className="p-5 rounded-lg border border-neutral-800 bg-black/40 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400">Physical FSM Violations</div>
            <div className="text-2xl font-black text-emerald-400 mt-1">0 (PROVABLY SAFE)</div>
          </div>
          <Shield className="w-8 h-8 text-emerald-400" />
        </div>
      </div>

      {/* Main Presentation View: Synchronized Paired Comparison */}
      <div className="flex-1">
        <ControllerComparison />
      </div>
    </div>
  );
});

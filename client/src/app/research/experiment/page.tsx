"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { Sliders, Activity, Eye, Info, Database } from "lucide-react";
import {
  ResearchExperimentBuilder,
  ResearchRunHeader,
  DecisionInspector,
  QValuePanel,
  UncertaintyPanel,
  SafetyFSMPanel,
  ResearchMetricsPanel,
  PerceptionHealthPanel,
  ProvenanceDrawer,
} from "@/components/research";
import { useResearchSocket } from "@/hooks/useResearchSocket";
import { useResearchStore } from "@/store/researchStore";

// Dynamically import Three.js canvas to avoid SSR issues
const ResearchCanvas = dynamic(
  () => import("@/components/research/ResearchCanvas").then((mod) => mod.ResearchCanvas),
  { ssr: false }
);

export default function ResearchExperimentPage() {
  const { isConnected, sendCommand } = useResearchSocket();
  const [showConfigPanel, setShowConfigPanel] = useState<boolean>(true);
  const toggleProvenanceDrawer = useResearchStore((s) => s.toggleProvenanceDrawer);
  const runStatus = useResearchStore((s) => s.runStatus);

  return (
    <div className="min-h-screen bg-[#090b10] text-slate-100 flex flex-col">
      {/* Top Header */}
      <ResearchRunHeader />

      {/* Main Content Area */}
      <div className="flex-1 p-4 lg:p-6 grid grid-cols-1 xl:grid-cols-12 gap-5 max-w-[1920px] mx-auto w-full">
        {/* Left Side: 3D Simulation & Experiment Setup */}
        <div className="xl:col-span-7 flex flex-col gap-4">
          {/* Top Utility Bar */}
          <div className="flex items-center justify-between bg-[#12151c]/90 border border-white/10 rounded-xl px-4 py-2.5 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowConfigPanel((prev) => !prev)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold font-mono tracking-wide border transition-all ${
                  showConfigPanel
                    ? "bg-indigo-600/30 text-indigo-300 border-indigo-500/40 shadow-sm shadow-indigo-600/20"
                    : "bg-white/5 text-slate-400 border-white/10 hover:text-white"
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>{showConfigPanel ? "Hide Config" : "Show Config"}</span>
              </button>

              <div className="text-xs text-slate-400 font-mono hidden sm:flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>10 Hz Authoritative Research Stream</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={toggleProvenanceDrawer}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
                title="View deterministic experiment provenance and hashes"
              >
                <Database className="w-3.5 h-3.5 text-indigo-400" />
                <span>Provenance</span>
              </button>
            </div>
          </div>

          {/* Config Builder (Collapsible) */}
          {showConfigPanel && (
            <div className="transition-all duration-300">
              <ResearchExperimentBuilder />
            </div>
          )}

          {/* 3D Canvas */}
          <div className="flex-1 min-h-[480px] h-[540px] xl:h-[620px] relative">
            <ResearchCanvas quality="performance" />
          </div>

          {/* Live Decision Pipeline (FlowSync 6-Stage Pipeline) */}
          <DecisionInspector />
        </div>

        {/* Right Side: Deep Telemetry & Explainability Panels */}
        <div className="xl:col-span-5 flex flex-col gap-4">
          {/* Research Metrics (Authoritative Single Source of Truth) */}
          <ResearchMetricsPanel />

          {/* Uncertainty Timeline & Multi-cue Breakdown */}
          <UncertaintyPanel />

          {/* Two-column layout for Q-Values and Physical FSM */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <QValuePanel />
            <SafetyFSMPanel />
          </div>

          {/* Perception Health & Oracle Debug Overlay */}
          <PerceptionHealthPanel />
        </div>
      </div>

      {/* Provenance Audit Drawer */}
      <ProvenanceDrawer />
    </div>
  );
}

"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import Header from "@/components/layout/Header";
import { ResearchSubNav } from "@/components/research/ResearchSubNav";
import {
  Sliders,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  ResearchExperimentBuilder,
  ResearchRunHeader,
  ResearchConnectionBanner,
  ResearchRunSummary,
  DecisionInspector,
  QValuePanel,
  UncertaintyPanel,
  SafetyFSMPanel,
  ResearchMetricsPanel,
  PerceptionHealthPanel,
  ProvenanceDrawer,
} from "@/components/research";
import { useResearchStore } from "@/store/researchStore";

// Dynamically import Three.js canvas to avoid SSR issues
const ResearchCanvas = dynamic(
  () => import("@/components/research/ResearchCanvas").then((mod) => mod.ResearchCanvas),
  { ssr: false }
);

export default function ResearchExperimentPage() {
  const [showConfigPanel, setShowConfigPanel] = useState<boolean>(true);
  const toggleProvenanceDrawer = useResearchStore((s) => s.toggleProvenanceDrawer);
  const runStatus = useResearchStore((s) => s.runStatus);
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const hasStreamed = !!currentFrame;

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Global Application Header */}
      <Header />

      {/* Research Mode Sub-Navigation Bar */}
      <ResearchSubNav showActions={false} />

      {/* Main Content Area */}
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-4 max-w-[1440px] mx-auto w-full">
        {/* Backend connection + error surface (previously errors were invisible) */}
        <ResearchConnectionBanner />

        {/* Run completion summary (previously completion left panels frozen silently) */}
        <ResearchRunSummary />

        {/* Experiment Run Header (ID, Badges, Pause/Resume, Debug Overlay) */}
        <ResearchRunHeader onOpenProvenance={toggleProvenanceDrawer} />

        {/* Grid Layout: Left (Simulation & Inspector) / Right (Deep Telemetry Panels) */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 w-full">
          {/* Left Column: 3D Simulation & Experiment Setup */}
          <div className="xl:col-span-7 flex flex-col gap-4">
            {/* Config toggle */}
            <div className="flex items-center">
              <button
                onClick={() => setShowConfigPanel((prev) => !prev)}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>{showConfigPanel ? "Hide setup" : "Show setup"}</span>
                {showConfigPanel ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            {/* Config Builder (Collapsible) */}
            {showConfigPanel && (
              <div className="transition-all duration-300">
                <ResearchExperimentBuilder />
              </div>
            )}

            {/* 3D Canvas */}
            <div className="flex-1 min-h-[480px] h-[540px] xl:h-[620px] relative rounded-lg overflow-hidden border border-neutral-800 bg-neutral-900/60">
              <ResearchCanvas quality="performance" />
              {!hasStreamed && runStatus !== "running" && runStatus !== "starting" && (
                <div className="absolute inset-x-0 bottom-4 z-10 flex justify-center pointer-events-none">
                  <p className="text-xs text-neutral-400 bg-neutral-900/90 border border-neutral-800 rounded-full px-4 py-1.5">
                    Configure above, then press Run simulation
                  </p>
                </div>
              )}
            </div>

            {/* Live Decision Pipeline (FlowSync 6-Stage Pipeline) */}
            <DecisionInspector />
          </div>

          {/* Right Column: Deep Telemetry & Explainability Panels */}
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
      </main>

      {/* Provenance Audit Drawer */}
      <ProvenanceDrawer />
    </div>
  );
}

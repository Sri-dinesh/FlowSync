"use client";

import React from "react";
import Header from "@/components/layout/Header";
import { ResearchSubNav } from "@/components/research/ResearchSubNav";
import { Database } from "lucide-react";
import { ControllerComparison } from "@/components/research/ControllerComparison";
import { ProvenanceDrawer } from "@/components/research/ProvenanceDrawer";
import { ResearchConnectionBanner } from "@/components/research/ResearchConnectionBanner";
import { ResearchRunSummary } from "@/components/research/ResearchRunSummary";
import { useResearchStore } from "@/store/researchStore";

export default function ResearchComparePage() {
  const toggleProvenanceDrawer = useResearchStore((s) => s.toggleProvenanceDrawer);
  const selectNoise = useResearchStore((s) => s.selectNoise);
  const activeNoise = useResearchStore((s) => s.activeNoise);

  // NOTE: ids MUST match backend FAULT_PRESETS keys in
  // research/noise/fault_injector.py — unknown ids silently run as clean.
  const presets = [
    { id: "clean", name: "Clean", desc: "No camera faults" },
    { id: "miss_30", name: "30% missed", desc: "Camera drops 30% of vehicles (benchmark standard)" },
    { id: "burst_occlusion", name: "Burst occlusion", desc: "Prolonged line-of-sight loss, north/south" },
    { id: "combined_severe", name: "Combined", desc: "Missed + latency + burst + ghosts" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Global Application Header */}
      <Header />

      {/* Research Mode Sub-Navigation Bar */}
      <ResearchSubNav showActions={false} />

      {/* Main Container */}
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 max-w-[1440px] mx-auto w-full flex flex-col gap-4">
        <ResearchConnectionBanner />
        <ResearchRunSummary />

        {/* Fault + provenance row */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-neutral-500">
            Camera fault:
          </span>
          {presets.map((preset) => {
            const isSelected = activeNoise.id === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => selectNoise({ ...preset, type: "FAULT", intensity: preset.id === "clean" ? 0 : 0.3 })}
                title={preset.desc}
                className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
                  isSelected
                    ? "bg-white/10 text-white border-white/20"
                    : "bg-transparent text-neutral-400 border-neutral-800 hover:text-white hover:border-neutral-700"
                }`}
              >
                {preset.name}
              </button>
            );
          })}
          <button
            onClick={toggleProvenanceDrawer}
            className="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs text-neutral-500 hover:text-white transition-colors"
            title="View deterministic experiment provenance and hashes"
          >
            <Database className="w-3.5 h-3.5" />
            <span>Provenance</span>
          </button>
        </div>

        {/* Controller Comparison Core */}
        <ControllerComparison />
      </main>

      {/* Provenance Drawer */}
      <ProvenanceDrawer />
    </div>
  );
}

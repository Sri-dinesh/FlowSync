"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Database, Sliders, ShieldCheck } from "lucide-react";
import { ControllerComparison } from "@/components/research/ControllerComparison";
import { ProvenanceDrawer } from "@/components/research/ProvenanceDrawer";
import { useResearchStore } from "@/store/researchStore";

export default function ResearchComparePage() {
  const toggleProvenanceDrawer = useResearchStore((s) => s.toggleProvenanceDrawer);
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const selectNoise = useResearchStore((s) => s.selectNoise);
  const activeNoise = useResearchStore((s) => s.activeNoise);

  const presets = [
    {
      id: "clean",
      name: "Clean Baseline",
      type: "NONE",
      intensity: 0.0,
      desc: "Zero corruption on camera sensors",
    },
    {
      id: "missed_30",
      name: "30% Missed Detections",
      type: "MISSED_DETECTION",
      intensity: 0.3,
      desc: "Camera drops 30% of incoming vehicles",
    },
    {
      id: "occlusion_high",
      name: "Occlusion + High Latency",
      type: "OCCLUSION",
      intensity: 0.4,
      desc: "Severe field-of-view blindspots",
    },
    {
      id: "combined_corrupt",
      name: "Combined Degradation (30%)",
      type: "COMBINED",
      intensity: 0.3,
      desc: "Missed + False Positives + Latency + Noise",
    },
  ];

  return (
    <div className="min-h-screen bg-[#090b10] text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 border-b border-white/10 bg-[#0d1017]/95 px-6 flex items-center justify-between sticky top-0 z-30 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <Link
            href="/research/experiment"
            className="flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-white px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Single Experiment</span>
          </Link>
          <div className="h-5 w-[1px] bg-white/10" />
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">
              Paired Controller Comparison Mode
            </h1>
            <p className="text-[11px] font-mono text-slate-400">
              Synchronized Common Random Numbers (CRN) Evaluation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleProvenanceDrawer}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 transition-colors"
          >
            <Database className="w-3.5 h-3.5 text-indigo-400" />
            <span>Provenance</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 p-6 max-w-[1920px] mx-auto w-full flex flex-col gap-6">
        {/* Preset Selector Bar */}
        <div className="bg-[#12151c]/90 border border-white/10 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-bold font-mono uppercase text-slate-300">
              Quick Research Presets:
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {presets.map((preset) => {
              const isSelected = activeNoise.name === preset.name;
              return (
                <button
                  key={preset.id}
                  onClick={() => selectNoise(preset)}
                  className={`px-3 py-2 rounded-xl text-xs font-mono tracking-wide border transition-all text-left ${
                    isSelected
                      ? "bg-indigo-600/30 text-indigo-200 border-indigo-500/50 shadow-md shadow-indigo-600/20"
                      : "bg-black/40 text-slate-400 border-white/5 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <div className="font-bold">{preset.name}</div>
                  <div className="text-[10px] text-slate-400">{preset.desc}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Controller Comparison Core */}
        <ControllerComparison />
      </main>

      {/* Provenance Drawer */}
      <ProvenanceDrawer />
    </div>
  );
}

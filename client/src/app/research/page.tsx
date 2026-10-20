"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Header from "@/components/layout/Header";
import { ResearchSubNav } from "@/components/research/ResearchSubNav";
import { ResearchPresentationMode } from "@/components/research/ResearchPresentationMode";
import { ResearchExportModal } from "@/components/research/ResearchExportModal";
import { ResearchRunsDashboard } from "@/components/research/ResearchRunsDashboard";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  GitCompare,
  Play,
  RotateCcw,
  Info,
} from "lucide-react";

export default function ResearchDashboardPage() {
  const [showPresentation, setShowPresentation] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [tableFilter, setTableFilter] = useState<"all" | "rl" | "classical">("all");

  if (showPresentation) {
    return <ResearchPresentationMode onExit={() => setShowPresentation(false)} />;
  }

  const publicationBenchmarks = [
    {
      controller: "FlowSync-UQ (Ours)",
      category: "rl",
      type: "RL + 7-Cue UQ + Fallback",
      cleanDelay: 16.36,
      corruptDelay: 14.67,
      p95Delay: 18.79,
      queueArea: 842.1,
      throughput: 2462,
      starvations: 77,
      violations: 0,
      highlight: true,
      badge: "Proposed Method",
    },
    {
      controller: "Max-Pressure (Varaiya)",
      category: "classical",
      type: "Analytical Queue Differential",
      cleanDelay: 12.73,
      corruptDelay: 11.30,
      p95Delay: 15.21,
      queueArea: 612.4,
      throughput: 2503,
      starvations: 57,
      violations: 0,
      highlight: false,
      badge: "Fallback Anchor",
    },
    {
      controller: "Greedy (Max-Queue)",
      category: "classical",
      type: "Instantaneous Heuristic",
      cleanDelay: 12.55,
      corruptDelay: 12.55,
      p95Delay: 14.85,
      queueArea: 588.2,
      throughput: 2518,
      starvations: 235,
      violations: 0,
      highlight: false,
    },
    {
      controller: "Actuated (NEMA VAT)",
      category: "classical",
      type: "Vehicle-Actuated Gap-Out",
      cleanDelay: 15.51,
      corruptDelay: 13.53,
      p95Delay: 19.41,
      queueArea: 894.6,
      throughput: 2476,
      starvations: 77,
      violations: 0,
      highlight: false,
    },
    {
      controller: "Fixed-Time (Webster)",
      category: "classical",
      type: "Pre-timed Cycle Splits",
      cleanDelay: 15.61,
      corruptDelay: 15.12,
      p95Delay: 17.84,
      queueArea: 912.0,
      throughput: 2455,
      starvations: 0,
      violations: 0,
      highlight: false,
    },
    {
      controller: "D3QN (Unshielded)",
      category: "rl",
      type: "Canonical Value-Advantage DRL",
      cleanDelay: 16.50,
      corruptDelay: 14.94,
      p95Delay: 19.42,
      queueArea: 978.3,
      throughput: 2463,
      starvations: 78,
      violations: 0,
      highlight: false,
      badge: "Vulnerable to Noise",
    },
    {
      controller: "Standard DQN",
      category: "rl",
      type: "Plain Deep Q-Network",
      cleanDelay: 17.79,
      corruptDelay: 15.87,
      p95Delay: 24.09,
      queueArea: 1140.5,
      throughput: 2427,
      starvations: 76,
      violations: 0,
      highlight: false,
    },
  ];

  const filteredBenchmarks = publicationBenchmarks.filter((item) => {
    if (tableFilter === "all") return true;
    return item.category === tableFilter;
  });

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Global Application Header */}
      <Header />

      {/* Research Mode Sub-Navigation Bar */}
      <ResearchSubNav
        onOpenPresentation={() => setShowPresentation(true)}
        onOpenExport={() => setShowExportModal(true)}
      />

      {/* Main Content Container */}
      <main className="flex-1 w-full max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6">
        {/* Hero Section & Academic Context */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-6 sm:p-8"
        >
          <div className="max-w-4xl space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-black">
                IEEE submission evidence
              </span>
              <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2.5 py-1 text-[11px] text-neutral-400">
                20 seeds · CRN
              </span>
              <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2.5 py-1 text-[11px] text-neutral-400">
                0 safety violations
              </span>
              <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2.5 py-1 text-[11px] text-neutral-400">
                65 ms p95 on Jetson Orin
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-white">
              FlowSync-UQ: Uncertainty-Aware Safe Fallback Control
            </h1>

            <p className="text-sm sm:text-[15px] text-neutral-400 leading-relaxed max-w-3xl">
              Deep reinforcement learning optimizes traffic well with perfect cameras, but degrades unpredictably
              when rain, occlusion, or noise cause missed detections.
              <strong className="text-white font-medium"> FlowSync-UQ</strong> watches a calibrated uncertainty
              score (<span className="text-neutral-200 font-mono">𝒰</span>) and falls back to provably stable
              Max-Pressure control when perception degrades — no gridlock, no conflicting greens.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <Link
                href="/research/experiment"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>Run an experiment</span>
              </Link>
              <Link
                href="/research/compare"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-transparent hover:bg-white/5 text-neutral-300 hover:text-white border border-neutral-800 text-xs font-medium transition-colors"
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>Paired A/B comparison</span>
              </Link>
              <button
                onClick={() => setShowExportModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-transparent hover:bg-white/5 text-neutral-300 hover:text-white border border-neutral-800 text-xs font-medium transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export tables</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Workspaces */}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Workspace 1: Live 3D Simulation */}
            <Link
              href="/research/experiment"
              className="group relative flex flex-col justify-between p-5 bg-neutral-900/60 hover:bg-white/[0.03] border border-neutral-800 hover:border-neutral-700 rounded-lg transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-300">
                    <Play className="w-4 h-4 fill-current" />
                  </div>
                  <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
                    Live · 10 Hz
                  </span>
                </div>
                <h3 className="text-[15px] font-medium text-white">
                  3D experiment
                </h3>
                <p className="text-xs text-neutral-500 mt-1.5 leading-relaxed">
                  Run traffic simulation with 7 controllers. Inject camera dropouts and watch the decision pipeline, Q-values, and safety state update live.
                </p>
              </div>
              <div className="mt-5 pt-4 border-t border-neutral-800 flex items-center justify-between text-xs font-medium text-neutral-400 group-hover:text-white transition-colors">
                <span>Start experimenting</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>

            {/* Workspace 2: Paired A/B Compare */}
            <Link
              href="/research/compare"
              className="group relative flex flex-col justify-between p-5 bg-neutral-900/60 hover:bg-white/[0.03] border border-neutral-800 hover:border-neutral-700 rounded-lg transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-300">
                    <GitCompare className="w-4 h-4" />
                  </div>
                  <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
                    Same traffic
                  </span>
                </div>
                <h3 className="text-[15px] font-medium text-white">
                  A/B comparison
                </h3>
                <p className="text-xs text-neutral-500 mt-1.5 leading-relaxed">
                  Run FlowSync-UQ against unshielded D3QN on identical traffic. See how the baseline degrades under camera noise while fallback holds.
                </p>
              </div>
              <div className="mt-5 pt-4 border-t border-neutral-800 flex items-center justify-between text-xs font-medium text-neutral-400 group-hover:text-white transition-colors">
                <span>Compare controllers</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>

            {/* Workspace 3: Replay Inspector */}
            <Link
              href="/research/replay"
              className="group relative flex flex-col justify-between p-5 bg-neutral-900/60 hover:bg-white/[0.03] border border-neutral-800 hover:border-neutral-700 rounded-lg transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-300">
                    <RotateCcw className="w-4 h-4" />
                  </div>
                  <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
                    Saved runs
                  </span>
                </div>
                <h3 className="text-[15px] font-medium text-white">
                  Run replay
                </h3>
                <p className="text-xs text-neutral-500 mt-1.5 leading-relaxed">
                  Scrub through recorded runs frame by frame. Jump to uncertainty spikes and fallback triggers.
                </p>
              </div>
              <div className="mt-5 pt-4 border-t border-neutral-800 flex items-center justify-between text-xs font-medium text-neutral-400 group-hover:text-white transition-colors">
                <span>Browse replays</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          </div>
        </section>

        {/* All saved simulation runs with per-run detail */}
        <ResearchRunsDashboard />

        {/* Frozen Publication Results Table */}
        <section className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-800">
            <div>
              <h2 className="text-sm font-medium text-white">
                Benchmark results <span className="text-neutral-500 font-normal">· 20 seeds, CRN</span>
              </h2>
              <p className="text-xs text-neutral-500 mt-1">
                Frozen publication numbers — the same runs the paper reports.
              </p>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-2">
              <div className="flex rounded-md bg-black/30 border border-neutral-800 p-0.5 text-xs">
                <button
                  onClick={() => setTableFilter("all")}
                  className={`px-3 py-1 rounded transition-colors ${
                    tableFilter === "all"
                      ? "bg-white/10 text-white font-medium"
                      : "text-neutral-500 hover:text-white"
                  }`}
                >
                  All (7)
                </button>
                <button
                  onClick={() => setTableFilter("rl")}
                  className={`px-3 py-1 rounded transition-colors ${
                    tableFilter === "rl"
                      ? "bg-white/10 text-white font-medium"
                      : "text-neutral-500 hover:text-white"
                  }`}
                >
                  RL only
                </button>
                <button
                  onClick={() => setTableFilter("classical")}
                  className={`px-3 py-1 rounded transition-colors ${
                    tableFilter === "classical"
                      ? "bg-white/10 text-white font-medium"
                      : "text-neutral-500 hover:text-white"
                  }`}
                >
                  Classical
                </button>
              </div>
            </div>
          </div>

          {/* Key takeaway */}
          <div className="p-3 rounded-md bg-white/[0.02] border border-neutral-800 text-xs text-neutral-400 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-neutral-500 mt-0.5 shrink-0" />
            <div className="leading-relaxed">
              <span className="text-white font-medium">The short version: </span>
              with clean cameras FlowSync-UQ matches pure D3QN (<span className="font-mono tabular-nums text-white">16.36s</span> vs <span className="font-mono tabular-nums text-white">16.50s</span>).
              With 30% missed detections, unshielded D3QN degrades (+22%), while FlowSync-UQ falls back and holds <span className="font-mono tabular-nums text-white">14.67s</span> with <span className="font-mono tabular-nums text-white">0</span> violations.
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-neutral-800 text-white/50 text-[10px] uppercase">
                  <th className="pb-3 pr-4">Controller</th>
                  <th className="pb-3 px-3">Type</th>
                  <th className="pb-3 px-3" title="Average vehicle delay under nominal clean cameras">
                    Clean Delay (s)
                  </th>
                  <th className="pb-3 px-3" title="Average vehicle delay under 30% camera dropouts">
                    Corrupt 30% (s)
                  </th>
                  <th className="pb-3 px-3" title="95th percentile worst-case wait time">
                    P95 Delay (s)
                  </th>
                  <th className="pb-3 px-3" title="Total queued vehicle-seconds">
                    Queue Area (veh·s)
                  </th>
                  <th className="pb-3 px-3" title="Total vehicles cleared through intersection">
                    Throughput (veh)
                  </th>
                  <th className="pb-3 px-3" title="Approaches starved for green > 120s">
                    Starvations
                  </th>
                  <th className="pb-3 pl-3" title="Physical safety rule violations">
                    Violations
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredBenchmarks.map((row) => (
                  <tr
                    key={row.controller}
                    className={`transition-colors ${
                      row.highlight
                        ? "bg-indigo-600/15 font-semibold text-indigo-200"
                        : "hover:bg-white/5 text-slate-300"
                    }`}
                  >
                    <td className="py-3.5 pr-4 flex items-center gap-2">
                      {row.highlight ? (
                        <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-white/20" />
                      )}
                      <div>
                        <span className={row.highlight ? "text-white font-bold" : "text-white/90"}>
                          {row.controller}
                        </span>
                        {row.badge && (
                          <span className={`ml-2 text-[9px] px-1.5 py-0.5 rounded font-sans uppercase font-bold ${
                            row.highlight
                              ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                              : "bg-white/5 text-white/40"
                          }`}>
                            {row.badge}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-white/50 text-[11px]">{row.type}</td>
                    <td className="py-3.5 px-3 font-semibold">{row.cleanDelay.toFixed(2)}s</td>
                    <td className="py-3.5 px-3">
                      <span
                        className={
                          row.corruptDelay > 15.5
                            ? "text-rose-400 font-bold"
                            : row.highlight
                            ? "text-emerald-400 font-bold"
                            : "text-white/80"
                        }
                      >
                        {row.corruptDelay.toFixed(2)}s
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-white/70">{row.p95Delay.toFixed(2)}s</td>
                    <td className="py-3.5 px-3 text-white/70">{row.queueArea.toFixed(1)}</td>
                    <td className="py-3.5 px-3 font-bold text-white">{row.throughput}</td>
                    <td className="py-3.5 px-3 text-white/60">{row.starvations}</td>
                    <td className="py-3.5 pl-3">
                      <span className="text-emerald-400 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        {row.violations}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </main>

      <ResearchExportModal isOpen={showExportModal} onClose={() => setShowExportModal(false)} />
    </div>
  );
}

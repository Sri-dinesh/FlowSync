"use client";

import React, { useState, useEffect, Suspense } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import Header from "@/components/layout/Header";
import { ResearchSubNav } from "@/components/research/ResearchSubNav";
import {
  Database,
  Play,
  AlertTriangle,
} from "lucide-react";
import {
  ReplayTimeline,
  ResearchMetricsPanel,
  UncertaintyPanel,
  DecisionInspector,
  ProvenanceDrawer,
  ResearchConnectionBanner,
  ResearchRunSummary,
} from "@/components/research";
import { useResearchStore } from "@/store/researchStore";
import { useResearchSocket } from "@/hooks/useResearchSocket";
import { getFastApiUrls } from "@/lib/utils";

const ResearchCanvas = dynamic(
  () => import("@/components/research/ResearchCanvas").then((mod) => mod.ResearchCanvas),
  { ssr: false }
);

interface SavedRun {
  run_id: string;
  scenario: string;
  controller: string;
  seed: number;
  steps: number;
  duration_s: number;
  avg_delay: number;
  p95_delay: number;
  throughput: number;
  status: string;
  timestamp: string;
  /** True for built-in demo rows shown while the backend is offline (not replayable). */
  demo?: boolean;
}

/** Map the FastAPI /research/runs shape onto the replay catalog rows. */
function mapBackendRuns(payload: { runs?: unknown }): SavedRun[] {
  const list = Array.isArray(payload?.runs) ? payload.runs : [];
  return (list as Record<string, unknown>[]).map((r) => ({
    run_id: String(r.experiment_id ?? r.run_id ?? ""),
    scenario: String(r.scenario_id ?? r.scenario ?? ""),
    controller: String(r.controller_name ?? r.controller ?? ""),
    seed: Number(r.seed ?? 0),
    steps: Number(r.num_steps ?? r.steps ?? 0),
    duration_s: Number(r.duration_s ?? Number(r.num_steps ?? r.steps ?? 0) * 0.1),
    avg_delay: Number(r.avg_delay ?? 0),
    p95_delay: Number(r.p95_delay ?? 0),
    throughput: Number(r.throughput ?? 0),
    status: String(r.status ?? (r.has_trajectory ? "COMPLETED" : "UNKNOWN")),
    timestamp: String(r.timestamp ?? ""),
  })).filter((r: SavedRun) => r.run_id);
}

function ResearchReplayContent({ initialRunId }: { initialRunId?: string }) {
  const searchParams = useSearchParams();
  const runFromUrl = searchParams?.get("run") ?? undefined;
  const effectiveInitial = initialRunId ?? runFromUrl;
  const [runs, setRuns] = useState<SavedRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(effectiveInitial ?? null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const { replayRun } = useResearchSocket();
  const toggleProvenanceDrawer = useResearchStore((s) => s.toggleProvenanceDrawer);
  const runStatus = useResearchStore((s) => s.runStatus);
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const isConnected = useResearchStore((s) => s.isWsConnected);

  useEffect(() => {
    const { httpUrl } = getFastApiUrls();
    // Authoritative backend catalog (previously this hit a non-existent
    // Next.js route /api/research/runs, so the list was always mock data).
    fetch(`${httpUrl}/research/runs?limit=100`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const mapped = mapBackendRuns(data);
        setRuns(mapped);
        setCatalogError(null);
        if (!selectedRunId && mapped.length > 0) {
          setSelectedRunId(mapped[0].run_id);
        }
        setIsLoading(false);
      })
      .catch((err) => {
        console.warn("Backend runs fetch failed, showing demo preview:", err);
        setCatalogError(
          `Cannot reach backend catalog at ${httpUrl}/research/runs. Showing a read-only demo preview — start the backend to replay real runs.`
        );
        // Clearly-labelled demo rows (not replayable) instead of silent mock data.
        const demoRuns: SavedRun[] = [
          {
            run_id: "demo_flowsync_uq_clean",
            scenario: "test_clean_balanced_01",
            controller: "FlowSync-UQ (Ours)",
            seed: 1101,
            steps: 1200,
            duration_s: 120.0,
            avg_delay: 16.36,
            p95_delay: 18.79,
            throughput: 2462,
            status: "DEMO",
            timestamp: "2026-10-01T10:00:00Z",
            demo: true,
          },
          {
            run_id: "demo_d3qn_corrupted30",
            scenario: "test_clean_balanced_01",
            controller: "D3QN (Unshielded)",
            seed: 1101,
            steps: 1200,
            duration_s: 120.0,
            avg_delay: 18.21,
            p95_delay: 24.4,
            throughput: 2410,
            status: "DEMO",
            timestamp: "2026-10-01T11:00:00Z",
            demo: true,
          },
        ];
        setRuns(demoRuns);
        if (!selectedRunId) setSelectedRunId(demoRuns[0].run_id);
        setIsLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectRun = (run: SavedRun) => {
    if (run.demo) return; // demo rows carry no backend trajectory
    setSelectedRunId(run.run_id);
    replayRun(run.run_id, 1.0);
  };

  // Deep-link support: auto-stream the requested run once the catalog arrives.
  // selectedRunId is already initialised to effectiveInitial, so this effect
  // only kicks off the stream (an external-system update, not a render sync).
  const didAutoReplay = React.useRef(false);
  useEffect(() => {
    if (isLoading || !effectiveInitial || didAutoReplay.current) return;
    const target = runs.find((r) => r.run_id === effectiveInitial);
    if (target && !target.demo && !useResearchStore.getState().currentFrame) {
      didAutoReplay.current = true;
      replayRun(target.run_id, 1.0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, runs]);

  const activeRun = runs.find((r) => r.run_id === selectedRunId);
  const isReplayingSelected =
    !!currentFrame && currentFrame.experiment_id === selectedRunId &&
    (runStatus === "running" || runStatus === "paused" || runStatus === "starting");

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

        {catalogError && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-4 flex items-start gap-2.5 text-xs text-amber-200/90">
            <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <span>{catalogError}</span>
          </div>
        )}

        {/* Main Grid: Catalog / 3D Canvas / Telemetry */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 w-full">
          {/* Left Column: Replay Catalog & Selector */}
          <div className="xl:col-span-4 flex flex-col gap-4">
            <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4">
              <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
                <h2 className="text-sm font-medium text-white">
                  Saved runs ({runs.length})
                </h2>
                <button
                  onClick={toggleProvenanceDrawer}
                  className="flex items-center gap-1 text-[11px] text-neutral-500 hover:text-white transition-colors"
                  title="View deterministic experiment provenance and hashes"
                >
                  <Database className="w-3 h-3" />
                  <span>Provenance</span>
                </button>
              </div>

              {isLoading ? (
                <div className="text-center py-12 text-xs font-mono text-white/40 animate-pulse">
                  Loading saved runs...
                </div>
              ) : runs.length === 0 ? (
                <div className="text-center py-12 px-4 space-y-2">
                  <p className="text-xs font-bold text-white">No saved runs yet</p>
                  <p className="text-xs text-white/50 leading-relaxed">
                    Run a simulation on the <span className="text-indigo-300 font-semibold">Live 3D Experiment</span> page
                    first — finished runs are saved automatically and appear here for replay.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                  {runs.map((run) => {
                    const isSelected = run.run_id === selectedRunId;
                    return (
                      <button
                        key={run.run_id}
                        onClick={() => handleSelectRun(run)}
                        disabled={run.demo}
                        title={run.demo ? "Demo preview only — start the backend to replay real runs" : `Replay ${run.run_id}`}
                        className={`w-full text-left p-3 rounded-md border transition-colors flex flex-col gap-1.5 ${
                          isSelected
                            ? "bg-white/[0.06] border-neutral-500"
                            : run.demo
                              ? "bg-transparent border-neutral-800/60 opacity-50 cursor-not-allowed"
                              : "bg-transparent border-neutral-800 hover:border-neutral-600 hover:bg-white/[0.02]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-mono tabular-nums text-white truncate">
                            {run.run_id}
                          </span>
                          <span
                            className={`shrink-0 rounded-full border px-1.5 py-px text-[10px] ${
                              run.status === "COMPLETED"
                                ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/10"
                                : run.demo || run.status === "DEMO"
                                  ? "text-neutral-500 border-neutral-800"
                                  : "text-amber-300 border-amber-500/30 bg-amber-500/10"
                            }`}
                          >
                            {run.status === "COMPLETED" ? "Done" : run.status}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-neutral-500">
                          <span className="truncate">{run.controller}</span>
                          <span className="font-mono tabular-nums shrink-0">seed {run.seed}</span>
                        </div>

                        <div className="flex items-center gap-3 text-[11px] font-mono tabular-nums text-neutral-500 pt-1.5 border-t border-neutral-800/70">
                          <span>{run.avg_delay}s avg</span>
                          <span>{run.throughput} cleared</span>
                          {isSelected && !run.demo && (
                            <span className="ml-auto flex items-center gap-1 text-neutral-300">
                              <Play className="w-3 h-3" />
                              {isReplayingSelected ? "Playing" : "Replay"}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Selected run details */}
            {activeRun && (
              <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 text-xs flex flex-col gap-2">
                <h3 className="text-sm font-medium text-white pb-2 border-b border-neutral-800">Run details</h3>

                <div className="space-y-1.5 text-neutral-500 text-[11px]">
                  <div className="flex justify-between gap-2">
                    <span>Scenario</span>
                    <span className="text-neutral-200 font-mono truncate">{activeRun.scenario}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Length</span>
                    <span className="text-neutral-200 font-mono tabular-nums">{activeRun.duration_s}s · {activeRun.steps} steps</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Worst 5%</span>
                    <span className="text-neutral-200 font-mono tabular-nums">{activeRun.p95_delay}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Saved</span>
                    <span className="text-neutral-200">
                      {activeRun.timestamp ? new Date(activeRun.timestamp).toLocaleString() : "—"}
                    </span>
                  </div>
                  {!isConnected && (
                    <div className="pt-1 text-amber-300/90">
                      Offline — replay starts on reconnect.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Canvas, Scrubber & Telemetry */}
          <div className="xl:col-span-8 flex flex-col gap-4">
            {/* Scrubber Timeline */}
            <ReplayTimeline />

            {/* Canvas */}
            <div className="h-[420px] w-full rounded-lg overflow-hidden border border-neutral-800 bg-neutral-900/60 relative">
              <ResearchCanvas quality="performance" />
              {!currentFrame && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/55 p-6 pointer-events-none">
                  <p className="text-xs text-neutral-400 text-center max-w-sm leading-relaxed bg-neutral-900 border border-neutral-800 rounded-md px-4 py-3">
                    Pick a saved run on the left to play its recording here, then drag the timeline to jump around.
                  </p>
                </div>
              )}
            </div>

            {/* Decision Inspector and Uncertainty Panel */}
            <DecisionInspector />
            <UncertaintyPanel />
            <ResearchMetricsPanel />
          </div>
        </div>
      </main>

      {/* Provenance Drawer */}
      <ProvenanceDrawer />
    </div>
  );
}

export default function ResearchReplayPage({ initialRunId }: { initialRunId?: string }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center text-xs font-mono text-white/40">Loading replay…</div>}>
      <ResearchReplayContent initialRunId={initialRunId} />
    </Suspense>
  );
}

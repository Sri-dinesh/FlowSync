"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import SimulationControls from "@/components/controls/SimulationControls";
import TrainingControls from "@/components/controls/TrainingControls";
import SimulationBenchmarkPanel from "@/components/dashboard/SimulationBenchmarkPanel";
import LiveSnapshot from "@/components/dashboard/LiveSnapshot";
import MetricsPanel from "@/components/dashboard/MetricsPanel";
import QValuePanel from "@/components/dashboard/QValuePanel";
import { ScenarioSelector } from "@/components/simulation/ScenarioSelector";
import dynamic from "next/dynamic";

const SimulationCanvas = dynamic(
  () => import("@/components/simulation/SimulationCanvas"),
  { ssr: false }
);

const TrainingChart = dynamic(
  () => import("@/components/dashboard/TrainingChart"),
  {
    ssr: false,
    loading: () => (
      <div className="h-40 flex items-center justify-center text-xs text-neutral-500">
        Loading charts…
      </div>
    ),
  }
);

const EpisodeHistory = dynamic(
  () => import("@/components/dashboard/EpisodeHistory"),
  {
    ssr: false,
    loading: () => (
      <div className="h-40 flex items-center justify-center text-xs text-neutral-500">
        Loading history…
      </div>
    ),
  }
);

const ScenarioHistory = dynamic(
  () =>
    import("@/components/simulation/ScenarioHistory").then(
      (m) => m.ScenarioHistory
    ),
  { ssr: false }
);

const ScenarioAggregatePanel = dynamic(
  () =>
    import("@/components/simulation/ScenarioAggregatePanel").then(
      (m) => m.ScenarioAggregatePanel
    ),
  { ssr: false }
);

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSimulationSocket } from "@/hooks/useSimulationSocket";
import { useTrainingSocket } from "@/hooks/useTrainingSocket";
import { useSimulations } from "@/hooks/useSimulations";
import { useSimulationStore } from "@/store/simulationStore";
import type { Scenario } from "@/types/simulation";

export default function SimulationPage() {
  const {
    sendCommand: sendSimulationCommand,
    benchmarkRunning,
    benchmarkProgress,
    benchmarkResults,
    scenarioBenchmarkResults,
    startBenchmark,
    startScenarioBenchmark,
    stopBenchmark,
    resetBenchmark,
  } = useSimulationSocket();

  const { sendCommand: sendTrainingCommand } = useTrainingSocket();
  const { data: simulations = [] } = useSimulations();
  const simulationId = simulations[0]?.id ?? null;
  const mode = useSimulationStore((s) => s.mode);
  const rl = useSimulationStore((s) => s.currentFrame?.rl);

  // Tabs and Scenario state
  const [activeTab, setActiveTab] = useState("comparison");
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  // Latest scenario run result (for optimistic ScenarioHistory update)
  const latestScenarioRun = scenarioBenchmarkResults
    ? {
        model_episode: scenarioBenchmarkResults.model_episode,
        avg_wait_time: scenarioBenchmarkResults.results?.ai?.avg_wait_time ?? 0,
        total_passed: scenarioBenchmarkResults.results?.ai?.total_passed ?? 0,
        max_queue: scenarioBenchmarkResults.results?.ai?.max_queue ?? 0,
        override_rate: scenarioBenchmarkResults.results?.ai?.override_rate ?? 0,
      }
    : null;

  /** Runs benchmark: uses scenario seed if one is selected, otherwise random */
  const handleRunBenchmark = (durationSeconds: number, modes?: string[]) => {
    startBenchmark(durationSeconds, modes);
  };

  /** Runs the locked-seed AI-only scenario benchmark */
  const handleRunScenarioBenchmark = () => {
    if (!selectedScenario) return;
    // model_id and model_episode come from the currently loaded model
    // (app.state.active_model_id / active_model_episode on the server)
    startScenarioBenchmark(
      selectedScenario.id,
      selectedScenario.seed,
      selectedScenario.spawn_lambda,
      selectedScenario.duration_seconds,
      "",  // server falls back to active_model_id
      0,   // server falls back to active_model_episode
    );
  };

  return (
    <div className="relative h-screen bg-[#0a0a0a] text-white flex flex-col overflow-hidden">
      <div className="z-50 relative flex-none">
        <Header />
      </div>

      <div className="flex-1 flex w-full overflow-hidden">
        {/* Left Side: 3D Canvas and Floating UI */}
        <div className="flex-1 relative">
          <LiveSnapshot />

          {/* Active Benchmark Canvas Overlay */}
          {benchmarkRunning && benchmarkProgress && (
            <div className="absolute top-4 left-4 z-40 flex items-center gap-2 pointer-events-none">
              <div className="bg-indigo-950/80 backdrop-blur-md border border-indigo-500/40 rounded-xl px-3.5 py-2 shadow-2xl flex items-center gap-2.5 animate-pulse">
                <span className="h-2 w-2 rounded-full bg-indigo-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-200">
                  {benchmarkProgress.scenario_id ? "Scenario" : "Benchmark"}:{" "}
                  {benchmarkProgress.current_mode?.toUpperCase()}
                </span>
                <span className="text-[11px] font-mono text-indigo-300/80">
                  {benchmarkProgress.elapsed?.toFixed(0)}s / {benchmarkProgress.duration_seconds}s
                </span>
                <span className="text-[10px] bg-indigo-500/30 text-indigo-300 px-1.5 py-0.5 rounded font-semibold">
                  Phase {(benchmarkProgress.mode_index ?? 0) + 1}/{benchmarkProgress.modes_total ?? 3}
                </span>
              </div>
            </div>
          )}

          <SimulationCanvas />
        </div>

        {/* Right Side: Controls Sidebar — order for usage: Act → Understand → Analyze → Observe */}
        <aside className="w-[440px] flex-shrink-0 flex flex-col h-full overflow-y-auto bg-[#0a0a0a] border-l border-neutral-800 scrollbar-thin scrollbar-thumb-neutral-800 scrollbar-track-transparent hover:scrollbar-thumb-neutral-700 shadow-2xl z-10 pointer-events-auto">
          {/* 1. Act — primary controls at top for immediate interaction */}
          <div className="border-b border-neutral-800 bg-transparent flex-none">
            <div className="px-4 pt-4 pb-3">
              <h3 className="text-xs font-medium text-neutral-400">
                Controls
              </h3>
              <p className="text-[10px] text-neutral-600 mt-0.5">Mode, playback, and density</p>
            </div>
            <div className="px-4 pb-4 space-y-5">
              <SimulationControls sendCommand={sendSimulationCommand} />
              <TrainingControls
                sendCommand={sendTrainingCommand}
                simulationId={simulationId}
              />
            </div>
          </div>

          {/* 2. Understand — AI reasoning directly below controls */}
          <div className="border-b border-neutral-800 bg-transparent p-4 flex-none">
            <h3 className="mb-3 text-xs font-medium text-neutral-400 flex items-center justify-between">
              <span>Agent Reasoning</span>
              {mode !== "ai" && <span className="text-[10px] font-normal text-neutral-600">AI mode only</span>}
            </h3>
            <QValuePanel rl={mode === "ai" ? rl : null} />
          </div>

          <div className="bg-transparent flex-none min-h-[300px] overflow-visible pb-10">
            <div className="px-4 pt-6 pb-3">
              <h3 className="text-xs font-medium text-neutral-400">
                Analytics
              </h3>
            </div>
            <div className="px-4 pb-6">
              <Tabs defaultValue="comparison" value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="h-auto gap-1 bg-transparent p-0 flex-wrap">
                  <TabsTrigger
                    value="comparison"
                    className="text-neutral-500 hover:text-neutral-300 data-[state=active]:border-neutral-700 data-[state=active]:bg-neutral-800 data-[state=active]:text-white"
                  >
                    Benchmark
                  </TabsTrigger>
                  <TabsTrigger
                    value="scenarios"
                    className="text-neutral-500 hover:text-neutral-300 data-[state=active]:border-neutral-700 data-[state=active]:bg-neutral-800 data-[state=active]:text-white"
                  >
                    Scenarios
                  </TabsTrigger>
                  <TabsTrigger
                    value="training"
                    className="text-neutral-500 hover:text-neutral-300 data-[state=active]:border-neutral-700 data-[state=active]:bg-neutral-800 data-[state=active]:text-white"
                  >
                    Training
                  </TabsTrigger>
                  <TabsTrigger
                    value="history"
                    className="text-neutral-500 hover:text-neutral-300 data-[state=active]:border-neutral-700 data-[state=active]:bg-neutral-800 data-[state=active]:text-white"
                  >
                    History
                  </TabsTrigger>
                </TabsList>

                {/* Standard benchmark tab */}
                <TabsContent value="comparison" className="mt-4 text-sm text-neutral-400">
                  <SimulationBenchmarkPanel
                    running={benchmarkRunning}
                    progress={benchmarkProgress}
                    results={benchmarkResults}
                    onStart={handleRunBenchmark}
                    onStop={stopBenchmark}
                    onReset={resetBenchmark}
                  />
                </TabsContent>

                {/* Scenario Builder tab */}
                <TabsContent value="scenarios" className="mt-4 text-sm text-white/70 space-y-4">
                  {activeTab === "scenarios" && (
                    <>
                      {/* Scenario Selector inline card */}
                      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
                        <p className="text-[11px] uppercase tracking-widest text-white/30 font-semibold">
                          Reproducible Scenario
                        </p>
                        <ScenarioSelector
                          selected={selectedScenario}
                          onSelect={setSelectedScenario}
                        />

                        {/* Run Scenario Benchmark button */}
                        {selectedScenario && (
                          <div className="pt-2 border-t border-neutral-800 space-y-3">
                            <div>
                              <p className="text-[11px] text-neutral-400 leading-relaxed">
                                Runs <span className="text-white font-medium">Fixed</span>, <span className="text-white font-medium">Greedy</span>, and <span className="text-white font-medium">DQN</span> on identical seeded conditions (CRN) to evaluate policy consistency.
                              </p>
                            </div>

                            <div className="flex gap-2">
                              <button
                                className={`py-2.5 rounded-lg text-white text-xs font-semibold tracking-wide transition-all shadow-lg flex items-center justify-center gap-2 ${
                                  benchmarkRunning
                                    ? "flex-1 bg-violet-600/30 border border-violet-500/40 text-violet-200 cursor-default"
                                    : "w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 shadow-violet-950/40"
                                }`}
                                onClick={handleRunScenarioBenchmark}
                                disabled={benchmarkRunning}
                                type="button"
                              >
                                {benchmarkRunning ? (
                                  <>
                                    <span className="h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
                                    <span>
                                      Evaluating: {benchmarkProgress?.current_mode?.toUpperCase() ?? "CRN BENCHMARK"}… ({((benchmarkProgress?.mode_index ?? 0) + 1)}/3)
                                    </span>
                                  </>
                                ) : (
                                  <>▶ Run 3-Controller Benchmark (Fixed · Greedy · DQN)</>
                                )}
                              </button>

                              {benchmarkRunning && (
                                <button
                                  className="px-4 py-2.5 rounded-lg bg-rose-600/90 hover:bg-rose-600 active:scale-95 text-white text-xs font-semibold tracking-wide transition-all shadow-lg shadow-rose-950/40 flex items-center justify-center gap-1.5 shrink-0 border border-rose-500/40"
                                  onClick={stopBenchmark}
                                  type="button"
                                  title="Stop Scenario Benchmark"
                                >
                                  <span className="h-2 w-2 rounded-sm bg-white" />
                                  <span>Stop</span>
                                </button>
                              )}
                            </div>

                            {/* Benchmark Controller Progress Pills */}
                            {benchmarkRunning && benchmarkProgress && (
                              <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 space-y-2">
                                <div className="flex items-center justify-between text-[10px] text-white/40">
                                  <span>Multi-Controller Execution</span>
                                  <span className="font-mono text-violet-300">Phase {(benchmarkProgress.mode_index ?? 0) + 1} of 3</span>
                                </div>
                                <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
                                  {["fixed", "greedy", "ai"].map((mode) => {
                                    const isDone = benchmarkProgress.modes_done?.includes(mode);
                                    const isCurrent = benchmarkProgress.current_mode === mode;
                                    return (
                                      <div
                                        key={mode}
                                        className={`py-1.5 px-1.5 rounded-lg border transition-all flex flex-col items-center justify-center ${
                                          isDone
                                            ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                                            : isCurrent
                                            ? "bg-violet-500/30 border-violet-500/60 text-white font-bold"
                                            : "bg-white/[0.03] border-white/10 text-white/30"
                                        }`}
                                      >
                                        <span className="text-[10px] tracking-wider">
                                          {isDone ? "✓ " : isCurrent ? "▶ " : ""}{mode.toUpperCase()}
                                        </span>
                                        {/* Active live timer exclusively when benchmark is running */}
                                        {isCurrent && (
                                          <span className="mt-0.5 text-[9px] text-violet-200 font-bold">
                                            {Math.round(benchmarkProgress.elapsed ?? 0)}s / {Math.round(benchmarkProgress.duration_seconds ?? 60)}s
                                          </span>
                                        )}
                                        {isDone && (
                                          <span className="mt-0.5 text-[9px] text-emerald-400/80">
                                            {Math.round(benchmarkProgress.duration_seconds ?? 60)}s done
                                          </span>
                                        )}
                                        {!isCurrent && !isDone && (
                                          <span className="mt-0.5 text-[9px] text-white/20">
                                            queued
                                          </span>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                                {/* Active controller mini progress bar */}
                                <div className="space-y-1 pt-1">
                                  <div className="flex justify-between text-[9px] text-white/50 font-mono">
                                    <span className="capitalize">{benchmarkProgress.current_mode} controller active</span>
                                    <span>
                                      {Math.max(
                                        0,
                                        Math.round(
                                          (benchmarkProgress.duration_seconds ?? 60) - (benchmarkProgress.elapsed ?? 0)
                                        )
                                      )}s remaining
                                    </span>
                                  </div>
                                  <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-violet-500 via-indigo-400 to-emerald-400 transition-all duration-300 rounded-full"
                                      style={{
                                        width: `${Math.min(
                                          100,
                                          Math.round(
                                            ((benchmarkProgress.elapsed ?? 0) /
                                              Math.max(1, benchmarkProgress.duration_seconds ?? 60)) *
                                              100
                                          )
                                        )}%`,
                                      }}
                                    />
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Show latest 3-controller paired result for this scenario */}
                            {scenarioBenchmarkResults?.scenario_id === selectedScenario.id && (
                              <div className="p-3 rounded-xl border border-violet-500/30 bg-violet-500/[0.06] space-y-2">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="font-semibold text-violet-200">Latest Benchmark Results</span>
                                  <span className="font-mono text-[10px] text-white/40">
                                    ep{scenarioBenchmarkResults.model_episode}
                                  </span>
                                </div>

                                <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
                                  {/* Fixed */}
                                  <div className="p-2 rounded-lg bg-black/40 border border-blue-500/20">
                                    <div className="text-[10px] text-blue-400 font-semibold">Fixed</div>
                                    <div className="text-white font-bold mt-0.5">
                                      {scenarioBenchmarkResults.results?.fixed?.avg_wait_time?.toFixed(1) ?? "—"}s
                                    </div>
                                    <div className="text-[9px] text-white/40 mt-0.5">
                                      {scenarioBenchmarkResults.results?.fixed?.total_passed ?? "—"} veh
                                    </div>
                                  </div>

                                  {/* Greedy */}
                                  <div className="p-2 rounded-lg bg-black/40 border border-emerald-500/20">
                                    <div className="text-[10px] text-emerald-400 font-semibold">Greedy</div>
                                    <div className="text-white font-bold mt-0.5">
                                      {scenarioBenchmarkResults.results?.greedy?.avg_wait_time?.toFixed(1) ?? "—"}s
                                    </div>
                                    <div className="text-[9px] text-white/40 mt-0.5">
                                      {scenarioBenchmarkResults.results?.greedy?.total_passed ?? "—"} veh
                                    </div>
                                  </div>

                                  {/* DQN */}
                                  <div className="p-2 rounded-lg bg-violet-950/40 border border-violet-500/40">
                                    <div className="text-[10px] text-violet-300 font-bold">DQN Policy</div>
                                    <div className="text-violet-200 font-bold mt-0.5">
                                      {scenarioBenchmarkResults.results?.ai?.avg_wait_time?.toFixed(1) ?? "—"}s
                                    </div>
                                    <div className="text-[9px] text-violet-300/60 mt-0.5">
                                      {scenarioBenchmarkResults.results?.ai?.total_passed ?? "—"} veh
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Scenario History — 3-tab Paired Runs + 3-line Learning Curve + Metric Details */}
                      <ScenarioHistory
                        selectedScenario={selectedScenario}
                        latestRunResult={latestScenarioRun}
                        latestBenchmarkResults={scenarioBenchmarkResults}
                      />

                      {/* Cross-Scenario Aggregate Summary */}
                      <ScenarioAggregatePanel refreshTrigger={scenarioBenchmarkResults} />
                    </>
                  )}
                </TabsContent>

                <TabsContent value="training" className="mt-4 text-sm text-white/70">
                  {activeTab === "training" && <TrainingChart simulationId={simulationId} />}
                </TabsContent>
                <TabsContent value="history" className="mt-4 text-sm text-white/70">
                  {activeTab === "history" && <EpisodeHistory simulationId={simulationId} />}
                </TabsContent>
              </Tabs>
            </div>
          </div>

          {/* 4. Observe — live telemetry at last, one-by-one, clear deltas */}
          <div className="border-t border-neutral-800 bg-neutral-900/20 p-4 flex-none">
            <h3 className="mb-3 text-xs font-medium text-neutral-300 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live Telemetry
            </h3>
            <p className="text-[11px] text-neutral-500 mb-3 leading-relaxed">
              Real-time stream — each metric stacked vertically with trend and delta.
            </p>
            <MetricsPanel />
          </div>
        </aside>
      </div>
    </div>
  );
}
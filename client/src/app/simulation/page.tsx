"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import SimulationControls from "@/components/controls/SimulationControls";
import TrainingControls from "@/components/controls/TrainingControls";
import ComparisonChart from "@/components/dashboard/ComparisonChart";
import SimulationBenchmarkPanel from "@/components/dashboard/SimulationBenchmarkPanel";
import EpisodeHistory from "@/components/dashboard/EpisodeHistory";
import LiveSnapshot from "@/components/dashboard/LiveSnapshot";
import MetricsPanel from "@/components/dashboard/MetricsPanel";
import QValuePanel from "@/components/dashboard/QValuePanel";
import TrainingChart from "@/components/dashboard/TrainingChart";
import { ScenarioSelector } from "@/components/simulation/ScenarioSelector";
import { ScenarioHistory } from "@/components/simulation/ScenarioHistory";
import { ScenarioAggregatePanel } from "@/components/simulation/ScenarioAggregatePanel";
import dynamic from "next/dynamic";

const SimulationCanvas = dynamic(
  () => import("@/components/simulation/SimulationCanvas"),
  { ssr: false }
);

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  const rl   = useSimulationStore((s) => s.currentFrame?.rl);

  // Scenario state
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  // Latest scenario run result (for optimistic ScenarioHistory update)
  const latestScenarioRun = scenarioBenchmarkResults
    ? {
        model_episode: scenarioBenchmarkResults.model_episode,
        avg_wait_time: scenarioBenchmarkResults.results?.ai?.avg_wait_time ?? 0,
        total_passed:  scenarioBenchmarkResults.results?.ai?.total_passed ?? 0,
        max_queue:     scenarioBenchmarkResults.results?.ai?.max_queue ?? 0,
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

        {/* Right Side: Controls Sidebar */}
        <aside className="w-[420px] flex-shrink-0 flex flex-col h-full overflow-y-auto bg-black/60 backdrop-blur-xl border-l border-white/10 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent hover:scrollbar-thumb-white/30 shadow-2xl z-10 pointer-events-auto">
          <Card className="rounded-none border-0 border-b border-white/10 bg-transparent flex-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                Controls
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pb-4">
              <SimulationControls sendCommand={sendSimulationCommand} />
              <TrainingControls
                sendCommand={sendTrainingCommand}
                simulationId={simulationId}
              />
            </CardContent>
          </Card>

          <Card className="rounded-none border-0 border-b border-white/10 bg-transparent p-4 flex-none">
            <CardTitle className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">
              Real-time Metrics
            </CardTitle>
            <MetricsPanel />
          </Card>

          {/* Agent Reasoning — only in AI mode */}
          <Card className="rounded-none border-0 border-b border-white/10 bg-transparent p-4 flex-none">
            <CardTitle className="mb-3 text-xs uppercase tracking-[0.14em] text-white/35">
              Agent Reasoning
            </CardTitle>
            <QValuePanel rl={mode === "ai" ? rl : null} />
          </Card>

          <Card className="rounded-none border-0 bg-transparent flex-none min-h-[300px] overflow-visible pb-10">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-white/35">
                Analytics
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 pb-6">
              <Tabs defaultValue="comparison" className="w-full">
                <TabsList className="h-auto gap-1 bg-transparent p-0 flex-wrap">
                  <TabsTrigger
                    value="comparison"
                    className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                  >
                    Benchmark
                  </TabsTrigger>
                  <TabsTrigger
                    value="scenarios"
                    className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                  >
                    Scenarios
                  </TabsTrigger>
                  <TabsTrigger
                    value="training"
                    className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                  >
                    Training
                  </TabsTrigger>
                  <TabsTrigger
                    value="history"
                    className="text-white/40 hover:text-white/70 data-[state=active]:border-white/20 data-[state=active]:bg-white/10 data-[state=active]:text-white"
                  >
                    History
                  </TabsTrigger>
                </TabsList>

                {/* Standard benchmark tab */}
                <TabsContent value="comparison" className="mt-4 text-sm text-white/70">
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
                      <div className="pt-2 border-t border-white/10 space-y-3">
                        <div>
                          <p className="text-[11px] text-white/50 leading-relaxed">
                            Runs <span className="text-blue-400 font-medium">Fixed</span>, <span className="text-emerald-400 font-medium">Greedy</span>, and <span className="text-violet-400 font-medium">DQN</span> on identical seeded conditions (CRN) to evaluate policy consistency.
                          </p>
                        </div>

                        <button
                          className="w-full py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold tracking-wide transition-all shadow-lg shadow-violet-950/40 flex items-center justify-center gap-2"
                          onClick={handleRunScenarioBenchmark}
                          disabled={benchmarkRunning}
                          type="button"
                        >
                          {benchmarkRunning ? (
                            <>
                              <span className="h-2 w-2 rounded-full bg-white animate-pulse" />
                              <span>
                                Evaluating: {benchmarkProgress?.current_mode?.toUpperCase() ?? "CRN BENCHMARK"}… ({((benchmarkProgress?.mode_index ?? 0) + 1)}/3)
                              </span>
                            </>
                          ) : (
                            <>▶ Run 3-Controller Benchmark (Fixed · Greedy · DQN)</>
                          )}
                        </button>

                        {/* Benchmark Controller Progress Pills */}
                        {benchmarkRunning && benchmarkProgress && (
                          <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 space-y-2">
                            <div className="flex items-center justify-between text-[10px] text-white/40">
                              <span>Multi-Controller Execution</span>
                              <span className="font-mono text-violet-300">Phase {(benchmarkProgress.mode_index ?? 0) + 1} of 3</span>
                            </div>
                            <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] font-mono">
                              {["fixed", "greedy", "ai"].map((mode) => {
                                const isDone = benchmarkProgress.modes_done?.includes(mode);
                                const isCurrent = benchmarkProgress.current_mode === mode;
                                return (
                                  <div
                                    key={mode}
                                    className={`py-1 px-1.5 rounded border transition-all ${
                                      isDone
                                        ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300 font-medium"
                                        : isCurrent
                                        ? "bg-violet-500/30 border-violet-500/60 text-white font-bold animate-pulse"
                                        : "bg-white/[0.03] border-white/10 text-white/30"
                                    }`}
                                  >
                                    {isDone ? "✓ " : isCurrent ? "▶ " : ""}{mode.toUpperCase()}
                                  </div>
                                );
                              })}
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
                </TabsContent>

                <TabsContent value="training" className="mt-4 text-sm text-white/70">
                  <TrainingChart simulationId={simulationId} />
                </TabsContent>
                <TabsContent value="history" className="mt-4 text-sm text-white/70">
                  <EpisodeHistory simulationId={simulationId} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}


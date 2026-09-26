"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Trophy,
  History,
  RotateCw,
  Cpu,
  Clock,
  Zap,
  Bot,
  Sparkles,
  Search,
  Filter,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import EpisodeHistory from "@/components/dashboard/EpisodeHistory";

export interface BenchmarkModeStats {
  avg_wait_s?: number;
  avg_wait_time?: number;
  throughput?: number;
  total_passed?: number;
  peak_queue?: number;
  max_queue?: number;
  duration_seconds?: number;
}

export interface BenchmarkRecord {
  benchmark_id: string;
  session_id?: string;
  created_at: string;
  timestamp_ms: number;
  duration_seconds: number;
  scenario_id?: string | null;
  winner?: string;
  improvements?: {
    ai_wait_pct?: number;
    greedy_wait_pct?: number;
  };
  modes?: string[];
  modes_results?: {
    ai?: BenchmarkModeStats;
    fixed?: BenchmarkModeStats;
    greedy?: BenchmarkModeStats;
    [key: string]: BenchmarkModeStats | undefined;
  };
  model_name?: string | null;
  model_episodes?: number | null;
  is_finetuned?: boolean;
  finetune_scenario?: string | null;
}

interface SimulationHistoryTabProps {
  simulationId: string | null;
  onSwitchToBenchmark?: () => void;
  latestBenchmarkResults?: any;
}

function formatRelativeTime(createdAt?: string, timestampMs?: number): string {
  const ts =
    timestampMs ||
    (createdAt ? new Date(createdAt.replace(" ", "T")).getTime() : Date.now());
  const diffSec = Math.floor((Date.now() - ts) / 1000);
  if (diffSec < 45) return "Just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}d ago`;
}

function formatTimestampDisplay(
  createdAt?: string,
  timestampMs?: number
): string {
  try {
    const d = timestampMs
      ? new Date(timestampMs)
      : new Date((createdAt || "").replace(" ", "T"));
    if (isNaN(d.getTime())) return createdAt || "Recent run";
    return d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      month: "short",
      day: "numeric",
    });
  } catch {
    return createdAt || "Recent run";
  }
}

function getLos(wait: number): { label: string; className: string } {
  if (wait <= 10)
    return {
      label: "LOS A",
      className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    };
  if (wait <= 20)
    return {
      label: "LOS B",
      className: "bg-teal-500/10 text-teal-400 border-teal-500/20",
    };
  if (wait <= 35)
    return {
      label: "LOS C",
      className: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    };
  if (wait <= 55)
    return {
      label: "LOS D",
      className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    };
  if (wait <= 80)
    return {
      label: "LOS E",
      className: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    };
  return {
    label: "LOS F",
    className: "bg-rose-500/15 text-rose-300 border-rose-500/25",
  };
}

export default function SimulationHistoryTab({
  simulationId,
  onSwitchToBenchmark,
  latestBenchmarkResults,
}: SimulationHistoryTabProps) {
  const [subTab, setSubTab] = useState<"benchmarks" | "episodes">("benchmarks");
  const [benchmarks, setBenchmarks] = useState<BenchmarkRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [modelFilter, setModelFilter] = useState("ALL");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const fetchBenchmarks = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch(`${API_BASE}/analytics/benchmarks`);
      if (res.ok) {
        const json = await res.json();
        const list = (json.benchmarks || []) as BenchmarkRecord[];
        setBenchmarks(list);
      }
    } catch (e) {
      console.warn("Failed to load benchmarks:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchBenchmarks();
  }, [fetchBenchmarks]);

  // If a new benchmark just finished in the parent, refresh to capture it
  useEffect(() => {
    if (latestBenchmarkResults) {
      fetchBenchmarks();
    }
  }, [latestBenchmarkResults, fetchBenchmarks]);

  // Unique model episode checkpoints found across runs
  const uniqueModelEpisodes = useMemo(() => {
    const eps = new Set<number>();
    benchmarks.forEach((b) => {
      if (b.model_episodes) eps.add(b.model_episodes);
    });
    return Array.from(eps).sort((a, b) => b - a);
  }, [benchmarks]);

  const filteredBenchmarks = useMemo(() => {
    return benchmarks.filter((b) => {
      const term = searchTerm.toLowerCase().trim();
      const scenarioText = (b.scenario_id || "standard").toLowerCase();
      const idText = b.benchmark_id.toLowerCase();
      const matchesSearch =
        !term || scenarioText.includes(term) || idText.includes(term);

      const matchesModel =
        modelFilter === "ALL" ||
        String(b.model_episodes ?? 1000) === modelFilter;

      return matchesSearch && matchesModel;
    });
  }, [benchmarks, searchTerm, modelFilter]);

  return (
    <div className="space-y-4 font-sans">
      {/* Sub-tab Navigation Bar & Quick Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] pb-3.5">
        <div className="flex items-center gap-1.5 rounded-lg bg-neutral-900 border border-neutral-800 p-1">
          <button
            onClick={() => setSubTab("benchmarks")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              subTab === "benchmarks"
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/20"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Trophy className="h-3.5 w-3.5 text-amber-400" />
            <span>Benchmark Runs</span>
            {benchmarks.length > 0 && (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                  subTab === "benchmarks"
                    ? "bg-indigo-700/80 text-white"
                    : "bg-neutral-800 text-neutral-400"
                }`}
              >
                {benchmarks.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setSubTab("episodes")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              subTab === "episodes"
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/20"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <History className="h-3.5 w-3.5 text-indigo-400" />
            <span>Training Episodes</span>
          </button>
        </div>

        {subTab === "benchmarks" && (
          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-neutral-500" />
              <input
                type="text"
                placeholder="Filter runs"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-7 w-32 sm:w-44 rounded-md bg-neutral-900 border border-neutral-800 pl-8 pr-2.5 text-xs text-white placeholder:text-neutral-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Model Episode Filter */}
            {uniqueModelEpisodes.length > 0 && (
              <select
                value={modelFilter}
                onChange={(e) => setModelFilter(e.target.value)}
                className="h-7 rounded-md bg-neutral-900 border border-neutral-800 px-2.5 text-xs text-neutral-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Models</option>
                {uniqueModelEpisodes.map((ep) => (
                  <option key={ep} value={String(ep)}>
                    {ep} eps
                  </option>
                ))}
              </select>
            )}

            {/* Refresh Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchBenchmarks}
              disabled={refreshing}
              className="h-7 text-xs text-neutral-400 hover:text-white border border-neutral-800 bg-neutral-900/60 hover:bg-neutral-800 px-2.5"
            >
              <RotateCw
                className={`h-3 w-3 mr-1.5 ${
                  refreshing ? "animate-spin text-indigo-400" : ""
                }`}
              />
              Refresh
            </Button>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {subTab === "episodes" ? (
        <EpisodeHistory simulationId={simulationId} />
      ) : (
        <div className="space-y-4">
          {loading ? (
            <div className="flex h-44 items-center justify-center text-xs text-neutral-500 gap-2">
              <RotateCw className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Loading benchmark history…</span>
            </div>
          ) : filteredBenchmarks.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30 p-8 text-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-800 text-neutral-400">
                <Trophy className="h-5 w-5 text-neutral-500" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-medium text-white">
                  No Benchmark Simulations Found
                </h4>
                <p className="text-xs text-neutral-500 max-w-md">
                  {searchTerm || modelFilter !== "ALL"
                    ? "No benchmark runs match the current search or model filter."
                    : "Run a 3-controller benchmark (FlowSync DQN AI, Fixed Timer, Greedy) to test and compare real-time traffic performance."}
                </p>
              </div>
              {onSwitchToBenchmark && !searchTerm && modelFilter === "ALL" && (
                <Button
                  size="sm"
                  onClick={onSwitchToBenchmark}
                  className="mt-2 h-8 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 shadow-md shadow-indigo-600/20"
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5 text-amber-300" />
                  Run Benchmark Now
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredBenchmarks.map((bm, index) => {
                const ai = bm.modes_results?.ai;
                const fixed = bm.modes_results?.fixed;
                const greedy = bm.modes_results?.greedy;

                const aiWait = ai?.avg_wait_s ?? ai?.avg_wait_time ?? 0;
                const fixedWait = fixed?.avg_wait_s ?? fixed?.avg_wait_time ?? 0;
                const greedyWait =
                  greedy?.avg_wait_s ?? greedy?.avg_wait_time ?? 0;

                const aiThru = ai?.throughput ?? ai?.total_passed ?? 0;
                const fixedThru = fixed?.throughput ?? fixed?.total_passed ?? 0;
                const greedyThru =
                  greedy?.throughput ?? greedy?.total_passed ?? 0;

                const aiQueue = ai?.peak_queue ?? ai?.max_queue ?? 0;
                const fixedQueue = fixed?.peak_queue ?? fixed?.max_queue ?? 0;
                const greedyQueue =
                  greedy?.peak_queue ?? greedy?.max_queue ?? 0;

                const winner = bm.winner || "ai";
                const isAIWinner = winner === "ai";
                const isGreedyWinner = winner === "greedy";
                const isFixedWinner = winner === "fixed";

                const aiImprovement =
                  bm.improvements?.ai_wait_pct ??
                  (fixedWait > 0 && aiWait > 0
                    ? Number(
                        (((fixedWait - aiWait) / fixedWait) * 100).toFixed(1)
                      )
                    : 0);

                const greedyImprovement =
                  bm.improvements?.greedy_wait_pct ??
                  (fixedWait > 0 && greedyWait > 0
                    ? Number(
                        (((fixedWait - greedyWait) / fixedWait) * 100).toFixed(1)
                      )
                    : 0);

                const timeDisplay = formatTimestampDisplay(
                  bm.created_at,
                  bm.timestamp_ms
                );
                const relativeTime = formatRelativeTime(
                  bm.created_at,
                  bm.timestamp_ms
                );

                const aiLos = getLos(aiWait);
                const fixedLos = getLos(fixedWait);
                const greedyLos = getLos(greedyWait);

                const modelEps = bm.model_episodes ?? 1000;
                const isBmFinetuned = Boolean(bm.is_finetuned || bm.model_name?.includes("-ft-") || bm.session_id?.includes("-ft-"));
                const bmScenario = bm.finetune_scenario || (bm.model_name?.includes("-ft-") ? bm.model_name.split("-ft-")[1]?.split(/[\s:_\-]/)[0] : null);

                return (
                  <div
                    key={bm.benchmark_id || index}
                    className="rounded-2xl border border-neutral-800 bg-[#0d0d0d] p-5 transition-all hover:border-neutral-700 space-y-4 shadow-xl shadow-black/40"
                  >
                    {/* Run Header with Benchmark Group Metadata */}
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800/80 pb-3.5">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-[10px] text-neutral-400 bg-neutral-800/80 border border-neutral-700 px-2 py-0.5 rounded">
                          RUN #{filteredBenchmarks.length - index}
                        </span>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold text-white">
                              {bm.scenario_id
                                ? `Scenario Benchmark · ${bm.scenario_id.toUpperCase()}`
                                : `Standard 3-Controller Benchmark`}
                            </span>
                            {isBmFinetuned && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/40 px-2.5 py-0.5 text-[10px] font-semibold text-amber-300 shadow-sm shadow-amber-500/10">
                                <Zap className="h-2.5 w-2.5 text-amber-400" />
                                <span>Fine-Tuned Model</span>
                                {bmScenario && (
                                  <span className="text-amber-200/80 font-normal">
                                    · {bmScenario.replace(/_/g, " ")}
                                  </span>
                                )}
                              </span>
                            )}
                            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-0.5 text-[10px] font-mono text-indigo-300">
                              <Bot className="h-3 w-3" />
                              DQN Model: {modelEps} eps
                            </span>
                          </div>
                          <p className="text-[11px] text-neutral-500 mt-0.5">
                            {timeDisplay} · {relativeTime} ·{" "}
                            <span className="font-mono text-neutral-400">
                              {bm.duration_seconds}s per controller (
                              {bm.duration_seconds * 3}s total)
                            </span>
                          </p>
                        </div>
                      </div>

                      {/* Winner Badge Banner */}
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                            isAIWinner
                              ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                              : isGreedyWinner
                              ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30 shadow-sm shadow-emerald-500/10"
                              : "bg-slate-500/15 text-slate-300 border-slate-500/30 shadow-sm"
                          }`}
                        >
                          <Trophy className="h-3.5 w-3.5 text-amber-400" />
                          <span>
                            {isAIWinner
                              ? `FlowSync DQN AI Won (${modelEps} eps)`
                              : isGreedyWinner
                              ? "Greedy Controller Won"
                              : "Fixed Timer Won"}
                          </span>
                          {aiImprovement !== 0 && isAIWinner && (
                            <span className="font-mono text-emerald-400 font-bold ml-0.5">
                              ({aiImprovement > 0 ? "+" : ""}
                              {aiImprovement}% delay reduction)
                            </span>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* 3 Modes Side-by-Side Cards in STRICT Order: 1. DQN AI, 2. Fixed, 3. Greedy */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 pt-0.5">
                      {/* 1. FlowSync DQN AI */}
                      <div
                        className={`rounded-xl p-4 border transition-all space-y-3 ${
                          isAIWinner
                            ? "bg-indigo-950/30 border-indigo-500/50 shadow-md shadow-indigo-500/10"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Cpu className="h-4 w-4 text-indigo-400" />
                            <div>
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs font-semibold text-white block leading-none">
                                  FlowSync DQN AI
                                </span>
                                {isBmFinetuned && (
                                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold uppercase tracking-wider">
                                    Fine-Tuned
                                  </span>
                                )}
                              </div>
                              <span className="text-[10px] text-indigo-300 font-mono mt-0.5 block">
                                {modelEps} eps checkpoint
                              </span>
                            </div>
                          </div>
                          {isAIWinner ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                              <Trophy className="h-2.5 w-2.5" />
                              WINNER
                            </span>
                          ) : (
                            <span className="text-[10px] text-neutral-500 font-mono">
                              DQN Agent
                            </span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Avg Delay
                            </span>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="font-mono font-medium text-white text-base">
                                {aiWait.toFixed(1)}s
                              </span>
                              <span
                                className={`text-[10px] px-1 py-0.2 rounded border font-medium ${aiLos.className}`}
                              >
                                {aiLos.label}
                              </span>
                            </div>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Throughput
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {aiThru}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                vehs
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Peak Queue
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {aiQueue}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                cars
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              vs Fixed Baseline
                            </span>
                            <span
                              className={`font-mono font-semibold text-sm mt-1 ${
                                aiImprovement > 0
                                  ? "text-emerald-400"
                                  : aiImprovement < 0
                                  ? "text-rose-400"
                                  : "text-neutral-400"
                              }`}
                            >
                              {aiImprovement > 0
                                ? `+${aiImprovement}% faster`
                                : `${aiImprovement}%`}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 2. Fixed Timer */}
                      <div
                        className={`rounded-xl p-4 border transition-all space-y-3 ${
                          isFixedWinner
                            ? "bg-slate-900/60 border-slate-500/50 shadow-md"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-slate-400" />
                            <div>
                              <span className="text-xs font-semibold text-white block leading-none">
                                Fixed Timer
                              </span>
                              <span className="text-[10px] text-neutral-400 font-mono mt-0.5 block">
                                Deterministic Cycle
                              </span>
                            </div>
                          </div>
                          {isFixedWinner ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                              <Trophy className="h-2.5 w-2.5" />
                              WINNER
                            </span>
                          ) : (
                            <span className="text-[10px] text-neutral-500 font-mono">
                              Baseline
                            </span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Avg Delay
                            </span>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="font-mono font-medium text-white text-base">
                                {fixedWait.toFixed(1)}s
                              </span>
                              <span
                                className={`text-[10px] px-1 py-0.2 rounded border font-medium ${fixedLos.className}`}
                              >
                                {fixedLos.label}
                              </span>
                            </div>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Throughput
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {fixedThru}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                vehs
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Peak Queue
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {fixedQueue}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                cars
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              vs Fixed Baseline
                            </span>
                            <span className="font-mono font-semibold text-neutral-400 text-sm mt-1">
                              Baseline (0%)
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 3. Greedy Controller */}
                      <div
                        className={`rounded-xl p-4 border transition-all space-y-3 ${
                          isGreedyWinner
                            ? "bg-emerald-950/30 border-emerald-500/50 shadow-md shadow-emerald-500/10"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4 text-emerald-400" />
                            <div>
                              <span className="text-xs font-semibold text-white block leading-none">
                                Greedy Controller
                              </span>
                              <span className="text-[10px] text-emerald-300 font-mono mt-0.5 block">
                                Queue Priority
                              </span>
                            </div>
                          </div>
                          {isGreedyWinner ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                              <Trophy className="h-2.5 w-2.5" />
                              WINNER
                            </span>
                          ) : (
                            <span className="text-[10px] text-neutral-500 font-mono">
                              Actuated
                            </span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Avg Delay
                            </span>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="font-mono font-medium text-white text-base">
                                {greedyWait.toFixed(1)}s
                              </span>
                              <span
                                className={`text-[10px] px-1 py-0.2 rounded border font-medium ${greedyLos.className}`}
                              >
                                {greedyLos.label}
                              </span>
                            </div>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Throughput
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {greedyThru}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                vehs
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              Peak Queue
                            </span>
                            <span className="font-mono font-medium text-white text-base mt-1">
                              {greedyQueue}{" "}
                              <span className="text-[10px] text-neutral-500 font-sans">
                                cars
                              </span>
                            </span>
                          </div>

                          <div className="bg-black/60 rounded-lg p-2.5 border border-white/[0.06] flex flex-col justify-between">
                            <span className="text-[9.5px] uppercase tracking-wider text-neutral-400 font-medium">
                              vs Fixed Baseline
                            </span>
                            <span
                              className={`font-mono font-semibold text-sm mt-1 ${
                                greedyImprovement > 0
                                  ? "text-emerald-400"
                                  : greedyImprovement < 0
                                  ? "text-rose-400"
                                  : "text-neutral-400"
                              }`}
                            >
                              {greedyImprovement > 0
                                ? `+${greedyImprovement}% faster`
                                : `${greedyImprovement}%`}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

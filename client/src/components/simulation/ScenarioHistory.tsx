"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  ChevronDown, ChevronUp, TrendingDown, TableProperties,
  RefreshCw, Trophy, Activity, AlertTriangle, Sparkles,
} from "lucide-react";
import type {
  Scenario,
  ScenarioRun,
  ScenarioRunGroup,
  ScenarioBenchmarkResults,
} from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";

interface ScenarioHistoryProps {
  selectedScenario: Scenario | null;
  latestRunResult?: {
    model_episode: number;
    avg_wait_time: number;
    total_passed: number;
    max_queue: number;
    override_rate: number;
  } | null;
  latestBenchmarkResults?: ScenarioBenchmarkResults | null;
}

type Tab = "paired" | "chart" | "details";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function ScenarioHistory({
  selectedScenario,
  latestRunResult,
  latestBenchmarkResults,
}: ScenarioHistoryProps) {
  const { fetchRuns, fetchGroupedRuns } = useScenarios();
  const [groupedRuns, setGroupedRuns] = useState<ScenarioRunGroup[]>([]);
  const [flatRuns, setFlatRuns]       = useState<ScenarioRun[]>([]);
  const [tab, setTab]                 = useState<Tab>("paired");
  const [expanded, setExpanded]       = useState(true);
  const [loading, setLoading]         = useState(false);

  const loadData = useCallback(async () => {
    if (!selectedScenario) {
      setGroupedRuns([]);
      setFlatRuns([]);
      return;
    }
    setLoading(true);
    try {
      const [grouped, flat] = await Promise.all([
        fetchGroupedRuns(selectedScenario.id),
        fetchRuns(selectedScenario.id),
      ]);
      setGroupedRuns(grouped);
      setFlatRuns(flat);
    } catch (e) {
      console.error("Failed to load scenario history", e);
    } finally {
      setLoading(false);
    }
  }, [selectedScenario, fetchGroupedRuns, fetchRuns]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle incoming benchmark results
  useEffect(() => {
    if (!selectedScenario) return;

    if (latestBenchmarkResults && latestBenchmarkResults.scenario_id === selectedScenario.id) {
      const bRes = latestBenchmarkResults.results;
      const optimisticGroup: ScenarioRunGroup = {
        run_group_id: latestBenchmarkResults.run_group_id || `optimistic-${Date.now()}`,
        ran_at: new Date().toISOString(),
        model_episode: latestBenchmarkResults.model_episode,
        fixed: bRes?.fixed,
        greedy: bRes?.greedy,
        ai: bRes?.ai,
      };

      setGroupedRuns((prev) => {
        const filtered = prev.filter(
          (g) => g.run_group_id !== optimisticGroup.run_group_id &&
                 !(g.model_episode === optimisticGroup.model_episode && Math.abs((g.ai?.avg_wait_time ?? 0) - (optimisticGroup.ai?.avg_wait_time ?? 0)) < 0.01)
        );
        return [...filtered, optimisticGroup].sort((a, b) => a.model_episode - b.model_episode);
      });

      const timer = setTimeout(() => loadData(), 2000);
      return () => clearTimeout(timer);
    } else if (latestRunResult) {
      // Legacy fallback
      const timer = setTimeout(() => loadData(), 2000);
      return () => clearTimeout(timer);
    }
  }, [latestBenchmarkResults, latestRunResult, selectedScenario, loadData]);

  const sortedGroups = useMemo(() => {
    return [...groupedRuns].sort((a, b) => a.model_episode - b.model_episode);
  }, [groupedRuns]);

  // Chart data formatting: Fixed, Greedy, DQN across episodes
  const chartData = useMemo(() => {
    return sortedGroups.map((g) => ({
      episode: g.model_episode,
      dqn: g.ai ? Number(g.ai.avg_wait_time.toFixed(2)) : undefined,
      greedy: g.greedy ? Number(g.greedy.avg_wait_time.toFixed(2)) : undefined,
      fixed: g.fixed ? Number(g.fixed.avg_wait_time.toFixed(2)) : undefined,
      dqn_starvation: g.ai?.starvation_count ?? 0,
      greedy_starvation: g.greedy?.starvation_count ?? 0,
      fixed_starvation: g.fixed?.starvation_count ?? 0,
    }));
  }, [sortedGroups]);

  // Total counts & win rate for this scenario
  const stats = useMemo(() => {
    let dqnWins = 0;
    let total = 0;
    for (const g of sortedGroups) {
      if (g.ai && g.greedy) {
        total++;
        if (g.ai.avg_wait_time < g.greedy.avg_wait_time) {
          dqnWins++;
        }
      }
    }
    return {
      totalGroups: sortedGroups.length,
      dqnWins,
      winRate: total > 0 ? (dqnWins / total) * 100 : 0,
    };
  }, [sortedGroups]);

  if (!selectedScenario) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden shadow-xl backdrop-blur-sm">
      {/* ── Collapsible header ─────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-widest text-violet-400 font-semibold">
            📊 Scenario Multi-Run Evaluation
          </span>
          {stats.totalGroups > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-violet-500/20 text-violet-300 border border-violet-500/30">
              DQN Win Rate: {stats.winRate.toFixed(0)}% ({stats.dqnWins}/{stats.totalGroups})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-white/40 font-mono shrink-0">
            {sortedGroups.length} execution{sortedGroups.length !== 1 ? "s" : ""}
          </span>
          <div
            role="button"
            tabIndex={0}
            onClick={(e) => { e.stopPropagation(); loadData(); }}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); loadData(); } }}
            className="p-1 rounded text-white/30 hover:text-white/70 transition-colors cursor-pointer"
            title="Refresh History"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </div>
          {expanded ? <ChevronUp size={14} className="text-white/40" /> : <ChevronDown size={14} className="text-white/40" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Scenario info bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-white/40 font-mono px-1 py-1 border-b border-white/[0.05]">
            <div className="flex items-center gap-2">
              <span className="text-white/80 font-medium">{selectedScenario.name}</span>
              <span>·</span>
              <span>seed: {selectedScenario.seed}</span>
              <span>·</span>
              <span>λ={selectedScenario.spawn_lambda.toFixed(1)} veh/s</span>
              <span>·</span>
              <span>{selectedScenario.duration_seconds}s</span>
            </div>
            {selectedScenario.is_held_out && (
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30">
                🔒 Held-Out Scenario
              </span>
            )}
          </div>

          {/* 3 Tabs */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-white/[0.04] border border-white/[0.07]">
            <button
              type="button"
              onClick={() => setTab("paired")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "paired"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-white/40 hover:text-white/60"
              }`}
            >
              <TableProperties size={12} /> Paired Runs (3-Controller)
            </button>
            <button
              type="button"
              onClick={() => setTab("chart")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "chart"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-white/40 hover:text-white/60"
              }`}
            >
              <TrendingDown size={12} /> Learning Curve (3 Lines)
            </button>
            <button
              type="button"
              onClick={() => setTab("details")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "details"
                  ? "bg-white/10 text-white shadow-sm"
                  : "text-white/40 hover:text-white/60"
              }`}
            >
              <Activity size={12} /> Metric Details
            </button>
          </div>

          {/* Empty state */}
          {!loading && sortedGroups.length === 0 && (
            <div className="text-center py-8 px-4 rounded-xl border border-dashed border-white/10 bg-white/[0.01]">
              <Sparkles className="mx-auto text-violet-400/50 mb-2" size={24} />
              <p className="text-sm font-medium text-white/70">No evaluation runs yet</p>
              <p className="text-xs text-white/40 max-w-sm mx-auto mt-1 leading-relaxed">
                Click <span className="text-violet-300 font-semibold">▶ Run Scenario Benchmark</span> above to execute Fixed, Greedy, and DQN under identical CRN conditions.
              </p>
            </div>
          )}

          {loading && sortedGroups.length === 0 && (
            <div className="text-center py-6 text-xs text-white/40 animate-pulse">
              Loading benchmark history…
            </div>
          )}

          {/* ── TAB 1: PAIRED RUNS ──────────────────────────────────────── */}
          {tab === "paired" && sortedGroups.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-white/[0.07]">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-white/[0.07] bg-white/[0.03]">
                    <th className="text-left px-3 py-2 text-white/40 font-medium">Checkpoint</th>
                    <th className="text-right px-3 py-2 text-blue-400/80 font-medium">Fixed</th>
                    <th className="text-right px-3 py-2 text-emerald-400/80 font-medium">Greedy</th>
                    <th className="text-right px-3 py-2 text-violet-400 font-medium">DQN Policy</th>
                    <th className="text-center px-3 py-2 text-white/40 font-medium">Winner</th>
                    <th className="text-right px-3 py-2 text-white/40 font-medium">Starvation (F / G / DQN)</th>
                    <th className="text-right px-3 py-2 text-white/30 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {sortedGroups.map((group) => {
                    const fWait = group.fixed?.avg_wait_time;
                    const gWait = group.greedy?.avg_wait_time;
                    const dWait = group.ai?.avg_wait_time;

                    // Determine winner
                    const candidates: { name: string; wait: number }[] = [];
                    if (fWait !== undefined) candidates.push({ name: "Fixed", wait: fWait });
                    if (gWait !== undefined) candidates.push({ name: "Greedy", wait: gWait });
                    if (dWait !== undefined) candidates.push({ name: "DQN", wait: dWait });

                    candidates.sort((a, b) => a.wait - b.wait);
                    const winner = candidates[0]?.name;
                    const isDqnWinner = winner === "DQN";

                    // Delta DQN vs Greedy
                    const deltaGreedy = (dWait !== undefined && gWait !== undefined)
                      ? dWait - gWait
                      : null;

                    return (
                      <tr
                        key={group.run_group_id}
                        className={`hover:bg-white/[0.02] transition-colors ${
                          isDqnWinner ? "bg-violet-500/[0.05]" : ""
                        }`}
                      >
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-mono text-[10px] font-medium border border-violet-500/30">
                            ep{group.model_episode}
                          </span>
                        </td>

                        {/* Fixed */}
                        <td className="px-3 py-2 text-right font-mono text-white/60">
                          {fWait !== undefined ? `${fWait.toFixed(2)}s` : "—"}
                        </td>

                        {/* Greedy */}
                        <td className="px-3 py-2 text-right font-mono text-white/80">
                          {gWait !== undefined ? `${gWait.toFixed(2)}s` : "—"}
                        </td>

                        {/* DQN with Delta */}
                        <td className="px-3 py-2 text-right font-mono">
                          {dWait !== undefined ? (
                            <div className="inline-flex flex-col items-end">
                              <span className={`font-semibold ${
                                isDqnWinner ? "text-emerald-400" : "text-violet-300"
                              }`}>
                                {dWait.toFixed(2)}s
                              </span>
                              {deltaGreedy !== null && (
                                <span className={`text-[9px] ${
                                  deltaGreedy <= 0 ? "text-emerald-400" : "text-rose-400/80"
                                }`}>
                                  {deltaGreedy <= 0 ? "▼" : "▲"} {Math.abs(deltaGreedy).toFixed(2)}s vs Grd
                                </span>
                              )}
                            </div>
                          ) : "—"}
                        </td>

                        {/* Winner */}
                        <td className="px-3 py-2 text-center">
                          {winner ? (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              isDqnWinner
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : winner === "Greedy"
                                ? "bg-emerald-500/10 text-emerald-300/80"
                                : "bg-blue-500/10 text-blue-300/80"
                            }`}>
                              {isDqnWinner && <Trophy size={10} className="text-amber-400" />}
                              {winner}
                            </span>
                          ) : "—"}
                        </td>

                        {/* Starvation */}
                        <td className="px-3 py-2 text-right font-mono text-[10px] text-white/50">
                          <span className="text-blue-300">{group.fixed?.starvation_count ?? 0}</span>
                          <span className="mx-1 text-white/20">/</span>
                          <span className="text-emerald-300">{group.greedy?.starvation_count ?? 0}</span>
                          <span className="mx-1 text-white/20">/</span>
                          <span className={
                            (group.ai?.starvation_count ?? 0) === 0 ? "text-emerald-400 font-semibold" : "text-amber-300"
                          }>
                            {group.ai?.starvation_count ?? 0}
                          </span>
                        </td>

                        {/* Date */}
                        <td className="px-3 py-2 text-right text-white/30 text-[10px]">
                          {formatDate(group.ran_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── TAB 2: 3-LINE LEARNING CURVE CHART ───────────────────────── */}
          {tab === "chart" && sortedGroups.length > 0 && (
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between text-[11px] text-white/40 px-1">
                <span>Checkpoint Progression: Fixed vs. Greedy vs. DQN</span>
                <span className="text-emerald-400 font-medium">Lower wait time = Superior Controller</span>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-black/20 p-2">
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={chartData} margin={{ top: 12, right: 16, left: -6, bottom: 6 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="episode"
                      stroke="rgba(255,255,255,0.2)"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
                      tickLine={false}
                      label={{ value: "Episode Checkpoint", position: "insideBottom", offset: -4, fontSize: 10, fill: "rgba(255,255,255,0.3)" }}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.2)"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
                      tickLine={false}
                      domain={["auto", "auto"]}
                      width={38}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(12,12,20,0.96)",
                        border: "1px solid rgba(139,92,246,0.3)",
                        borderRadius: 10,
                        fontSize: 11,
                        padding: "8px 12px",
                      }}
                      labelFormatter={(ep) => `Checkpoint Episode ${ep}`}
                      formatter={(v: unknown, name: unknown) => [
                        `${Number(v).toFixed(2)}s`,
                        name === "dqn" ? "DQN AI" : name === "greedy" ? "Greedy" : "Fixed",
                      ]}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11, paddingTop: 4 }}
                      iconType="circle"
                      iconSize={8}
                    />

                    {/* Fixed Baseline */}
                    <Line
                      type="monotone"
                      dataKey="fixed"
                      name="Fixed Time"
                      stroke="#3b82f6"
                      strokeWidth={1.5}
                      strokeDasharray="4 3"
                      dot={{ r: 3, fill: "#3b82f6" }}
                    />

                    {/* Greedy Baseline */}
                    <Line
                      type="monotone"
                      dataKey="greedy"
                      name="Greedy"
                      stroke="#10b981"
                      strokeWidth={1.5}
                      strokeDasharray="3 2"
                      dot={{ r: 3, fill: "#10b981" }}
                    />

                    {/* DQN Learning Curve */}
                    <Line
                      type="monotone"
                      dataKey="dqn"
                      name="DQN Agent"
                      stroke="#a855f7"
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: "#c084fc", strokeWidth: 0 }}
                      activeDot={{ r: 6, fill: "#e879f9" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ── TAB 3: METRIC DETAILS DRILL-DOWN ────────────────────────── */}
          {tab === "details" && sortedGroups.length > 0 && (
            <div className="space-y-3">
              {sortedGroups.map((g) => (
                <div
                  key={g.run_group_id}
                  className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3 space-y-2.5"
                >
                  <div className="flex items-center justify-between text-xs border-b border-white/[0.05] pb-2">
                    <span className="font-semibold text-violet-300 font-mono flex items-center gap-1.5">
                      Episode {g.model_episode} Paired Metrics
                    </span>
                    <span className="text-[10px] text-white/30 font-mono">
                      {formatDate(g.ran_at)}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    {/* Fixed Card */}
                    <div className="rounded-lg bg-blue-500/[0.04] border border-blue-500/20 p-2 space-y-1">
                      <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider block">
                        Fixed Timing
                      </span>
                      <div className="space-y-0.5 text-[11px] font-mono">
                        <div className="flex justify-between text-white/60">
                          <span>Avg Wait:</span>
                          <span className="text-white">{g.fixed ? `${g.fixed.avg_wait_time.toFixed(2)}s` : "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>P95 Delay:</span>
                          <span>{g.fixed?.p95_delay ? `${g.fixed.p95_delay.toFixed(1)}s` : "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Throughput:</span>
                          <span>{g.fixed?.total_passed ?? "—"} veh</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Max Queue:</span>
                          <span>{g.fixed?.max_queue ?? "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Starvations:</span>
                          <span className={g.fixed?.starvation_count ? "text-amber-400 font-bold" : "text-emerald-400"}>
                            {g.fixed?.starvation_count ?? 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Greedy Card */}
                    <div className="rounded-lg bg-emerald-500/[0.04] border border-emerald-500/20 p-2 space-y-1">
                      <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider block">
                        Greedy (Actuated)
                      </span>
                      <div className="space-y-0.5 text-[11px] font-mono">
                        <div className="flex justify-between text-white/60">
                          <span>Avg Wait:</span>
                          <span className="text-white">{g.greedy ? `${g.greedy.avg_wait_time.toFixed(2)}s` : "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>P95 Delay:</span>
                          <span>{g.greedy?.p95_delay ? `${g.greedy.p95_delay.toFixed(1)}s` : "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Throughput:</span>
                          <span>{g.greedy?.total_passed ?? "—"} veh</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Max Queue:</span>
                          <span>{g.greedy?.max_queue ?? "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Starvations:</span>
                          <span className={g.greedy?.starvation_count ? "text-amber-400 font-bold" : "text-emerald-400"}>
                            {g.greedy?.starvation_count ?? 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* DQN Card */}
                    <div className="rounded-lg bg-violet-500/[0.06] border border-violet-500/30 p-2 space-y-1">
                      <span className="text-[10px] font-semibold text-violet-300 uppercase tracking-wider block flex items-center justify-between">
                        <span>DQN Reinforcement</span>
                        {g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time && (
                          <span className="text-[9px] text-amber-300 font-bold flex items-center gap-0.5">
                            <Trophy size={9} /> WIN
                          </span>
                        )}
                      </span>
                      <div className="space-y-0.5 text-[11px] font-mono">
                        <div className="flex justify-between text-white/60">
                          <span>Avg Wait:</span>
                          <span className="text-violet-200 font-bold">
                            {g.ai ? `${g.ai.avg_wait_time.toFixed(2)}s` : "—"}
                          </span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>P95 Delay:</span>
                          <span>{g.ai?.p95_delay ? `${g.ai.p95_delay.toFixed(1)}s` : "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Throughput:</span>
                          <span>{g.ai?.total_passed ?? "—"} veh</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Max Queue:</span>
                          <span>{g.ai?.max_queue ?? "—"}</span>
                        </div>
                        <div className="flex justify-between text-white/50">
                          <span>Starvations:</span>
                          <span className={g.ai?.starvation_count ? "text-amber-400 font-bold" : "text-emerald-400"}>
                            {g.ai?.starvation_count ?? 0}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

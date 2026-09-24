"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  ChevronDown, ChevronUp, TrendingDown, TableProperties,
  RefreshCw, Trophy, Activity,
} from "lucide-react";
import type {
  Scenario,
  ScenarioRun,
  ScenarioRunGroup,
  ScenarioBenchmarkResults,
} from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";
import { Button } from "@/components/ui/button";

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

  useEffect(() => {
    if (!selectedScenario) return;

    if (latestBenchmarkResults && latestBenchmarkResults.scenario_id === selectedScenario.id) {
      const bRes = latestBenchmarkResults.results;
      const optimisticGroup: ScenarioRunGroup = {
        run_group_id: latestBenchmarkResults.run_group_id || `optimistic-${Date.now()}`,
        ran_at: new Date().toISOString(),
        model_episode: latestBenchmarkResults.model_episode,
        ai: bRes?.ai,
        fixed: bRes?.fixed,
        greedy: bRes?.greedy,
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
      const timer = setTimeout(() => loadData(), 2000);
      return () => clearTimeout(timer);
    }
  }, [latestBenchmarkResults, latestRunResult, selectedScenario, loadData]);

  const sortedGroups = useMemo(() => {
    return [...groupedRuns].sort((a, b) => a.model_episode - b.model_episode);
  }, [groupedRuns]);

  const chartData = useMemo(() => {
    return sortedGroups.map((g, idx) => ({
      runKey: `R${idx + 1}·ep${g.model_episode}`,
      runLabel: `Run #${idx + 1} (ep ${g.model_episode})`,
      episode: g.model_episode,
      dqn: g.ai ? Number(g.ai.avg_wait_time.toFixed(2)) : undefined,
      greedy: g.greedy ? Number(g.greedy.avg_wait_time.toFixed(2)) : undefined,
      fixed: g.fixed ? Number(g.fixed.avg_wait_time.toFixed(2)) : undefined,
      dqn_starvation: g.ai?.starvation_count ?? 0,
      greedy_starvation: g.greedy?.starvation_count ?? 0,
      fixed_starvation: g.fixed?.starvation_count ?? 0,
    }));
  }, [sortedGroups]);

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
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden shadow-sm">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((e) => !e)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setExpanded((prev) => !prev);
        }}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-neutral-800/50 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wider text-neutral-400 font-medium">
            Scenario Multi-Run Evaluation
          </span>
          {stats.totalGroups > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-neutral-800 text-neutral-300 border border-neutral-700">
              DQN Win Rate: {stats.winRate.toFixed(0)}% ({stats.dqnWins}/{stats.totalGroups})
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-neutral-500 font-mono shrink-0">
            {sortedGroups.length} execution{sortedGroups.length !== 1 ? "s" : ""}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-neutral-500 hover:text-white"
            onClick={(e) => { e.stopPropagation(); loadData(); }}
            title="Refresh History"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </Button>
          {expanded ? <ChevronUp size={14} className="text-neutral-500" /> : <ChevronDown size={14} className="text-neutral-500" />}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Scenario info bar — wrap-friendly, truncate long names */}
          <div className="flex flex-col gap-1.5 px-1 py-2 border-b border-neutral-800">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs font-medium text-white truncate flex-1 min-w-0" title={selectedScenario.name}>
                {selectedScenario.name}
              </span>
              {selectedScenario.is_held_out && (
                <span className="shrink-0 inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/20">
                  🔒 Held-Out
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-neutral-500">
              <span className="inline-flex items-center gap-1 rounded-full bg-neutral-900 border border-neutral-800 px-2 py-0.5">
                seed {selectedScenario.seed}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-neutral-900 border border-neutral-800 px-2 py-0.5">
                λ {selectedScenario.spawn_lambda.toFixed(1)} veh/s
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-neutral-900 border border-neutral-800 px-2 py-0.5">
                {selectedScenario.duration_seconds}s
              </span>
            </div>
          </div>

          {/* 3 Tabs */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-neutral-900 border border-neutral-800">
            <button
              type="button"
              onClick={() => setTab("paired")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "paired"
                  ? "bg-neutral-800 text-white shadow-sm"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <TableProperties size={12} /> Paired Runs
            </button>
            <button
              type="button"
              onClick={() => setTab("chart")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "chart"
                  ? "bg-neutral-800 text-white shadow-sm"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <TrendingDown size={12} /> Learning Curve
            </button>
            <button
              type="button"
              onClick={() => setTab("details")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "details"
                  ? "bg-neutral-800 text-white shadow-sm"
                  : "text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <Activity size={12} /> Details
            </button>
          </div>

          {/* Empty state */}
          {!loading && sortedGroups.length === 0 && (
            <div className="text-center py-8 px-4 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30">
              <Activity className="mx-auto text-neutral-700 mb-2" size={24} />
              <p className="text-sm font-medium text-neutral-400">No evaluation runs yet</p>
              <p className="text-xs text-neutral-600 max-w-sm mx-auto mt-1 leading-relaxed">
                Execute a scenario benchmark to evaluate controller performance under identical conditions.
              </p>
            </div>
          )}

          {loading && sortedGroups.length === 0 && (
            <div className="text-center py-6 text-xs text-neutral-500 animate-pulse">
              Loading benchmark history…
            </div>
          )}

          {/* ── TAB 1: PAIRED RUNS ──────────────────────────────────────── */}
          {tab === "paired" && sortedGroups.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-neutral-800">
              <table className="w-full text-[11px]">
                <thead className="bg-neutral-900">
                  <tr className="border-b border-neutral-800">
                    <th className="text-left px-3 py-2 text-neutral-500 font-medium">Checkpoint</th>
                    <th className="text-right px-3 py-2 text-white font-medium">DQN Policy</th>
                    <th className="text-right px-3 py-2 text-neutral-400 font-medium">Fixed</th>
                    <th className="text-right px-3 py-2 text-neutral-400 font-medium">Greedy</th>
                    <th className="text-center px-3 py-2 text-neutral-500 font-medium">Winner</th>
                    <th className="text-right px-3 py-2 text-neutral-500 font-medium">Starvation</th>
                    <th className="text-right px-3 py-2 text-neutral-600 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800">
                  {sortedGroups.map((group) => {
                    const fWait = group.fixed?.avg_wait_time;
                    const gWait = group.greedy?.avg_wait_time;
                    const dWait = group.ai?.avg_wait_time;

                    const candidates: { name: string; wait: number }[] = [];
                    if (fWait !== undefined) candidates.push({ name: "Fixed", wait: fWait });
                    if (gWait !== undefined) candidates.push({ name: "Greedy", wait: gWait });
                    if (dWait !== undefined) candidates.push({ name: "DQN", wait: dWait });

                    candidates.sort((a, b) => a.wait - b.wait);
                    const winner = candidates[0]?.name;
                    const isDqnWinner = winner === "DQN";

                    const deltaGreedy = (dWait !== undefined && gWait !== undefined)
                      ? dWait - gWait
                      : null;

                    return (
                      <tr
                        key={group.run_group_id}
                        className={`hover:bg-neutral-800/30 transition-colors ${
                          isDqnWinner ? "bg-neutral-800/20" : ""
                        }`}
                      >
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 font-mono text-[10px] font-medium border border-neutral-700">
                            ep{group.model_episode}
                          </span>
                        </td>

                        <td className="px-3 py-2 text-right font-mono">
                          {dWait !== undefined ? (
                            <div className="inline-flex flex-col items-end">
                              <span className={`font-semibold ${
                                isDqnWinner ? "text-white" : "text-neutral-300"
                              }`}>
                                {dWait.toFixed(2)}s
                              </span>
                              {deltaGreedy !== null && (
                                <span className={`text-[9px] ${
                                  deltaGreedy <= 0 ? "text-neutral-400" : "text-neutral-500"
                                }`}>
                                  {deltaGreedy <= 0 ? "▼" : "▲"} {Math.abs(deltaGreedy).toFixed(2)}s vs Grd
                                </span>
                              )}
                            </div>
                          ) : "—"}
                        </td>

                        <td className="px-3 py-2 text-right font-mono text-neutral-500">
                          {fWait !== undefined ? `${fWait.toFixed(2)}s` : "—"}
                        </td>

                        <td className="px-3 py-2 text-right font-mono text-neutral-400">
                          {gWait !== undefined ? `${gWait.toFixed(2)}s` : "—"}
                        </td>

                        <td className="px-3 py-2 text-center">
                          {winner ? (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              isDqnWinner
                                ? "bg-neutral-700 text-white border border-neutral-600"
                                : "bg-neutral-800 text-neutral-400 border border-neutral-700"
                            }`}>
                              {isDqnWinner && <Trophy size={10} className="text-neutral-300" />}
                              {winner}
                            </span>
                          ) : "—"}
                        </td>

                        <td className="px-3 py-2 text-right font-mono text-[10px] text-neutral-600">
                          <span className={
                            (group.ai?.starvation_count ?? 0) === 0 ? "text-white font-semibold" : "text-neutral-400"
                          }>
                            {group.ai?.starvation_count ?? 0}
                          </span>
                          <span className="mx-1 text-neutral-800">/</span>
                          <span className="text-neutral-400">{group.fixed?.starvation_count ?? 0}</span>
                          <span className="mx-1 text-neutral-800">/</span>
                          <span className="text-neutral-400">{group.greedy?.starvation_count ?? 0}</span>
                        </td>

                        <td className="px-3 py-2 text-right text-neutral-600 text-[10px]">
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
              <div className="flex items-center justify-between text-[11px] text-neutral-500 px-1">
                <span>Checkpoint Progression: Fixed vs. Greedy vs. DQN</span>
                <span className="text-neutral-400 font-medium">Lower wait time = Superior Controller</span>
              </div>

              <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-2">
                <ResponsiveContainer width="100%" height={230} minWidth={100} minHeight={230}>
                  <LineChart data={chartData} margin={{ top: 12, right: 16, left: -6, bottom: 6 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="runKey"
                      stroke="rgba(255,255,255,0.2)"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.5)" }}
                      tickLine={false}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.2)"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.5)" }}
                      tickLine={false}
                      domain={["auto", "auto"]}
                      width={38}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0d1117",
                        border: "1px solid rgba(255,255,255,0.15)",
                        borderRadius: 10,
                        fontSize: 11,
                        padding: "8px 12px",
                      }}
                      labelFormatter={(_, payload) => {
                        const item = payload?.[0]?.payload;
                        return item?.runLabel ?? "";
                      }}
                      formatter={(v: unknown, name: unknown) => [
                        `${Number(v).toFixed(2)}s`,
                        name === "dqn" ? "DQN AI" : name === "greedy" ? "Greedy" : "Fixed Timer",
                      ]}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11, paddingTop: 4 }}
                      iconType="circle"
                      iconSize={8}
                    />

                    <Line
                      type="monotone"
                      dataKey="dqn"
                      name="DQN Agent"
                      stroke="#c084fc"
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: "#c084fc", strokeWidth: 0 }}
                      activeDot={{ r: 6, fill: "#e879f9" }}
                    />

                    <Line
                      type="monotone"
                      dataKey="fixed"
                      name="Fixed Time"
                      stroke="#60a5fa"
                      strokeWidth={2}
                      strokeDasharray="4 3"
                      dot={{ r: 3, fill: "#60a5fa" }}
                    />

                    <Line
                      type="monotone"
                      dataKey="greedy"
                      name="Greedy"
                      stroke="#34d399"
                      strokeWidth={2}
                      strokeDasharray="3 2"
                      dot={{ r: 3, fill: "#34d399" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ── TAB 3: METRIC DETAILS DRILL-DOWN — stacked cards for readability ─ */}
          {tab === "details" && sortedGroups.length > 0 && (
            <div className="space-y-4">
              {sortedGroups.map((g) => (
                <div
                  key={g.run_group_id}
                  className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-3.5 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-neutral-800 pb-2.5">
                    <span className="text-xs font-medium text-white flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white text-black text-[10px] font-bold">
                        {g.model_episode}
                      </span>
                      Episode {g.model_episode} · Paired Metrics
                    </span>
                    <span className="text-xs text-neutral-500 font-mono">
                      {formatDate(g.ran_at)}
                    </span>
                  </div>

                  <div className="flex flex-col gap-2.5">
                    {/* DQN */}
                    <div className={`rounded-lg border p-3 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "border-white bg-white text-black" : "border-neutral-800 bg-neutral-900 text-white"}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`text-xs font-medium flex items-center gap-1.5 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black" : "text-white"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "bg-black" : "bg-white"}`} /> DQN Reinforcement
                        </span>
                        {g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-bold bg-black text-white">
                            <Trophy size={10} /> WIN
                          </span>
                        ) : (
                          <span className={`text-xs font-mono ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/70" : "text-neutral-500"}`}>
                            {g.ai ? `${g.ai.avg_wait_time.toFixed(1)}s avg` : "—"}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className={`rounded-md border p-2 text-center ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "bg-black/5 border-black/10" : "bg-[#0a0a0a] border-neutral-800"}`}>
                          <div className={`text-[10px] ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/60" : "text-neutral-500"}`}>Avg Wait</div>
                          <div className={`text-xs font-mono font-bold mt-0.5 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black" : "text-white"}`}>
                            {g.ai ? `${g.ai.avg_wait_time.toFixed(2)}s` : "—"}
                          </div>
                        </div>
                        <div className={`rounded-md border p-2 text-center ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "bg-black/5 border-black/10" : "bg-[#0a0a0a] border-neutral-800"}`}>
                          <div className={`text-[10px] ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/60" : "text-neutral-500"}`}>Throughput</div>
                          <div className={`text-xs font-mono font-bold mt-0.5 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black" : "text-white"}`}>
                            {g.ai?.total_passed ?? "—"}
                          </div>
                          <div className={`text-[10px] ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/50" : "text-neutral-600"}`}>veh</div>
                        </div>
                        <div className={`rounded-md border p-2 text-center ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "bg-black/5 border-black/10" : "bg-[#0a0a0a] border-neutral-800"}`}>
                          <div className={`text-[10px] ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/60" : "text-neutral-500"}`}>P95 Delay</div>
                          <div className={`text-xs font-mono mt-0.5 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black" : "text-neutral-400"}`}>
                            {g.ai?.p95_delay ? `${g.ai.p95_delay.toFixed(1)}s` : "—"}
                          </div>
                        </div>
                      </div>
                      <div className={`mt-2 flex items-center justify-between text-xs border-t pt-2 ${g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black/60 border-black/10" : "text-neutral-600 border-neutral-800"}`}>
                        <span>Max Queue {g.ai?.max_queue ?? "—"} · Starvations {g.ai?.starvation_count ?? 0}</span>
                        {g.ai?.starvation_count === 0 ? (
                          <span className={g.ai && g.greedy && g.ai.avg_wait_time < g.greedy.avg_wait_time ? "text-black font-medium" : "text-emerald-400 font-medium"}>✓ No starvation</span>
                        ) : null}
                      </div>
                    </div>

                    {/* Fixed */}
                    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-neutral-300 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" /> Fixed Timing
                        </span>
                        <span className="text-xs font-mono text-neutral-500">
                          {g.fixed ? `${g.fixed.avg_wait_time.toFixed(1)}s avg` : "—"}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">Avg Wait</div>
                          <div className="text-xs font-mono font-medium text-white mt-0.5">
                            {g.fixed ? `${g.fixed.avg_wait_time.toFixed(2)}s` : "—"}
                          </div>
                        </div>
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">Throughput</div>
                          <div className="text-xs font-mono font-medium text-white mt-0.5">
                            {g.fixed?.total_passed ?? "—"}
                          </div>
                          <div className="text-[10px] text-neutral-600">veh</div>
                        </div>
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">P95 Delay</div>
                          <div className="text-xs font-mono text-neutral-400 mt-0.5">
                            {g.fixed?.p95_delay ? `${g.fixed.p95_delay.toFixed(1)}s` : "—"}
                          </div>
                        </div>
                      </div>
                      <div className="mt-2 flex items-center justify-between text-xs text-neutral-600 border-t border-neutral-800 pt-2">
                        <span>Max Queue {g.fixed?.max_queue ?? "—"} · Starvations {g.fixed?.starvation_count ?? 0}</span>
                        <span className="text-neutral-500">—</span>
                      </div>
                    </div>

                    {/* Greedy */}
                    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-neutral-300 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-neutral-500" /> Greedy (Actuated)
                        </span>
                        <span className="text-xs font-mono text-neutral-500">
                          {g.greedy ? `${g.greedy.avg_wait_time.toFixed(1)}s avg` : "—"}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">Avg Wait</div>
                          <div className="text-xs font-mono font-medium text-white mt-0.5">
                            {g.greedy ? `${g.greedy.avg_wait_time.toFixed(2)}s` : "—"}
                          </div>
                        </div>
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">Throughput</div>
                          <div className="text-xs font-mono font-medium text-white mt-0.5">
                            {g.greedy?.total_passed ?? "—"}
                          </div>
                          <div className="text-[10px] text-neutral-600">veh</div>
                        </div>
                        <div className="rounded-md bg-[#0a0a0a] border border-neutral-800 p-2 text-center">
                          <div className="text-[10px] text-neutral-500">P95 Delay</div>
                          <div className="text-xs font-mono text-neutral-400 mt-0.5">
                            {g.greedy?.p95_delay ? `${g.greedy.p95_delay.toFixed(1)}s` : "—"}
                          </div>
                        </div>
                      </div>
                      <div className="mt-2 flex items-center justify-between text-xs text-neutral-600 border-t border-neutral-800 pt-2">
                        <span>Max Queue {g.greedy?.max_queue ?? "—"} · Starvations {g.greedy?.starvation_count ?? 0}</span>
                        <span className="text-neutral-500">—</span>
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

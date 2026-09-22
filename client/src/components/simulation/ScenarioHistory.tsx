"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { ChevronDown, ChevronUp, TrendingDown, TableProperties, RefreshCw } from "lucide-react";
import type { Scenario, ScenarioRun } from "@/types/simulation";
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
}

type Tab = "table" | "chart";

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

export function ScenarioHistory({ selectedScenario, latestRunResult }: ScenarioHistoryProps) {
  const { fetchRuns } = useScenarios();
  const [runs, setRuns]       = useState<ScenarioRun[]>([]);
  const [tab, setTab]         = useState<Tab>("table");
  const [expanded, setExpanded] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadRuns = useCallback(async () => {
    if (!selectedScenario) { setRuns([]); return; }
    setLoading(true);
    const data = await fetchRuns(selectedScenario.id);
    setRuns(data);
    setLoading(false);
  }, [selectedScenario, fetchRuns]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  // Optimistic append when a new run completes
  useEffect(() => {
    if (!latestRunResult || !selectedScenario) return;
    setRuns((prev) => {
      const already = prev.some(
        (r) => r.model_episode === latestRunResult.model_episode &&
               Math.abs(r.avg_wait_time - latestRunResult.avg_wait_time) < 0.01,
      );
      if (already) return prev;
      const optimistic: ScenarioRun = {
        id: `optimistic-${Date.now()}`,
        scenario_id: selectedScenario.id,
        model_id: "",
        model_episode: latestRunResult.model_episode,
        controller: "ai",
        scenario_hash: "",
        avg_wait_time: latestRunResult.avg_wait_time,
        total_passed: latestRunResult.total_passed,
        max_queue: latestRunResult.max_queue,
        override_rate: latestRunResult.override_rate,
        ran_at: new Date().toISOString(),
      };
      return [...prev, optimistic].sort((a, b) => a.model_episode - b.model_episode);
    });
    const t = setTimeout(() => loadRuns(), 2500);
    return () => clearTimeout(t);
  }, [latestRunResult, selectedScenario, loadRuns]);

  if (!selectedScenario) return null;

  const sorted     = [...runs].sort((a, b) => a.model_episode - b.model_episode);
  const chartData  = sorted.map((r) => ({ episode: r.model_episode, wait: Number(r.avg_wait_time.toFixed(2)) }));
  const bestWait   = runs.length ? Math.min(...runs.map((r) => r.avg_wait_time)) : null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">

      {/* ── Collapsible header ─────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors"
      >
        <span className="text-[10px] uppercase tracking-widest text-white/30 font-semibold flex-1">
          📊 Scenario History
        </span>
        <span className="text-[11px] text-white/30 font-mono shrink-0">
          {runs.length} run{runs.length !== 1 ? "s" : ""}
        </span>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); loadRuns(); }}
          className="p-1 rounded text-white/25 hover:text-white/60 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
        </button>
        {expanded ? <ChevronUp size={13} className="text-white/30" /> : <ChevronDown size={13} className="text-white/30" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">

          {/* Scenario meta pill */}
          <div className="text-[10px] text-white/30 font-mono px-1">
            <em className="not-italic text-white/50">{selectedScenario.name}</em>
            <span className="mx-1.5 text-white/20">·</span>
            seed {selectedScenario.seed}
            <span className="mx-1.5 text-white/20">·</span>
            λ={selectedScenario.spawn_lambda.toFixed(1)}
          </div>

          {/* Tab bar */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-white/[0.04] border border-white/[0.07]">
            <button
              type="button"
              onClick={() => setTab("table")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "table"
                  ? "bg-white/10 text-white"
                  : "text-white/40 hover:text-white/60"
              }`}
            >
              <TableProperties size={11} /> Runs
            </button>
            <button
              type="button"
              onClick={() => setTab("chart")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
                tab === "chart"
                  ? "bg-white/10 text-white"
                  : "text-white/40 hover:text-white/60"
              }`}
            >
              <TrendingDown size={11} /> Learning Curve
            </button>
          </div>

          {/* Empty state */}
          {!loading && runs.length === 0 && (
            <p className="text-center text-[11px] text-white/25 py-6 leading-relaxed">
              No runs yet.<br />
              Load a checkpoint then click<br />
              <span className="text-violet-400">▶ Run Scenario Benchmark</span>
            </p>
          )}

          {loading && runs.length === 0 && (
            <p className="text-center text-[11px] text-white/30 py-4">Loading…</p>
          )}

          {/* ── Table ──────────────────────────────────────────────── */}
          {tab === "table" && sorted.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-white/[0.07]">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-white/[0.07] bg-white/[0.03]">
                    <th className="text-left px-3 py-2 text-white/30 font-medium">Episode</th>
                    <th className="text-right px-3 py-2 text-white/30 font-medium">Avg Wait</th>
                    <th className="text-right px-3 py-2 text-white/30 font-medium">Passed</th>
                    <th className="text-right px-3 py-2 text-white/30 font-medium">MaxQ</th>
                    <th className="text-right px-3 py-2 text-white/30 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r) => {
                    const isBest = bestWait !== null && r.avg_wait_time === bestWait;
                    return (
                      <tr
                        key={r.id}
                        className={`border-b border-white/[0.04] last:border-0 transition-colors ${
                          isBest ? "bg-emerald-500/[0.06]" : "hover:bg-white/[0.02]"
                        }`}
                      >
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-mono text-[10px]">
                            ep{r.model_episode}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          <span className={isBest ? "text-emerald-400 font-semibold" : "text-white/70"}>
                            {r.avg_wait_time.toFixed(2)}s
                          </span>
                          {isBest && (
                            <span className="ml-1 text-[9px] text-emerald-400 font-semibold">best</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-white/60">{r.total_passed}</td>
                        <td className="px-3 py-2 text-right font-mono text-white/60">{r.max_queue}</td>
                        <td className="px-3 py-2 text-right text-white/30 text-[10px]">{formatDate(r.ran_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Learning Curve ─────────────────────────────────────── */}
          {tab === "chart" && sorted.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-white/25 text-center">
                DQN avg wait time by checkpoint — lower is better
              </p>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: -8, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="episode"
                    stroke="rgba(255,255,255,0.2)"
                    tick={{ fontSize: 10, fill: "rgba(255,255,255,0.3)" }}
                    tickLine={false}
                    label={{ value: "Episode", position: "insideBottom", offset: -2, fontSize: 10, fill: "rgba(255,255,255,0.25)" }}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.2)"
                    tick={{ fontSize: 10, fill: "rgba(255,255,255,0.3)" }}
                    tickLine={false}
                    domain={["auto", "auto"]}
                    width={36}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "rgba(8,8,16,0.95)",
                      border: "1px solid rgba(139,92,246,0.35)",
                      borderRadius: 10,
                      fontSize: 12,
                      padding: "8px 12px",
                    }}
                    formatter={(v: unknown) => [`${Number(v).toFixed(2)}s`, "Avg Wait"]}
                    labelFormatter={(ep) => `Episode ${ep}`}
                    cursor={{ stroke: "rgba(139,92,246,0.3)", strokeWidth: 1 }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}
                    iconType="circle"
                    iconSize={7}
                  />
                  {bestWait !== null && (
                    <ReferenceLine
                      y={bestWait}
                      stroke="#22c55e"
                      strokeDasharray="4 3"
                      strokeWidth={1}
                      label={{
                        value: `Best ${bestWait.toFixed(1)}s`,
                        fill: "#22c55e",
                        fontSize: 9,
                        position: "right",
                      }}
                    />
                  )}
                  <Line
                    type="monotone"
                    dataKey="wait"
                    name="DQN AI"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ r: 3.5, fill: "#8b5cf6", strokeWidth: 0 }}
                    activeDot={{ r: 5.5, fill: "#a78bfa", strokeWidth: 0 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Chart empty state */}
          {tab === "chart" && sorted.length === 0 && !loading && (
            <p className="text-center text-[11px] text-white/25 py-6">
              Run at least one checkpoint to see the learning curve.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

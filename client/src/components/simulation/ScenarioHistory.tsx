/**
 * ScenarioHistory — displays all benchmark runs for a selected scenario.
 *
 * Two tabs:
 *  1. Runs Table — per-run row: model_episode, avg_wait, passed, max_queue, override%, date
 *  2. Learning Curve — line chart: episode → avg_wait_time (DQN trend)
 *
 * Auto-fetches runs whenever selectedScenario changes.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { ChevronDown, ChevronUp, TrendingDown, TableProperties } from "lucide-react";
import type { Scenario, ScenarioRun } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";

interface ScenarioHistoryProps {
  selectedScenario: Scenario | null;
  /** Latest result from a just-completed scenario benchmark run */
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
  const [runs, setRuns] = useState<ScenarioRun[]>([]);
  const [tab, setTab] = useState<Tab>("table");
  const [expanded, setExpanded] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadRuns = useCallback(async () => {
    if (!selectedScenario) { setRuns([]); return; }
    setLoading(true);
    const data = await fetchRuns(selectedScenario.id);
    setRuns(data);
    setLoading(false);
  }, [selectedScenario, fetchRuns]);

  // Re-fetch when selected scenario changes
  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Append latest run result to table immediately (optimistic UI before next fetch)
  useEffect(() => {
    if (!latestRunResult || !selectedScenario) return;
    setRuns((prev) => {
      const already = prev.some(
        (r) => r.model_episode === latestRunResult.model_episode &&
               r.avg_wait_time === latestRunResult.avg_wait_time,
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
    // Refresh from server shortly after
    const t = setTimeout(() => loadRuns(), 2500);
    return () => clearTimeout(t);
  }, [latestRunResult, selectedScenario, loadRuns]);

  if (!selectedScenario) return null;

  // Chart data — sorted by episode ascending
  const chartData = [...runs]
    .sort((a, b) => a.model_episode - b.model_episode)
    .map((r) => ({
      episode: r.model_episode,
      wait: Number(r.avg_wait_time.toFixed(2)),
    }));

  const bestWait = runs.length ? Math.min(...runs.map((r) => r.avg_wait_time)) : null;

  return (
    <div className="scenario-history">
      {/* Collapsible header */}
      <button
        className="scenario-history-header"
        onClick={() => setExpanded((e) => !e)}
        type="button"
      >
        <span className="scenario-history-title">
          📊 Scenario History — <em>{selectedScenario.name}</em>
        </span>
        <span className="scenario-history-meta">
          {runs.length} run{runs.length !== 1 ? "s" : ""}
          &nbsp;· seed {selectedScenario.seed}
          &nbsp;· λ={selectedScenario.spawn_lambda.toFixed(1)}
        </span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="scenario-history-body">
          {/* Tab bar */}
          <div className="scenario-history-tabs">
            <button
              className={`scenario-tab ${tab === "table" ? "active" : ""}`}
              onClick={() => setTab("table")}
              type="button"
            >
              <TableProperties size={13} /> Runs
            </button>
            <button
              className={`scenario-tab ${tab === "chart" ? "active" : ""}`}
              onClick={() => setTab("chart")}
              type="button"
            >
              <TrendingDown size={13} /> Learning Curve
            </button>
          </div>

          {loading && <div className="scenario-history-loading">Loading runs…</div>}

          {!loading && runs.length === 0 && (
            <div className="scenario-history-empty">
              No runs yet. Load a model checkpoint and click <strong>Run Scenario Benchmark</strong>.
            </div>
          )}

          {/* ── Table tab ────────────────────────────────────────────────── */}
          {tab === "table" && runs.length > 0 && (
            <div className="scenario-table-wrapper">
              <table className="scenario-table">
                <thead>
                  <tr>
                    <th>Episode</th>
                    <th>Avg Wait (s)</th>
                    <th>Passed</th>
                    <th>Max Queue</th>
                    <th>Override %</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {[...runs]
                    .sort((a, b) => a.model_episode - b.model_episode)
                    .map((r) => (
                      <tr
                        key={r.id}
                        className={r.avg_wait_time === bestWait ? "scenario-table-best" : ""}
                      >
                        <td>
                          <span className="scenario-ep-badge">ep{r.model_episode}</span>
                        </td>
                        <td className={r.avg_wait_time === bestWait ? "scenario-best-cell" : ""}>
                          {r.avg_wait_time.toFixed(2)}
                          {r.avg_wait_time === bestWait && (
                            <span className="scenario-best-tag">best</span>
                          )}
                        </td>
                        <td>{r.total_passed}</td>
                        <td>{r.max_queue}</td>
                        <td>{(r.override_rate * 100).toFixed(1)}%</td>
                        <td className="scenario-date-cell">{formatDate(r.ran_at)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Learning Curve tab ───────────────────────────────────────── */}
          {tab === "chart" && runs.length > 0 && (
            <div className="scenario-chart-wrapper">
              <p className="scenario-chart-subtitle">
                DQN avg wait time by training checkpoint — lower is better
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="episode"
                    stroke="rgba(255,255,255,0.35)"
                    tick={{ fontSize: 11 }}
                    label={{ value: "Episode", position: "insideBottom", offset: -2, fontSize: 11, fill: "rgba(255,255,255,0.4)" }}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.35)"
                    tick={{ fontSize: 11 }}
                    label={{ value: "Avg Wait (s)", angle: -90, position: "insideLeft", fontSize: 11, fill: "rgba(255,255,255,0.4)" }}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "rgba(10,10,20,0.92)",
                      border: "1px solid rgba(139,92,246,0.4)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(v: unknown) => [`${Number(v).toFixed(2)}s`, "Avg Wait"]}
                    labelFormatter={(ep) => `Episode ${ep}`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {/* Best wait reference line */}
                  {bestWait !== null && (
                    <ReferenceLine
                      y={bestWait}
                      stroke="#22c55e"
                      strokeDasharray="4 3"
                      label={{ value: `Best ${bestWait.toFixed(1)}s`, fill: "#22c55e", fontSize: 10 }}
                    />
                  )}
                  <Line
                    type="monotone"
                    dataKey="wait"
                    name="DQN AI"
                    stroke="#8b5cf6"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#8b5cf6", strokeWidth: 0 }}
                    activeDot={{ r: 6, fill: "#a78bfa" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

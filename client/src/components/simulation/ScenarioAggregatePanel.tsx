"use client";

import { useCallback, useEffect, useState } from "react";
import { Award, BarChart3, RefreshCw, TrendingDown, Zap } from "lucide-react";
import type { ScenarioAggregateStats } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";
import { Button } from "@/components/ui/button";

interface ScenarioAggregatePanelProps {
  refreshTrigger?: unknown;
}

export function ScenarioAggregatePanel({ refreshTrigger }: ScenarioAggregatePanelProps) {
  const { fetchAggregateStats } = useScenarios();
  const [stats, setStats] = useState<ScenarioAggregateStats | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAggregateStats();
      setStats(data);
    } catch (e) {
      console.error("Failed to load aggregate stats", e);
    } finally {
      setLoading(false);
    }
  }, [fetchAggregateStats]);

  useEffect(() => {
    loadStats();
  }, [loadStats, refreshTrigger]);

  if (!stats || stats.total_groups === 0) {
    return null;
  }

  const pCtrl = stats.per_controller || {};
  const fixed = pCtrl.fixed;
  const greedy = pCtrl.greedy;
  const ai = pCtrl.ai;

  let bestCtrl: string | null = null;
  let minMean = Infinity;
  if (fixed?.mean_wait != null && fixed.mean_wait < minMean) {
    minMean = fixed.mean_wait;
    bestCtrl = "fixed";
  }
  if (greedy?.mean_wait != null && greedy.mean_wait < minMean) {
    minMean = greedy.mean_wait;
    bestCtrl = "greedy";
  }
  if (ai?.mean_wait != null && ai.mean_wait < minMean) {
    minMean = ai.mean_wait;
    bestCtrl = "ai";
  }

  const winRatePct = (stats.dqn_win_rate * 100).toFixed(0);

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-neutral-800 text-neutral-400 border border-neutral-700">
            <BarChart3 size={16} />
          </div>
          <div className="flex flex-col">
            <h3 className="text-sm font-medium text-white flex items-center gap-2">
              Cross-Scenario Aggregate Performance
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-neutral-800 text-neutral-300 border border-neutral-700">
                CRN Validated
              </span>
            </h3>
            <p className="text-[11px] text-neutral-500">
              Aggregated across {stats.total_scenarios} scenarios · {stats.total_groups} paired executions ({stats.total_runs} runs)
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-8 w-8 p-0 border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-white"
          onClick={loadStats}
          disabled={loading}
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </Button>
      </div>

      {/* ── Key Metrics Cards ───────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3">
        {/* Win Rate */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3 space-y-1">
          <span className="text-[10px] uppercase font-medium text-neutral-500 tracking-wider flex items-center gap-1">
            <Award size={11} className="text-neutral-400" /> DQN Win Rate
          </span>
          <div className="text-xl font-medium font-mono text-white flex items-baseline gap-1.5">
            <span className="text-white">
              {winRatePct}%
            </span>
            <span className="text-[11px] font-normal text-neutral-600 font-sans">of paired groups</span>
          </div>
        </div>

        {/* Delta vs Greedy */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3 space-y-1">
          <span className="text-[10px] uppercase font-medium text-neutral-500 tracking-wider flex items-center gap-1">
            <TrendingDown size={11} className="text-neutral-400" /> DQN vs. Greedy
          </span>
          <div className="text-xl font-medium font-mono text-white flex items-baseline gap-1.5">
            {stats.dqn_vs_greedy_delta != null ? (
              <>
                <span className="text-white">
                  {stats.dqn_vs_greedy_delta <= 0 ? "-" : "+"}{Math.abs(stats.dqn_vs_greedy_delta).toFixed(2)}s
                </span>
                <span className="text-[11px] font-normal text-neutral-600 font-sans">
                  {stats.dqn_vs_greedy_delta <= 0 ? "faster" : "slower"}
                </span>
              </>
            ) : (
              <span className="text-neutral-600 text-sm font-sans">No paired runs</span>
            )}
          </div>
        </div>

        {/* Delta vs Fixed */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3 space-y-1">
          <span className="text-[10px] uppercase font-medium text-neutral-500 tracking-wider flex items-center gap-1">
            <Zap size={11} className="text-neutral-400" /> DQN vs. Fixed
          </span>
          <div className="text-xl font-medium font-mono text-white flex items-baseline gap-1.5">
            {stats.dqn_vs_fixed_delta != null ? (
              <>
                <span className="text-white">
                  {stats.dqn_vs_fixed_delta <= 0 ? "-" : "+"}{Math.abs(stats.dqn_vs_fixed_delta).toFixed(2)}s
                </span>
                <span className="text-[11px] font-normal text-neutral-600 font-sans">
                  {stats.dqn_vs_fixed_delta <= 0 ? "faster" : "slower"}
                </span>
              </>
            ) : (
              <span className="text-neutral-600 text-sm font-sans">No paired runs</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Controller Comparison Table ─────────────────────────── */}
      <div className="overflow-x-auto rounded-lg border border-neutral-800">
        <table className="w-full text-[11px]">
          <thead className="bg-neutral-900">
            <tr className="border-b border-neutral-800">
              <th className="text-left px-3 py-2 text-neutral-500 font-medium">Controller</th>
              <th className="text-right px-3 py-2 text-neutral-500 font-medium">Mean Wait (± Std)</th>
              <th className="text-right px-3 py-2 text-neutral-500 font-medium">Mean Throughput</th>
              <th className="text-right px-3 py-2 text-neutral-500 font-medium">Mean Starvations</th>
              <th className="text-center px-3 py-2 text-neutral-500 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800">
            {/* Fixed */}
            <tr className="hover:bg-neutral-800/30">
              <td className="px-3 py-2 font-medium text-neutral-300 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" /> Fixed Time
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-400">
                {fixed?.mean_wait != null ? (
                  <span>
                    {fixed.mean_wait.toFixed(2)}s
                    <span className="text-neutral-600 ml-1">±{fixed.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-500">
                {fixed?.mean_throughput != null ? `${fixed.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-500">
                {fixed?.mean_starvation != null ? fixed.mean_starvation.toFixed(1) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "fixed" ? (
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-neutral-800 text-neutral-300 font-semibold border border-neutral-700">
                    👑 Leader
                  </span>
                ) : (
                  <span className="text-[10px] text-neutral-600">Baseline</span>
                )}
              </td>
            </tr>

            {/* Greedy */}
            <tr className="hover:bg-neutral-800/30">
              <td className="px-3 py-2 font-medium text-neutral-300 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-500" /> Greedy Actuated
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-400">
                {greedy?.mean_wait != null ? (
                  <span>
                    {greedy.mean_wait.toFixed(2)}s
                    <span className="text-neutral-600 ml-1">±{greedy.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-500">
                {greedy?.mean_throughput != null ? `${greedy.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-neutral-500">
                {greedy?.mean_starvation != null ? greedy.mean_starvation.toFixed(1) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "greedy" ? (
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-neutral-800 text-neutral-300 font-semibold border border-neutral-700">
                    👑 Leader
                  </span>
                ) : (
                  <span className="text-[10px] text-neutral-600">Strong Baseline</span>
                )}
              </td>
            </tr>

            {/* DQN */}
            <tr className={`hover:bg-neutral-800/30 ${bestCtrl === "ai" ? "bg-neutral-800/40" : ""}`}>
              <td className="px-3 py-2 font-semibold text-white flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-white" /> DQN Policy
              </td>
              <td className="px-3 py-2 text-right font-mono font-semibold">
                {ai?.mean_wait != null ? (
                  <span className={bestCtrl === "ai" ? "text-white" : "text-neutral-300"}>
                    {ai.mean_wait.toFixed(2)}s
                    <span className="text-neutral-600 ml-1">±{ai.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/80 font-medium">
                {ai?.mean_throughput != null ? `${ai.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/80">
                L-T {ai?.mean_starvation != null ? (
                  <span className={ai.mean_starvation === 0 ? "text-white font-bold" : "text-neutral-400"}>
                    {ai.mean_starvation.toFixed(1)}
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "ai" ? (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] bg-white text-black font-bold border border-neutral-700">
                    <Award size={10} /> DQN WIN
                  </span>
                ) : (
                  <span className="text-[10px] text-neutral-500">Trained Agent</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

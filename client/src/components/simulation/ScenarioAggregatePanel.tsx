"use client";

import { useCallback, useEffect, useState } from "react";
import { Award, BarChart3, RefreshCw, Sparkles, TrendingDown, Zap } from "lucide-react";
import type { ScenarioAggregateStats } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";

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

  // Determine best controller by mean wait
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
    <div className="rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-950/20 via-black/40 to-slate-950/40 p-4 space-y-4 shadow-xl backdrop-blur-md">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-violet-500/20 text-violet-300 border border-violet-500/30">
            <BarChart3 size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              Cross-Scenario Aggregate Performance
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-violet-500/20 text-violet-300 border border-violet-500/30">
                CRN Validated
              </span>
            </h3>
            <p className="text-[11px] text-white/40">
              Aggregated across {stats.total_scenarios} scenarios · {stats.total_groups} paired executions ({stats.total_runs} runs)
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadStats}
          disabled={loading}
          className="p-1.5 rounded-lg border border-white/10 bg-white/[0.04] text-white/40 hover:text-white/80 hover:border-white/20 transition-colors"
          title="Refresh aggregate stats"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* ── Key Metrics Cards ───────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3">
        {/* Win Rate */}
        <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3 space-y-1">
          <span className="text-[10px] uppercase font-semibold text-white/40 tracking-wider flex items-center gap-1">
            <Award size={11} className="text-violet-400" /> DQN Win Rate
          </span>
          <div className="text-xl font-bold font-mono text-white flex items-baseline gap-1.5">
            <span className={Number(winRatePct) >= 50 ? "text-emerald-400" : "text-violet-300"}>
              {winRatePct}%
            </span>
            <span className="text-[11px] font-normal text-white/30 font-sans">of paired groups</span>
          </div>
        </div>

        {/* Delta vs Greedy */}
        <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3 space-y-1">
          <span className="text-[10px] uppercase font-semibold text-white/40 tracking-wider flex items-center gap-1">
            <TrendingDown size={11} className="text-emerald-400" /> DQN vs. Greedy
          </span>
          <div className="text-xl font-bold font-mono text-white flex items-baseline gap-1.5">
            {stats.dqn_vs_greedy_delta != null ? (
              <>
                <span className={stats.dqn_vs_greedy_delta <= 0 ? "text-emerald-400" : "text-rose-400"}>
                  {stats.dqn_vs_greedy_delta <= 0 ? "-" : "+"}{Math.abs(stats.dqn_vs_greedy_delta).toFixed(2)}s
                </span>
                <span className="text-[11px] font-normal text-white/30 font-sans">
                  {stats.dqn_vs_greedy_delta <= 0 ? "faster" : "slower"}
                </span>
              </>
            ) : (
              <span className="text-white/40 text-sm font-sans">No paired runs</span>
            )}
          </div>
        </div>

        {/* Delta vs Fixed */}
        <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3 space-y-1">
          <span className="text-[10px] uppercase font-semibold text-white/40 tracking-wider flex items-center gap-1">
            <Zap size={11} className="text-blue-400" /> DQN vs. Fixed
          </span>
          <div className="text-xl font-bold font-mono text-white flex items-baseline gap-1.5">
            {stats.dqn_vs_fixed_delta != null ? (
              <>
                <span className={stats.dqn_vs_fixed_delta <= 0 ? "text-emerald-400" : "text-rose-400"}>
                  {stats.dqn_vs_fixed_delta <= 0 ? "-" : "+"}{Math.abs(stats.dqn_vs_fixed_delta).toFixed(2)}s
                </span>
                <span className="text-[11px] font-normal text-white/30 font-sans">
                  {stats.dqn_vs_fixed_delta <= 0 ? "faster" : "slower"}
                </span>
              </>
            ) : (
              <span className="text-white/40 text-sm font-sans">No paired runs</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Controller Comparison Table ─────────────────────────── */}
      <div className="overflow-x-auto rounded-lg border border-white/[0.07]">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.07] bg-white/[0.03]">
              <th className="text-left px-3 py-2 text-white/40 font-medium">Controller</th>
              <th className="text-right px-3 py-2 text-white/40 font-medium">Mean Wait (± Std)</th>
              <th className="text-right px-3 py-2 text-white/40 font-medium">Mean Throughput</th>
              <th className="text-right px-3 py-2 text-white/40 font-medium">Mean Starvations</th>
              <th className="text-center px-3 py-2 text-white/40 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {/* Fixed */}
            <tr className="hover:bg-white/[0.02]">
              <td className="px-3 py-2 font-medium text-blue-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" /> Fixed Time
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/70">
                {fixed?.mean_wait != null ? (
                  <span>
                    {fixed.mean_wait.toFixed(2)}s
                    <span className="text-white/30 ml-1">±{fixed.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/60">
                {fixed?.mean_throughput != null ? `${fixed.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/60">
                {fixed?.mean_starvation != null ? fixed.mean_starvation.toFixed(1) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "fixed" ? (
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-300 font-semibold">
                    👑 Leader
                  </span>
                ) : (
                  <span className="text-[10px] text-white/30">Baseline</span>
                )}
              </td>
            </tr>

            {/* Greedy */}
            <tr className="hover:bg-white/[0.02]">
              <td className="px-3 py-2 font-medium text-emerald-400 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Greedy Actuated
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/80">
                {greedy?.mean_wait != null ? (
                  <span>
                    {greedy.mean_wait.toFixed(2)}s
                    <span className="text-white/30 ml-1">±{greedy.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/60">
                {greedy?.mean_throughput != null ? `${greedy.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/60">
                {greedy?.mean_starvation != null ? greedy.mean_starvation.toFixed(1) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "greedy" ? (
                  <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/20 text-amber-300 font-semibold">
                    👑 Leader
                  </span>
                ) : (
                  <span className="text-[10px] text-white/30">Strong Baseline</span>
                )}
              </td>
            </tr>

            {/* DQN */}
            <tr className={`hover:bg-white/[0.02] ${bestCtrl === "ai" ? "bg-violet-500/[0.06]" : ""}`}>
              <td className="px-3 py-2 font-semibold text-violet-300 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400" /> DQN Policy
              </td>
              <td className="px-3 py-2 text-right font-mono font-semibold">
                {ai?.mean_wait != null ? (
                  <span className={bestCtrl === "ai" ? "text-emerald-400" : "text-violet-200"}>
                    {ai.mean_wait.toFixed(2)}s
                    <span className="text-white/30 ml-1">±{ai.std_wait?.toFixed(2) ?? 0}</span>
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/80 font-medium">
                {ai?.mean_throughput != null ? `${ai.mean_throughput.toFixed(1)} veh` : "—"}
              </td>
              <td className="px-3 py-2 text-right font-mono text-white/80">
                {ai?.mean_starvation != null ? (
                  <span className={ai.mean_starvation === 0 ? "text-emerald-400 font-bold" : "text-white/70"}>
                    {ai.mean_starvation.toFixed(1)}
                  </span>
                ) : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                {bestCtrl === "ai" ? (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
                    <Sparkles size={10} /> DQN WIN
                  </span>
                ) : (
                  <span className="text-[10px] text-violet-400/60">Trained Agent</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

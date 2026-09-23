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
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4 overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-neutral-800 text-white border border-neutral-700 shrink-0">
            <BarChart3 size={14} />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-white leading-tight flex flex-wrap items-center gap-1.5">
              <span>Cross-Scenario Aggregate</span>
              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white text-black border border-neutral-200 font-semibold">
                CRN Validated
              </span>
            </h3>
            <p className="text-xs text-neutral-500 leading-tight mt-0.5 truncate">
              {stats.total_scenarios} scenarios · {stats.total_groups} paired · {stats.total_runs} runs
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-7 w-7 p-0 border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-white shrink-0"
          onClick={loadStats}
          disabled={loading}
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </Button>
      </div>

      {/* ── Key Metrics Cards ───────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-3 space-y-1.5">
          <span className="text-[10px] font-medium text-neutral-500 flex items-center gap-1">
            <Award size={10} className="text-neutral-500" /> Win Rate
          </span>
          <div className="text-lg font-mono font-medium text-white leading-none">
            {winRatePct}%
          </div>
          <div className="text-xs text-neutral-500 leading-tight">of paired groups</div>
        </div>
        <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-3 space-y-1.5">
          <span className="text-[10px] font-medium text-neutral-500 flex items-center gap-1">
            <TrendingDown size={10} className="text-neutral-500" /> vs Greedy
          </span>
          <div className="text-sm font-mono font-medium text-white leading-none">
            {stats.dqn_vs_greedy_delta != null ? (
              <span className={stats.dqn_vs_greedy_delta <= 0 ? "text-emerald-400" : "text-rose-400"}>
                {stats.dqn_vs_greedy_delta <= 0 ? "" : "+"}{stats.dqn_vs_greedy_delta.toFixed(2)}s
              </span>
            ) : (
              <span className="text-neutral-600 text-xs">—</span>
            )}
          </div>
          <div className="text-xs text-neutral-500 leading-tight">
            {stats.dqn_vs_greedy_delta != null
              ? stats.dqn_vs_greedy_delta <= 0 ? "faster" : "slower"
              : "no data"}
          </div>
        </div>
        <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] p-3 space-y-1.5">
          <span className="text-[10px] font-medium text-neutral-500 flex items-center gap-1">
            <Zap size={10} className="text-neutral-500" /> vs Fixed
          </span>
          <div className="text-sm font-mono font-medium text-white leading-none">
            {stats.dqn_vs_fixed_delta != null ? (
              <span className={stats.dqn_vs_fixed_delta <= 0 ? "text-emerald-400" : "text-rose-400"}>
                {stats.dqn_vs_fixed_delta <= 0 ? "" : "+"}{stats.dqn_vs_fixed_delta.toFixed(2)}s
              </span>
            ) : (
              <span className="text-neutral-600 text-xs">—</span>
            )}
          </div>
          <div className="text-xs text-neutral-500 leading-tight">
            {stats.dqn_vs_fixed_delta != null
              ? stats.dqn_vs_fixed_delta <= 0 ? "faster" : "slower"
              : "no data"}
          </div>
        </div>
      </div>

      {/* ── Controller Comparison — card stack (no horizontal scroll) ─ */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-medium text-neutral-400">Controller Means</span>
          <span className="text-xs text-neutral-600">{stats.total_groups} paired runs</span>
        </div>

        {[
          { key: "fixed", label: "Fixed Time", dot: "bg-neutral-600", data: fixed, baseline: true },
          { key: "greedy", label: "Greedy Actuated", dot: "bg-neutral-500", data: greedy, baseline: false },
          { key: "ai", label: "DQN Policy", dot: "bg-white", data: ai, baseline: false },
        ].map(({ key, label, dot, data: d, baseline }) => {
          const isBest = bestCtrl === key;
          return (
            <div
              key={key}
              className={`rounded-xl border p-3 space-y-2.5 ${
                isBest ? "border-white bg-white text-black" : "border-neutral-800 bg-[#0a0a0a] text-white"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs font-medium flex items-center gap-1.5 ${isBest ? "text-black" : "text-white"}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${isBest ? "bg-black" : dot}`} /> {label}
                </span>
                {isBest ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-black text-white">
                    <Award size={10} /> Leader
                  </span>
                ) : (
                  <span className={`text-xs ${baseline ? "text-neutral-500" : "text-neutral-600"}`}>
                    {baseline ? "Baseline" : key === "greedy" ? "Strong Baseline" : "Trained Agent"}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-neutral-800/50">
                <div className="space-y-0.5">
                  <div className={`text-[10px] ${isBest ? "text-black/60" : "text-neutral-500"}`}>Mean Wait</div>
                  <div className={`text-xs font-mono font-medium ${isBest ? "text-black" : "text-white"}`}>
                    {d?.mean_wait != null ? `${d.mean_wait.toFixed(2)}s` : "—"}
                  </div>
                  <div className={`text-xs font-mono ${isBest ? "text-black/50" : "text-neutral-600"}`}>
                    {d?.mean_wait != null ? `±${d.std_wait?.toFixed(2) ?? "0.00"}s` : ""}
                  </div>
                </div>
                <div className="space-y-0.5 text-center border-x border-neutral-800/50 px-2">
                  <div className={`text-[10px] ${isBest ? "text-black/60" : "text-neutral-500"}`}>Throughput</div>
                  <div className={`text-xs font-mono font-medium ${isBest ? "text-black" : "text-white"}`}>
                    {d?.mean_throughput != null ? d.mean_throughput.toFixed(1) : "—"}
                  </div>
                  <div className={`text-xs ${isBest ? "text-black/50" : "text-neutral-600"}`}>veh avg</div>
                </div>
                <div className="space-y-0.5 text-right">
                  <div className={`text-[10px] ${isBest ? "text-black/60" : "text-neutral-500"}`}>Starvations</div>
                  <div className={`text-xs font-mono font-medium ${isBest ? "text-black" : d?.mean_starvation === 0 ? "text-emerald-400" : "text-white"}`}>
                    {d?.mean_starvation != null ? d.mean_starvation.toFixed(1) : "—"}
                  </div>
                  <div className={`text-xs ${isBest ? "text-black/50" : "text-neutral-600"}`}>mean</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

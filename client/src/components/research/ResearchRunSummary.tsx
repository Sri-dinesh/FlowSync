"use client";

import React from "react";
import { CheckCircle2, Trophy, ShieldCheck } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

/**
 * Plain-language completion card shown when a run finishes.
 * Previously a completed run left the panels frozen with no explanation.
 */
export function ResearchRunSummary() {
  const runStatus = useResearchStore((s) => s.runStatus);
  const summary = useResearchStore((s) => s.experimentSummary);
  const pairedSummary = useResearchStore((s) => s.pairedSummary);
  const isPairedMode = useResearchStore((s) => s.isPairedMode);

  if (runStatus !== "completed") return null;

  if (isPairedMode && pairedSummary) {
    const s = pairedSummary as Record<string, unknown>;
    const a = (s.controller_a ?? {}) as Record<string, unknown>;
    const b = (s.controller_b ?? {}) as Record<string, unknown>;
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-white">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Comparison complete
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3">
          <div className="rounded-md bg-black/30 border border-neutral-800 p-3">
            <div className="text-[11px] text-neutral-500 font-mono">{String(a.name ?? "Controller A")}</div>
            <div className="text-lg font-semibold font-mono tabular-nums text-white">{Number(a.final_delay ?? 0).toFixed(2)}s</div>
            <div className="text-[11px] text-neutral-500">{Number(a.throughput ?? 0)} cleared</div>
          </div>
          <div className="rounded-md bg-black/30 border border-neutral-800 p-3">
            <div className="text-[11px] text-neutral-500 font-mono">{String(b.name ?? "Controller B")}</div>
            <div className="text-lg font-semibold font-mono tabular-nums text-white">{Number(b.final_delay ?? 0).toFixed(2)}s</div>
            <div className="text-[11px] text-neutral-500">{Number(b.throughput ?? 0)} cleared</div>
          </div>
          <div className="rounded-md bg-black/30 border border-neutral-800 p-3">
            <div className="text-[11px] text-neutral-500">Delay saving</div>
            <div className="text-lg font-semibold font-mono tabular-nums text-emerald-300 flex items-center gap-1.5">
              <Trophy className="w-4 h-4" /> {Number(s.delay_savings_pct ?? 0).toFixed(1)}%
            </div>
            <div className="text-[11px] text-neutral-500">with {String(b.name ?? "B")}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-white">
        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        Run complete
        <span className="font-mono text-[11px] font-normal text-neutral-500 truncate">{summary.experiment_id}</span>
      </div>
      <p className="text-xs text-neutral-400 mt-1">
        Avg delay <span className="font-mono tabular-nums text-white">{summary.avg_delay.toFixed(2)}s</span>
        {" "}(worst 5% <span className="font-mono tabular-nums text-white">{summary.p95_delay.toFixed(2)}s</span>),{" "}
        <span className="font-mono tabular-nums text-white">{summary.throughput}</span> cleared,{" "}
        <span className="font-mono tabular-nums text-white">{summary.starvation_count}</span> starved.
      </p>
      <div className="flex items-center gap-1.5 mt-2 text-[11px] text-emerald-300">
        <ShieldCheck className="w-3.5 h-3.5" />
        {summary.executed_violations === 0
          ? "0 safety violations."
          : `${summary.executed_violations} safety violations detected.`}
      </div>
    </div>
  );
}

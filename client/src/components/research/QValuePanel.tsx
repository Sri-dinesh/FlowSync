"use client";

import { useMemo } from "react";
import { Cpu, CheckCircle2, Lock } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

const PHASE_LABELS = [
  "Phase 0: NS Straight",
  "Phase 1: EW Straight",
  "Phase 2: NS Left-Turn",
  "Phase 3: EW Left-Turn",
];

const PHASE_COLORS = [
  "from-emerald-500 to-emerald-400",
  "from-sky-500 to-sky-400",
  "from-violet-500 to-violet-400",
  "from-rose-500 to-rose-400",
];

export default function QValuePanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);

  const policy = currentFrame?.policy;
  const currentPhase = currentFrame?.signal.current_phase ?? 0;

  const { qValues, maxQ, valueMargin, validActions, selectedAction } = useMemo(() => {
    if (!policy || !policy.q_values?.length) {
      return {
        qValues: [0, 0, 0, 0],
        maxQ: 1.0,
        valueMargin: 0.0,
        validActions: [true, true, true, true],
        selectedAction: 0,
      };
    }
    const qVals = policy.q_values;
    const max = Math.max(...qVals, 1e-6);
    const sorted = [...qVals].sort((a, b) => b - a);
    const margin = Math.max(0, (sorted[0] ?? 0) - (sorted[1] ?? 0));
    return {
      qValues: qVals,
      maxQ: max,
      valueMargin: margin,
      validActions: policy.valid_actions || [true, true, true, true],
      selectedAction: policy.proposed_action,
    };
  }, [policy]);

  if (!policy) {
    return (
      <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl text-center text-xs text-white/30 font-mono">
        Awaiting D3QN Q-value estimates...
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-xl flex flex-col gap-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-indigo-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white">
            Policy Value Estimates (Q-Values)
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="text-white/40">Exploration Rate:</span>
          <span className="text-indigo-300 font-bold">ε = {policy.epsilon.toFixed(3)}</span>
        </div>
      </div>

      {/* 4 Q-Value Bars */}
      <div className="space-y-2">
        {qValues.map((q, i) => {
          const isValid = validActions[i] !== false;
          const isSelected = i === selectedAction;
          const isCurrent = i === currentPhase;
          const pct = maxQ > 0 ? Math.max(0, (q / maxQ) * 100) : 0;

          return (
            <div
              key={i}
              className={`rounded-xl p-3 border transition-all ${
                isSelected
                  ? "bg-indigo-500/10 border-indigo-500/30 shadow-lg shadow-indigo-500/10"
                  : !isValid
                  ? "bg-white/[0.01] border-white/[0.04] opacity-50"
                  : "bg-white/[0.02] border-white/[0.06]"
              }`}
            >
              <div className="flex items-center justify-between mb-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold ${isSelected ? "text-indigo-200" : "text-white/70"}`}>
                    {PHASE_LABELS[i]}
                  </span>
                  {!isValid && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      <Lock className="h-2.5 w-2.5" /> Masked
                    </span>
                  )}
                  {isSelected && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      <CheckCircle2 className="h-2.5 w-2.5" /> Max Action
                    </span>
                  )}
                  {isCurrent && !isSelected && (
                    <span className="text-[9px] text-white/40 font-mono">Active Phase</span>
                  )}
                </div>

                <div className="font-mono text-xs font-bold tabular-nums">
                  {q.toFixed(3)}
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${PHASE_COLORS[i] || "from-indigo-500 to-indigo-400"} transition-all duration-150`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Metrics */}
      <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="text-white/40">Action Margin (ΔQ):</span>
          <span className="font-mono font-bold text-indigo-300">+{valueMargin.toFixed(3)}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-white/40">Action Source:</span>
          <span className="font-mono text-white/80">
            {policy.is_exploring ? "ε-Greedy Exploration" : "Greedy Exploitation"}
          </span>
        </div>
      </div>
    </div>
  );
}

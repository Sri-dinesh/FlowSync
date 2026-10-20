"use client";

import { useMemo } from "react";
import { CheckCircle2, Lock } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

const PHASE_LABELS = [
  "NS straight",
  "EW straight",
  "NS left turn",
  "EW left turn",
];

const PHASE_BAR = "bg-neutral-300";

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
      <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-xs text-neutral-500">
        Waiting for Q-values — run a simulation to see what the AI policy prefers.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="text-sm font-medium text-white">
          Policy values
        </h3>
        <span className="text-[11px] font-mono tabular-nums text-neutral-500" title="Random-action probability. 0 means the AI always picks its best guess.">
          ε = {policy.epsilon.toFixed(3)}
        </span>
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
              className={`rounded-md p-2.5 border transition-colors ${
                isSelected
                  ? "bg-white/[0.04] border-neutral-600"
                  : !isValid
                  ? "bg-transparent border-neutral-800/60 opacity-50"
                  : "bg-black/30 border-neutral-800"
              }`}
            >
              <div className="flex items-center justify-between mb-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono tabular-nums text-neutral-500">P{i}</span>
                  <span className={`font-medium ${isSelected ? "text-white" : "text-neutral-400"}`}>
                    {PHASE_LABELS[i]}
                  </span>
                  {!isValid && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] text-neutral-500 border border-neutral-800">
                      <Lock className="h-2.5 w-2.5" /> Blocked
                    </span>
                  )}
                  {isSelected && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] text-indigo-300 border border-indigo-500/30 bg-indigo-500/10">
                      <CheckCircle2 className="h-2.5 w-2.5" /> AI pick
                    </span>
                  )}
                  {isCurrent && !isSelected && (
                    <span className="text-[11px] text-neutral-600">on road now</span>
                  )}
                </div>

                <div className="font-mono text-xs tabular-nums text-neutral-200">
                  {q.toFixed(3)}
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-150 ${isSelected ? "bg-indigo-400" : PHASE_BAR}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Metrics */}
      <div className="rounded-md bg-black/30 border border-neutral-800 p-2.5 flex items-center justify-between text-xs text-neutral-500">
        <span>
          Lead over runner-up: <span className="font-mono tabular-nums text-neutral-200">+{valueMargin.toFixed(3)}</span>
        </span>
        <span>
          {policy.is_exploring ? "Exploring randomly" : "Using best guess"}
        </span>
      </div>
    </div>
  );
}

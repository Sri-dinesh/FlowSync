"use client";

import { CheckCircle2 } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

export default function SafetyFSMPanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);

  const signal = currentFrame?.signal;
  const safety = currentFrame?.safety;

  if (!signal || !safety) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-xs text-neutral-500">
        Waiting for signal telemetry — run a simulation to see safety timing.
      </div>
    );
  }

  const isTransitioning = signal.fsm_state !== "IDLE" && signal.fsm_state !== "MIN_GREEN";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="text-sm font-medium text-white">
          Signal safety
        </h3>
        <span
          className={`rounded-full border px-2 py-0.5 text-[11px] font-medium font-mono ${
            isTransitioning
              ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
              : "border-neutral-700 bg-white/[0.03] text-neutral-300"
          }`}
        >
          {signal.fsm_state}
        </span>
      </div>

      {/* Clearance Timers Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* Min Green Elapsed */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-0.5">
          <span className="text-[11px] text-neutral-500">Green elapsed</span>
          <span className="text-base font-semibold font-mono tabular-nums text-white">
            {signal.green_elapsed_s.toFixed(1)}s
          </span>
          <span className="text-[11px] text-neutral-600">8.0s minimum</span>
        </div>

        {/* Min Green Remaining */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-0.5">
          <span className="text-[11px] text-neutral-500">Switch lock</span>
          <span
            className={`text-base font-semibold font-mono tabular-nums ${
              signal.min_green_remaining_s > 0 ? "text-amber-300" : "text-emerald-300"
            }`}
          >
            {signal.min_green_remaining_s > 0
              ? `${signal.min_green_remaining_s.toFixed(1)}s`
              : "Free"}
          </span>
          <span className="text-[11px] text-neutral-600">switch allowed when free</span>
        </div>

        {/* Yellow Clearance */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-0.5">
          <span className="text-[11px] text-neutral-500">Yellow left</span>
          <span
            className={`text-base font-semibold font-mono tabular-nums ${
              signal.fsm_state.includes("YELLOW") ? "text-amber-300" : "text-neutral-500"
            }`}
          >
            {signal.fsm_state.includes("YELLOW")
              ? `${signal.transition_remaining_s.toFixed(1)}s`
              : "—"}
          </span>
          <span className="text-[11px] text-neutral-600">3.0s standard</span>
        </div>

        {/* All-Red Clearance */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-0.5">
          <span className="text-[11px] text-neutral-500">All-red left</span>
          <span
            className={`text-base font-semibold font-mono tabular-nums ${
              signal.fsm_state.includes("RED") ? "text-amber-300" : "text-neutral-500"
            }`}
          >
            {signal.fsm_state.includes("RED")
              ? `${signal.transition_remaining_s.toFixed(1)}s`
              : "—"}
          </span>
          <span className="text-[11px] text-neutral-600">1.0s standard</span>
        </div>
      </div>

      {/* Safety counters */}
      <div className="grid grid-cols-3 gap-2 text-xs pt-3 border-t border-neutral-800">
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 text-center">
          <div className="text-[11px] text-neutral-500">Blocked switches</div>
          <div className="text-base font-semibold font-mono tabular-nums text-white mt-0.5">
            {safety.premature_switch_attempts}
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 text-center">
          <div className="text-[11px] text-neutral-500">Violations</div>
          <div className="text-base font-semibold font-mono tabular-nums text-emerald-300 mt-0.5 flex items-center justify-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> 0
          </div>
        </div>

        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 text-center">
          <div className="text-[11px] text-neutral-500">Shield</div>
          <div className="text-base font-semibold font-mono tabular-nums text-white mt-0.5">
            {safety.shield_override ? "On" : "Off"}
          </div>
        </div>
      </div>
    </div>
  );
}

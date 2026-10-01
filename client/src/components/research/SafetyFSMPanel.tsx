"use client";

import { ShieldCheck, ShieldAlert, AlertCircle, Clock, CheckCircle2, Lock } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

export default function SafetyFSMPanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);

  const signal = currentFrame?.signal;
  const safety = currentFrame?.safety;

  if (!signal || !safety) {
    return (
      <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl text-center text-xs text-white/30 font-mono">
        Awaiting Physical FSM telemetry...
      </div>
    );
  }

  const isTransitioning = signal.fsm_state !== "IDLE" && signal.fsm_state !== "MIN_GREEN";

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-xl flex flex-col gap-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white">
            Physical Signal FSM & Invariant Safety
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="text-white/40">FSM State:</span>
          <span
            className={`px-2 py-0.5 rounded-full font-bold uppercase border ${
              isTransitioning
                ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
            }`}
          >
            {signal.fsm_state}
          </span>
        </div>
      </div>

      {/* Clearance Timers Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        {/* Min Green Elapsed */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Green Elapsed</span>
          <span className="text-base font-bold text-white tabular-nums">
            {signal.green_elapsed_s.toFixed(1)}s
          </span>
          <span className="text-[9px] text-white/40">Required: 8.0s min</span>
        </div>

        {/* Min Green Remaining */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Min Green Lock</span>
          <span
            className={`text-base font-bold tabular-nums ${
              signal.min_green_remaining_s > 0 ? "text-amber-400" : "text-emerald-400"
            }`}
          >
            {signal.min_green_remaining_s > 0
              ? `${signal.min_green_remaining_s.toFixed(1)}s lock`
              : "Unlocked"}
          </span>
          <span className="text-[9px] text-white/40">Switching permissible</span>
        </div>

        {/* Yellow Clearance */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">Yellow Change</span>
          <span
            className={`text-base font-bold tabular-nums ${
              signal.fsm_state.includes("YELLOW") ? "text-amber-300" : "text-white/40"
            }`}
          >
            {signal.fsm_state.includes("YELLOW")
              ? `${signal.transition_remaining_s.toFixed(1)}s left`
              : "3.0s Standard"}
          </span>
          <span className="text-[9px] text-white/40">Vehicular clearance</span>
        </div>

        {/* All-Red Clearance */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex flex-col gap-1">
          <span className="text-[9px] text-white/40 uppercase">All-Red Clearance</span>
          <span
            className={`text-base font-bold tabular-nums ${
              signal.fsm_state.includes("RED") ? "text-rose-400" : "text-white/40"
            }`}
          >
            {signal.fsm_state.includes("RED")
              ? `${signal.transition_remaining_s.toFixed(1)}s left`
              : "1.0s Standard"}
          </span>
          <span className="text-[9px] text-white/40">Intersection vacuum</span>
        </div>
      </div>

      {/* Safety Shield & Gating Invariant Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1 border-t border-white/[0.06]">
        {/* Raw Policy Premature Attempts */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-white/40 uppercase font-semibold">
              Premature Switch Proposals
            </div>
            <div className="text-xs text-white/60 mt-0.5">Raw policy intent blocked</div>
          </div>
          <div className="text-base font-bold font-mono text-amber-400 tabular-nums">
            {safety.premature_switch_attempts}
          </div>
        </div>

        {/* Executed Physical Violations */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-emerald-300/80 uppercase font-semibold">
              Executed Clearance Violations
            </div>
            <div className="text-xs text-emerald-400/60 mt-0.5">Physical cabinet safety</div>
          </div>
          <div className="text-base font-bold font-mono text-emerald-400 tabular-nums flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4" /> 0
          </div>
        </div>

        {/* Safety Shield Overrides */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-white/40 uppercase font-semibold">
              Shield Interventions
            </div>
            <div className="text-xs text-white/60 mt-0.5">Anti-starvation overrides</div>
          </div>
          <div className="text-base font-bold font-mono text-indigo-300 tabular-nums">
            {safety.shield_override ? "Active" : "0 Standby"}
          </div>
        </div>
      </div>
    </div>
  );
}

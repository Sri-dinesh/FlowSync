"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

const PHASE_NAMES = [
  "Phase 0: NS Straight",
  "Phase 1: EW Straight",
  "Phase 2: NS Left-Turn",
  "Phase 3: EW Left-Turn",
];

const PHASE_SHORT = ["NS", "EW", "NS-L", "EW-L"];

export default function DecisionInspector() {
  const currentFrame = useResearchStore((s) => s.currentFrame);

  if (!currentFrame) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-xs text-neutral-500">
        Waiting for controller telemetry — run a simulation to see the decision pipeline.
      </div>
    );
  }

  const { policy, supervisor, safety, signal, uncertainty } = currentFrame;

  const isFallbackActive = supervisor.mode.toLowerCase().includes("fallback");
  const d3qnAction = policy.proposed_action;
  const fallbackAction = supervisor.fallback_action;
  const supervisorAction = isFallbackActive && fallbackAction !== null ? fallbackAction : d3qnAction;
  const shieldOverride = safety.shield_override;
  const fsmDeferred = safety.fsm_deferred;
  const executedPhase = signal.executed_phase;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3 text-white">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="text-sm font-medium text-white">
          Decision pipeline
        </h3>
        <span
          className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
            isFallbackActive
              ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
              : "border-neutral-700 bg-white/[0.03] text-neutral-300"
          }`}
        >
          {isFallbackActive ? "Fallback in control" : "Neural policy in control"}
        </span>
      </div>

      {/* Action Flow Pipeline */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
        {/* Step 1: D3QN Proposed */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] font-medium text-neutral-500">AI proposes</span>
          <div className="text-[13px] font-semibold text-white font-mono tabular-nums">
            {PHASE_SHORT[d3qnAction] ?? `P${d3qnAction}`}
          </div>
          <span className="text-[11px] text-neutral-500 truncate">
            {PHASE_NAMES[d3qnAction] ?? ""}
          </span>
        </div>

        {/* Step 2: Fallback Proposed */}
        <div className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col gap-1">
          <span className="text-[11px] font-medium text-neutral-500">Fallback proposes</span>
          <div className="text-[13px] font-semibold font-mono tabular-nums text-neutral-200">
            {fallbackAction !== null ? (PHASE_SHORT[fallbackAction] ?? `P${fallbackAction}`) : "—"}
          </div>
          <span className="text-[11px] text-neutral-500 truncate">
            {fallbackAction !== null ? (PHASE_NAMES[fallbackAction] ?? "") : "Standby"}
          </span>
        </div>

        {/* Step 3: Supervisor Selection */}
        <div
          className={`rounded-md border p-2.5 flex flex-col gap-1 ${
            isFallbackActive
              ? "border-amber-500/30 bg-amber-500/[0.07]"
              : "border-neutral-800 bg-black/30"
          }`}
        >
          <span className="text-[11px] font-medium text-neutral-500">Supervisor picks</span>
          <div className="text-[13px] font-semibold font-mono tabular-nums text-white">
            {PHASE_SHORT[supervisorAction] ?? `P${supervisorAction}`}
          </div>
          <span className="text-[11px] text-neutral-500 truncate">
            {isFallbackActive ? "Fallback chosen" : "AI approved"}
          </span>
        </div>

        {/* Step 4: Safety Shield */}
        <div
          className={`rounded-md border p-2.5 flex flex-col gap-1 ${
            shieldOverride
              ? "border-amber-500/30 bg-amber-500/[0.07]"
              : "border-neutral-800 bg-black/30"
          }`}
        >
          <span className="text-[11px] font-medium text-neutral-500">Safety check</span>
          <div className="text-[13px] font-semibold font-mono flex items-center gap-1 text-white">
            {shieldOverride ? (
              <>
                <ShieldAlert className="h-3 w-3 text-amber-400" /> Override
              </>
            ) : (
              <>
                <ShieldCheck className="h-3 w-3 text-emerald-400" /> Pass
              </>
            )}
          </div>
          <span className="text-[11px] text-neutral-500 truncate">
            {shieldOverride ? "Corrected action" : "Within limits"}
          </span>
        </div>

        {/* Step 5: Physical FSM */}
        <div
          className={`rounded-md border p-2.5 flex flex-col gap-1 ${
            fsmDeferred
              ? "border-amber-500/30 bg-amber-500/[0.07]"
              : "border-neutral-800 bg-black/30"
          }`}
        >
          <span className="text-[11px] font-medium text-neutral-500">Signal rules</span>
          <div className="text-[13px] font-semibold font-mono text-white">
            {fsmDeferred ? "Wait" : "Go"}
          </div>
          <span className="text-[11px] text-neutral-500 truncate">
            {fsmDeferred ? safety.reason : signal.fsm_state}
          </span>
        </div>

        {/* Step 6: Final Executed Phase */}
        <div className="rounded-md border border-emerald-500/30 bg-emerald-500/[0.07] p-2.5 flex flex-col gap-1">
          <span className="text-[11px] font-medium text-emerald-300/80">Executed</span>
          <div className="text-[13px] font-semibold font-mono tabular-nums text-emerald-300">
            {PHASE_SHORT[executedPhase] ?? `Phase ${executedPhase}`}
          </div>
          <span className="text-[11px] text-emerald-200/50 truncate">
            {signal.fsm_state}
          </span>
        </div>
      </div>

      {/* Decision Metadata Banner */}
      <div className="rounded-md bg-black/30 border border-neutral-800 p-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500">
        <span>
          Uncertainty <span className="font-mono tabular-nums text-neutral-200">𝒰 = {uncertainty.score.toFixed(3)}</span>
          <span className="text-neutral-600"> (fallback above {uncertainty.threshold_high.toFixed(2)})</span>
        </span>
        <span>
          Reason: <span className="text-neutral-300 capitalize">
            {supervisor?.reason ? String(supervisor.reason).replace(/_/g, " ") : "Nominal"}
          </span>
        </span>
        {supervisor.dwell_remaining_s > 0 && (
          <span className="text-amber-300/90">
            Cooldown {supervisor.dwell_remaining_s.toFixed(1)}s
          </span>
        )}
      </div>
    </div>
  );
}

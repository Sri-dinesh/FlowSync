"use client";

import { ArrowRight, ShieldAlert, ShieldCheck, Cpu, AlertCircle, Clock, Zap } from "lucide-react";
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
      <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl text-center text-xs text-white/30 font-mono">
        Awaiting live controller telemetry...
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
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-xl flex flex-col gap-4 text-white">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white">
            FlowSync-UQ Decision Pipeline
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="text-white/40">Authority:</span>
          <span
            className={`px-2 py-0.5 rounded-full font-bold uppercase ${
              isFallbackActive
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
            }`}
          >
            {isFallbackActive ? "Max-Pressure Fallback" : "D3QN Neural Policy"}
          </span>
        </div>
      </div>

      {/* Action Flow Pipeline */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-2 items-center">
        {/* Step 1: D3QN Proposed */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 flex flex-col gap-1.5">
          <span className="text-[9px] uppercase font-bold text-white/40">1. D3QN Proposed</span>
          <div className="text-xs font-bold text-indigo-300 font-mono">
            {PHASE_SHORT[d3qnAction] ?? `P${d3qnAction}`}
          </div>
          <span className="text-[10px] text-white/50 truncate">
            {PHASE_NAMES[d3qnAction] ?? ""}
          </span>
        </div>

        {/* Step 2: Fallback Proposed */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 flex flex-col gap-1.5">
          <span className="text-[9px] uppercase font-bold text-white/40">2. Fallback (MP)</span>
          <div className="text-xs font-bold font-mono text-cyan-300">
            {fallbackAction !== null ? (PHASE_SHORT[fallbackAction] ?? `P${fallbackAction}`) : "Standby"}
          </div>
          <span className="text-[10px] text-white/50 truncate">
            {fallbackAction !== null ? (PHASE_NAMES[fallbackAction] ?? "") : "Not invoked"}
          </span>
        </div>

        {/* Step 3: Supervisor Selection */}
        <div
          className={`rounded-xl border p-3 flex flex-col gap-1.5 ${
            isFallbackActive
              ? "bg-rose-500/10 border-rose-500/30"
              : "bg-emerald-500/10 border-emerald-500/30"
          }`}
        >
          <span className="text-[9px] uppercase font-bold text-white/40">3. Supervisor</span>
          <div className="text-xs font-bold font-mono text-white">
            {PHASE_SHORT[supervisorAction] ?? `P${supervisorAction}`}
          </div>
          <span className="text-[10px] text-white/60 truncate">
            {isFallbackActive ? "Triggered Fallback" : "Approved D3QN"}
          </span>
        </div>

        {/* Step 4: Safety Shield */}
        <div
          className={`rounded-xl border p-3 flex flex-col gap-1.5 ${
            shieldOverride
              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
              : "bg-white/[0.02] border-white/10 text-white"
          }`}
        >
          <span className="text-[9px] uppercase font-bold text-white/40">4. Safety Shield</span>
          <div className="text-xs font-bold font-mono flex items-center gap-1">
            {shieldOverride ? (
              <>
                <ShieldAlert className="h-3 w-3 text-amber-400" /> Override
              </>
            ) : (
              <>
                <ShieldCheck className="h-3 w-3 text-emerald-400" /> Passed
              </>
            )}
          </div>
          <span className="text-[10px] text-white/50 truncate">
            {shieldOverride ? "Anti-starvation" : "Invariant valid"}
          </span>
        </div>

        {/* Step 5: Physical FSM */}
        <div
          className={`rounded-xl border p-3 flex flex-col gap-1.5 ${
            fsmDeferred
              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
              : "bg-white/[0.02] border-white/10 text-white"
          }`}
        >
          <span className="text-[9px] uppercase font-bold text-white/40">5. Physical FSM</span>
          <div className="text-xs font-bold font-mono">
            {fsmDeferred ? "Deferred" : "Accepted"}
          </div>
          <span className="text-[10px] text-white/50 truncate">
            {fsmDeferred ? safety.reason : signal.fsm_state}
          </span>
        </div>

        {/* Step 6: Final Executed Phase */}
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex flex-col gap-1.5">
          <span className="text-[9px] uppercase font-bold text-emerald-400">6. Executed Phase</span>
          <div className="text-sm font-bold font-mono text-emerald-300">
            {PHASE_SHORT[executedPhase] ?? `Phase ${executedPhase}`}
          </div>
          <span className="text-[10px] text-emerald-200/60 truncate">
            {signal.fsm_state}
          </span>
        </div>
      </div>

      {/* Decision Metadata Banner */}
      <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-white/40">Uncertainty Status:</span>
          <span className="font-mono font-bold text-white">
            U(s) = {uncertainty.score.toFixed(3)}
          </span>
          <span className="text-white/30">|</span>
          <span className="text-white/40">Thresholds:</span>
          <span className="font-mono text-white/70">
            τ_high = {uncertainty.threshold_high.toFixed(2)}, τ_low = {uncertainty.threshold_low.toFixed(2)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-white/40">Supervisor Dwell Timer:</span>
          <span className="font-mono text-amber-300">
            {supervisor.dwell_remaining_s > 0 ? `${supervisor.dwell_remaining_s.toFixed(1)}s` : "Inactive"}
          </span>
          <span className="text-white/30">|</span>
          <span className="text-white/40">Reason:</span>
          <span className="font-mono text-white/80 capitalize">
            {supervisor?.reason ? String(supervisor.reason).replace(/_/g, " ") : "Nominal Execution"}
          </span>
        </div>
      </div>
    </div>
  );
}

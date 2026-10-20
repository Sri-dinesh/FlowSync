"use client";

import React, { memo, useState } from "react";
import dynamic from "next/dynamic";
import {
  Play,
  Pause,
  RotateCcw,
  Minus,
  ArrowDown,
  ArrowUp,
  Layers,
  Sparkles,
} from "lucide-react";
import { useResearchSocket } from "@/hooks/useResearchSocket";
import { useResearchStore } from "@/store/researchStore";
import type { PairedControllerState, ResearchTelemetryFrame, NoisePresetKey } from "@/types/research";

const ResearchCanvas = dynamic(
  () => import("@/components/research/ResearchCanvas").then((mod) => mod.ResearchCanvas),
  { ssr: false }
);

function toTelemetryFrame(
  ctrl: PairedControllerState | undefined,
  step: number,
  simTime: number
): ResearchTelemetryFrame | null {
  if (!ctrl) return null;
  return {
    step,
    sim_time: simTime,
    signal_phase: ctrl.phase,
    fsm: {
      current_state: ctrl.fsm_state,
      remaining_in_state_s: 0,
      min_green_remaining_s: 0,
      premature_switch_attempts: 0,
      executed_safety_violations: 0,
    },
    actions: {
      executed: ctrl.phase,
      proposed_d3qn: ctrl.phase,
      fallback: ctrl.phase,
      supervisor_selected: ctrl.phase,
      shield_validated: ctrl.phase,
    },
    metrics: {
      delay_mean_s: ctrl.mean_delay,
      delay_p95_s: ctrl.mean_delay * 1.35,
      queue_area_veh_s: ctrl.queue_area,
      throughput_total_veh: ctrl.throughput,
      service_rate_vph: ctrl.throughput * 12,
      starvation_count: 0,
      spillback_seconds: 0,
      queue_length_north: Math.round(ctrl.queue_area / 40),
      queue_length_south: Math.round(ctrl.queue_area / 45),
      queue_length_east: Math.round(ctrl.queue_area / 50),
      queue_length_west: Math.round(ctrl.queue_area / 42),
    },
    vehicles: ctrl.vehicles || [],
    uncertainty: {
      composite_u: ctrl.uncertainty ?? 0,
      tau_high: 0.65,
      tau_low: 0.50,
      cues: { entropy: 0, ensemble_variance: 0, track_loss: 0, occlusion_rate: 0 },
    },
    perception: {
      camera_health: ctrl.fallback_active ? "DEGRADED" : "HEALTHY",
      detected_count: ctrl.vehicles?.length ?? 0,
      ground_truth_count: ctrl.vehicles?.length ?? 0,
      missed_count: 0,
      false_positive_count: 0,
      occluded_count: 0,
      cv_latency_ms: 8.2,
      track_confidence_avg: ctrl.fallback_active ? 0.55 : 0.92,
      noise_type: "NONE",
      noise_intensity: 0,
      active_cues: [],
    },
  } as unknown as ResearchTelemetryFrame;
}

export const ControllerComparison = memo(function ControllerComparison() {
  const { isConnected, startPairedComparison, pause, resume, stop } = useResearchSocket();
  const pairedFrame = useResearchStore((s) => s.pairedFrame);
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const activeNoise = useResearchStore((s) => s.activeNoise);
  const runStatus = useResearchStore((s) => s.runStatus);

  const [controllerA, setControllerA] = useState("d3qn");
  const [controllerB, setControllerB] = useState("flowsync_uq");

  const ctrlA = pairedFrame?.controller_a;
  const ctrlB = pairedFrame?.controller_b;
  const deltas = pairedFrame?.deltas;
  const hasPairedData = !!pairedFrame;

  const isRunning = runStatus === "running";
  const isStarting = runStatus === "starting";
  const step = pairedFrame?.step ?? 0;
  const simTime = pairedFrame?.sim_time_s ?? 0;
  const traceHash = pairedFrame?.trace_hash ?? `crn_seed_${activeSeed}_${activeScenario?.id || "arterial"}`;

  const frameA = toTelemetryFrame(ctrlA, step, simTime);
  const frameB = toTelemetryFrame(ctrlB, step, simTime);

  const handleStartComparison = () => {
    const scId = activeScenario?.scenario_id || activeScenario?.id || "test_clean_balanced_01";
    // activeNoise.id is synced to backend FAULT_PRESETS keys by the compare page pills.
    const presetKey = (activeNoise?.id || "miss_30") as NoisePresetKey;
    startPairedComparison(scId, controllerA, controllerB, activeSeed, presetKey);
  };

  const handlePauseResume = () => {
    if (isRunning) {
      pause();
    } else {
      resume();
    }
  };

  const handleStop = () => {
    stop();
  };

  // Deltas evaluation: delay_delta = delay_b - delay_a
  const delayDelta = deltas?.delay_delta ?? 0;
  const queueDelta = deltas?.queue_area_delta ?? 0;
  const tpDelta = deltas?.throughput_delta ?? 0;

  // Scientific Integrity Logic:
  // If delay_b < delay_a by >0.2s: FlowSync-UQ wins
  // If delay_b > delay_a by >0.2s: Baseline D3QN wins
  // Else: Tie / Parity
  const flowSyncWinsDelay = delayDelta < -0.2;
  const baselineWinsDelay = delayDelta > 0.2;
  const isDelayTie = Math.abs(delayDelta) <= 0.2;

  return (
    <div className="flex flex-col gap-4">
      {/* Synchronized Shared Experiment Header */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-medium text-white">
              Paired comparison
            </h2>
            <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
              Identical traffic
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-neutral-500">
            <span>Scenario: <strong className="text-neutral-200 font-medium">{activeScenario?.scenario_id ?? activeScenario?.id}</strong></span>
            <span>Seed: <strong className="text-neutral-200 font-medium font-mono">{activeSeed}</strong></span>
            <span>Fault: <strong className="text-neutral-200 font-medium">{activeNoise.name}</strong></span>
            <span className="truncate max-w-[280px] font-mono">Trace: <strong className="text-neutral-300">{traceHash}</strong></span>
          </div>
          {/* Controller pickers */}
          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
            <label className="flex items-center gap-1.5 text-neutral-500">
              <span className="text-[11px]">Left (A)</span>
              <select
                value={controllerA}
                onChange={(e) => setControllerA(e.target.value)}
                disabled={isRunning || isStarting}
                className="rounded-md border border-neutral-800 bg-black/30 px-2 py-1 text-xs text-white focus:outline-none focus:border-neutral-600"
              >
                {["d3qn", "dqn", "flowsync_uq", "max_pressure", "greedy", "actuated", "fixed"].map((c) => (
                  <option key={c} value={c} className="bg-neutral-900">{c}</option>
                ))}
              </select>
            </label>
            <span className="text-neutral-600 text-[11px]">vs</span>
            <label className="flex items-center gap-1.5 text-neutral-500">
              <span className="text-[11px]">Right (B)</span>
              <select
                value={controllerB}
                onChange={(e) => setControllerB(e.target.value)}
                disabled={isRunning || isStarting}
                className="rounded-md border border-neutral-800 bg-black/30 px-2 py-1 text-xs text-white focus:outline-none focus:border-neutral-600"
              >
                {["flowsync_uq", "d3qn", "dqn", "max_pressure", "greedy", "actuated", "fixed"].map((c) => (
                  <option key={c} value={c} className="bg-neutral-900">{c}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* Global Lockstep Controls */}
        <div className="flex items-center gap-3">
          <div className="text-right pr-3 border-r border-neutral-800 hidden sm:block">
            <div className="text-[11px] text-neutral-500">Sim time</div>
            <div className="text-sm font-semibold font-mono text-white">{simTime.toFixed(1)}s <span className="text-neutral-500 font-normal">· {step} steps</span></div>
          </div>

          {!isRunning && runStatus !== "paused" ? (
            <div className="flex flex-col items-end gap-1.5">
              <button
                onClick={handleStartComparison}
                disabled={isStarting}
                title={
                  isConnected
                    ? "Start both controllers on identical traffic"
                    : "Backend offline — the paired run will queue and start on reconnect"
                }
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-800 disabled:text-neutral-500 text-white rounded-md text-xs font-medium transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                <span>{isStarting ? "Connecting…" : "Launch paired run"}</span>
              </button>
              {!isConnected && !isStarting && (
                <span className="text-[11px] text-amber-300/90">
                  Offline — run queues and starts on reconnect
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={handlePauseResume}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-transparent hover:bg-white/5 border border-neutral-700 text-neutral-300 rounded-md text-xs font-medium transition-colors"
              >
                {isRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                <span>{isRunning ? "Pause" : "Resume"}</span>
              </button>
              <button
                onClick={handleStop}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-transparent hover:bg-white/5 border border-neutral-700 text-neutral-300 hover:text-white rounded-md text-xs font-medium transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Stop</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Result deltas — neutral cards, color only on values */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Mean Delay Delta */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-medium text-neutral-500">
              Delay delta · {controllerB} vs {controllerA}
            </div>
            <div className="text-xl font-semibold font-mono tabular-nums flex items-center gap-2 mt-1 text-white">
              <span>{delayDelta > 0 ? `+${delayDelta.toFixed(2)}s` : `${delayDelta.toFixed(2)}s`}</span>
              {flowSyncWinsDelay && <span className="text-[11px] font-medium text-emerald-300">B leads</span>}
              {baselineWinsDelay && <span className="text-[11px] font-medium text-red-300">A leads</span>}
              {isDelayTie && <span className="text-[11px] font-medium text-neutral-400">Tie</span>}
            </div>
          </div>
          {flowSyncWinsDelay ? (
            <ArrowDown className="w-4 h-4 text-emerald-400" />
          ) : baselineWinsDelay ? (
            <ArrowUp className="w-4 h-4 text-red-400" />
          ) : (
            <Minus className="w-4 h-4 text-neutral-500" />
          )}
        </div>

        {/* Queue Area Delta */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-medium text-neutral-500">
              Queue area delta
            </div>
            <div className="text-xl font-semibold font-mono tabular-nums flex items-center gap-2 mt-1 text-white">
              <span>{queueDelta > 0 ? `+${queueDelta.toFixed(1)}` : queueDelta.toFixed(1)}</span>
              <span className="text-[11px] font-normal text-neutral-500">veh·s</span>
            </div>
          </div>
          <Layers className="w-4 h-4 text-neutral-500" />
        </div>

        {/* Throughput Delta */}
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-medium text-neutral-500">
              Throughput delta
            </div>
            <div className="text-xl font-semibold font-mono tabular-nums flex items-center gap-2 mt-1 text-white">
              <span>{tpDelta > 0 ? `+${tpDelta}` : `${tpDelta}`}</span>
              <span className="text-[11px] font-normal text-neutral-500">vehicles</span>
            </div>
          </div>
          <Sparkles className="w-4 h-4 text-neutral-500" />
        </div>
      </div>

      {/* Side-by-side 3D views */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Controller A */}
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
            <div>
              <div className="text-[11px] text-neutral-500">Controller A</div>
              <h3 className="text-sm font-medium text-white font-mono">
                {ctrlA?.name ?? controllerA}
              </h3>
            </div>
            <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
              Baseline
            </span>
          </div>

          <div className="h-[420px] rounded-md overflow-hidden relative">
            <ResearchCanvas frameOverride={frameA} label="D3QN Baseline" quality="performance" />
            {!hasPairedData && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/55 p-6 pointer-events-none">
                <p className="text-xs text-white/70 text-center max-w-xs leading-relaxed bg-neutral-900 border border-neutral-800 rounded-md px-4 py-3">
                  Left view shows <span className="font-mono text-white">{controllerA}</span> once you press{" "}
                  <span className="font-semibold text-white">Launch Paired Run</span>.
                </p>
              </div>
            )}
          </div>

          {/* Controller A telemetry */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Mean delay</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlA?.mean_delay !== undefined ? `${ctrlA.mean_delay.toFixed(1)}s` : "-"}
              </div>
            </div>
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Queue area</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlA?.queue_area !== undefined ? ctrlA.queue_area.toFixed(0) : "-"}
              </div>
            </div>
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Throughput</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlA?.throughput !== undefined ? `${ctrlA.throughput}` : "-"}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Controller B */}
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
            <div>
              <div className="text-[11px] text-neutral-500">Controller B</div>
              <h3 className="text-sm font-medium text-white font-mono">
                {ctrlB?.name ?? controllerB}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {ctrlB?.fallback_active ? (
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
                  Fallback active
                </span>
              ) : (
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
                  Nominal
                </span>
              )}
            </div>
          </div>

          <div className="h-[420px] rounded-md overflow-hidden relative">
            <ResearchCanvas frameOverride={frameB} label="FlowSync-UQ (Ours)" quality="performance" />
            {!hasPairedData && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/55 p-6 pointer-events-none">
                <p className="text-xs text-white/70 text-center max-w-xs leading-relaxed bg-neutral-900 border border-neutral-800 rounded-md px-4 py-3">
                  Right view shows <span className="font-mono text-white">{controllerB}</span> once you press{" "}
                  <span className="font-semibold text-white">Launch Paired Run</span>.
                </p>
              </div>
            )}
          </div>

          {/* Controller B telemetry */}
          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Mean delay</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlB?.mean_delay !== undefined ? `${ctrlB.mean_delay.toFixed(1)}s` : "-"}
              </div>
            </div>
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Queue area</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlB?.queue_area !== undefined ? ctrlB.queue_area.toFixed(0) : "-"}
              </div>
            </div>
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Throughput</div>
              <div className="text-base font-semibold font-mono tabular-nums text-white mt-1">
                {ctrlB?.throughput !== undefined ? `${ctrlB.throughput}` : "-"}
              </div>
            </div>
            <div className="bg-black/30 border border-neutral-800 rounded-md p-3">
              <div className="text-[11px] text-neutral-500">Uncertainty</div>
              <div
                className={`text-base font-semibold font-mono tabular-nums mt-1 ${
                  (ctrlB?.uncertainty ?? 0) >= 0.65 ? "text-red-300" : "text-neutral-200"
                }`}
              >
                {ctrlB?.uncertainty !== undefined ? ctrlB.uncertainty.toFixed(2) : "0.00"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

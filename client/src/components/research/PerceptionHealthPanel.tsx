"use client";

import React, { memo } from "react";
import { Eye, ShieldAlert, Video, Camera, Activity, CheckCircle2, AlertTriangle } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

export const PerceptionHealthPanel = memo(function PerceptionHealthPanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const showPerceptionDebug = useResearchStore((s) => s.showPerceptionDebug);
  const togglePerceptionDebug = useResearchStore((s) => s.togglePerceptionDebug);

  const perception = currentFrame?.perception;
  const isHealthy = perception?.camera_health === "HEALTHY";
  const isDegraded = perception?.camera_health === "DEGRADED";
  const isOccluded = perception?.camera_health === "OCCLUDED";
  const isOffline = perception?.camera_health === "OFFLINE";

  const detected = perception?.detected_count ?? 0;
  const groundTruth = perception?.ground_truth_count ?? detected;
  const missed = perception?.missed_count ?? 0;
  const falsePositives = perception?.false_positive_count ?? 0;
  const occluded = perception?.occluded_count ?? 0;
  const cvLatency = perception?.cv_latency_ms ?? 0;
  const trackConfidence = perception?.track_confidence_avg ?? 1.0;

  return (
    <div className="bg-[#12151c]/90 border border-white/10 rounded-xl p-4 shadow-xl backdrop-blur-md flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Camera className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Perception & Sensor Health
          </span>
        </div>
        <button
          onClick={togglePerceptionDebug}
          className={`px-2.5 py-1 rounded text-[10px] font-semibold tracking-wide border transition-all ${
            showPerceptionDebug
              ? "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm shadow-amber-500/10"
              : "bg-white/5 text-slate-400 border-white/10 hover:text-white"
          }`}
          title="Toggle oracle debug overlay (Detected vs Ground-truth ghosts)"
        >
          {showPerceptionDebug ? "Oracle Overlay: ON" : "Oracle Overlay: OFF"}
        </button>
      </div>

      {/* Sensor Status Indicator */}
      <div className="grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2.5 bg-black/40 border border-white/5 rounded-lg p-2.5">
          <div
            className={`w-3 h-3 rounded-full flex items-center justify-center animate-pulse ${
              isHealthy
                ? "bg-emerald-500/20 text-emerald-400"
                : isDegraded
                ? "bg-amber-500/20 text-amber-400"
                : "bg-rose-500/20 text-rose-400"
            }`}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                isHealthy ? "bg-emerald-400" : isDegraded ? "bg-amber-400" : "bg-rose-400"
              }`}
            />
          </div>
          <div>
            <div className="text-[10px] uppercase font-mono text-slate-400">Stream Status</div>
            <div
              className={`text-xs font-bold font-mono ${
                isHealthy ? "text-emerald-400" : isDegraded ? "text-amber-400" : "text-rose-400"
              }`}
            >
              {perception?.camera_health ?? "ONLINE (NOMINAL)"}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 bg-black/40 border border-white/5 rounded-lg p-2.5">
          <Activity className="w-3.5 h-3.5 text-sky-400" />
          <div>
            <div className="text-[10px] uppercase font-mono text-slate-400">Vision Latency</div>
            <div className="text-xs font-bold font-mono text-slate-200">
              {cvLatency > 0 ? `${cvLatency.toFixed(1)} ms` : "< 8.5 ms"}
            </div>
          </div>
        </div>
      </div>

      {/* Detection Counts vs Oracle Truth */}
      <div className="bg-black/30 rounded-lg p-3 border border-white/5">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
          <span>Observed Vehicles (Policy Input):</span>
          <span className="text-emerald-400 font-bold text-xs">{detected}</span>
        </div>

        {showPerceptionDebug ? (
          <div className="space-y-1.5 pt-2 border-t border-white/10 font-mono text-[10px]">
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-slate-400" />
                Ground Truth Total:
              </span>
              <span className="text-slate-200 font-bold">{groundTruth}</span>
            </div>
            <div className="flex items-center justify-between text-rose-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500/80" />
                Missed Detections (Red):
              </span>
              <span className="font-bold">{missed}</span>
            </div>
            <div className="flex items-center justify-between text-amber-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400/80" />
                False Positives (Yellow):
              </span>
              <span className="font-bold">{falsePositives}</span>
            </div>
            <div className="flex items-center justify-between text-indigo-300">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-400/80" />
                Occluded / Border (Blue):
              </span>
              <span className="font-bold">{occluded}</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 pt-2 border-t border-white/5 text-[10px] text-slate-500">
            <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
            <span>Enable Oracle Overlay above to inspect missed/false tracks.</span>
          </div>
        )}
      </div>

      {/* Multi-cue Perception Quality Breakdown */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono">
          <span className="text-slate-400">Mean Track Confidence:</span>
          <span
            className={`font-bold ${
              trackConfidence >= 0.8
                ? "text-emerald-400"
                : trackConfidence >= 0.6
                ? "text-amber-400"
                : "text-rose-400"
            }`}
          >
            {(trackConfidence * 100).toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              trackConfidence >= 0.8
                ? "bg-emerald-500"
                : trackConfidence >= 0.6
                ? "bg-amber-500"
                : "bg-rose-500"
            }`}
            style={{ width: `${Math.min(100, Math.max(0, trackConfidence * 100))}%` }}
          />
        </div>
      </div>
    </div>
  );
});

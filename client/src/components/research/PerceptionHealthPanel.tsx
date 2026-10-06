"use client";

import React, { memo } from "react";
import { ShieldAlert } from "lucide-react";
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

  const healthTone = isHealthy
    ? "border-neutral-700 bg-white/[0.03] text-neutral-300"
    : isDegraded
      ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
      : "border-red-500/30 bg-red-500/10 text-red-300";

  const healthDot = isHealthy ? "bg-emerald-400" : isDegraded ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
        <h3 className="text-sm font-medium text-white">
          Cameras
        </h3>
        <button
          onClick={() => togglePerceptionDebug()}
          className={`rounded-md px-2.5 py-1 text-[11px] font-medium border transition-colors ${
            showPerceptionDebug
              ? "bg-white/10 text-white border-white/20"
              : "bg-transparent text-neutral-500 border-neutral-800 hover:text-white hover:border-neutral-700"
          }`}
          title="Show missed vs detected vehicles in the 3D view"
        >
          Overlay {showPerceptionDebug ? "on" : "off"}
        </button>
      </div>

      {/* Sensor Status Indicator */}
      <div className="grid grid-cols-2 gap-2">
        <div className={`flex items-center gap-2.5 rounded-md border p-2.5 ${healthTone}`}>
          <span className={`h-2 w-2 rounded-full ${healthDot} ${!isOffline ? "animate-pulse" : ""}`} />
          <div>
            <div className="text-[11px] text-neutral-500">Cameras</div>
            <div className="text-xs font-medium">
              {isHealthy ? "Healthy" : isDegraded ? "Degraded" : isOccluded ? "Occluded" : isOffline ? "Offline" : (perception?.camera_health ?? "Healthy")}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 bg-black/30 border border-neutral-800 rounded-md p-2.5">
          <div>
            <div className="text-[11px] text-neutral-500">Vision latency</div>
            <div className="text-xs font-medium font-mono tabular-nums text-neutral-200">
              {cvLatency > 0 ? `${cvLatency.toFixed(1)} ms` : "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Detection Counts vs Oracle Truth */}
      <div className="bg-black/30 rounded-md p-3 border border-neutral-800">
        <div className="flex items-center justify-between text-xs text-neutral-400">
          <span>Cars the AI sees</span>
          <span className="text-sm font-semibold font-mono tabular-nums text-white">{detected}</span>
        </div>

        {showPerceptionDebug ? (
          <div className="space-y-1.5 pt-2 mt-2 border-t border-neutral-800 font-mono text-[11px] tabular-nums">
            <div className="flex items-center justify-between text-neutral-400">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-neutral-400" />
                Actually on road
              </span>
              <span className="text-neutral-200 font-medium">{groundTruth}</span>
            </div>
            <div className="flex items-center justify-between text-neutral-400">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
                Missed by cameras
              </span>
              <span className="font-medium text-red-300">{missed}</span>
            </div>
            <div className="flex items-center justify-between text-neutral-400">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                Ghost detections
              </span>
              <span className="font-medium text-amber-300">{falsePositives}</span>
            </div>
            <div className="flex items-center justify-between text-neutral-400">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                Occluded
              </span>
              <span className="font-medium text-indigo-300">{occluded}</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 pt-2 mt-2 border-t border-neutral-800 text-[11px] text-neutral-500">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Turn the overlay on to compare against ground truth.</span>
          </div>
        )}
      </div>

      {/* Track confidence */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-neutral-500">Track confidence</span>
          <span className="font-mono tabular-nums font-medium text-neutral-200">
            {(trackConfidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1 overflow-hidden">
          <div
            className="h-full rounded-full bg-neutral-300 transition-all duration-300"
            style={{ width: `${Math.min(100, Math.max(0, trackConfidence * 100))}%` }}
          />
        </div>
      </div>
    </div>
  );
});

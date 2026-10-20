"use client";

import { Copy, Pause, Play, RotateCcw, Eye, Monitor, FileText, Check } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useResearchStore } from "@/store/researchStore";
import { useResearchSocket } from "@/hooks/useResearchSocket";

interface Props {
  onOpenProvenance?: () => void;
}

export default function ResearchRunHeader({ onOpenProvenance }: Props) {
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeController = useResearchStore((s) => s.activeController);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const activeNoisePreset = useResearchStore((s) => s.activeNoisePreset);
  const runStatus = useResearchStore((s) => s.runStatus);
  const debugOverlay = useResearchStore((s) => s.debugOverlay);
  const presentationMode = useResearchStore((s) => s.presentationMode);
  const toggleDebugOverlay = useResearchStore((s) => s.toggleDebugOverlay);
  const togglePresentationMode = useResearchStore((s) => s.togglePresentationMode);

  const { pause, resume, stop } = useResearchSocket();
  const [copied, setCopied] = useState(false);

  const ctrlKey =
    typeof activeController === "object" && activeController !== null
      ? activeController.id || "flowsync_uq"
      : activeController || "flowsync_uq";
  const experimentId =
    currentFrame?.experiment_id ||
    `exp_${activeScenario?.scenario_id || "test"}_${ctrlKey}_s${activeSeed}`;
  const totalSteps = activeScenario?.duration_steps || 1200;
  const currentStep = currentFrame?.step ?? 0;
  const progressPct = Math.min(100, (currentStep / totalSteps) * 100);

  const handleCopyId = () => {
    navigator.clipboard.writeText(experimentId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const statusTone =
    runStatus === "running"
      ? "bg-emerald-400 animate-pulse"
      : runStatus === "paused"
        ? "bg-amber-400"
        : runStatus === "completed"
          ? "bg-indigo-400"
          : runStatus === "error"
            ? "bg-red-400"
            : "bg-neutral-600";

  const statusLabel =
    runStatus === "idle" ? "Idle — no run yet" : runStatus.charAt(0).toUpperCase() + runStatus.slice(1);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-4 py-3 flex flex-col gap-2.5 text-white">
      {/* Top row: run identity + actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: status + run config */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="inline-flex items-center gap-1.5 font-medium text-white">
            <span className={`h-1.5 w-1.5 rounded-full ${statusTone}`} />
            {statusLabel}
          </span>
          <span className="text-neutral-700">|</span>
          <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-300">
            {String(typeof activeController === "object" ? activeController?.name || activeController?.id : activeController || "flowsync-uq").replace(/_/g, "-")}
          </span>
          {activeScenario && (
            <span className="font-mono text-[11px] text-neutral-500">
              {activeScenario.scenario_id} · seed {activeSeed} · {activeNoisePreset === "clean" ? "clean cameras" : activeNoisePreset}
            </span>
          )}
          <button
            onClick={handleCopyId}
            title={`Copy run ID: ${experimentId}`}
            className="text-neutral-600 hover:text-white transition-colors"
          >
            {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          </button>
        </div>

        {/* Right: view toggles + run controls */}
        <div className="flex items-center gap-1.5">
          {/* Debug Overlay Toggle */}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => toggleDebugOverlay()}
            className={`text-xs h-7 gap-1.5 border ${
              debugOverlay
                ? "bg-white/10 border-white/20 text-white"
                : "border-transparent text-neutral-500 hover:text-white hover:bg-white/5"
            }`}
            title="Toggle perception debug overlay (detected vs missed vehicles)"
          >
            <Eye className="h-3.5 w-3.5" />
            <span className="hidden lg:inline">Debug</span>
          </Button>

          {/* Presentation Mode Toggle */}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => togglePresentationMode()}
            className={`text-xs h-7 gap-1.5 border ${
              presentationMode
                ? "bg-white/10 border-white/20 text-white"
                : "border-transparent text-neutral-500 hover:text-white hover:bg-white/5"
            }`}
            title="Toggle high-contrast presentation mode"
          >
            <Monitor className="h-3.5 w-3.5" />
            <span className="hidden lg:inline">Present</span>
          </Button>

          {/* Provenance Drawer Trigger */}
          {onOpenProvenance && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onOpenProvenance}
              className="text-xs h-7 gap-1.5 border border-transparent text-neutral-500 hover:text-white hover:bg-white/5"
            >
              <FileText className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">Provenance</span>
            </Button>
          )}

          {/* Pause / Resume Controls */}
          {runStatus === "running" && (
            <Button
              size="sm"
              variant="outline"
              onClick={pause}
              className="text-xs h-7 gap-1.5 border-neutral-700 text-neutral-300 hover:bg-white/5"
            >
              <Pause className="h-3.5 w-3.5" /> Pause
            </Button>
          )}

          {runStatus === "paused" && (
            <Button
              size="sm"
              onClick={resume}
              className="text-xs h-7 gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              <Play className="h-3.5 w-3.5 fill-current" /> Resume
            </Button>
          )}

          {(runStatus === "running" || runStatus === "paused" || runStatus === "starting") && (
            <Button
              size="sm"
              variant="ghost"
              onClick={stop}
              className="text-xs h-7 gap-1.5 text-neutral-500 hover:text-white hover:bg-white/5"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Stop
            </Button>
          )}
        </div>
      </div>

      {/* Bottom row: time progress */}
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-mono tabular-nums text-neutral-500 whitespace-nowrap">
          {(currentStep * 0.1).toFixed(1)}s / {(totalSteps * 0.1).toFixed(1)}s
        </span>

        {/* Progress bar */}
        <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full rounded-full bg-indigo-500 transition-all duration-150"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-[11px] font-mono tabular-nums text-neutral-500">{progressPct.toFixed(0)}%</span>
      </div>
    </div>
  );
}

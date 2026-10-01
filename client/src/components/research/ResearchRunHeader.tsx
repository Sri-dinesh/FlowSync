"use client";

import { Copy, Pause, Play, RotateCcw, Eye, Monitor, FileText, Check, ShieldCheck } from "lucide-react";
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

  const experimentId = currentFrame?.experiment_id || `exp_${activeScenario?.scenario_id || "test"}_${activeController}_s${activeSeed}`;
  const totalSteps = activeScenario?.duration_steps || 1200;
  const currentStep = currentFrame?.step ?? 0;
  const progressPct = Math.min(100, (currentStep / totalSteps) * 100);

  const handleCopyId = () => {
    navigator.clipboard.writeText(experimentId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-4 backdrop-blur-xl shadow-xl flex flex-col gap-3 text-white">
      {/* Top row: ID, Badges, Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Experiment ID & controller badge */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono">
            <span className="text-white/40">ID:</span>
            <span className="text-indigo-300 font-medium truncate max-w-[200px]">{experimentId}</span>
            <button
              onClick={handleCopyId}
              title="Copy Experiment ID"
              className="text-white/40 hover:text-white transition-colors"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            </button>
          </div>

          <div className="px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-xs font-bold uppercase tracking-wider">
            {String(typeof activeController === "object" ? activeController?.name || activeController?.id : activeController || "flowsync-uq").replace(/_/g, "-")}
          </div>

          {activeScenario && (
            <div className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-white/70">
              {activeScenario.scenario_id} ({activeScenario.split})
            </div>
          )}

          <div className="px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-white/60">
            Seed {activeSeed}
          </div>

          <div
            className={`px-2 py-1 rounded-lg text-xs font-mono border ${
              activeNoisePreset === "clean"
                ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-300"
                : "bg-amber-500/10 border-amber-500/25 text-amber-300"
            }`}
          >
            Noise: {activeNoisePreset}
          </div>
        </div>

        {/* Right: Controls & Mode Toggles */}
        <div className="flex items-center gap-2">
          {/* Debug Overlay Toggle */}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => toggleDebugOverlay()}
            className={`text-xs h-8 gap-1.5 border ${
              debugOverlay
                ? "bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25"
                : "border-white/10 text-white/60 hover:text-white"
            }`}
            title="Toggle Oracle Perception Debug Overlay (Detected vs Ghost Vehicles)"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>Perception Debug</span>
          </Button>

          {/* Presentation Mode Toggle */}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => togglePresentationMode()}
            className={`text-xs h-8 gap-1.5 border ${
              presentationMode
                ? "bg-indigo-500/15 border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/25"
                : "border-white/10 text-white/60 hover:text-white"
            }`}
            title="Toggle High-Contrast Academic Presentation Mode"
          >
            <Monitor className="h-3.5 w-3.5" />
            <span>Presentation</span>
          </Button>

          {/* Provenance Drawer Trigger */}
          {onOpenProvenance && (
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenProvenance}
              className="text-xs h-8 gap-1.5 border-white/10 text-white/70 hover:text-white"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Provenance</span>
            </Button>
          )}

          {/* Pause / Resume Controls */}
          {runStatus === "running" && (
            <Button
              size="sm"
              variant="outline"
              onClick={pause}
              className="text-xs h-8 gap-1.5 border-white/10 text-white hover:bg-white/10"
            >
              <Pause className="h-3.5 w-3.5" /> Pause
            </Button>
          )}

          {runStatus === "paused" && (
            <Button
              size="sm"
              onClick={resume}
              className="text-xs h-8 gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              <Play className="h-3.5 w-3.5 fill-current" /> Resume
            </Button>
          )}

          {(runStatus === "running" || runStatus === "paused") && (
            <Button
              size="sm"
              variant="destructive"
              onClick={stop}
              className="text-xs h-8 gap-1.5"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Stop
            </Button>
          )}
        </div>
      </div>

      {/* Bottom row: Time Progress bar */}
      <div className="flex items-center gap-3 pt-1">
        <div className="flex items-center gap-2 text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              runStatus === "running"
                ? "bg-emerald-400 animate-pulse"
                : runStatus === "paused"
                ? "bg-amber-400"
                : runStatus === "completed"
                ? "bg-indigo-400"
                : "bg-neutral-600"
            }`}
          />
          <span className="font-bold text-white uppercase">{runStatus}</span>
          <span className="text-white/40">|</span>
          <span className="text-white/70">
            t = {(currentStep * 0.1).toFixed(1)}s / {(totalSteps * 0.1).toFixed(1)}s
          </span>
          <span className="text-white/40">({currentStep} / {totalSteps} steps)</span>
        </div>

        {/* Progress bar */}
        <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full rounded-full bg-indigo-500 transition-all duration-150"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-white/40">{progressPct.toFixed(0)}%</span>
      </div>
    </div>
  );
}

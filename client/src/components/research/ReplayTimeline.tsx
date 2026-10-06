"use client";

import React, { memo, useEffect, useMemo } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Flame,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import { useResearchStore } from "@/store/researchStore";
import { useResearchSocket } from "@/hooks/useResearchSocket";

interface ReplayTimelineProps {
  totalSteps?: number;
  currentStep?: number;
  onSeek?: (step: number) => void;
}

export const ReplayTimeline = memo(function ReplayTimeline({
  totalSteps = 0,
  currentStep = 0,
  onSeek,
}: ReplayTimelineProps) {
  const replayState = useResearchStore((s) => s.replayState);
  const setReplayState = useResearchStore((s) => s.setReplayState);
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const history = useResearchStore((s) => s.history);
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const runStatus = useResearchStore((s) => s.runStatus);
  const { sendCommand } = useResearchSocket();

  const isPlaying = replayState.isPlaying;
  const speed = replayState.speed;
  // Prefer live frame position; fall back to explicit props, then replay state.
  const liveStep = currentFrame?.step ?? 0;
  const step = currentStep || replayState.currentStep || liveStep;
  const scenarioSteps = activeScenario?.duration_steps ?? 0;
  const maxSteps = Math.max(totalSteps, replayState.totalSteps, scenarioSteps, liveStep + 1, 1);

  // Keep the scrubber in sync as new frames stream in (without fighting manual seeks).
  useEffect(() => {
    if (currentFrame && currentFrame.step > useResearchStore.getState().replayState.currentStep) {
      setReplayState({
        currentStep: currentFrame.step,
        totalSteps: Math.max(useResearchStore.getState().replayState.totalSteps, currentFrame.step + 1),
      });
    }
  }, [currentFrame, setReplayState]);

  // Derive real event markers from streamed history instead of hardcoded guesses.
  const eventSteps = useMemo(() => {
    let fallback = -1;
    let peakU = -1;
    let peakQueue = -1;
    let maxU = -Infinity;
    let maxQ = -Infinity;
    for (const f of history) {
      const u = f.uncertainty?.score ?? 0;
      if (u > maxU) { maxU = u; peakU = f.step; }
      const q = f.metrics?.max_queue ?? 0;
      if (q > maxQ) { maxQ = q; peakQueue = f.step; }
      if (fallback < 0 && u >= (f.uncertainty?.threshold_high ?? 0.65)) fallback = f.step;
    }
    return {
      fallback: fallback >= 0 ? fallback : Math.round(maxSteps * 0.2),
      peakU: peakU >= 0 ? peakU : Math.round(maxSteps * 0.35),
      peakQueue: peakQueue >= 0 ? peakQueue : Math.round(maxSteps * 0.65),
      hasRealData: history.length > 0,
    };
  }, [history, maxSteps]);

  const hasFrames = !!currentFrame || history.length > 0;

  const handlePlayPause = () => {
    if (!hasFrames && runStatus !== "paused") return;
    const nextPlaying = !isPlaying;
    setReplayState({ isPlaying: nextPlaying });
    if (nextPlaying) {
      sendCommand({ command: "resume" });
    } else {
      sendCommand({ command: "pause" });
    }
  };

  const handleSpeedChange = (newSpeed: number) => {
    setReplayState({ speed: newSpeed });
    sendCommand({ command: "set_speed", speed: newSpeed });
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetStep = parseInt(e.target.value, 10);
    setReplayState({ currentStep: targetStep });
    if (onSeek) onSeek(targetStep);
    // Live runs ignore seeks server-side; replays jump to the stored frame.
    sendCommand({ command: "seek", step: targetStep });
  };

  // Quick Event Jump Markers
  const jumpTo = (targetStep: number) => {
    const clamped = Math.max(0, Math.min(maxSteps - 1, targetStep));
    setReplayState({ currentStep: clamped });
    if (onSeek) onSeek(clamped);
    sendCommand({ command: "seek", step: clamped });
  };

  const progressPercent = Math.min(100, Math.max(0, (step / maxSteps) * 100));

  return (
    <div className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4">
      {/* Top Header: Step & Time display */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
            Replay
          </span>
          <span className="text-xs text-neutral-400">
            Step <strong className="text-white font-mono tabular-nums">{step}</strong> of <span className="font-mono tabular-nums">{maxSteps}</span> <span className="text-neutral-500">({(step * 0.1).toFixed(1)}s)</span>
          </span>
        </div>

        {/* Playback speed buttons */}
        <div className="flex items-center gap-0.5 bg-black/30 border border-neutral-800 rounded-md p-0.5">
          {[0.25, 0.5, 1.0, 2.0].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono tabular-nums transition-colors ${
                speed === s
                  ? "bg-white/10 text-white"
                  : "text-neutral-500 hover:text-white"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Scrub Bar with Event Marker Pins */}
      <div className="relative flex flex-col gap-1.5">
        <div className="relative w-full h-2 bg-black/60 rounded-full border border-neutral-800 overflow-hidden cursor-pointer">
          {/* Progress fill */}
          <div
            className="h-full bg-indigo-500 transition-all duration-75"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Invisible native range input for precision dragging */}
        <input
          type="range"
          min={0}
          max={maxSteps}
          value={step}
          onChange={handleSliderChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />

        {/* Timeline Event Markers Display */}
        <div className="flex items-center justify-between text-[11px] font-mono tabular-nums text-neutral-500 pt-1">
          <span>0.0s</span>
          <span className="flex items-center gap-1" title={eventSteps.hasRealData ? `First threshold crossing at step ${eventSteps.fallback}` : "Estimate — markers become exact once frames stream"}>
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            Fallback @ {(eventSteps.fallback * 0.1).toFixed(0)}s
          </span>
          <span className="flex items-center gap-1" title={eventSteps.hasRealData ? `Peak uncertainty at step ${eventSteps.peakU}` : "Estimate — markers become exact once frames stream"}>
            <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
            Peak 𝒰 @ {(eventSteps.peakU * 0.1).toFixed(0)}s
          </span>
          <span>{(maxSteps * 0.1).toFixed(0)}s</span>
        </div>
      </div>

      {/* Controls & Quick Event Jump Navigation */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-neutral-800">
        {/* Play / Pause / Seek Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => jumpTo(Math.max(0, step - 10))}
            className="p-2 rounded-md hover:bg-white/5 text-neutral-500 hover:text-white transition-colors"
            title="Step Back 10 steps (1s)"
          >
            <Rewind className="w-4 h-4" />
          </button>
          <button
            onClick={handlePlayPause}
            disabled={!hasFrames && runStatus !== "paused"}
            title={hasFrames ? "Play / pause the stream" : "Select a run first — nothing to play yet"}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-800 disabled:text-neutral-500 text-white rounded-md text-xs font-medium transition-colors"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-white" />}
            <span>{isPlaying ? "Pause" : "Play"}</span>
          </button>
          <button
            onClick={() => jumpTo(Math.min(maxSteps, step + 10))}
            className="p-2 rounded-md hover:bg-white/5 text-neutral-500 hover:text-white transition-colors"
            title="Step Forward 10 steps (1s)"
          >
            <FastForward className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => jumpTo(0)}
            className="p-2 rounded-md hover:bg-white/5 text-neutral-500 hover:text-white transition-colors ml-1"
            title="Reset to Beginning"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Critical Event Jump Buttons */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-neutral-600 hidden md:inline">
            Jump to
          </span>
          <button
            onClick={() => jumpTo(eventSteps.fallback)}
            className="flex items-center gap-1 px-2.5 py-1.5 hover:bg-white/5 text-neutral-400 hover:text-white border border-neutral-800 rounded-md text-xs transition-colors"
            title={`Jump to fallback trigger (step ${eventSteps.fallback})`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Fallback</span>
          </button>
          <button
            onClick={() => jumpTo(eventSteps.peakU)}
            className="flex items-center gap-1 px-2.5 py-1.5 hover:bg-white/5 text-neutral-400 hover:text-white border border-neutral-800 rounded-md text-xs transition-colors"
            title={`Jump to peak uncertainty (step ${eventSteps.peakU})`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>Peak 𝒰</span>
          </button>
          <button
            onClick={() => jumpTo(eventSteps.peakQueue)}
            className="flex items-center gap-1 px-2.5 py-1.5 hover:bg-white/5 text-neutral-400 hover:text-white border border-neutral-800 rounded-md text-xs transition-colors"
            title={`Jump to peak queue (step ${eventSteps.peakQueue})`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Peak queue</span>
          </button>
        </div>
      </div>
    </div>
  );
});

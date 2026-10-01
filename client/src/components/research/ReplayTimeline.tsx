"use client";

import React, { memo } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Flame,
  AlertTriangle,
  ShieldAlert,
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
  totalSteps = 600,
  currentStep = 0,
  onSeek,
}: ReplayTimelineProps) {
  const replayState = useResearchStore((s) => s.replayState);
  const setReplayState = useResearchStore((s) => s.setReplayState);
  const { sendCommand } = useResearchSocket();

  const isPlaying = replayState.isPlaying;
  const speed = replayState.speed;
  const step = currentStep || replayState.currentStep;
  const maxSteps = totalSteps || replayState.totalSteps || 600;

  const handlePlayPause = () => {
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
    sendCommand({ command: "seek", step: targetStep });
  };

  // Quick Event Jump Markers
  const jumpTo = (targetStep: number) => {
    setReplayState({ currentStep: targetStep });
    if (onSeek) onSeek(targetStep);
    sendCommand({ command: "seek", step: targetStep });
  };

  const progressPercent = Math.min(100, Math.max(0, (step / maxSteps) * 100));

  return (
    <div className="bg-[#12151c]/95 border border-white/10 rounded-2xl p-5 shadow-2xl backdrop-blur-md flex flex-col gap-4">
      {/* Top Header: Step & Time display */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Replay Mode
          </span>
          <span className="text-xs font-mono text-slate-300">
            Step <strong className="text-white">{step}</strong> of {maxSteps} ({(step * 0.1).toFixed(1)}s)
          </span>
        </div>

        {/* Playback speed buttons */}
        <div className="flex items-center gap-1.5 bg-black/40 border border-white/5 rounded-lg p-1">
          {[0.25, 0.5, 1.0, 2.0].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-colors ${
                speed === s
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Scrub Bar with Event Marker Pins */}
      <div className="relative flex flex-col gap-1.5">
        <div className="relative w-full h-3 bg-black/60 rounded-full border border-white/10 overflow-hidden cursor-pointer">
          {/* Progress fill */}
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-all duration-75"
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
        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
          <span>0.0s (Start)</span>
          <span className="flex items-center gap-1 text-amber-400/80">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            Noise Injected @ 60s
          </span>
          <span className="flex items-center gap-1 text-rose-400/80">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            Peak Uncertainty @ 120s
          </span>
          <span>{(maxSteps * 0.1).toFixed(0)}s (End)</span>
        </div>
      </div>

      {/* Controls & Quick Event Jump Navigation */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-white/10">
        {/* Play / Pause / Seek Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => jumpTo(Math.max(0, step - 10))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Step Back 10 steps (1s)"
          >
            <Rewind className="w-4 h-4" />
          </button>
          <button
            onClick={handlePlayPause}
            className="flex items-center gap-1.5 px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold font-mono tracking-wider transition-all shadow-lg shadow-indigo-600/30"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-white" />}
            <span>{isPlaying ? "PAUSE" : "PLAY"}</span>
          </button>
          <button
            onClick={() => jumpTo(Math.min(maxSteps, step + 10))}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Step Forward 10 steps (1s)"
          >
            <FastForward className="w-4 h-4" />
          </button>
          <button
            onClick={() => jumpTo(0)}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors ml-1"
            title="Reset to Beginning"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Critical Event Jump Buttons */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase text-slate-500 hidden md:inline">
            Event Jumps:
          </span>
          <button
            onClick={() => jumpTo(Math.round(maxSteps * 0.2))}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-mono transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Fallback</span>
          </button>
          <button
            onClick={() => jumpTo(Math.round(maxSteps * 0.35))}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-mono transition-colors"
          >
            <Flame className="w-3.5 h-3.5" />
            <span>Peak U(s)</span>
          </button>
          <button
            onClick={() => jumpTo(Math.round(maxSteps * 0.65))}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 rounded-lg text-xs font-mono transition-colors"
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Peak Queue</span>
          </button>
        </div>
      </div>
    </div>
  );
});

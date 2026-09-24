"use client";

import type { CityMode } from "@/types/city";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Play, Square, RotateCcw, Layers } from "lucide-react";

interface CityControlsProps {
  running: boolean;
  mode: CityMode;
  spawnRate: number;
  showCongestion: boolean;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onModeChange: (m: CityMode) => void;
  onSpawnRateChange: (v: number) => void;
  onToggleCongestion: () => void;
}

export default function CityControls({
  running,
  mode,
  spawnRate,
  showCongestion,
  onStart,
  onStop,
  onReset,
  onModeChange,
  onSpawnRateChange,
  onToggleCongestion,
}: CityControlsProps) {
  return (
    <div className="flex flex-col gap-4 text-white w-full">
      {/* Mode toggle */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-col">
          <p className="text-xs font-medium text-neutral-400">Control Mode</p>
          <p className="text-sm text-white">
            {mode === "ai" ? "AI Agent" : mode === "greedy" ? "Greedy Controller" : "Fixed Timer"}
          </p>
        </div>
        <div className="flex items-center p-1 bg-neutral-900 rounded-lg border border-neutral-800">
          {["ai", "fixed", "greedy"].map((m) => (
            <Button
              key={m}
              size="sm"
              variant="ghost"
              onClick={() => onModeChange(m as CityMode)}
              className={`flex-1 h-7 text-xs capitalize ${
                mode === m
                  ? "bg-neutral-800 text-white shadow-sm"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
              }`}
            >
              {m}
            </Button>
          ))}
        </div>
        {mode === "ai" && (
          <div className="text-[9px] text-neutral-500 italic pl-1">
            Shared-policy DQN — one agent, 4 intersections
          </div>
        )}
      </div>

      {/* Control buttons */}
      <div className="flex gap-2">
        {!running ? (
          <Button
            size="sm"
            className="flex-1 bg-white text-black hover:bg-neutral-200 font-medium"
            onClick={onStart}
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            Start
          </Button>
        ) : (
          <Button
            size="sm"
            className="flex-1 bg-neutral-900 text-white border border-neutral-800 hover:bg-neutral-800"
            onClick={onStop}
          >
            <Square className="h-3.5 w-3.5 mr-1.5" />
            Stop
          </Button>
        )}

        <Button
          size="sm"
          variant="outline"
          className="border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white"
          onClick={onReset}
        >
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
          Reset
        </Button>
      </div>

      {/* Spawn rate */}
      <div className="space-y-1.5 rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 font-medium text-neutral-400">
            Spawn Rate (λ)
          </span>
          <span className="font-mono text-white font-medium">{spawnRate.toFixed(2)}</span>
        </div>
        <Slider
          min={0.05}
          max={1.5}
          step={0.05}
          value={[spawnRate]}
          onValueChange={(val) => onSpawnRateChange(val[0] ?? 0.3)}
        />
        <div className="flex justify-between text-[9px] text-neutral-500">
          <span>0.05</span><span>0.75</span><span>1.50</span>
        </div>
      </div>

      {/* Congestion heatmap toggle */}
      <Button
        variant="outline"
        size="sm"
        onClick={onToggleCongestion}
        className={`w-full h-8 text-[11px] font-medium border-neutral-800 transition-colors ${
          showCongestion
            ? "bg-neutral-800 text-white border-neutral-700"
            : "bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white"
        }`}
      >
        <Layers className="h-3.5 w-3.5 mr-1.5 text-neutral-500" />
        {showCongestion ? "Congestion Heatmap ON" : "Congestion Heatmap OFF"}
      </Button>
    </div>
  );
}

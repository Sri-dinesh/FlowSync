"use client";

import type { CityMode } from "@/types/city";

function ModeButton({
  label,
  active,
  onClick,
  color,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  color: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-1.5 rounded-md text-[11px] font-semibold tracking-wider uppercase transition-all duration-200 ${
        active
          ? `bg-gradient-to-r ${color} text-white shadow-md shadow-black/20`
          : "bg-white/5 text-white/40 hover:bg-white/10 hover:text-white/70"
      }`}
    >
      {label}
    </button>
  );
}

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
    <div className="flex flex-col gap-5 text-white w-full">
      {/* Mode */}
      <div className="space-y-2.5">
        <div className="text-[10px] uppercase tracking-wider text-white/40">Control Mode</div>
        <div className="flex gap-1.5">
          <ModeButton label="Fixed" active={mode === "fixed"} onClick={() => onModeChange("fixed")} color="from-slate-600 to-slate-500" />
          <ModeButton label="Greedy" active={mode === "greedy"} onClick={() => onModeChange("greedy")} color="from-amber-600 to-amber-500" />
          <ModeButton label="AI" active={mode === "ai"} onClick={() => onModeChange("ai")} color="from-emerald-600 to-emerald-500" />
        </div>
        {mode === "ai" && (
          <div className="text-[9px] text-emerald-400/70 italic pl-1">
            Shared-policy DQN — one agent, 4 intersections
          </div>
        )}
      </div>

      {/* Start / Stop / Reset */}
      <div className="flex gap-1.5">
        <button
          onClick={running ? onStop : onStart}
          className={`flex-1 py-2 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all duration-200 shadow-lg ${
            running
              ? "bg-gradient-to-r from-red-700 to-rose-600 hover:from-red-600 hover:to-rose-500 text-white shadow-rose-900/20"
              : "bg-gradient-to-r from-emerald-700 to-teal-600 hover:from-emerald-600 hover:to-teal-500 text-white shadow-emerald-900/20"
          }`}
        >
          {running ? "■ Stop" : "▶ Start"}
        </button>
        <button
          onClick={onReset}
          className="px-3 py-2 rounded-md text-xs font-bold uppercase tracking-wider bg-white/5 hover:bg-white/10 text-white/60 hover:text-white/90 transition-all border border-white/5 hover:border-white/10"
        >
          ↺
        </button>
      </div>

      {/* Spawn rate */}
      <div className="space-y-2.5">
        <div className="flex justify-between items-center">
          <span className="text-[10px] uppercase tracking-wider text-white/40">Spawn Rate (λ)</span>
          <span className="text-xs font-mono text-white/70">{spawnRate.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.05}
          max={1.5}
          step={0.05}
          value={spawnRate}
          onChange={(e) => onSpawnRateChange(parseFloat(e.target.value))}
          className="w-full h-1.5 accent-violet-500 cursor-pointer"
        />
        <div className="flex justify-between text-[9px] text-white/20">
          <span>0.05</span><span>0.75</span><span>1.5</span>
        </div>
      </div>

      {/* Congestion heatmap toggle */}
      <button
        onClick={onToggleCongestion}
        className={`py-2 rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all border ${
          showCongestion
            ? "bg-orange-600/20 text-orange-300 border-orange-600/40"
            : "bg-white/5 text-white/40 border-white/10 hover:bg-white/10"
        }`}
      >
        {showCongestion ? "● Congestion Heatmap ON" : "○ Congestion Heatmap"}
      </button>
    </div>
  );
}

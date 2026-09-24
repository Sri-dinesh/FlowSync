"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Play, RotateCcw, Square, Siren, FastForward, Gauge, Zap, Timer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationMode, VehicleState } from "@/types/simulation";

const EMPTY_VEHICLES: VehicleState[] = [];
const SPEED_OPTIONS = [1.0, 2.0, 4.0, 8.0, 16.0] as const;

interface SimulationControlsProps {
  sendCommand: (command: Record<string, unknown>) => void;
}

export default function SimulationControls({
  sendCommand,
}: SimulationControlsProps) {
  const isConnected = useSimulationStore((s) => s.isConnected);
  const mode = useSimulationStore((s) => s.mode);
  const setMode = useSimulationStore((s) => s.setMode);
  const isRunning = useSimulationStore((s) => s.isRunning);
  const setRunning = useSimulationStore((s) => s.setRunning);
  const resetSimulation = useSimulationStore((s) => s.resetSimulation);
  const currentFrame = useSimulationStore((s) => s.currentFrame);

  const [durationMode, setDurationMode] = useState<"continuous" | "timed">("timed");
  const [targetDuration, setTargetDuration] = useState<number>(60);
  const [spawnRate, setSpawnRate] = useState(0.5);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [isSwitching, setIsSwitching] = useState(false);

  const speedIndex = useMemo(() => {
    const exact = SPEED_OPTIONS.indexOf(simSpeed as (typeof SPEED_OPTIONS)[number]);
    if (exact !== -1) return exact;
    return SPEED_OPTIONS.reduce(
      (bestIdx, val, idx) =>
        Math.abs(val - simSpeed) < Math.abs(SPEED_OPTIONS[bestIdx] - simSpeed) ? idx : bestIdx,
      0
    );
  }, [simSpeed]);

  const runStartTimestepRef = useRef<number | null>(null);

  // If backend resets timestep to 0 on a new run, adapt the base step
  if (currentFrame && currentFrame.timestep < (runStartTimestepRef.current ?? 0)) {
    runStartTimestepRef.current = 0;
  }

  const baseStep = runStartTimestepRef.current ?? (currentFrame?.timestep ?? 0);
  const simElapsedSec = Math.max(0, ((currentFrame?.timestep ?? 0) - baseStep) * 0.1);

  const modeLabel = useMemo(
    () =>
      mode === "ai"
        ? "AI Agent"
        : mode === "manual"
        ? "Manual Control"
        : mode === "greedy"
        ? "Greedy Controller"
        : "Fixed Timer",
    [mode],
  );

  const handleModeChange = (nextMode: SimulationMode) => {
    if (mode === nextMode) return;
    setMode(nextMode);
    setIsSwitching(true);
    sendCommand({ command: "set_mode", mode: nextMode });
    setTimeout(() => setIsSwitching(false), 2000);
  };

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const handleManualPhase = (phase: number) => {
    sendCommand({ command: "manual_override", phase });
  };

  const handleStart = () => {
    runStartTimestepRef.current = currentFrame?.timestep ?? 0;
    setRunning(true);
    const durationSeconds = durationMode === "timed" ? targetDuration : null;
    sendCommand({ command: "start", duration_seconds: durationSeconds });
  };

  const handleStop = () => {
    setRunning(false);
    sendCommand({ command: "stop" });
    fetch(`${API_BASE}/simulation/stop`, { method: "POST" }).catch(() => {});
  };

  const handleReset = () => {
    runStartTimestepRef.current = 0;
    // Send reset to backend first — cancels tasks, empties all vehicle queues, disables spawner
    sendCommand({ command: "reset" });
    fetch(`${API_BASE}/simulation/reset`, { method: "POST" }).catch(() => {});
    // Clear frontend state so the canvas and metrics wipe immediately
    resetSimulation();
  };

  // Client-side failsafe watchdog: enforce auto-stop when target duration is reached
  useEffect(() => {
    if (!isRunning || durationMode !== "timed" || !targetDuration) return;

    if (simElapsedSec >= targetDuration && simElapsedSec > 0.5) {
      console.log(
        `[SimulationControls] Target duration reached (${simElapsedSec.toFixed(1)}s >= ${targetDuration}s). Auto-stopping simulation.`
      );
      handleStop();
    }
  }, [isRunning, durationMode, targetDuration, simElapsedSec]);

  const handleSpeedChange = (newSpeed: number) => {
    const clamped = Math.max(0.25, Math.min(16.0, newSpeed));
    setSimSpeed(clamped);
    sendCommand({ command: "set_speed", value: clamped });
  };

  const handleSpawnChange = (value: number[]) => {
    const raw = value[0] ?? spawnRate;
    const nextRate = Math.round(raw * 10) / 10;
    setSpawnRate(nextRate);
    sendCommand({ command: "set_spawn_rate", value: nextRate });
  };

  const handleStressTest500 = () => {
    handleSpeedChange(8.0);
    const stressRate = 3.5;
    setSpawnRate(stressRate);
    sendCommand({ command: "set_spawn_rate", value: stressRate });
    if (!isRunning) {
      handleStart();
    }
  };

  const vehicles = useSimulationStore((s) => s.currentFrame?.vehicles ?? EMPTY_VEHICLES);
  
  const isEmergencyActive = useMemo(() => {
    return vehicles.some((v) => v.is_emergency);
  }, [vehicles]);

  const activeEmergencyLanes = useMemo(() => {
    const laneSet = new Set(
      vehicles.filter((v) => v.is_emergency).map((v) => v.lane.toUpperCase())
    );
    return Array.from(laneSet).join(" / ");
  }, [vehicles]);

  const handleEmergencyTrigger = (lane: string) => {
    sendCommand({ command: "emergency_override", lane });
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Target Run Duration Option */}
      <div className="flex flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900/60 p-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Timer className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-semibold text-white tracking-wide">
              Run Duration
            </span>
          </div>
          <span className="font-mono text-xs font-medium text-emerald-400">
            {durationMode === "continuous" ? "∞ Continuous" : `${targetDuration}s`}
          </span>
        </div>

        {/* Quick preset selector */}
        <div className="flex items-center gap-1 p-0.5 bg-neutral-950/80 rounded-lg border border-neutral-800/80">
          {[
            { label: "30s", val: 30 },
            { label: "60s", val: 60 },
            { label: "120s", val: 120 },
            { label: "300s", val: 300 },
          ].map((preset) => (
            <Button
              key={preset.val}
              size="sm"
              variant="ghost"
              disabled={isRunning}
              onClick={() => {
                setDurationMode("timed");
                setTargetDuration(preset.val);
              }}
              className={`flex-1 h-6 text-[11px] font-medium rounded-md transition-all ${
                durationMode === "timed" && targetDuration === preset.val
                  ? "bg-neutral-800 text-white border border-neutral-700 shadow-sm"
                  : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
              }`}
            >
              {preset.label}
            </Button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            disabled={isRunning}
            onClick={() => setDurationMode("continuous")}
            className={`px-2 h-6 text-[11px] font-medium rounded-md transition-all ${
              durationMode === "continuous"
                ? "bg-neutral-800 text-white border border-neutral-700 shadow-sm"
                : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
            }`}
            title="Run continuously until manual Stop"
          >
            ∞ Continuous
          </Button>
        </div>

        {/* Custom duration input */}
        {durationMode === "timed" && (
          <div className="flex items-center justify-between gap-2 pt-0.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-neutral-400">Custom (sec):</span>
              <input
                type="number"
                min={5}
                max={3600}
                step={5}
                disabled={isRunning}
                value={targetDuration}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (!isNaN(val)) {
                    setTargetDuration(Math.max(5, Math.min(3600, val)));
                  }
                }}
                className="w-16 h-6 rounded-md bg-neutral-950 border border-neutral-800 px-1.5 text-center text-xs font-mono text-white focus:outline-none focus:border-neutral-600 disabled:opacity-50"
              />
            </div>
            <span className="text-[10px] text-neutral-500 text-right">
              Runs selected mode for {targetDuration}s then auto-stops
            </span>
          </div>
        )}

        {/* Live Elapsed Progress Bar when simulation is running in timed mode */}
        {isRunning && durationMode === "timed" && (
          <div className="flex flex-col gap-1 mt-1 pt-2 border-t border-neutral-800/60">
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-neutral-400">Execution Progress</span>
              <span className="font-mono text-emerald-400 font-medium">
                {simElapsedSec.toFixed(1)}s / {targetDuration}s ({Math.min(100, Math.round((simElapsedSec / targetDuration) * 100))}%)
              </span>
            </div>
            <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-150"
                style={{ width: `${Math.min(100, (simElapsedSec / targetDuration) * 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Run Completed status badge */}
        {!isRunning && durationMode === "timed" && simElapsedSec >= targetDuration && simElapsedSec > 0 && (
          <div className="flex items-center justify-between text-[11px] text-emerald-400 font-medium bg-emerald-950/40 border border-emerald-800/60 rounded-lg px-2.5 py-1.5 mt-1">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Completed {targetDuration}s run
            </span>
            <span className="text-[10px] text-neutral-400">Ready for next run</span>
          </div>
        )}
      </div>

      {/* Mode toggle */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <p className="text-xs font-medium text-neutral-400">Mode</p>
            <p className="text-sm text-white">{modeLabel}</p>
          </div>
          {isSwitching && <Loader2 className="h-4 w-4 animate-spin text-neutral-500" />}
        </div>
        <div className="flex items-center p-1 bg-neutral-900 rounded-lg border border-neutral-800">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("fixed")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "fixed" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"}`}
          >
            Fixed
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("greedy")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "greedy" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"}`}
          >
            Greedy
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("manual")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "manual" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"}`}
          >
            Manual
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("ai")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "ai" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"}`}
          >
            AI
          </Button>
        </div>
      </div>

      {/* Manual Phase Controls */}
      {mode === "manual" && (
        <div className="flex flex-col gap-2 p-3 bg-neutral-900 rounded-lg border border-neutral-800">
          <p className="text-xs text-neutral-400 font-medium mb-1">Set Phase</p>
          <div className="grid grid-cols-2 gap-2">
            <Button size="sm" variant="outline" className="h-8 text-[10px] border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white" onClick={() => handleManualPhase(0)}>
              NS Green
            </Button>
            <Button size="sm" variant="outline" className="h-8 text-[10px] border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white" onClick={() => handleManualPhase(1)}>
              EW Green
            </Button>
            <Button size="sm" variant="outline" className="h-8 text-[10px] border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white" onClick={() => handleManualPhase(2)}>
              NS Left
            </Button>
            <Button size="sm" variant="outline" className="h-8 text-[10px] border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white" onClick={() => handleManualPhase(3)}>
              EW Left
            </Button>
          </div>
        </div>
      )}

      {/* Control buttons */}
      <div className="flex gap-2">
        {!isRunning ? (
          <Button
            size="sm"
            className="flex-1 bg-white text-black hover:bg-neutral-200 font-medium"
            onClick={handleStart}
            disabled={!isConnected}
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            Start
          </Button>
        ) : (
          <Button
            size="sm"
            className="flex-1 bg-neutral-900 text-white border border-neutral-800 hover:bg-neutral-800"
            onClick={handleStop}
            disabled={!isConnected}
            title="Stop simulation and persist metrics"
          >
            <Square className="h-3.5 w-3.5 mr-1.5" />
            Stop
          </Button>
        )}

        <Button
          size="sm"
          variant="outline"
          className="border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white"
          onClick={handleReset}
          disabled={!isConnected}
          title="Stop simulation and reset intersection to initial state"
        >
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
          Reset
        </Button>
      </div>

      {/* Status row */}
      <div className="flex items-center gap-2 text-[10px] text-neutral-500">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            !isConnected
              ? "bg-neutral-600"
              : isRunning
              ? "bg-white"
              : "bg-neutral-700"
          }`}
        />
        {!isConnected
          ? "Backend disconnected"
          : isRunning
          ? "Simulation running"
          : "Simulation stopped"}
      </div>

      {/* Simulation Playback Speed Control */}
      <div className="space-y-1.5 rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 font-medium text-neutral-400">
            <FastForward className="h-3.5 w-3.5 text-neutral-500" />
            Simulation Speed
          </span>
          <span className="font-mono text-white font-medium">{simSpeed}x</span>
        </div>
        <div className="flex items-center gap-1.5">
          {SPEED_OPTIONS.map((speed) => (
            <Button
              key={speed}
              size="sm"
              variant="ghost"
              onClick={() => handleSpeedChange(speed)}
              disabled={!isConnected}
              className={`flex-1 h-6 text-[10px] rounded px-0.5 ${
                Math.abs(simSpeed - speed) < 0.05
                  ? "bg-neutral-800 text-white border border-neutral-700 font-semibold"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
              }`}
            >
              {speed}x
            </Button>
          ))}
        </div>
        <Slider
          min={0}
          max={SPEED_OPTIONS.length - 1}
          step={1}
          value={[speedIndex]}
          disabled={!isConnected}
          onValueChange={(val) => {
            const idx = Math.max(0, Math.min(SPEED_OPTIONS.length - 1, val[0] ?? 0));
            handleSpeedChange(SPEED_OPTIONS[idx]);
          }}
        />
        <div className="flex justify-between text-[9px] font-mono text-neutral-500 px-0.5">
          {SPEED_OPTIONS.map((speed) => (
            <span key={speed}>{speed}x</span>
          ))}
        </div>
      </div>

      {/* Traffic Density (Arrival Rate λ) slider */}
      <div className="space-y-1.5 rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5">
        <div className="flex items-center justify-between text-xs">
          <div className="flex flex-col">
            <span className="flex items-center gap-1.5 font-medium text-neutral-400">
              <Gauge className="h-3.5 w-3.5 text-neutral-500" />
              Traffic Density (Arrival Rate λ)
            </span>
            <p className="text-[9px] text-neutral-500">
              Arrivals per approach / sec (Up to 16 veh/s total)
            </p>
          </div>
          <span className="font-mono text-white font-medium">{spawnRate.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1">
          {[
            { label: "Normal", rate: 0.5 },
            { label: "Busy", rate: 1.0 },
            { label: "Rush Hour", rate: 2.0 },
            { label: "Surge 500+", rate: 3.5 },
          ].map((preset) => (
            <Button
              key={preset.rate}
              size="sm"
              variant="ghost"
              onClick={() => {
                setSpawnRate(preset.rate);
                sendCommand({ command: "set_spawn_rate", value: preset.rate });
              }}
              disabled={!isConnected}
              className={`flex-1 h-5 text-[9px] rounded px-1 ${
                Math.abs(spawnRate - preset.rate) < 0.05
                  ? "bg-neutral-800 text-white border border-neutral-700"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
              }`}
            >
              {preset.label}
            </Button>
          ))}
        </div>
        <Slider
          min={0.1}
          max={4.0}
          step={0.1}
          value={[spawnRate]}
          disabled={!isConnected}
          onValueChange={handleSpawnChange}
        />
        <div className="flex justify-between text-[9px] text-neutral-500">
          <span>0.10 (Free Flow)</span>
          <span>2.00 (Rush Hour)</span>
          <span>4.00 (Extreme Surge)</span>
        </div>
      </div>

      {/* 500+ Vehicle Stress Test Preset Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleStressTest500}
        disabled={!isConnected}
        className="w-full h-8 text-[11px] font-medium border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors"
      >
        <Zap className="h-3.5 w-3.5 mr-1.5 text-neutral-500" />
        Run 500+ Vehicle Stress Test (8x Speed)
      </Button>

      {/* Emergency Override Panel */}
      <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-900/50 p-2.5 flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5 text-neutral-300 font-semibold text-[11px] tracking-wider uppercase">
          <Siren className="h-3.5 w-3.5 text-neutral-500" />
          Emergency Preemption
        </div>
        <p className="text-[9px] text-neutral-500 leading-normal">
          Force immediate priority green light and spawn an emergency vehicle to clear the approach.
        </p>

        {isEmergencyActive ? (
          <div className="rounded border border-neutral-700 bg-neutral-800 py-1 text-center text-[9px] font-bold tracking-wider text-white uppercase">
            ⚠️ Preemption Active: {activeEmergencyLanes} Lane
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-1 mt-0.5">
            {(["North", "South", "East", "West"] as const).map((direction) => (
              <Button
                key={direction}
                variant="outline"
                className="h-6 text-[9px] border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white"
                onClick={() => handleEmergencyTrigger(direction.toLowerCase())}
                disabled={!isConnected || !isRunning}
              >
                {direction}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { Loader2, Play, RotateCcw, Square, Siren, FastForward, Gauge, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationMode, VehicleState } from "@/types/simulation";

const EMPTY_VEHICLES: VehicleState[] = [];

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

  const [spawnRate, setSpawnRate] = useState(0.5);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [isSwitching, setIsSwitching] = useState(false);

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

  const handleManualPhase = (phase: number) => {
    sendCommand({ command: "manual_override", phase });
  };

  const handleStart = () => {
    setRunning(true);
    sendCommand({ command: "start" });
  };

  const handleStop = () => {
    setRunning(false);
    sendCommand({ command: "stop" });
  };

  const handleReset = () => {
    // Send reset to backend first — clears intersection state, timestep, all vehicles
    sendCommand({ command: "reset" });
    // Then clear frontend state so the canvas goes blank immediately
    resetSimulation();
  };

  const handleSpeedChange = (newSpeed: number) => {
    const clamped = Math.max(0.25, Math.min(16.0, newSpeed));
    setSimSpeed(clamped);
    sendCommand({ command: "set_speed", value: clamped });
  };

  const handleSpawnChange = (value: number[]) => {
    const nextRate = value[0] ?? spawnRate;
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
    <div className="flex flex-col gap-3">
      {/* Mode toggle */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-white">Mode</p>
            <p className="text-xs text-white/45">{modeLabel}</p>
          </div>
          {isSwitching && <Loader2 className="h-4 w-4 animate-spin text-white/50" />}
        </div>
        <div className="flex items-center p-1 bg-black/40 rounded-lg border border-white/5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("fixed")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "fixed" ? "bg-white/20 text-white hover:bg-white/30" : "text-white/50 hover:text-white hover:bg-white/10"}`}
          >
            Fixed
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("greedy")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "greedy" ? "bg-orange-500/30 text-orange-200 hover:bg-orange-500/40" : "text-white/50 hover:text-white hover:bg-white/10"}`}
          >
            Greedy
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("manual")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "manual" ? "bg-white/20 text-white hover:bg-white/30" : "text-white/50 hover:text-white hover:bg-white/10"}`}
          >
            Manual
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleModeChange("ai")}
            disabled={!isConnected || isSwitching}
            className={`flex-1 h-7 text-xs ${mode === "ai" ? "bg-white/20 text-white hover:bg-white/30" : "text-white/50 hover:text-white hover:bg-white/10"}`}
          >
            AI
          </Button>
        </div>
      </div>

      {/* Manual Phase Controls */}
      {mode === "manual" && (
        <div className="flex flex-col gap-2 p-3 bg-white/5 rounded-lg border border-white/10">
          <p className="text-xs text-white/70 font-medium mb-1">Set Phase</p>
          <div className="grid grid-cols-2 gap-2">
            <Button size="sm" variant="secondary" className="h-8 text-[10px] uppercase" onClick={() => handleManualPhase(0)}>
              NS Green
            </Button>
            <Button size="sm" variant="secondary" className="h-8 text-[10px] uppercase" onClick={() => handleManualPhase(1)}>
              EW Green
            </Button>
            <Button size="sm" variant="secondary" className="h-8 text-[10px] uppercase" onClick={() => handleManualPhase(2)}>
              NS Left
            </Button>
            <Button size="sm" variant="secondary" className="h-8 text-[10px] uppercase" onClick={() => handleManualPhase(3)}>
              EW Left
            </Button>
          </div>
        </div>
      )}

      {/* Control buttons */}
      <div className="flex gap-2">
        {/* Start / Stop */}
        {!isRunning ? (
          <Button
            size="sm"
            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={handleStart}
            disabled={!isConnected}
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            Start
          </Button>
        ) : (
          <Button
            size="sm"
            className="flex-1 bg-rose-600 hover:bg-rose-700 text-white"
            onClick={handleStop}
            disabled={!isConnected}
            title="Stop simulation and persist metrics"
          >
            <Square className="h-3.5 w-3.5 mr-1.5" />
            Stop
          </Button>
        )}

        {/* Reset — always visible, clears everything */}
        <Button
          size="sm"
          variant="outline"
          className="border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 hover:border-rose-500/60"
          onClick={handleReset}
          disabled={!isConnected}
          title="Stop simulation and reset intersection to initial state"
        >
          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
          Reset
        </Button>
      </div>

      {/* Status row */}
      <div className="flex items-center gap-2 text-[10px] text-white/40">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            !isConnected
              ? "bg-rose-500"
              : isRunning
              ? "bg-emerald-400 animate-pulse"
              : "bg-white/25"
          }`}
        />
        {!isConnected
          ? "Backend disconnected"
          : isRunning
          ? "Simulation running"
          : "Simulation stopped"}
      </div>

      {/* Simulation Playback Speed Control */}
      <div className="space-y-1.5 rounded-lg border border-white/10 bg-white/5 p-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 font-medium text-white/70">
            <FastForward className="h-3.5 w-3.5 text-sky-400" />
            Simulation Speed
          </span>
          <span className="font-mono text-sky-300 font-bold">{simSpeed.toFixed(1)}x</span>
        </div>
        <div className="flex items-center gap-1.5">
          {[1.0, 2.0, 4.0, 8.0, 16.0].map((speed) => (
            <Button
              key={speed}
              size="sm"
              variant="ghost"
              onClick={() => handleSpeedChange(speed)}
              disabled={!isConnected}
              className={`flex-1 h-6 text-[10px] rounded px-0.5 ${
                Math.abs(simSpeed - speed) < 0.05
                  ? "bg-sky-500/30 text-sky-200 border border-sky-400/40"
                  : "text-white/50 hover:text-white hover:bg-white/10"
              }`}
            >
              {speed}x
            </Button>
          ))}
        </div>
        <Slider
          min={0.5}
          max={16.0}
          step={0.5}
          value={[simSpeed]}
          disabled={!isConnected}
          onValueChange={(val) => handleSpeedChange(val[0] ?? 1.0)}
        />
      </div>

      {/* Traffic Density (Arrival Rate λ) slider */}
      <div className="space-y-1.5 rounded-lg border border-white/10 bg-white/5 p-2.5">
        <div className="flex items-center justify-between text-xs">
          <div>
            <span className="flex items-center gap-1.5 font-medium text-white/70">
              <Gauge className="h-3.5 w-3.5 text-amber-400" />
              Traffic Density (Arrival Rate λ)
            </span>
            <p className="text-[9px] text-white/35">
              Arrivals per approach / sec (Up to 16 veh/s total)
            </p>
          </div>
          <span className="font-mono text-amber-300 font-bold">{spawnRate.toFixed(2)}</span>
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
                  ? "bg-amber-500/30 text-amber-200 border border-amber-400/40"
                  : "text-white/40 hover:text-white hover:bg-white/10"
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
        <div className="flex justify-between text-[9px] text-white/30">
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
        className="w-full h-8 text-[11px] font-semibold border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-orange-500/15 to-amber-500/10 text-amber-300 hover:bg-amber-500/20 hover:text-amber-100 hover:border-amber-500/50 shadow-sm"
      >
        <Zap className="h-3.5 w-3.5 mr-1.5 text-amber-400 animate-pulse" />
        Run 500+ Vehicle Stress Test (8x Speed)
      </Button>

      {/* Emergency Override Panel */}
      <div className="mt-2 rounded-lg border border-red-500/25 bg-red-950/10 p-2.5 flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5 text-red-400 font-semibold text-[11px] tracking-wider uppercase">
          <Siren className="h-3.5 w-3.5 animate-pulse" />
          Emergency Preemption
        </div>
        <p className="text-[9px] text-white/40 leading-normal">
          Force immediate priority green light and spawn an emergency vehicle to clear the approach.
        </p>

        {isEmergencyActive ? (
          <div className="rounded border border-red-500/40 bg-red-500/20 py-1 text-center text-[9px] font-bold tracking-wider text-red-200 animate-pulse uppercase">
            ⚠️ Preemption Active: {activeEmergencyLanes} Lane
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-1 mt-0.5">
            {(["North", "South", "East", "West"] as const).map((direction) => (
              <Button
                key={direction}
                variant="outline"
                className="h-6 text-[9px] border-red-500/25 bg-red-500/5 text-red-300 hover:bg-red-500/20 hover:border-red-500/50 hover:text-white"
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

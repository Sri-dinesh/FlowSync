"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Play, RotateCcw, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationMode } from "@/types/simulation";

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

  const [spawnRate, setSpawnRate] = useState(0.3);
  const [isSwitching, setIsSwitching] = useState(false);

  const modeLabel = useMemo(
    () => (mode === "ai" ? "AI Agent" : "Fixed Timer"),
    [mode],
  );

  useEffect(() => {
    if (isConnected && isRunning) {
      sendCommand({ command: "start" });
    }
  }, [isConnected, isRunning, sendCommand]);

  const handleToggle = (checked: boolean) => {
    const nextMode: SimulationMode = checked ? "ai" : "fixed";
    setMode(nextMode);
    setIsSwitching(true);
    sendCommand({ command: "set_mode", mode: nextMode });
    setTimeout(() => setIsSwitching(false), 2000);
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

  const handleSpawnCommit = (value: number[]) => {
    const nextRate = value[0] ?? spawnRate;
    setSpawnRate(nextRate);
    sendCommand({ command: "set_spawn_rate", value: nextRate });
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Mode toggle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-white">Mode</p>
          <p className="text-xs text-white/45">{modeLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          {isSwitching && <Loader2 className="h-4 w-4 animate-spin text-white/50" />}
          <Switch
            checked={mode === "ai"}
            onCheckedChange={handleToggle}
            disabled={!isConnected || isSwitching}
          />
        </div>
      </div>

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
            className="flex-1 bg-amber-600 hover:bg-amber-700 text-white"
            onClick={handleStop}
            disabled={!isConnected}
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

      {/* Spawn rate slider */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-white/50">
          <span>Vehicle Arrival Rate</span>
          <span className="font-mono">{spawnRate.toFixed(2)}</span>
        </div>
        <Slider
          min={0.1}
          max={1.0}
          step={0.05}
          value={[spawnRate]}
          disabled={!isConnected}
          onValueChange={(value) => setSpawnRate(value[0] ?? spawnRate)}
          onValueCommit={handleSpawnCommit}
        />
        <div className="flex justify-between text-[9px] text-white/20">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>
    </div>
  );
}

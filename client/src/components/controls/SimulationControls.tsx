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
  const isConnected = useSimulationStore((state) => state.isConnected);
  const mode = useSimulationStore((state) => state.mode);
  const setMode = useSimulationStore((state) => state.setMode);
  const isRunning = useSimulationStore((state) => state.isRunning);
  const setRunning = useSimulationStore((state) => state.setRunning);

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

  const handleStartStop = () => {
    const nextRunning = !isRunning;
    setRunning(nextRunning);
    sendCommand({ command: nextRunning ? "start" : "stop" });
  };

  const handleReset = () => {
    if (!window.confirm("Reset the simulation?")) {
      return;
    }
    setRunning(false);
    sendCommand({ command: "reset" });
  };

  const handleSpawnCommit = (value: number[]) => {
    const nextRate = value[0] ?? spawnRate;
    setSpawnRate(nextRate);
    sendCommand({ command: "set_spawn_rate", value: nextRate });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-2sm font-semibold text-white">Mode Toggle</p>
          <p className="text-xs text-white/45">{modeLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          {isSwitching && <Loader2 className="h-4 w-4 animate-spin" />}
          <Switch
            checked={mode === "ai"}
            onCheckedChange={handleToggle}
            disabled={!isConnected || isSwitching}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          className="min-w-[84px]"
          onClick={handleStartStop}
          disabled={!isConnected}
        >
          {isRunning ? (
            <>
              <Square className="h-4 w-4" />
              Stop
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Start
            </>
          )}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="min-w-[84px] border-white/20 bg-white/5"
          onClick={handleReset}
          disabled={!isConnected}
        >
          <RotateCcw className="h-4 w-4" />
          Reset
        </Button>
      </div>
      <div className="text-xs text-white/45">
        Status: {isRunning ? "Running" : "Stopped"}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-white/50">
          <span>Vehicle Arrival Rate (lambda)</span>
          <span>{spawnRate.toFixed(2)}</span>
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
      </div>
    </div>
  );
}

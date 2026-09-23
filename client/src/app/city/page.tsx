"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import type { CityMode } from "@/types/city";
import { useCitySocket } from "@/hooks/useCitySocket";

import Header from "@/components/layout/Header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import CityControls from "@/components/city/CityControls";
import CityMetricsPanel from "@/components/city/CityMetricsPanel";
import CityComparisonPanel from "@/components/city/CityComparisonPanel";

// Lazy-load Three.js canvas to avoid SSR issues
const CityCanvas = dynamic(() => import("@/components/city/CityCanvas"), { 
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center bg-[#060a14]">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-white/40 text-sm">Loading 3D City…</p>
      </div>
    </div>
  )
});

export default function CityPage() {
  const { frame, comparisonResults, comparisonFullResults, comparisonRunning, sendCommand } = useCitySocket();

  const [mode, setMode] = useState<CityMode>("fixed");
  const [running, setRunning] = useState(false);
  const [spawnRate, setSpawnRate] = useState(0.3);
  const [showCongestion, setShowCongestion] = useState(false);

  const handleStart = useCallback(() => {
    sendCommand({ command: "start" });
    setRunning(true);
  }, [sendCommand]);

  const handleStop = useCallback(() => {
    sendCommand({ command: "stop" });
    setRunning(false);
  }, [sendCommand]);

  const handleReset = useCallback(() => {
    sendCommand({ command: "reset" });
    setRunning(false);
  }, [sendCommand]);

  const handleModeChange = useCallback(
    (m: CityMode) => {
      setMode(m);
      sendCommand({ command: "set_mode", mode: m });
    },
    [sendCommand]
  );

  const handleSpawnRateChange = useCallback(
    (v: number) => {
      setSpawnRate(v);
      sendCommand({ command: "set_spawn_rate", value: v });
    },
    [sendCommand]
  );

  const handleRunComparison = useCallback((durationSeconds: number = 30) => {
    sendCommand({ command: "run_comparison", duration_seconds: durationSeconds });
    setRunning(true);
  }, [sendCommand]);

  return (
    <div className="relative h-screen bg-[#0a0a0a] text-white flex flex-col overflow-hidden">
      <div className="z-50 relative flex-none">
        <Header />
      </div>

      <div className="flex-1 flex w-full overflow-hidden">
        {/* Left Side: Canvas area */}
        <div className="flex-1 relative min-w-0">
          <CityCanvas frame={frame} showCongestion={showCongestion} />

          {/* Overlay: timestep + mode */}
          <div className="absolute top-4 left-4 flex items-center gap-2 pointer-events-none">
            <div className="bg-black/60 backdrop-blur-sm border border-white/10 rounded-lg px-3 py-1.5">
              <span className="text-[10px] text-white/30 uppercase tracking-wider">Tick </span>
              <span className="text-xs font-mono text-white/70">{frame?.timestep ?? 0}</span>
            </div>
            {comparisonRunning && frame?.comparison_progress?.running && (
              <div className="bg-violet-900/60 backdrop-blur-sm border border-violet-700/50 rounded-lg px-3 py-1.5 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-violet-400 animate-ping" />
                <span className="text-[10px] text-violet-300 font-bold uppercase tracking-wider">
                  Comparing: {frame.comparison_progress.current_mode?.toUpperCase()} ({frame.comparison_progress.elapsed?.toFixed(0)}s / {frame.comparison_progress.total}s)
                </span>
              </div>
            )}
            
            {/* Added City Grid context pill since Header doesn't mention it */}
            <div className="bg-blue-900/40 backdrop-blur-sm border border-blue-500/30 rounded-lg px-3 py-1.5">
              <span className="text-[10px] text-blue-300 font-semibold tracking-wider">
                🏙 CITY GRID EXPERIMENT
              </span>
            </div>
          </div>

          {/* Overlay: grid legend */}
          <div className="absolute bottom-4 left-4 pointer-events-none space-y-1">
            <div className="bg-black/50 backdrop-blur-sm border border-white/8 rounded-lg px-3 py-2 text-[9px] space-y-1">
              <div className="text-white/30 uppercase tracking-widest mb-1">Legend</div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-white/40">Green — Phase active</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span className="text-white/40">Amber — Transitioning</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                <span className="text-white/40">Blue dots — Road vehicles</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Controls Sidebar */}
        <aside className="w-[420px] flex-shrink-0 flex flex-col h-full overflow-y-auto bg-[#0a0a0a] border-l border-neutral-800 scrollbar-thin scrollbar-thumb-neutral-800 scrollbar-track-transparent hover:scrollbar-thumb-neutral-700 shadow-2xl z-10 pointer-events-auto">
          <div className="border-b border-neutral-800 bg-transparent flex-none">
            <div className="px-4 pt-6 pb-3">
              <h3 className="text-xs font-medium text-neutral-400">
                Controls
              </h3>
            </div>
            <div className="px-4 pb-4 space-y-5">
              <CityControls
                running={running}
                mode={mode}
                spawnRate={spawnRate}
                showCongestion={showCongestion}
                onStart={handleStart}
                onStop={handleStop}
                onReset={handleReset}
                onModeChange={handleModeChange}
                onSpawnRateChange={handleSpawnRateChange}
                onToggleCongestion={() => setShowCongestion((v) => !v)}
              />
            </div>
          </div>

          <div className="border-b border-neutral-800 bg-transparent p-4 flex-none">
            <h3 className="mb-3 text-xs font-medium text-neutral-400">
              City Metrics
            </h3>
            <CityMetricsPanel frame={frame} />
          </div>

          <div className="bg-transparent flex-none min-h-[300px] overflow-visible pb-10">
            <div className="px-4 pt-6 pb-3">
              <h3 className="text-xs font-medium text-neutral-400">
                Analytics
              </h3>
            </div>
            <div className="px-4 pb-6">
              <Tabs defaultValue="comparison" className="w-full">
                <TabsList className="h-auto gap-1 bg-transparent p-0">
                  <TabsTrigger
                    value="comparison"
                    className="text-neutral-500 hover:text-neutral-300 data-[state=active]:border-neutral-700 data-[state=active]:bg-neutral-800 data-[state=active]:text-white"
                  >
                    Compare
                  </TabsTrigger>
                </TabsList>
                <TabsContent
                  value="comparison"
                  className="mt-4 text-sm text-neutral-400"
                >
                  <CityComparisonPanel
                    results={comparisonResults}
                    fullResults={comparisonFullResults}
                    running={comparisonRunning}
                    progress={frame?.comparison_progress?.running ? frame.comparison_progress : undefined}
                    onStart={handleRunComparison}
                    onStop={handleStop}
                  />
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

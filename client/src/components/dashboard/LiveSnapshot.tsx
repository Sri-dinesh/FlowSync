"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { useSimulationStore } from "@/store/simulationStore";

function formatSeconds(value: number) {
  if (value < 1) {
    return "just now";
  }
  return `${value.toFixed(1)}s ago`;
}

export default function LiveSnapshot() {
  const isConnected = useSimulationStore((state) => state.isConnected);
  const isRunning = useSimulationStore((state) => state.isRunning);
  const mode = useSimulationStore((state) => state.mode);
  const frame = useSimulationStore((state) => state.currentFrame);
  const lastFrameAt = useSimulationStore((state) => state.lastFrameAt);
  const isTraining = useSimulationStore((state) => state.isTraining);

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const snapshot = useMemo(() => {
    const queueLengths = frame?.queue_lengths ?? {};
    const maxQueue = frame ? Math.max(...Object.values(queueLengths), 0) : 0;
    return {
      vehicles: frame?.vehicles?.length ?? 0,
      avgWait: frame?.avg_wait_time ?? 0,
      throughput: frame?.throughput ?? 0,
      maxQueue,
    };
  }, [frame]);

  const lastUpdateText = useMemo(() => {
    if (!lastFrameAt) {
      return "No frames yet";
    }
    return formatSeconds((now - lastFrameAt) / 1000);
  }, [lastFrameAt, now]);

  return (
    <div className="space-y-3 text-sm text-white/70">
      <div className="flex flex-wrap gap-1.5">
        <Badge
          variant="outline"
          className={
            isConnected
              ? "h-5 border-emerald-500/40 bg-emerald-900/30 px-2 text-[10px] text-emerald-300"
              : "h-5 border-rose-500/40 bg-rose-900/20 px-2 text-[10px] text-rose-300"
          }
        >
          {isConnected ? "• Connected" : "• Disconnected"}
        </Badge>
        <Badge
          variant="outline"
          className="h-5 border-white/15 bg-white/5 px-2 text-[10px] text-white/65"
        >
          {isRunning ? "Running" : "Stopped"}
        </Badge>
        <Badge
          variant="outline"
          className="h-5 border-white/15 bg-white/5 px-2 text-[10px] text-white/65"
        >
          {mode === "ai" ? "AI Mode" : "Fixed Mode"}
        </Badge>
        <Badge
          variant="outline"
          className="h-5 border-white/15 bg-white/5 px-2 text-[10px] text-white/65"
        >
          {isTraining ? "Training Active" : "Training Idle"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        <div className="rounded-md border border-white/10 bg-[#151515] p-2.5">
          <div className="text-[9px] uppercase tracking-[0.08em] text-white/40">
            Last Frame
          </div>
          <div className="mt-0.5 text-sm font-medium text-white/90">
            {lastUpdateText}
          </div>
        </div>
        <div className="rounded-md border border-white/10 bg-[#151515] p-2.5">
          <div className="text-[9px] uppercase tracking-[0.08em] text-white/40">
            Vehicles
          </div>
          <div className="mt-0.5 text-sm font-medium text-white/90">
            {snapshot.vehicles}
          </div>
        </div>
        <div className="rounded-md border border-white/10 bg-[#151515] p-2.5">
          <div className="text-[9px] uppercase tracking-[0.08em] text-white/40">
            Avg Wait
          </div>
          <div className="mt-0.5 text-sm font-medium text-white/90">
            {snapshot.avgWait.toFixed(1)}s
          </div>
        </div>
        <div className="rounded-md border border-white/10 bg-[#151515] p-2.5">
          <div className="text-[9px] uppercase tracking-[0.08em] text-white/40">
            Max Queue
          </div>
          <div className="mt-0.5 text-sm font-medium text-white/90">
            {snapshot.maxQueue}
          </div>
        </div>
      </div>
    </div>
  );
}

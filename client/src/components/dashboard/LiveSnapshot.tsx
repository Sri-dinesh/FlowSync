"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { GripVertical } from "lucide-react";

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
      return "No frames";
    }
    return formatSeconds((now - lastFrameAt) / 1000);
  }, [lastFrameAt, now]);

  return (
    <motion.div
      drag
      dragMomentum={false}
      initial={{ x: 20, y: 80 }}
      className="absolute z-50 flex w-56 cursor-grab flex-col gap-3 rounded-xl border border-white/10 bg-black/80 p-3 shadow-2xl backdrop-blur-xl active:cursor-grabbing"
    >
      <div className="flex items-center justify-between opacity-50">
        <GripVertical className="h-3 w-3" />
        <span className="text-[9px] uppercase tracking-widest text-white/50">Live Stats</span>
        <div className="h-3 w-3" /> {/* spacer for balance */}
      </div>
      
      {/* Active Status Badges */}
      <div className="flex flex-wrap gap-2">
        <Badge
          variant="outline"
          className={
            isConnected
              ? "border-emerald-500/30 bg-emerald-950/20 px-2 py-0.5 text-[9px] font-medium tracking-wider text-emerald-400"
              : "border-rose-500/30 bg-rose-950/20 px-2 py-0.5 text-[9px] font-medium tracking-wider text-rose-400"
          }
        >
          {isConnected ? "● CONNECTED" : "● DISCONNECTED"}
        </Badge>
        <Badge
          variant="outline"
          className="border-white/10 bg-white/5 px-2 py-0.5 text-[9px] font-medium tracking-wider text-white/60"
        >
          {isRunning ? "RUNNING" : "STOPPED"}
        </Badge>
        <Badge
          variant="outline"
          className="border-blue-500/20 bg-blue-950/20 px-2 py-0.5 text-[9px] font-medium tracking-wider text-blue-400"
        >
          {mode === "ai" ? "AI MODE" : "FIXED MODE"}
        </Badge>
        {isTraining && (
          <Badge
            variant="outline"
            className="border-violet-500/20 bg-violet-950/20 px-2 py-0.5 text-[9px] font-medium tracking-wider text-violet-400 animate-pulse"
          >
            TRAINING
          </Badge>
        )}
      </div>

      {/* Vertical Stats */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between rounded border border-white/5 bg-[#0e0e0e] px-2.5 py-1.5">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-medium">Last Frame</div>
          <div className="text-[11px] font-semibold tracking-tight text-white/90">{lastUpdateText}</div>
        </div>
        <div className="flex items-center justify-between rounded border border-white/5 bg-[#0e0e0e] px-2.5 py-1.5">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-medium">Active Vehicles</div>
          <div className="text-[11px] font-semibold tracking-tight text-white/90">{snapshot.vehicles}</div>
        </div>
        <div className="flex items-center justify-between rounded border border-white/5 bg-[#0e0e0e] px-2.5 py-1.5">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-medium">Avg Wait Time</div>
          <div className="text-[11px] font-semibold tracking-tight text-white/90">{snapshot.avgWait.toFixed(1)}s</div>
        </div>
        <div className="flex items-center justify-between rounded border border-white/5 bg-[#0e0e0e] px-2.5 py-1.5">
          <div className="text-[9px] uppercase tracking-wider text-white/40 font-medium">Max Queue</div>
          <div className="text-[11px] font-semibold tracking-tight text-white/90">{snapshot.maxQueue}</div>
        </div>
        
        {/* CCTV AI Scanner Card */}
        <div className="mt-1 rounded-lg border border-white/5 bg-[#0b0e14] p-2 flex flex-col gap-1 shadow-inner">
          <div className="text-[8px] font-bold uppercase tracking-[0.1em] text-cyan-400/90 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
            CCTV AI SCANNER
          </div>
          <div className="flex items-center justify-between">
            <div className="text-[9px] text-white/40">4 channel feed</div>
            <div className="text-[10px] font-mono font-bold text-white/90">
              {isRunning && snapshot.vehicles > 0 ? `${snapshot.vehicles} det.` : "0 (idle)"}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

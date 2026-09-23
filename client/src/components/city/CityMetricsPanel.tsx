"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { CityFrame } from "@/types/city";

const HISTORY_LENGTH = 20;

function AnimatedValue({ value, suffix = "" }: { value: number; suffix?: string }) {
  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {value.toFixed(1)}
      {suffix}
    </motion.span>
  );
}

function Sparkline({ data }: { data: number[] }) {
  const points = useMemo(() => {
    if (!data.length) return "";
    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = Math.max(max - min, 1);

    return data
      .map((value, index) => {
        const x = data.length === 1 ? 0 : (index / (data.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  }, [data]);

  if (!data.length) {
    return <div className="h-10 w-full rounded bg-neutral-900" />;
  }

  return (
    <svg viewBox="0 0 100 100" className="h-10 w-full overflow-visible">
      <polyline
        fill="none"
        stroke="rgba(255,255,255,0.7)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

function QueueBar({ value, max = 12 }: { value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex-1 h-1 bg-neutral-800 rounded-full overflow-hidden">
      <div
        className="h-full bg-white transition-all duration-300"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function IntersectionRow({ data }: { data: { id: string; avg_wait: number; waiting: number; signal_color: string; phase: number; queues: Record<string, number> } }) {
  const colorClass: Record<string, string> = {
    green: "bg-white",
    yellow: "bg-neutral-400",
    red: "bg-neutral-600",
  };
  const totalQ = Object.values(data.queues).reduce((a, b) => a + b, 0);

  return (
    <div className="flex items-center gap-2 py-2 border-b border-neutral-800 last:border-0">
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${colorClass[data.signal_color] ?? "bg-neutral-700"}`} />
      <span className="text-[11px] font-medium text-neutral-300 w-5">ID {data.id}</span>
      <QueueBar value={totalQ} max={48} />
      <span className="text-[10px] font-mono text-neutral-500 w-14 text-right">{data.waiting} wait</span>
      <span className="text-[10px] font-mono text-neutral-600 w-6">P{data.phase}</span>
    </div>
  );
}

export default function CityMetricsPanel({ frame }: { frame: CityFrame | null }) {
  const [waitHistory, setWaitHistory] = useState<number[]>([]);
  const [throughputHistory, setThroughputHistory] = useState<number[]>([]);
  const [activeHistory, setActiveHistory] = useState<number[]>([]);
  const [roadsHistory, setRoadsHistory] = useState<number[]>([]);

  useEffect(() => {
    if (!frame) return;

    setWaitHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.city_metrics.avg_wait_time]);
    setThroughputHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.city_metrics.total_throughput]);
    setActiveHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.city_metrics.active_vehicles]);
    setRoadsHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.city_metrics.road_vehicles]);
  }, [frame]);

  const metrics = frame?.city_metrics;
  const intersections = frame?.intersections ?? {};

  const cards = [
    {
      title: "Avg Wait Time",
      value: metrics?.avg_wait_time ?? 0,
      suffix: "s",
      history: waitHistory,
      ratio: Math.min(1, (metrics?.avg_wait_time ?? 0) / 20),
    },
    {
      title: "Throughput",
      value: metrics?.total_throughput ?? 0,
      suffix: "",
      history: throughputHistory,
      ratio: Math.min(1, (metrics?.total_throughput ?? 0) / 400),
    },
    {
      title: "Active Waiting",
      value: metrics?.active_vehicles ?? 0,
      suffix: "",
      history: activeHistory,
      ratio: Math.min(1, (metrics?.active_vehicles ?? 0) / 100),
    },
    {
      title: "Road Vehicles",
      value: metrics?.road_vehicles ?? 0,
      suffix: "",
      history: roadsHistory,
      ratio: Math.min(1, (metrics?.road_vehicles ?? 0) / 100),
    },
  ];

  const currentCongestion = metrics?.congestion_level ?? "unknown";

  return (
    <div className="space-y-4">
      {/* Congestion Level Banner */}
      <div className="flex items-center justify-between px-3 py-2 rounded-lg border border-neutral-800 bg-neutral-900 text-neutral-400">
        <span className="text-[10px] uppercase tracking-wider font-medium opacity-80">City Congestion</span>
        <span className="text-xs font-bold uppercase tracking-widest text-white">{currentCongestion}</span>
      </div>

      {/* 2x2 Grid for Global Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {cards.map((card) => (
          <div key={card.title} className="p-3 rounded-lg border border-neutral-800 bg-neutral-900/50">
            <div className="text-[10px] font-medium text-neutral-500 mb-1 uppercase tracking-wider">
              {card.title}
            </div>
            <div className="text-2xl font-medium leading-none tracking-tight text-white mb-2">
              <AnimatedValue value={card.value} suffix={card.suffix} />
            </div>
            <div className="h-0.5 rounded bg-neutral-800 mb-3">
              <div
                className="h-0.5 rounded bg-white"
                style={{ width: `${card.ratio * 100}%` }}
              />
            </div>
            <Sparkline data={card.history} />
          </div>
        ))}
      </div>

      {/* Per-Intersection Breakdown */}
      <div className="space-y-1 bg-neutral-900/50 rounded-lg p-3 border border-neutral-800">
        <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-2">Per-Intersection</div>
        {(["A", "B", "C", "D"] as const).map((id) => {
          const inter = intersections[id];
          if (!inter) return <div key={id} className="text-[10px] text-neutral-600 pl-1 py-1">INT {id} — no data</div>;
          return (
            <IntersectionRow
              key={id}
              data={{
                id,
                avg_wait: inter.avg_wait_time,
                waiting: inter.total_waiting,
                signal_color: inter.signal.color,
                phase: inter.signal.current_phase,
                queues: {
                  north: inter.queue_lengths.north,
                  south: inter.queue_lengths.south,
                  east: inter.queue_lengths.east,
                  west: inter.queue_lengths.west,
                },
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

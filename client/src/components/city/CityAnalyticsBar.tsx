"use client";

import { useEffect, useRef } from "react";
import type { CityFrame } from "@/types/city";

interface DataPoint {
  timestep: number;
  throughput: number;
  avgWait: number;
}

interface CityAnalyticsBarProps {
  frame: CityFrame | null;
  history: DataPoint[];
}

// ── Mini sparkline chart ──────────────────────────────────────────────────────
function Sparkline({
  data,
  color,
  width = 120,
  height = 32,
}: {
  data: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const step = width / (data.length - 1);

    // Draw fill
    ctx.beginPath();
    ctx.moveTo(0, height);
    data.forEach((v, i) => {
      ctx.lineTo(i * step, height - ((v - min) / range) * (height - 4) - 2);
    });
    ctx.lineTo((data.length - 1) * step, height);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, `${color}40`);
    grad.addColorStop(1, `${color}00`);
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw line
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [data, color, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="opacity-90"
    />
  );
}

// ── Metric tile ───────────────────────────────────────────────────────────────
function MetricTile({
  label,
  value,
  sub,
  accent,
  sparkData,
  sparkColor,
}: {
  label: string;
  value: string;
  sub?: string;
  accent: string;
  sparkData?: number[];
  sparkColor?: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-r border-white/10 last:border-0">
      <div className="flex flex-col">
        <span className="text-[9px] uppercase tracking-widest text-white/30">{label}</span>
        <span className={`text-lg font-bold font-mono leading-tight ${accent}`}>{value}</span>
        {sub && <span className="text-[9px] text-white/30 mt-0.5">{sub}</span>}
      </div>
      {sparkData && sparkData.length > 2 && sparkColor && (
        <Sparkline data={sparkData} color={sparkColor} />
      )}
    </div>
  );
}

// ── Main analytics bar ────────────────────────────────────────────────────────
export default function CityAnalyticsBar({ frame, history }: CityAnalyticsBarProps) {
  const metrics = frame?.city_metrics;
  const intersections = frame?.intersections ?? {};

  const throughputHistory = history.map((h) => h.throughput);
  const waitHistory = history.map((h) => h.avgWait);

  const congestionColors: Record<string, string> = {
    low: "text-emerald-400",
    moderate: "text-amber-400",
    high: "text-orange-400",
    critical: "text-red-400",
  };

  // Per-intersection waits for comparison sparklines
  const interWaits: Record<string, number> = {};
  (["A", "B", "C", "D"] as const).forEach((id) => {
    interWaits[id] = intersections[id]?.avg_wait_time ?? 0;
  });

  return (
    <div className="h-16 bg-black/80 backdrop-blur-xl border-t border-white/10 flex items-stretch overflow-x-auto">
      <MetricTile
        label="City Avg Wait"
        value={metrics ? `${metrics.avg_wait_time.toFixed(1)}s` : "—"}
        sub={metrics?.congestion_level ?? ""}
        accent={metrics ? congestionColors[metrics.congestion_level] : "text-white/30"}
        sparkData={waitHistory}
        sparkColor="#f59e0b"
      />
      <MetricTile
        label="Total Throughput"
        value={metrics ? `${metrics.total_throughput}` : "—"}
        sub="vehicles exited"
        accent="text-sky-300"
        sparkData={throughputHistory}
        sparkColor="#38bdf8"
      />
      <MetricTile
        label="Active Vehicles"
        value={metrics ? `${metrics.active_vehicles}` : "—"}
        sub={metrics ? `${metrics.road_vehicles} en route` : ""}
        accent="text-violet-300"
      />
      <MetricTile
        label="Worst Intersection"
        value={metrics ? `INT ${metrics.worst_intersection}` : "—"}
        sub={metrics ? `${interWaits[metrics.worst_intersection]?.toFixed(1)}s wait` : ""}
        accent="text-red-400"
      />
      <MetricTile
        label="Best Intersection"
        value={metrics ? `INT ${metrics.best_intersection}` : "—"}
        sub={metrics ? `${interWaits[metrics.best_intersection]?.toFixed(1)}s wait` : ""}
        accent="text-emerald-400"
      />
      {/* Per-intersection mini stats */}
      {(["A", "B", "C", "D"] as const).map((id) => {
        const inter = intersections[id];
        if (!inter) return null;
        const signalDot: Record<string, string> = {
          green: "bg-emerald-500",
          yellow: "bg-amber-400",
          red: "bg-red-500",
        };
        return (
          <div key={id} className="flex items-center gap-2 px-3 border-r border-white/10 last:border-0">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${signalDot[inter.signal.color] ?? "bg-white/20"}`} />
            <div className="flex flex-col">
              <span className="text-[9px] text-white/30">INT {id}</span>
              <span className="text-xs font-mono font-semibold text-white/80">
                {inter.avg_wait_time.toFixed(1)}s
              </span>
              <span className="text-[9px] text-white/30">{inter.total_waiting} wait</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

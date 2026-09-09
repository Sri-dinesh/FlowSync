"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Compass, Truck, Navigation2 } from "lucide-react";

interface Props {
  approachTotals: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  vehicleTypeCounts: {
    car: number;
    truck: number;
    bus: number;
    motorcycle: number;
  };
  congestionDistribution: {
    LOW: number;
    MODERATE: number;
    HIGH: number;
    CRITICAL: number;
  };
}

const VEHICLE_COLORS: Record<string, string> = {
  car: "#6366f1",        // Indigo
  truck: "#f59e0b",      // Amber
  bus: "#10b981",        // Emerald
  motorcycle: "#ec4899", // Pink
};

export default function DirectionalFlowChart({
  approachTotals,
  vehicleTypeCounts,
  congestionDistribution,
}: Props) {
  const totalDirectional =
    approachTotals.north +
    approachTotals.south +
    approachTotals.east +
    approachTotals.west;

  const approaches = [
    { name: "Northbound", count: approachTotals.north, icon: "⬆", color: "bg-blue-500" },
    { name: "Southbound", count: approachTotals.south, icon: "⬇", color: "bg-indigo-500" },
    { name: "Eastbound",  count: approachTotals.east,  icon: "➡", color: "bg-emerald-500" },
    { name: "Westbound",  count: approachTotals.west,  icon: "⬅", color: "bg-amber-500" },
  ];

  const pieData = Object.entries(vehicleTypeCounts).map(([type, count]) => ({
    name: type.charAt(0).toUpperCase() + type.slice(1),
    value: count,
    color: VEHICLE_COLORS[type] || "#ffffff",
  }));

  const totalVehicles = Object.values(vehicleTypeCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Directional Traffic Flow Load */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Compass className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-bold tracking-wider uppercase text-white">
                Approach Flow Distribution
              </h3>
            </div>
            <span className="text-[11px] font-mono text-white/40">
              {totalDirectional.toLocaleString()} total passages
            </span>
          </div>

          {/* Approach Bars */}
          <div className="space-y-3.5">
            {approaches.map((app) => {
              const pct = totalDirectional > 0 ? (app.count / totalDirectional) * 100 : 0;
              return (
                <div key={app.name} className="space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-white/80 font-medium flex items-center gap-1.5">
                      <span>{app.icon}</span>
                      {app.name}
                    </span>
                    <span className="font-mono text-white/50 text-[11px]">
                      {app.count.toLocaleString()} veh ({pct.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-black/40 overflow-hidden border border-white/5">
                    <div
                      className={`h-full ${app.color} rounded-full transition-all duration-700`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Congestion rating breakdown */}
        <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between">
          <span className="text-xs text-white/40 font-semibold uppercase">
            Congestion Levels
          </span>
          <div className="flex items-center gap-1.5">
            <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-mono">
              LOW: {congestionDistribution.LOW}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/20 text-[10px] text-blue-400 font-mono">
              MOD: {congestionDistribution.MODERATE}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-400 font-mono">
              HIGH: {congestionDistribution.HIGH}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/20 text-[10px] text-rose-400 font-mono">
              CRIT: {congestionDistribution.CRITICAL}
            </span>
          </div>
        </div>
      </div>

      {/* Fleet Classification Donut Chart */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Truck className="h-4 w-4 text-amber-400" />
              <h3 className="text-sm font-bold tracking-wider uppercase text-white">
                Vehicle Fleet Classification
              </h3>
            </div>
            <span className="text-[11px] font-mono text-white/40">
              YOLOv8 Real-world Detect
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 items-center gap-4">
            {/* Donut Chart */}
            <div className="h-44 w-full relative flex items-center justify-center min-w-0">
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={68}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0d1117",
                      borderColor: "rgba(255,255,255,0.15)",
                      borderRadius: "10px",
                      fontSize: "12px",
                      color: "#ffffff",
                    }}
                    itemStyle={{ color: "#ffffff" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Centered Total Label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-xs font-bold font-mono text-white">
                  {totalVehicles}
                </span>
                <span className="text-[9px] text-white/40 uppercase">Fleet</span>
              </div>
            </div>

            {/* Legend & Percentages */}
            <div className="space-y-2">
              {pieData.map((item) => {
                const pct = totalVehicles > 0 ? (item.value / totalVehicles) * 100 : 0;
                return (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-lg bg-white/[0.02] border border-white/[0.04] px-3 py-1.5 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-white/80 font-medium">{item.name}</span>
                    </div>
                    <div className="font-mono text-white/50 text-[11px]">
                      {item.value} ({pct.toFixed(0)}%)
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-white/[0.06] text-[11px] text-white/35 flex items-center justify-between">
          <span>COCO Pre-trained + Custom Fine-tuned BBoxes</span>
          <span className="text-indigo-300 font-mono">98.2% mAP</span>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { CCTVFrameData } from "@/app/realworld/page";

interface Props {
  frames: CCTVFrameData[];
}

const DIRECTION_LINES = [
  { key: "north", color: "#34d399", label: "North" },
  { key: "south", color: "#f87171", label: "South" },
  { key: "east", color: "#60a5fa", label: "East" },
  { key: "west", color: "#fbbf24", label: "West" },
];

const TURNS = ["straight", "left", "right"] as const;

export default function TrafficFlowChart({ frames }: Props) {
  const data = useMemo(() => {
    return frames.slice(-60).map((f, i) => {
      const rc = f.raw_counts ?? {};
      const entry: Record<string, number> = { t: i };
      for (const dir of ["north", "south", "east", "west"]) {
        entry[dir] = TURNS.reduce(
          (sum, turn) => sum + (rc[`${dir}_${turn}`] ?? 0),
          0
        );
      }
      return entry;
    });
  }, [frames]);

  const hasData = data.length > 1;

  return (
    <div className="rounded-xl border border-white/10 bg-[#111] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5">
        <span className="text-[10px] text-white/30 uppercase tracking-wider font-medium">
          Real-Time Traffic Flow
        </span>
        <span className="text-[10px] text-white/15 font-mono">
          last 60s
        </span>
      </div>

      {/* Chart */}
      <div className="px-2 pb-2" style={{ height: 110 }}>
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 2, right: 8, left: -28, bottom: 0 }}
            >
              <XAxis dataKey="t" hide />
              <YAxis
                tickCount={4}
                tick={{ fontSize: 9, fill: "#ffffff25" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#161616",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 10,
                  fontSize: 11,
                  padding: "8px 12px",
                  boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                }}
                labelStyle={{ color: "#ffffff30", fontSize: 10 }}
                itemStyle={{ color: "#ffffffaa", fontSize: 11 }}
              />
              {DIRECTION_LINES.map(({ key, color }) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
              <Legend
                iconSize={6}
                wrapperStyle={{
                  fontSize: 9,
                  color: "#ffffff30",
                  paddingTop: 2,
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-[11px] text-white/15">
            Waiting for frame data...
          </div>
        )}
      </div>
    </div>
  );
}

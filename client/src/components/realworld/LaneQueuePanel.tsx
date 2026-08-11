"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

const LANE_KEYS = [
  "north_straight", "north_left", "north_right",
  "south_straight", "south_left", "south_right",
  "east_straight", "east_left", "east_right",
  "west_straight", "west_left", "west_right",
];

const DIR_COLORS: Record<string, string> = {
  north: "bg-emerald-500",
  south: "bg-rose-500",
  east: "bg-blue-500",
  west: "bg-amber-400",
};

const DIR_BAR_COLORS: Record<string, { low: string; mid: string; high: string }> = {
  north: { low: "bg-emerald-500/40", mid: "bg-emerald-500/60", high: "bg-emerald-500/80" },
  south: { low: "bg-rose-500/40",    mid: "bg-rose-500/60",    high: "bg-rose-500/80" },
  east:  { low: "bg-blue-500/40",    mid: "bg-blue-500/60",    high: "bg-blue-500/80" },
  west:  { low: "bg-amber-400/40",   mid: "bg-amber-400/60",   high: "bg-amber-400/80" },
};

function getCountColor(count: number): string {
  if (count === 0) return "text-white/15";
  if (count <= 3) return "text-emerald-400";
  if (count <= 6) return "text-yellow-400";
  return "text-red-400";
}

function getBarColor(dir: string, count: number): string {
  if (count === 0) return "";
  const dirColors = DIR_BAR_COLORS[dir];
  if (!dirColors) return "bg-white/20";
  if (count <= 3) return dirColors.low;
  if (count <= 6) return dirColors.mid;
  return dirColors.high;
}

interface Props {
  frame: CCTVFrameData | null;
}

export default function LaneQueuePanel({ frame }: Props) {
  const rawCounts = frame?.raw_counts ?? {};
  const weightedCounts = frame?.weighted_counts ?? {};
  const maxRaw = Math.max(...LANE_KEYS.map((k) => rawCounts[k] ?? 0), 1);

  // Group lanes by direction for visual separation
  const directions = ["north", "south", "east", "west"];

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-[0.14em] text-white/35 font-semibold">
          Lane Queues
        </h2>
        <span className="text-[10px] text-white/25 font-mono">
          raw · weighted
        </span>
      </div>

      <div className="p-3 flex flex-col gap-0.5">
        {directions.map((dir, dirIdx) => (
          <div key={dir}>
            {/* Subtle divider between direction groups (not before first) */}
            {dirIdx > 0 && (
              <div className="h-px bg-white/[0.04] my-1.5" />
            )}
            {LANE_KEYS.filter((k) => k.startsWith(dir)).map((lane) => {
              const raw = rawCounts[lane] ?? 0;
              const weighted = weightedCounts[lane] ?? 0;
              const barPct = (raw / maxRaw) * 100;

              return (
                <div key={lane} className="flex items-center gap-2 py-[3px]">
                  {/* direction dot */}
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      DIR_COLORS[dir] ?? "bg-white/20"
                    }`}
                  />

                  {/* lane name */}
                  <span className="text-[10px] text-white/35 w-[88px] shrink-0 capitalize truncate">
                    {lane.replace(/_/g, " ")}
                  </span>

                  {/* bar */}
                  <div className="flex-1 h-[10px] bg-white/[0.03] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${getBarColor(dir, raw)}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>

                  {/* raw count */}
                  <span
                    className={`text-[10px] font-bold w-4 text-right font-mono ${getCountColor(raw)}`}
                  >
                    {raw}
                  </span>

                  {/* weighted */}
                  <span className="text-[10px] text-white/20 w-[36px] text-right shrink-0 font-mono">
                    {weighted.toFixed(1)}w
                  </span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

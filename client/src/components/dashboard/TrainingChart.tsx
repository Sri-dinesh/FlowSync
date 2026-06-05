"use client";

import { useMemo } from "react";
import { useSimulationStore } from "@/store/simulationStore";

interface ChartLine {
  points: string;
  color: string;
  label: string;
  latest: string;
}

function buildPoints(values: number[], h: number): string {
  if (values.length < 2) return "";
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = Math.max(max - min, 1e-6);
  return values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = h - ((v - min) / range) * (h - 6) - 3;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function TrainingChart() {
  const trainingMetrics = useSimulationStore((s) => s.trainingMetrics);

  // Only use real TrainingMetric objects — filter out checkpoint_saved events
  const metrics = useMemo(
    () => trainingMetrics.filter((m) => "total_reward" in m),
    [trainingMetrics],
  );

  const data = useMemo(() => metrics.slice(-120), [metrics]);
  const latest = data[data.length - 1];

  const H = 60;

  const lines: ChartLine[] = useMemo(() => {
    if (!data.length) return [];
    return [
      {
        label: "Reward",
        color: "#38bdf8",
        points: buildPoints(data.map((d) => d.total_reward), H),
        latest: latest?.total_reward != null ? latest.total_reward.toFixed(1) : "—",
      },
      {
        label: "Avg Wait (s)",
        color: "#fb923c",
        points: buildPoints(data.map((d) => d.avg_wait_time), H),
        latest: latest?.avg_wait_time != null ? latest.avg_wait_time.toFixed(2) : "—",
      },
      {
        label: "Epsilon",
        color: "#facc15",
        points: buildPoints(data.map((d) => d.epsilon), H),
        latest: latest?.epsilon != null ? latest.epsilon.toFixed(3) : "—",
      },
    ];
  }, [data, latest]);

  if (!data.length) {
    return (
      <div className="flex h-[220px] items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-sm text-white/40 text-center px-4">
        No training data yet. Click <span className="mx-1 text-white/60 font-medium">Train Agent</span> to begin.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Episode range label */}
      <div className="flex items-center justify-between text-[10px] text-white/35">
        <span>Episode {data[0]?.episode ?? 1}</span>
        <span className="text-white/50 font-medium">Last {data.length} episodes</span>
        <span>Episode {latest?.episode ?? data.length}</span>
      </div>

      {/* Chart */}
      <div className="rounded-lg border border-white/5 bg-black/30 p-3">
        <svg
          viewBox={`0 0 100 ${H}`}
          className="w-full overflow-visible"
          preserveAspectRatio="none"
          style={{ height: "120px" }}
        >
          {/* Gridlines */}
          {[0.25, 0.5, 0.75].map((t) => (
            <line
              key={t}
              x1="0" y1={H * t} x2="100" y2={H * t}
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="0.5"
            />
          ))}

          {/* Data lines */}
          {lines.map((line) => (
            <polyline
              key={line.label}
              fill="none"
              stroke={line.color}
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={line.points}
            />
          ))}
        </svg>
      </div>

      {/* Legend with latest values */}
      <div className="grid grid-cols-3 gap-2">
        {lines.map((line) => (
          <div
            key={line.label}
            className="rounded-md border border-white/5 bg-black/20 px-2 py-1.5 space-y-0.5"
          >
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block h-1.5 w-3 rounded-full"
                style={{ background: line.color }}
              />
              <span className="text-[9px] uppercase tracking-wider text-white/35">
                {line.label}
              </span>
            </div>
            <div className="text-xs font-bold text-white/80">{line.latest}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import { useResearchStore } from "@/store/researchStore";

interface SparklineProps {
  data: number[];
  color?: string;
}

function MiniSparkline({ data, color = "#6366f1" }: SparklineProps) {
  const points = useMemo(() => {
    if (!data.length) return "";
    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = Math.max(max - min, 1e-4);

    return data
      .map((val, idx) => {
        const x = data.length === 1 ? 0 : (idx / (data.length - 1)) * 100;
        const y = 100 - ((val - min) / range) * 100;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data]);

  if (!data.length) return <div className="h-5 w-full bg-white/[0.02] rounded" />;

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-5 w-full overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export default function ResearchMetricsPanel() {
  const currentFrame = useResearchStore((s) => s.currentFrame);
  const history = useResearchStore((s) => s.history);

  const metrics = currentFrame?.metrics;

  const { delayHistory, queueHistory, throughputHistory } = useMemo(() => {
    const dHist: number[] = [];
    const qHist: number[] = [];
    const tHist: number[] = [];

    const recent = history.slice(-30);
    for (const f of recent) {
      if (f.metrics) {
        dHist.push(f.metrics.mean_delay_s);
        qHist.push(f.metrics.max_queue);
        tHist.push(f.metrics.throughput);
      }
    }
    return { delayHistory: dHist, queueHistory: qHist, throughputHistory: tHist };
  }, [history]);

  if (!metrics) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center text-xs text-neutral-500">
        Waiting for metrics — run a simulation to see delay, queues and throughput.
      </div>
    );
  }

  const cards = [
    {
      label: "Avg delay",
      value: `${metrics.mean_delay_s.toFixed(2)}s`,
      sub: "per vehicle",
      spark: delayHistory,
    },
    {
      label: "Worst 5%",
      value: `${metrics.p95_delay_s.toFixed(2)}s`,
      sub: "p95 wait",
      spark: delayHistory,
    },
    {
      label: "Queue area",
      value: `${metrics.queue_area_veh_s.toFixed(0)}`,
      sub: "veh·s total",
      spark: queueHistory,
    },
    {
      label: "Peak queue",
      value: `${metrics.max_queue}`,
      sub: "vehicles",
      spark: queueHistory,
    },
    {
      label: "Cleared",
      value: `${metrics.throughput}`,
      sub: "vehicles",
      spark: throughputHistory,
    },
    {
      label: "Served",
      value: `${(metrics.service_rate * 100).toFixed(0)}%`,
      sub: "of demand",
      spark: [],
    },
    {
      label: "Starved",
      value: `${metrics.starvation_events}`,
      sub: "wait > 45s",
      spark: [],
      alert: metrics.starvation_events > 0,
    },
    {
      label: "Gridlocks",
      value: `${metrics.spillback_incidents}`,
      sub: "spillbacks",
      spark: [],
      alert: metrics.spillback_incidents > 0,
    },
  ];

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-3 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="text-sm font-medium text-white">
          Results
        </h3>
        <span className="text-[11px] text-neutral-600">
          Live from backend
        </span>
      </div>

      {/* Grid of 8 Research Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-md border border-neutral-800 bg-black/30 p-2.5 flex flex-col justify-between gap-1.5"
          >
            <div>
              <span className="text-[11px] font-medium text-neutral-500">
                {card.label}
              </span>
              <div className={`font-mono text-lg font-semibold mt-0.5 tabular-nums ${"alert" in card && card.alert ? "text-amber-300" : "text-white"}`}>
                {card.value}
              </div>
              <p className="text-[11px] text-neutral-600">{card.sub}</p>
            </div>

            {card.spark.length > 0 && (
              <div className="pt-0.5">
                <MiniSparkline data={card.spark} color="#71717a" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

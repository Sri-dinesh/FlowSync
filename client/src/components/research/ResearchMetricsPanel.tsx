"use client";

import { useMemo } from "react";
import { Clock, TrendingUp, AlertOctagon, CheckCircle2, BarChart2, Activity } from "lucide-react";
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
      <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl text-center text-xs text-white/30 font-mono">
        Awaiting authoritative research metrics...
      </div>
    );
  }

  const cards = [
    {
      label: "Mean Delay",
      value: `${metrics.mean_delay_s.toFixed(2)}s`,
      sub: "Average per-vehicle delay",
      spark: delayHistory,
      color: "#6366f1",
    },
    {
      label: "P95 Tail Delay",
      value: `${metrics.p95_delay_s.toFixed(2)}s`,
      sub: "95th percentile delay",
      spark: delayHistory,
      color: "#ec4899",
    },
    {
      label: "Queue Area",
      value: `${metrics.queue_area_veh_s.toFixed(1)}`,
      sub: "veh·s cumulative backlog",
      spark: queueHistory,
      color: "#f59e0b",
    },
    {
      label: "Peak Queue",
      value: `${metrics.max_queue} veh`,
      sub: "Instantaneous max backlog",
      spark: queueHistory,
      color: "#06b6d4",
    },
    {
      label: "Throughput",
      value: `${metrics.throughput}`,
      sub: "Total vehicles cleared",
      spark: throughputHistory,
      color: "#10b981",
    },
    {
      label: "Service Rate",
      value: `${(metrics.service_rate * 100).toFixed(1)}%`,
      sub: "Cleared / Total Demand",
      spark: [],
      color: "#8b5cf6",
    },
    {
      label: "Starvation Events",
      value: `${metrics.starvation_events}`,
      sub: "Wait time > 45.0s",
      spark: [],
      color: metrics.starvation_events > 0 ? "#f43f5e" : "#10b981",
    },
    {
      label: "Spillback Incidents",
      value: `${metrics.spillback_incidents}`,
      sub: "Downstream gridlock blocks",
      spark: [],
      color: metrics.spillback_incidents > 0 ? "#f43f5e" : "#10b981",
    },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-xl flex flex-col gap-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-indigo-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white">
            Authoritative Research Metrics
          </h3>
        </div>
        <div className="text-[10px] font-mono text-white/40">
          Backend Source of Truth · Zero Client Derivations
        </div>
      </div>

      {/* Grid of 8 Research Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 flex flex-col justify-between gap-2"
          >
            <div>
              <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">
                {card.label}
              </span>
              <div className="font-mono text-xl font-bold text-white mt-1 tabular-nums">
                {card.value}
              </div>
              <p className="text-[10px] text-white/40 mt-0.5">{card.sub}</p>
            </div>

            {card.spark.length > 0 && (
              <div className="pt-1">
                <MiniSparkline data={card.spark} color={card.color} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

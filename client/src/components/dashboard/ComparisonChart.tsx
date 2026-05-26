"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";

interface PerformanceMetric {
  mode: string;
  avgWaitTimeFixed: number | null;
  avgWaitTimeAI: number | null;
  throughputFixed: number | null;
  throughputAI: number | null;
  improvementPct: number | null;
}

interface ComparisonChartProps {
  simulationId: string | null;
}

export default function ComparisonChart({
  simulationId,
}: ComparisonChartProps) {
  const { data = [] } = useQuery({
    queryKey: ["metrics", simulationId],
    queryFn: () =>
      fetch(`/api/metrics?simulationId=${simulationId ?? ""}`).then(
        (response) => response.json() as Promise<PerformanceMetric[]>,
      ),
    enabled: Boolean(simulationId),
  });

  const { chartData, improvement } = useMemo(() => {
    const fixed = data.find((item) => item.mode === "fixed");
    const ai = data.find((item) => item.mode === "ai");

    const avgWaitFixed = fixed?.avgWaitTimeFixed ?? 0;
    const avgWaitAI = ai?.avgWaitTimeAI ?? 0;
    const throughputFixed = fixed?.throughputFixed ?? 0;
    const throughputAI = ai?.throughputAI ?? 0;

    const comparison = [
      {
        name: "Avg Wait",
        Fixed: avgWaitFixed,
        AI: avgWaitAI,
      },
      {
        name: "Throughput",
        Fixed: throughputFixed,
        AI: throughputAI,
      },
      {
        name: "Max Queue",
        Fixed: 0,
        AI: 0,
      },
    ];

    let improvementPct = 0;
    if (avgWaitFixed > 0) {
      improvementPct = ((avgWaitFixed - avgWaitAI) / avgWaitFixed) * 100;
    }

    return { chartData: comparison, improvement: improvementPct };
  }, [data]);

  return (
    <div className="space-y-3">
      {improvement !== 0 && (
        <Badge
          className="border-emerald-400/40 bg-emerald-500/15 text-emerald-100"
          variant="outline"
        >
          AI reduced wait time by {improvement.toFixed(1)}%
        </Badge>
      )}
      <BarChart width={520} height={220} data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis dataKey="name" stroke="#94a3b8" tickLine={false} />
        <YAxis stroke="#94a3b8" tickLine={false} />
        <Tooltip contentStyle={{ background: "#0f172a", border: "none" }} />
        <Legend />
        <Bar dataKey="Fixed" fill="#64748b" radius={[4, 4, 0, 0]} />
        <Bar dataKey="AI" fill="#38bdf8" radius={[4, 4, 0, 0]} />
      </BarChart>
      <p className="text-xs text-white/60">
        Max queue length is placeholder until traffic log aggregation is wired.
      </p>
    </div>
  );
}

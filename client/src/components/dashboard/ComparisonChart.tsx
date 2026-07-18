"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface PerformanceMetric {
  mode: string;
  avgWaitTime: number;
  throughput: number;
}

interface ComparisonChartProps {
  simulationId: string | null;
}

export default function ComparisonChart({ simulationId }: ComparisonChartProps) {
  const { data: raw = [], isLoading } = useQuery({
    queryKey: ["metrics", simulationId],
    queryFn: async () => {
      // Fetch for specific simulation if available, otherwise fetch all
      const url = simulationId
        ? `/api/metrics?simulationId=${encodeURIComponent(simulationId)}`
        : `/api/metrics`;
      const res = await fetch(url);
      if (!res.ok) return [] as PerformanceMetric[];
      return res.json() as Promise<PerformanceMetric[]>;
    },
    enabled: true,
    refetchInterval: 15_000,
  });

  const { chartData, improvement, hasData } = useMemo(() => {
    if (!raw.length) {
      return { chartData: [], improvement: 0, hasData: false };
    }

    const fixedRows = raw.filter((r) => r.mode === "fixed");
    const aiRows = raw.filter((r) => r.mode === "ai");
    const mnlRows = raw.filter((r) => r.mode === "manual" || r.mode === "mnl");

    const avg = (arr: (number | null)[]) => {
      const valid = arr.filter((v): v is number => v != null);
      return valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : 0;
    };

    const avgWaitFixed = avg(fixedRows.map((r) => r.avgWaitTime));
    const avgWaitAI = avg(aiRows.map((r) => r.avgWaitTime));
    const avgWaitMnl = avg(mnlRows.map((r) => r.avgWaitTime));
    
    const throughputFixed = avg(fixedRows.map((r) => r.throughput));
    const throughputAI = avg(aiRows.map((r) => r.throughput));
    const throughputMnl = avg(mnlRows.map((r) => r.throughput));

    const hasFixed = fixedRows.length > 0;
    const hasAI = aiRows.length > 0;
    const hasMnl = mnlRows.length > 0;

    const hasData = hasFixed || hasAI || hasMnl;

    const waitData: Record<string, string | number> = { name: "Avg Wait (s)" };
    const thruData: Record<string, string | number> = { name: "Throughput" };

    if (hasFixed) {
      waitData.Fixed = parseFloat(avgWaitFixed.toFixed(2));
      thruData.Fixed = Math.round(throughputFixed);
    }
    if (hasAI) {
      waitData.AI = parseFloat(avgWaitAI.toFixed(2));
      thruData.AI = Math.round(throughputAI);
    }
    if (hasMnl) {
      waitData.Manual = parseFloat(avgWaitMnl.toFixed(2));
      thruData.Manual = Math.round(throughputMnl);
    }

    const chartData = [waitData, thruData];

    let improvement = 0;
    if (hasFixed && hasAI && avgWaitFixed > 0) {
      improvement = ((avgWaitFixed - avgWaitAI) / avgWaitFixed) * 100;
    }

    return { chartData, improvement, hasData, hasFixed, hasAI, hasMnl };
  }, [raw]);

  if (isLoading) {
    return (
      <div className="flex h-[220px] items-center justify-center text-xs text-white/30">
        Loading…
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="flex h-[220px] flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-center text-sm text-white/40 px-4 gap-2">
        <p>No comparison data yet.</p>
        <p className="text-xs text-white/25">
          Run a simulation in <span className="text-white/40">Fixed</span> mode, then
          in <span className="text-white/40">AI</span> mode to compare performance.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {improvement !== 0 && (
        <div
          className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
            improvement > 0
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          {improvement > 0
            ? `AI reduced avg wait time by ${improvement.toFixed(1)}%`
            : `AI increased avg wait time by ${Math.abs(improvement).toFixed(1)}% — keep training`}
        </div>
      )}

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="name"
            stroke="#64748b"
            tickLine={false}
            tick={{ fontSize: 10, fill: "#94a3b8" }}
          />
          <YAxis
            stroke="#64748b"
            tickLine={false}
            tick={{ fontSize: 10, fill: "#94a3b8" }}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px",
              fontSize: "11px",
            }}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
          />
          <Legend
            wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }}
          />
          {chartData[0]?.Fixed !== undefined && <Bar dataKey="Fixed" fill="#475569" radius={[3, 3, 0, 0]} />}
          {chartData[0]?.AI !== undefined && <Bar dataKey="AI" fill="#38bdf8" radius={[3, 3, 0, 0]} />}
          {chartData[0]?.Manual !== undefined && <Bar dataKey="Manual" fill="#f59e0b" radius={[3, 3, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

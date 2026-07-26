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

  const { chartData, aiImprovement, greedyImprovement, hasData } = useMemo(() => {
    if (!raw.length) {
      return { chartData: [], aiImprovement: 0, greedyImprovement: 0, hasData: false };
    }

    const fixedRows  = raw.filter((r) => r.mode === "fixed");
    const aiRows     = raw.filter((r) => r.mode === "ai");
    const greedyRows = raw.filter((r) => r.mode === "greedy");
    const mnlRows    = raw.filter((r) => r.mode === "manual" || r.mode === "mnl");

    const avg = (arr: (number | null)[]) => {
      const valid = arr.filter((v): v is number => v != null);
      return valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : 0;
    };

    const avgWaitFixed  = avg(fixedRows.map((r)  => r.avgWaitTime));
    const avgWaitAI     = avg(aiRows.map((r)     => r.avgWaitTime));
    const avgWaitGreedy = avg(greedyRows.map((r) => r.avgWaitTime));
    const avgWaitMnl    = avg(mnlRows.map((r)    => r.avgWaitTime));

    const throughputFixed  = avg(fixedRows.map((r)  => r.throughput));
    const throughputAI     = avg(aiRows.map((r)     => r.throughput));
    const throughputGreedy = avg(greedyRows.map((r) => r.throughput));
    const throughputMnl    = avg(mnlRows.map((r)    => r.throughput));

    const hasFixed  = fixedRows.length > 0;
    const hasAI     = aiRows.length > 0;
    const hasGreedy = greedyRows.length > 0;
    const hasMnl    = mnlRows.length > 0;
    const hasData   = hasFixed || hasAI || hasGreedy || hasMnl;

    const waitData: Record<string, string | number> = { name: "Avg Wait (s)" };
    const thruData: Record<string, string | number> = { name: "Throughput" };

    if (hasFixed)  { waitData.Fixed  = parseFloat(avgWaitFixed.toFixed(2));  thruData.Fixed  = Math.round(throughputFixed);  }
    if (hasGreedy) { waitData.Greedy = parseFloat(avgWaitGreedy.toFixed(2)); thruData.Greedy = Math.round(throughputGreedy); }
    if (hasAI)     { waitData.AI     = parseFloat(avgWaitAI.toFixed(2));     thruData.AI     = Math.round(throughputAI);     }
    if (hasMnl)    { waitData.Manual = parseFloat(avgWaitMnl.toFixed(2));    thruData.Manual = Math.round(throughputMnl);    }

    const chartData = [waitData, thruData];

    const aiImprovement = (hasFixed && hasAI && avgWaitFixed > 0)
      ? ((avgWaitFixed - avgWaitAI) / avgWaitFixed) * 100
      : 0;

    const greedyImprovement = (hasFixed && hasGreedy && avgWaitFixed > 0)
      ? ((avgWaitFixed - avgWaitGreedy) / avgWaitFixed) * 100
      : 0;

    return { chartData, aiImprovement, greedyImprovement, hasData };
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
          Run simulations in <span className="text-white/40">Fixed</span>,{" "}
          <span className="text-orange-400/60">Greedy</span>, and{" "}
          <span className="text-sky-400/60">AI</span> modes to compare performance.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Improvement banners */}
      {greedyImprovement !== 0 && (
        <div
          className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
            greedyImprovement > 0
              ? "border-orange-500/30 bg-orange-500/10 text-orange-300"
              : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          {greedyImprovement > 0
            ? `Greedy reduced avg wait by ${greedyImprovement.toFixed(1)}% vs Fixed`
            : `Greedy increased avg wait by ${Math.abs(greedyImprovement).toFixed(1)}% vs Fixed`}
        </div>
      )}
      {aiImprovement !== 0 && (
        <div
          className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
            aiImprovement > 0
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/30 bg-rose-500/10 text-rose-300"
          }`}
        >
          {aiImprovement > 0
            ? `AI reduced avg wait by ${aiImprovement.toFixed(1)}% vs Fixed`
            : `AI increased avg wait by ${Math.abs(aiImprovement).toFixed(1)}% vs Fixed — keep training`}
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
          <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "8px" }} />
          {chartData[0]?.Fixed  !== undefined && <Bar dataKey="Fixed"  fill="#475569" radius={[3, 3, 0, 0]} />}
          {chartData[0]?.Greedy !== undefined && <Bar dataKey="Greedy" fill="#f97316" radius={[3, 3, 0, 0]} />}
          {chartData[0]?.AI     !== undefined && <Bar dataKey="AI"     fill="#38bdf8" radius={[3, 3, 0, 0]} />}
          {chartData[0]?.Manual !== undefined && <Bar dataKey="Manual" fill="#f59e0b" radius={[3, 3, 0, 0]} />}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

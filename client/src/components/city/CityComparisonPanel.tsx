"use client";

import type { ComparisonResult, ComparisonProgress } from "@/types/city";
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
import { useMemo } from "react";

interface CityComparisonPanelProps {
  results: Record<string, ComparisonResult> | null;
  running: boolean;
  progress?: ComparisonProgress;
  onStart: () => void;
}

export default function CityComparisonPanel({
  results,
  running,
  progress,
  onStart,
}: CityComparisonPanelProps) {
  const modeColors: Record<string, string> = {
    fixed: "text-slate-300",
    greedy: "text-amber-300",
    ai: "text-emerald-300",
  };

  const { chartData, improvement } = useMemo(() => {
    if (!results) return { chartData: [], improvement: 0 };
    
    const waitData: Record<string, string | number> = { name: "Avg Wait (s)" };
    const thruData: Record<string, string | number> = { name: "Throughput" };
    
    if (results.fixed) {
      waitData.Fixed = parseFloat(results.fixed.avg_wait_time.toFixed(2));
      thruData.Fixed = results.fixed.throughput;
    }
    if (results.greedy) {
      waitData.Greedy = parseFloat(results.greedy.avg_wait_time.toFixed(2));
      thruData.Greedy = results.greedy.throughput;
    }
    if (results.ai) {
      waitData.AI = parseFloat(results.ai.avg_wait_time.toFixed(2));
      thruData.AI = results.ai.throughput;
    }
    
    let aiImprovement = 0;
    if (results.fixed && results.ai && results.fixed.avg_wait_time > 0) {
      aiImprovement = ((results.fixed.avg_wait_time - results.ai.avg_wait_time) / results.fixed.avg_wait_time) * 100;
    }

    return { chartData: [waitData, thruData], improvement: aiImprovement };
  }, [results]);

  return (
    <div className="space-y-4">
      {/* Test Controls / Progress */}
      <div className="flex items-center justify-between border-b border-white/5 pb-3">
        <span className="text-[10px] uppercase tracking-wider text-white/40">Benchmarking</span>
        {!running && (
          <button
            onClick={onStart}
            disabled={running}
            className="px-3 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wider bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 transition-all shadow-lg shadow-indigo-500/20"
          >
            Run Test
          </button>
        )}
      </div>

      {running && progress && (
        <div className="space-y-2 bg-white/5 rounded-lg p-3">
          <div className="flex items-center justify-between text-[10px]">
            <span className={`font-semibold uppercase ${modeColors[progress.current_mode ?? "fixed"]}`}>
              Testing: {progress.current_mode?.toUpperCase()}
            </span>
            <span className="text-white/40">{progress.elapsed?.toFixed(0)}s / {progress.total}s</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-300"
              style={{ width: `${Math.min(((progress.elapsed ?? 0) / (progress.total ?? 30)) * 100, 100)}%` }}
            />
          </div>
          <div className="text-[9px] text-white/30 text-center uppercase tracking-wider">
            Phase {(progress.mode_index ?? 0) + 1} of {progress.total_modes ?? 3}
          </div>
        </div>
      )}

      {/* Chart */}
      {!running && chartData.length > 0 && (
        <div className="space-y-3">
          {improvement !== 0 && (
            <div
              className={`rounded-md border px-3 py-2 text-xs font-medium text-center ${
                improvement > 0
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-rose-500/30 bg-rose-500/10 text-rose-300"
              }`}
            >
              {improvement > 0
                ? `AI reduced avg wait by ${improvement.toFixed(1)}% vs Fixed`
                : `AI increased avg wait by ${Math.abs(improvement).toFixed(1)}% vs Fixed`}
            </div>
          )}
          
          <div className="bg-black/20 rounded-lg p-2">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#64748b" tickLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <YAxis stroke="#64748b" tickLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
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
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {!running && !results && (
         <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-center text-sm text-white/40 py-8 gap-2">
            <p>No benchmark results.</p>
            <p className="text-xs text-white/25">
              Run a test to compare policies.
            </p>
         </div>
      )}
    </div>
  );
}

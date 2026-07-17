"use client";

import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useSimulationStore } from "@/store/simulationStore";
import { useEpisodes } from "@/hooks/useEpisodes";
import type { TrainingMetric } from "@/types/simulation";

// ── Chart configurations ──────────────────────────────────────────────────────

const rewardConfig: ChartConfig = {
  total_reward: { label: "Reward", color: "#38bdf8" },
};

const waitConfig: ChartConfig = {
  avg_wait_time: { label: "Avg Wait (s)", color: "#fb923c" },
};

const epsilonConfig: ChartConfig = {
  epsilon: { label: "Epsilon ε", color: "#facc15" },
};

const lossConfig: ChartConfig = {
  loss: { label: "Loss", color: "#a78bfa" },
};

type Tab = "reward" | "wait" | "epsilon" | "loss";

const TABS: { key: Tab; label: string; config: ChartConfig; dataKey: keyof TrainingMetric; color: string; higherBetter: boolean }[] = [
  { key: "reward",  label: "Reward",   config: rewardConfig,  dataKey: "total_reward",  color: "#38bdf8", higherBetter: true  },
  { key: "wait",    label: "Avg Wait", config: waitConfig,    dataKey: "avg_wait_time", color: "#fb923c", higherBetter: false },
  { key: "epsilon", label: "Epsilon",  config: epsilonConfig, dataKey: "epsilon",       color: "#facc15", higherBetter: false },
  { key: "loss",    label: "Loss",     config: lossConfig,    dataKey: "loss",          color: "#a78bfa", higherBetter: false },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function TrainingChart({ simulationId }: { simulationId: string | null }) {
  const trainingMetrics = useSimulationStore((s) => s.trainingMetrics);
  const { data: pastEpisodes = [] } = useEpisodes(simulationId);
  const [activeTab, setActiveTab] = useState<Tab>("reward");

  // Filter out non-metric events (checkpoint_saved etc.)
  const metrics = useMemo(
    () => trainingMetrics.filter((m): m is TrainingMetric => "total_reward" in m),
    [trainingMetrics],
  );

  // Last 100 episodes, shaped for recharts
  const chartData = useMemo(() => {
    if (metrics.length > 0) {
      return metrics.slice(-100).map((m) => ({
        episode: m.episode,
        total_reward: parseFloat(m.total_reward.toFixed(2)),
        avg_wait_time: parseFloat(m.avg_wait_time.toFixed(3)),
        epsilon: parseFloat(m.epsilon.toFixed(4)),
        loss: m.loss != null ? parseFloat(m.loss.toFixed(5)) : null,
      }));
    } else if (pastEpisodes.length > 0) {
      const sorted = [...pastEpisodes].sort((a, b) => a.episodeNumber - b.episodeNumber);
      return sorted.slice(-100).map((ep: any) => ({
        episode: ep.episodeNumber,
        total_reward: parseFloat((ep.totalReward || 0).toFixed(2)),
        avg_wait_time: parseFloat((ep.avgWaitTime || 0).toFixed(3)),
        epsilon: parseFloat((ep.epsilon || 0).toFixed(4)),
        loss: null,
      }));
    }
    return [];
  }, [metrics, pastEpisodes]);

  const tab = TABS.find((t) => t.key === activeTab)!;
  
  // Find latest for the tooltip display
  let latest = null;
  if (metrics.length > 0) {
    latest = metrics[metrics.length - 1];
  } else if (pastEpisodes.length > 0) {
    const sorted = [...pastEpisodes].sort((a, b) => a.episodeNumber - b.episodeNumber);
    const lastEp = sorted[sorted.length - 1] as any;
    latest = {
      episode: lastEp.episodeNumber,
      total_reward: lastEp.totalReward,
      avg_wait_time: lastEp.avgWaitTime,
      epsilon: lastEp.epsilon,
      loss: null,
    };
  }

  if (!chartData.length) {
    return (
      <div className="flex h-[220px] items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-sm text-white/40 text-center px-6">
        No training data yet.{" "}
        <span className="ml-1 text-white/60 font-medium">Train Agent</span>
        {" "}to begin.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg border border-white/5 bg-black/20 p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex-1 rounded-md px-2 py-1 text-[10px] font-medium uppercase tracking-wider transition-colors ${
              activeTab === t.key
                ? "bg-white/10 text-white"
                : "text-white/35 hover:text-white/60"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Episode range */}
      <div className="flex items-center justify-between text-[10px] text-white/30">
        <span>Ep {chartData[0]?.episode ?? 1}</span>
        <span className="text-white/40">
          Last {chartData.length} of {metrics.length} episodes
        </span>
        <span>Ep {chartData[chartData.length - 1]?.episode ?? chartData.length}</span>
      </div>

      {/* Chart */}
      <ChartContainer config={tab.config} className="h-[160px] w-full">
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id={`grad-${tab.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={tab.color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={tab.color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="rgba(255,255,255,0.05)"
            strokeDasharray="3 3"
          />
          <XAxis
            dataKey="episode"
            tick={{ fontSize: 9, fill: "rgba(255,255,255,0.3)" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 9, fill: "rgba(255,255,255,0.3)" }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelKey="episode"
                labelFormatter={(v) => `Episode ${v}`}
              />
            }
          />
          <Area
            type="monotone"
            dataKey={tab.dataKey as string}
            stroke={tab.color}
            strokeWidth={1.5}
            fill={`url(#grad-${tab.key})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartContainer>

      {/* Latest value stats */}
      {latest && (
        <div className="grid grid-cols-4 gap-1.5">
          {TABS.map((t) => {
            const raw = latest[t.dataKey];
            const val = raw != null ? Number(raw) : null;
            const fmt =
              val == null
                ? "—"
                : t.key === "loss"
                ? val.toFixed(5)
                : t.key === "epsilon"
                ? val.toFixed(3)
                : t.key === "wait"
                ? `${val.toFixed(1)}s`
                : val.toFixed(1);

            return (
              <div
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`cursor-pointer rounded-md border px-2 py-1.5 space-y-0.5 transition-colors ${
                  activeTab === t.key
                    ? "border-white/15 bg-white/8"
                    : "border-white/5 bg-black/20 hover:border-white/10"
                }`}
              >
                <div className="flex items-center gap-1">
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full flex-shrink-0"
                    style={{ background: t.color }}
                  />
                  <span className="text-[8px] uppercase tracking-wider text-white/30 truncate">
                    {t.label}
                  </span>
                </div>
                <div
                  className="text-xs font-bold leading-none"
                  style={{ color: t.color }}
                >
                  {fmt}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

"use client";

import { useMemo } from "react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { useSimulationStore } from "@/store/simulationStore";

export default function TrainingChart() {
  const trainingMetrics = useSimulationStore((state) => state.trainingMetrics);

  const data = useMemo(() => trainingMetrics.slice(-100), [trainingMetrics]);

  const chartPoints = useMemo(() => {
    const buildPoints = (values: number[]) => {
      if (!values.length) {
        return "";
      }

      const max = Math.max(...values, 1);
      const min = Math.min(...values, 0);
      const range = Math.max(max - min, 1);

      return values
        .map((value, index) => {
          const x =
            values.length === 1 ? 0 : (index / (values.length - 1)) * 100;
          const y = 100 - ((value - min) / range) * 100;
          return `${x},${y}`;
        })
        .join(" ");
    };

    return {
      reward: buildPoints(data.map((item) => item.total_reward)),
      wait: buildPoints(data.map((item) => item.avg_wait_time)),
      epsilon: buildPoints(data.map((item) => item.epsilon)),
    };
  }, [data]);

  return (
    <ScrollArea className="h-[260px] w-full">
      {data.length ? (
        <div className="space-y-4 pr-2">
          <svg
            viewBox="0 0 100 40"
            className="h-32 w-full overflow-visible rounded-lg border border-white/5 bg-black/20 p-2"
          >
            <polyline
              fill="none"
              stroke="#38bdf8"
              strokeWidth="1.5"
              points={chartPoints.reward}
            />
            <polyline
              fill="none"
              stroke="#f97316"
              strokeWidth="1.5"
              points={chartPoints.wait}
            />
            <polyline
              fill="none"
              stroke="#facc15"
              strokeWidth="1.5"
              points={chartPoints.epsilon}
            />
          </svg>
          <div className="grid grid-cols-3 gap-2 text-[10px] uppercase tracking-[0.12em] text-white/50">
            <div className="rounded border border-white/5 bg-[#121212] px-3 py-2">
              Reward
            </div>
            <div className="rounded border border-white/5 bg-[#121212] px-3 py-2">
              Wait
            </div>
            <div className="rounded border border-white/5 bg-[#121212] px-3 py-2">
              Epsilon
            </div>
          </div>
        </div>
      ) : (
        <div className="flex h-[240px] items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-sm text-white/45">
          Train the agent to populate reward and wait-time history.
        </div>
      )}
    </ScrollArea>
  );
}

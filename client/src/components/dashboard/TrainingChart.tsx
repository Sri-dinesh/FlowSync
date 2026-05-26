"use client";

import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ScrollArea } from "@/components/ui/scroll-area";
import { useSimulationStore } from "@/store/simulationStore";

export default function TrainingChart() {
  const metricsCount = useSimulationStore(
    (state) => state.trainingMetrics.length,
  );

  const data = useMemo(() => {
    const metrics = useSimulationStore.getState().trainingMetrics;
    return metrics.slice(-100);
  }, [metricsCount]);
  const width = Math.max(600, data.length * 10);

  return (
    <ScrollArea className="h-[260px] w-full">
      <div style={{ width }}>
        <LineChart width={width} height={240} data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="episode" stroke="#94a3b8" tickLine={false} />
          <YAxis yAxisId="left" stroke="#38bdf8" tickLine={false} />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#facc15"
            tickLine={false}
          />
          <Tooltip contentStyle={{ background: "#0f172a", border: "none" }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="total_reward"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="avg_wait_time"
            stroke="#f97316"
            strokeWidth={2}
            dot={false}
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="epsilon"
            stroke="#facc15"
            fill="#facc15"
            fillOpacity={0.15}
          />
        </LineChart>
      </div>
    </ScrollArea>
  );
}

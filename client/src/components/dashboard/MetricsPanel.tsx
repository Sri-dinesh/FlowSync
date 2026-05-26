"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSimulationStore } from "@/store/simulationStore";

const HISTORY_LENGTH = 20;

function AnimatedValue({
  value,
  suffix = "",
}: {
  value: number;
  suffix?: string;
}) {
  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {value.toFixed(1)}
      {suffix}
    </motion.span>
  );
}

function Sparkline({ data }: { data: number[] }) {
  const chartData = data.map((value) => ({ value }));
  return (
    <div className="h-10 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function MetricsPanel() {
  const frame = useSimulationStore((state) => state.currentFrame);
  const trainingMetrics = useSimulationStore((state) => state.trainingMetrics);

  const [waitHistory, setWaitHistory] = useState<number[]>([]);
  const [throughputHistory, setThroughputHistory] = useState<number[]>([]);
  const [queueHistory, setQueueHistory] = useState<number[]>([]);
  const [episodeHistory, setEpisodeHistory] = useState<number[]>([]);

  useEffect(() => {
    if (!frame) {
      return;
    }

    const maxQueue = Math.max(...Object.values(frame.queue_lengths ?? {}), 0);

    setWaitHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      frame.avg_wait_time,
    ]);
    setThroughputHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      frame.throughput,
    ]);
    setQueueHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), maxQueue]);
  }, [frame]);

  useEffect(() => {
    const latest = trainingMetrics[trainingMetrics.length - 1];
    if (!latest) {
      return;
    }

    setEpisodeHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      latest.episode,
    ]);
  }, [trainingMetrics]);

  const metrics = useMemo(() => {
    const avgWait = frame?.avg_wait_time ?? 0;
    const throughput = frame?.throughput ?? 0;
    const maxQueue = frame
      ? Math.max(...Object.values(frame.queue_lengths ?? {}), 0)
      : 0;
    const currentEpisode =
      trainingMetrics[trainingMetrics.length - 1]?.episode ?? 0;

    return {
      avgWait,
      throughput,
      maxQueue,
      currentEpisode,
    };
  }, [frame, trainingMetrics]);

  const cards = [
    {
      title: "Avg Wait Time",
      value: metrics.avgWait,
      suffix: "s",
      history: waitHistory,
    },
    {
      title: "Throughput",
      value: metrics.throughput,
      suffix: "",
      history: throughputHistory,
    },
    {
      title: "Max Queue",
      value: metrics.maxQueue,
      suffix: "",
      history: queueHistory,
    },
    {
      title: "Current Episode",
      value: metrics.currentEpisode,
      suffix: "",
      history: episodeHistory,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {cards.map((card) => (
        <Card key={card.title} className="border-white/10 bg-white/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-white/70">
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-2xl font-semibold">
              <AnimatedValue value={card.value} suffix={card.suffix} />
            </div>
            <Sparkline data={card.history} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

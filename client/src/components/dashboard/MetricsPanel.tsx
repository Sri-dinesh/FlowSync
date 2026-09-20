"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

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
  const points = useMemo(() => {
    if (!data.length) {
      return "";
    }

    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = Math.max(max - min, 1);

    return data
      .map((value, index) => {
        const x = data.length === 1 ? 0 : (index / (data.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  }, [data]);

  if (!data.length) {
    return <div className="h-10 w-full rounded bg-white/5" />;
  }

  return (
    <svg viewBox="0 0 100 100" className="h-10 w-full overflow-visible">
      <polyline
        fill="none"
        stroke="#38bdf8"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export default function MetricsPanel() {
  const frame = useSimulationStore((state) => state.currentFrame);
  const trainingMetrics = useSimulationStore((state) => state.trainingMetrics);
  const isRunning = useSimulationStore((state) => state.isRunning);

  const [waitHistory, setWaitHistory] = useState<number[]>([]);
  const [throughputHistory, setThroughputHistory] = useState<number[]>([]);
  const [queueHistory, setQueueHistory] = useState<number[]>([]);
  const [episodeHistory, setEpisodeHistory] = useState<number[]>([]);

  useEffect(() => {
    // Only accumulate telemetry history while simulation is actively running
    if (!frame || !isRunning) {
      return;
    }

    const maxQueue = Math.max(...Object.values(frame.queue_lengths ?? {}), 0);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWaitHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      frame.avg_wait_time,
    ]);
     
    setThroughputHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      frame.throughput,
    ]);
     
    setQueueHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), maxQueue]);
  }, [frame, isRunning]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const latest = trainingMetrics[trainingMetrics.length - 1];
    if (!latest) {
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEpisodeHistory((prev) => [
      ...prev.slice(-HISTORY_LENGTH + 1),
      latest.episode,
    ]);
  }, [trainingMetrics, isRunning]);

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
      accent: "bg-blue-500",
      ratio: Math.min(1, metrics.avgWait / 14),
    },
    {
      title: "Throughput",
      value: metrics.throughput,
      suffix: "",
      history: throughputHistory,
      accent: "bg-emerald-500",
      ratio: Math.min(1, metrics.throughput / 200),
    },
    {
      title: "Max Queue",
      value: metrics.maxQueue,
      suffix: "",
      history: queueHistory,
      accent: "bg-amber-400",
      ratio: Math.min(1, metrics.maxQueue / 10),
    },
    {
      title: "Episode",
      value: metrics.currentEpisode,
      suffix: "",
      history: episodeHistory,
      accent: "bg-violet-400",
      ratio: Math.min(1, metrics.currentEpisode / 500),
    },
  ];

  return (
    <div className="space-y-2.5">
      {/* Real-time streaming status banner */}
      <div className="flex items-center justify-between px-0.5 text-[10px]">
        <div className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              isRunning
                ? "bg-emerald-400 animate-pulse shadow-[0_0_8px_#34d399]"
                : "bg-white/30"
            }`}
          />
          <span className="font-semibold uppercase tracking-wider text-white/50">
            {isRunning ? "Live Stream Active" : "Telemetry Frozen"}
          </span>
        </div>
        <span
          className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
            isRunning
              ? "text-emerald-400 bg-emerald-950/50 border-emerald-500/30"
              : "text-amber-300 bg-amber-950/40 border-amber-500/30"
          }`}
        >
          {isRunning ? "STREAMING" : "STOPPED"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
      {cards.map((card) => (
        <Card key={card.title} className="border-white/10 bg-[#161616]">
          <CardHeader className="pb-1">
            <CardTitle className="text-[10px] uppercase tracking-[0.09em] text-white/40">
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            <div className="text-[34px] font-medium leading-none tracking-tight text-white">
              <AnimatedValue value={card.value} suffix={card.suffix} />
            </div>
            <div className="h-0.5 rounded bg-white/10">
              <div
                className={`h-0.5 rounded ${card.accent}`}
                style={{ width: `${card.ratio * 100}%` }}
              />
            </div>
            <Sparkline data={card.history} />
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
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
    return <div className="h-10 w-full rounded bg-neutral-900" />;
  }

  return (
    <svg viewBox="0 0 100 100" className="h-10 w-full overflow-visible">
      <polyline
        fill="none"
        stroke="rgba(255,255,255,0.7)"
        strokeWidth="2"
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
    if (!frame || !isRunning) {
      return;
    }

    const maxQueue = Math.max(...Object.values(frame.queue_lengths ?? {}), 0);
    setWaitHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.avg_wait_time]);
    setThroughputHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), frame.throughput]);
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
    setEpisodeHistory((prev) => [...prev.slice(-HISTORY_LENGTH + 1), latest.episode]);
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
      ratio: Math.min(1, metrics.avgWait / 14),
    },
    {
      title: "Throughput",
      value: metrics.throughput,
      suffix: "",
      history: throughputHistory,
      ratio: Math.min(1, metrics.throughput / 200),
    },
    {
      title: "Max Queue",
      value: metrics.maxQueue,
      suffix: "",
      history: queueHistory,
      ratio: Math.min(1, metrics.maxQueue / 10),
    },
    {
      title: "Episode",
      value: metrics.currentEpisode,
      suffix: "",
      history: episodeHistory,
      ratio: Math.min(1, metrics.currentEpisode / 500),
    },
  ];

  return (
    <div className="space-y-3">
      {/* Real-time streaming status banner */}
      <div className="flex items-center justify-between px-0.5 text-[10px]">
        <div className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              isRunning
                ? "bg-white"
                : "bg-neutral-600"
            }`}
          />
          <span className="font-medium text-neutral-400">
            {isRunning ? "Live Stream Active" : "Telemetry Frozen"}
          </span>
        </div>
        <span
          className={`text-[9px] font-mono font-medium px-1.5 py-0.5 rounded border ${
            isRunning
              ? "text-white bg-neutral-800 border-neutral-700"
              : "text-neutral-500 bg-neutral-900 border-neutral-800"
          }`}
        >
          {isRunning ? "STREAMING" : "STOPPED"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
      {cards.map((card) => (
        <div key={card.title} className="p-3 rounded-lg border border-neutral-800 bg-neutral-900/50">
          <div className="text-[10px] font-medium text-neutral-500 mb-1 uppercase tracking-wider">
            {card.title}
          </div>
          <div className="text-2xl font-medium leading-none tracking-tight text-white mb-2">
            <AnimatedValue value={card.value} suffix={card.suffix} />
          </div>
          <div className="h-0.5 rounded bg-neutral-800 mb-3">
            <div
              className="h-0.5 rounded bg-white"
              style={{ width: `${card.ratio * 100}%` }}
            />
          </div>
          <Sparkline data={card.history} />
        </div>
      ))}
      </div>
    </div>
  );
}

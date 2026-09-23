"use client";

import { useEffect, useMemo, useState } from "react";
import { useSimulationStore } from "@/store/simulationStore";

const HISTORY_LENGTH = 20;

function AnimatedValue({
  value,
  suffix = "",
  decimals = 1,
}: {
  value: number;
  suffix?: string;
  decimals?: number;
}) {
  return (
    <span className="tabular-nums transition-colors duration-150">
      {value.toFixed(decimals)}
      {suffix}
    </span>
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
      unit: "seconds avg",
      decimals: 1,
      history: waitHistory,
      ratio: Math.min(1, metrics.avgWait / 14),
    },
    {
      title: "Throughput",
      value: metrics.throughput,
      suffix: "",
      unit: "veh cleared",
      decimals: 1,
      history: throughputHistory,
      ratio: Math.min(1, metrics.throughput / 200),
    },
    {
      title: "Max Queue",
      value: metrics.maxQueue,
      suffix: "",
      unit: "veh peak",
      decimals: 0,
      history: queueHistory,
      ratio: Math.min(1, metrics.maxQueue / 10),
    },
    {
      title: "Episode",
      value: metrics.currentEpisode,
      suffix: "",
      unit: "training eps",
      decimals: 0,
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
                ? "bg-emerald-500 animate-pulse"
                : "bg-neutral-600"
            }`}
          />
          <span className="font-medium text-neutral-400">
            {isRunning ? "Live Stream Active" : "Telemetry Frozen"}
          </span>
        </div>
        <span
          className={`text-[9px] font-mono font-medium px-1.5 py-0.5 rounded-full border ${
            isRunning
              ? "text-emerald-300 bg-emerald-950/30 border-emerald-800/50"
              : "text-neutral-500 bg-neutral-900 border-neutral-800"
          }`}
        >
          {isRunning ? "STREAMING" : "STOPPED"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {cards.map((card) => {
          const prev = card.history[card.history.length - 2];
          const hasDelta = prev !== undefined && card.history.length >= 2;
          const delta = hasDelta ? card.value - prev : 0;
          const isUp = delta > 0.01;
          const isDown = delta < -0.01;
          // For wait/queue/episode, down is good; for throughput, up is good
          const isPositive = card.title === "Throughput" ? isUp : isDown;
          const isNegative = card.title === "Throughput" ? isDown : isUp;
          return (
            <div
              key={card.title}
              className="flex flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900/40 p-3.5 transition-colors hover:bg-neutral-900/60"
            >
              <div className="flex h-5 items-center justify-between gap-2">
                <span className="truncate text-[11px] font-medium text-neutral-400">
                  {card.title}
                </span>
                {hasDelta ? (
                  <span
                    className={`inline-flex shrink-0 items-center gap-0.5 rounded-full border px-1.5 py-px font-mono text-[10px] leading-4 ${
                      isPositive
                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                        : isNegative
                          ? "border-rose-500/20 bg-rose-500/10 text-rose-400"
                          : "border-neutral-700 bg-neutral-800 text-neutral-500"
                    }`}
                  >
                    <span>{isUp ? "↑" : isDown ? "↓" : "→"}</span>
                    <span>
                      {delta > 0 ? "+" : ""}
                      {delta.toFixed(card.decimals)}
                    </span>
                  </span>
                ) : (
                  <span className="h-4" />
                )}
              </div>

              <div>
                <div className="font-mono text-2xl font-medium leading-none tracking-tight text-white">
                  <AnimatedValue
                    value={card.value}
                    suffix={card.suffix}
                    decimals={card.decimals}
                  />
                </div>
                <div className="mt-1.5 font-mono text-[10px] text-neutral-500">
                  {card.unit}
                </div>
              </div>

              <div className="mt-auto space-y-2 pt-1">
                <Sparkline data={card.history} />
                <div className="h-1 overflow-hidden rounded-full bg-neutral-800">
                  <div
                    className="h-full rounded-full bg-white/70 transition-all duration-500"
                    style={{ width: `${card.ratio * 100}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

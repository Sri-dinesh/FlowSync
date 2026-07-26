"use client";

import { useMemo } from "react";
import { useSimulationStore } from "@/store/simulationStore";
import type { RLInfo } from "@/types/simulation";

const PHASE_LABELS = ["NS Straight", "EW Straight", "NS Left", "EW Left"];
const PHASE_COLORS = [
  "from-emerald-500 to-emerald-400",
  "from-sky-500 to-sky-400",
  "from-violet-500 to-violet-400",
  "from-rose-500 to-rose-400",
];
const PHASE_GLOW = [
  "shadow-emerald-500/40",
  "shadow-sky-500/40",
  "shadow-violet-500/40",
  "shadow-rose-500/40",
];

function computeConfidence(qValues: number[]): number {
  if (qValues.length < 2) return 0;
  const sorted = [...qValues].sort((a, b) => b - a);
  const max = sorted[0]!;
  const second = sorted[1]!;
  if (Math.abs(max) < 1e-6) return 0;
  return Math.min(100, Math.max(0, ((max - second) / Math.abs(max)) * 100));
}

interface QValueBarProps {
  label: string;
  qValue: number;
  maxQ: number;
  isActive: boolean;
  colorClass: string;
  glowClass: string;
}

function QValueBar({ label, qValue, maxQ, isActive, colorClass, glowClass }: QValueBarProps) {
  const pct = maxQ > 0 ? Math.max(0, (qValue / maxQ) * 100) : 0;

  return (
    <div
      className={`relative rounded-md p-2 transition-all duration-200 ${
        isActive
          ? `bg-white/[0.06] ring-1 ring-white/20 shadow-lg ${glowClass}`
          : "bg-white/[0.02]"
      }`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-[10px] font-medium ${isActive ? "text-white" : "text-white/50"}`}>
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {isActive && (
            <span className="inline-flex items-center gap-0.5 rounded px-1 py-0.5 bg-emerald-500/20 text-emerald-300 text-[8px] font-semibold uppercase tracking-wide">
              Active
            </span>
          )}
          <span className={`text-[10px] font-mono tabular-nums ${isActive ? "text-white/90" : "text-white/35"}`}>
            {qValue.toFixed(3)}
          </span>
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colorClass} transition-all duration-150`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

interface QValuePanelProps {
  rl?: RLInfo | null;
}

export default function QValuePanel({ rl }: QValuePanelProps) {
  const currentPhase = useSimulationStore((s) => s.currentFrame?.signal_phase ?? 0);

  const { maxQ, confidence } = useMemo(() => {
    if (!rl) return { maxQ: 1, confidence: 0 };
    const maxQ = Math.max(...rl.q_values, 1e-6);
    const confidence = computeConfidence(rl.q_values);
    return { maxQ, confidence };
  }, [rl]);

  if (!rl) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 p-4 gap-1.5 text-center min-h-[120px]">
        <span className="text-2xl">🧠</span>
        <p className="text-xs text-white/35">Switch to AI mode to see agent reasoning</p>
      </div>
    );
  }

  const confidenceColor =
    confidence >= 40
      ? "text-emerald-400"
      : confidence >= 20
      ? "text-amber-400"
      : "text-rose-400";

  const confidenceBg =
    confidence >= 40
      ? "bg-emerald-500/10 border-emerald-500/25"
      : confidence >= 20
      ? "bg-amber-500/10 border-amber-500/25"
      : "bg-rose-500/10 border-rose-500/25";

  return (
    <div className="space-y-2">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-[9px] uppercase tracking-[0.12em] text-white/30 font-semibold">
          Q-Values per Phase
        </p>
        <span className="text-[9px] font-mono text-white/35">
          ε = {rl.epsilon.toFixed(3)}
        </span>
      </div>

      {/* Q-value bars */}
      <div className="space-y-1">
        {rl.q_values.map((q, i) => (
          <QValueBar
            key={i}
            label={PHASE_LABELS[i] ?? `Phase ${i}`}
            qValue={q}
            maxQ={maxQ}
            isActive={i === currentPhase}
            colorClass={PHASE_COLORS[i] ?? "from-white to-white/50"}
            glowClass={PHASE_GLOW[i] ?? ""}
          />
        ))}
      </div>

      {/* Footer: confidence + exploration status */}
      <div className="flex items-center gap-2 pt-0.5">
        {/* Confidence score */}
        <div className={`flex-1 rounded border px-2 py-1 ${confidenceBg}`}>
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-white/40">Confidence</span>
            <span className={`text-[11px] font-bold tabular-nums ${confidenceColor}`}>
              {confidence.toFixed(0)}%
            </span>
          </div>
          <div className="mt-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                confidence >= 40 ? "bg-emerald-500" : confidence >= 20 ? "bg-amber-500" : "bg-rose-500"
              }`}
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>

        {/* Exploration / Exploitation badge */}
        {rl.is_exploring ? (
          <div className="flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1.5">
            <span className="text-sm">🎲</span>
            <div>
              <p className="text-[8px] font-bold text-amber-300 uppercase tracking-wide">Exploring</p>
              <p className="text-[8px] text-amber-300/60">Random action</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1.5">
            <span className="text-sm">🧠</span>
            <div>
              <p className="text-[8px] font-bold text-emerald-300 uppercase tracking-wide">Exploiting</p>
              <p className="text-[8px] text-emerald-300/60">Learned policy</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

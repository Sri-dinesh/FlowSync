"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

const PHASE_COLORS: Record<number, string> = {
  0: "text-emerald-400",
  1: "text-blue-400",
  2: "text-amber-400",
  3: "text-purple-400",
};

const Q_BAR_COLORS = [
  "bg-emerald-500",
  "bg-blue-500",
  "bg-amber-500",
  "bg-purple-500",
];

interface Props {
  frame: CCTVFrameData | null;
}

export default function SignalDecisionPanel({ frame }: Props) {
  const qValues = frame?.q_values ?? [0, 0, 0, 0];
  const maxQ = Math.max(...qValues, 0.001);
  const phaseNames = ["NS Straight", "EW Straight", "NS Left", "EW Left"];

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-[0.14em] text-white/35 font-semibold">
          Signal Decision
        </h2>
        {frame && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
            {frame.confidence_pct.toFixed(0)}% conf
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-4">
        {/* Current DQN Phase */}
        <div className="text-center py-1">
          <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1.5">
            DQN Decision
          </div>
          <div
            className={`text-xl font-bold ${
              PHASE_COLORS[frame?.signal_phase ?? 0]
            }`}
          >
            {frame?.signal_phase_name ?? "—"}
          </div>
        </div>

        {/* Q-value bars */}
        <div className="flex flex-col gap-2">
          {phaseNames.map((name, i) => {
            const q = qValues[i] ?? 0;
            const barPct = maxQ > 0 ? (q / maxQ) * 100 : 0;
            const isSelected = frame?.signal_phase === i;
            return (
              <div key={i} className="flex items-center gap-2">
                <div
                  className={`text-[10px] w-[85px] shrink-0 truncate ${
                    isSelected ? "text-white font-medium" : "text-white/35"
                  }`}
                >
                  {name}
                </div>
                <div className="flex-1 h-[14px] bg-white/[0.04] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${Q_BAR_COLORS[i]} ${
                      isSelected ? "opacity-100" : "opacity-30"
                    }`}
                    style={{ width: `${barPct}%` }}
                  />
                </div>
                <div
                  className={`text-[10px] w-10 text-right font-mono ${
                    isSelected ? "text-white" : "text-white/25"
                  }`}
                >
                  {q.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Fixed timer comparison */}
        {frame?.fixed_timer_phase !== null &&
          frame?.fixed_timer_phase_name && (
            <div className="border-t border-white/[0.06] pt-3">
              <div className="text-[10px] text-white/30 uppercase tracking-wider mb-1">
                Fixed Timer Would Choose
              </div>
              <div className="text-sm font-semibold text-white/45">
                {frame.fixed_timer_phase_name}
              </div>
              {frame.fixed_timer_phase !== frame.signal_phase && (
                <div className="text-[10px] text-amber-400 mt-1 font-medium">
                  ⚡ AI overrides fixed timer
                </div>
              )}
            </div>
          )}
      </div>
    </div>
  );
}

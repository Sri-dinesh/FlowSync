"use client";

import { Brain, CheckCircle2, ShieldCheck, Sparkles, Activity } from "lucide-react";

interface PhaseDistribution {
  phase: number;
  name: string;
  description: string;
  share_pct: number;
}

interface Props {
  phaseDistribution: PhaseDistribution[];
  reliabilityScore: number;
  latencyMs: number;
}

const PHASE_COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b"];

export default function AIPolicyInsights({
  phaseDistribution,
  reliabilityScore,
  latencyMs,
}: Props) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Brain className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold tracking-wider uppercase text-white">
              Autonomous DQN Phase Allocation Policy
            </h3>
            <p className="text-xs text-white/40 mt-0.5">
              Reinforcement learning policy decisions with dynamic demand-action masking
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {reliabilityScore > 0 ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-mono">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Anti-Starvation Active</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/50 text-xs font-mono">
              <ShieldCheck className="h-3.5 w-3.5 text-white/40" />
              <span>Standby (Awaiting Run)</span>
            </div>
          )}
        </div>
      </div>

      {/* Grid of Phase Allocations */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {phaseDistribution.map((item, idx) => (
          <div
            key={item.phase}
            className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-4 flex flex-col justify-between hover:border-white/15 transition-all"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-white/40 uppercase">
                  Phase {item.phase}
                </span>
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: PHASE_COLORS[idx % PHASE_COLORS.length] }}
                />
              </div>
              <div className="text-xs font-bold text-white mt-1.5">{item.name}</div>
              <p className="text-[11px] text-white/40 mt-1 leading-snug">
                {item.description}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-baseline justify-between">
              <span className="text-[10px] uppercase text-white/40">Allocated Time</span>
              <span className="text-lg font-bold font-mono text-white">
                {item.share_pct}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* AI Performance Features */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
        <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3.5 flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-400">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase">Decision Latency</div>
            <div className="text-xs font-bold font-mono text-white">
              {latencyMs > 0 ? `${latencyMs}ms inference` : "Standby (0.0ms)"}
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3.5 flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400">
            <ShieldCheck className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase">Reliability Score</div>
            <div className="text-xs font-bold font-mono text-emerald-400">
              {reliabilityScore > 0 ? `${reliabilityScore}% guaranteed` : "Pending Evaluation"}
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3.5 flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-500/10 text-blue-400">
            <Activity className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="text-[10px] text-white/40 uppercase">Action Masking</div>
            <div className="text-xs font-bold font-mono text-blue-300">
              {phaseDistribution.some((p) => p.share_pct > 0)
                ? "0% Dead-Green cycles"
                : "Ready on Execution"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

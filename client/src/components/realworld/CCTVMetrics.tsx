"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

interface Props {
  frame: CCTVFrameData | null;
}

const CONGESTION_STYLE: Record<string, string> = {
  LOW: "text-emerald-400 border-emerald-500/25 bg-emerald-500/10",
  MODERATE: "text-yellow-400 border-yellow-500/25 bg-yellow-500/10",
  HIGH: "text-orange-400 border-orange-500/25 bg-orange-500/10",
  CRITICAL: "text-red-400 border-red-500/25 bg-red-500/10",
};

function MetricCard({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit?: string;
}) {
  return (
    <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3">
      <div className="text-[10px] text-white/30 uppercase tracking-wider font-medium mb-1.5">
        {label}
      </div>
      <div className="text-lg font-bold text-white leading-none font-mono">
        {value}
        {unit && (
          <span className="text-[10px] text-white/25 ml-1 font-sans font-normal">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}

export default function CCTVMetrics({ frame }: Props) {
  const vehicleTypes = frame?.vehicle_types ?? {};
  const totalVehicles = Object.values(vehicleTypes).reduce(
    (a, b) => a + b,
    0
  );
  const congestion = frame?.congestion_level ?? "LOW";

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <h2 className="text-xs uppercase tracking-[0.14em] text-white/35 font-semibold">
          Live Metrics
        </h2>
      </div>

      <div className="p-3 grid grid-cols-2 gap-2">
        <MetricCard
          label="Est. Wait"
          value={frame ? frame.estimated_avg_wait.toFixed(1) : "—"}
          unit="s"
        />
        <MetricCard
          label="Vehicles"
          value={frame ? String(totalVehicles) : "—"}
          unit="detected"
        />
        <MetricCard
          label="Detection FPS"
          value={frame ? frame.detection_fps.toFixed(1) : "—"}
        />

        {/* Congestion chip */}
        <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3">
          <div className="text-[10px] text-white/30 uppercase tracking-wider font-medium mb-1.5">
            Congestion
          </div>
          {frame ? (
            <span
              className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                CONGESTION_STYLE[congestion] ?? ""
              }`}
            >
              {congestion}
            </span>
          ) : (
            <span className="text-lg font-bold text-white font-mono">—</span>
          )}
        </div>
      </div>

      {/* Vehicle type breakdown */}
      {frame && totalVehicles > 0 && (
        <div className="px-3 pb-3 border-t border-white/[0.04] pt-2.5">
          <div className="text-[10px] text-white/25 uppercase tracking-wider font-medium mb-2">
            Vehicle Types
          </div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(vehicleTypes)
              .filter(([, v]) => v > 0)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => (
                <span
                  key={type}
                  className="px-2 py-0.5 rounded-full text-[10px] bg-white/[0.05] border border-white/[0.08] text-white/50 font-medium"
                >
                  {type.replace(/_/g, " ")}: {count}
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

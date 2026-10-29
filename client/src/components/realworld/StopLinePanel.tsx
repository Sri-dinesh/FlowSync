"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

export default function StopLinePanel({ frame }: { frame: CCTVFrameData | null }) {
  const observation = frame?.crossing_observation;
  const last = observation?.last_event;
  const status = !observation ? "Supply approach geometry and a recorded video."
    : observation.status === "geometry_unavailable" ? "Crossing detection paused: geometry or detector unavailable."
    : observation.status === "source_timing_unavailable" ? "Crossing detection paused: advancing video timestamps unavailable. Live-stream timing is not supported."
    : "Tracking recorded-video crossings.";
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3 text-xs text-white/65">
      <h2 className="font-semibold text-sm text-white/85">Stop-line crossings</h2>
      <p role="status">{status}</p>
      {observation && <>
        <p className="text-white/45">Recorded totals for this session</p>
        <dl className="grid grid-cols-2 gap-2">
          {Object.entries(observation.counts).map(([approach, count]) => (
            <div key={approach} className="flex justify-between gap-3 capitalize"><dt>{approach}</dt><dd className="font-mono">{count}</dd></div>
          ))}
        </dl>
        {observation.status === "available" && observation.source_time_s !== null && <p>Video position: {observation.source_time_s.toFixed(2)} s</p>}
      </>}
      {last && <p>Last: {last.approach}, track {last.track_id}, between {last.time_interval_s[0].toFixed(2)}–{last.time_interval_s[1].toFixed(2)} s (estimated {last.estimated_time_s.toFixed(2)} s).</p>}
      <p className="text-white/45">Inferred discharge events, not incoming demand. Turns remain unknown; tracking and camera accuracy still need validation.</p>
    </section>
  );
}

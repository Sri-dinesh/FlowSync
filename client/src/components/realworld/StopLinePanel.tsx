"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

export default function StopLinePanel({ frame }: { frame: CCTVFrameData | null }) {
  const observation = frame?.crossing_observation;
  const last = observation?.last_event;
  const turns = frame?.trajectory_observation;
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
      {turns && <div className="space-y-2 border-t border-white/10 pt-3">
        <h3 className="font-semibold text-white/85">Observed departures</h3>
        <p role="status">{turns.status === "available" ? "Following crossing tracks into configured exits." : "Trajectory observations unavailable."}</p>
        <p>{turns.classified_count} labeled · {turns.pending_count} pending · {turns.unresolved_count} unresolved</p>
        {turns.last_event && <p>Last: {turns.last_event.approach} · {turns.last_event.turn?.replaceAll("_", " ") ?? `unknown (${turns.last_event.reason.replaceAll("_", " ")})`}
          {turns.last_event.available_time_s !== null ? ` · observed at ${turns.last_event.available_time_s.toFixed(2)} s` : ""}.</p>}
      </div>}
      <p className="text-white/45">Discharge observations describe vehicles already crossing. Exit-based labels do not reveal earlier queued turns. Tracking and camera accuracy still need validation.</p>
    </section>
  );
}

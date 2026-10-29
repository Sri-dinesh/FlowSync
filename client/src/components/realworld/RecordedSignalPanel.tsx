"use client";
import type { CCTVFrameData } from "@/app/realworld/page";

const PHASES = ["NS straight", "EW straight", "NS left", "EW left"];

export default function RecordedSignalPanel({ frame }: { frame: CCTVFrameData | null }) {
  const signal = frame?.recorded_signal;
  const message = !signal ? "No signal timeline supplied."
    : signal.status === "gap" ? "No annotation covers this video time."
    : signal.status === "unknown" ? "Signal state is marked unknown."
    : signal.status === "source_timing_unavailable" ? "Video timestamp unavailable."
    : signal.status === "video_mismatch" ? "Timeline does not match this video."
    : null;
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2 text-xs text-white/65">
      <h2 className="font-semibold text-sm text-white/85">Recorded signal state</h2>
      {message ? <p role="status">{message}</p> : signal && <>
        <p className="capitalize">{signal.state?.replace("_", " ")}{signal.phase !== null ? ` · ${PHASES[signal.phase] ?? "Unsupported phase"}` : ""}</p>
        {signal.state === "green" && <p>Elapsed green: {signal.green_elapsed_s === null ? "unknown — onset not observed" : `${signal.green_elapsed_s.toFixed(2)} s`}</p>}
      </>}
      {signal && <p>Source: {signal.origin.replaceAll("_", " ")} · annotation resolution {signal.time_resolution_s} s</p>}
      <p className="text-white/45">Imported observation, not a controller recommendation. Signal history and movement inputs remain incomplete.</p>
    </section>
  );
}

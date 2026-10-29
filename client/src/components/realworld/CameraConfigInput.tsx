"use client";

import { useState } from "react";

type Selection =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; source: string; sha256: string; filename: string };

export default function CameraConfigInput({ kind, source, disabled, onChange }: {
  kind: "geometry" | "signal_timeline";
  source: string;
  disabled: boolean;
  onChange: (json: string | undefined, blocked: boolean) => void;
}) {
  const [selection, setSelection] = useState<Selection>({ kind: "none" });
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const geometry = kind === "geometry";
  const title = geometry ? "Approach geometry" : "Recorded signal timeline";
  const jsonKey = geometry ? "calibration_json" : "signal_timeline_json";
  const endpoint = geometry ? "/cctv/calibration/validate" : "/cctv/signal-timeline/validate";

  async function load(file: File) {
    setSelection({ kind: "loading" });
    onChange(undefined, true);
    try {
      if (file.size > 1048576) throw new Error("Configuration files must be smaller than 1 MB.");
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: await file.text(),
      });
      const value: unknown = await response.json();
      if (!response.ok) {
        const detail = typeof value === "object" && value !== null && "detail" in value
          ? JSON.stringify(value.detail) : "Invalid configuration.";
        throw new Error(detail);
      }
      if (typeof value !== "object" || value === null || !(jsonKey in value)
          || !("sha256" in value) || typeof value.sha256 !== "string") {
        throw new Error("Unexpected configuration response.");
      }
      const json: unknown = Reflect.get(value, jsonKey);
      if (typeof json !== "string") throw new Error("Missing normalized configuration.");
      if (geometry && (!("source" in value) || value.source !== source)) throw new Error("The configuration source must exactly match the selected video path or URL.");
      setSelection({ kind: "ready", source, sha256: value.sha256, filename: file.name });
      onChange(json, false);
    } catch (error) {
      setSelection({ kind: "error", message: error instanceof Error ? error.message : "Configuration could not be loaded." });
      onChange(undefined, true);
    }
  }

  return (
    <fieldset disabled={disabled || selection.kind === "loading"} className="space-y-2 rounded-lg border border-white/15 p-3 text-xs text-white/70">
      <legend className="px-1 font-medium">{title} (optional)</legend>
      <p>{geometry ? "Import polygons and stop lines for this camera. Geometry is checked; counting accuracy still needs labeled video."
        : "Import annotated green, yellow, all-red and unknown intervals. Video identity is checked on Start. This does not issue signal commands."}</p>
      <label className="block space-y-1">
        <span>{title} JSON</span>
        <input type="file" accept=".json,application/json" className="block w-full min-h-11 py-2 text-xs file:mr-2 file:rounded file:border-0 file:px-2 file:py-1"
          onChange={(event) => { const file = event.target.files?.[0]; if (file) void load(file); event.target.value = ""; }} />
      </label>
      {selection.kind === "loading" && <p role="status">Checking configuration…</p>}
      {selection.kind === "error" && <p role="alert" className="break-words text-rose-300">{selection.message}</p>}
      {selection.kind === "ready" && <p role="status" className="break-words text-emerald-300">{selection.filename} · {geometry ? "geometry checked" : "timeline format checked"} · {selection.sha256.slice(0, 12)}</p>}
      {selection.kind !== "none" && <button type="button" className="min-h-11 underline underline-offset-4"
        onClick={() => { setSelection({ kind: "none" }); onChange(undefined, false); }}>Remove {geometry ? "calibration" : "timeline"}</button>}
      <p className="break-all text-white/50">Source: {source || "Select a video first"}</p>
    </fieldset>
  );
}

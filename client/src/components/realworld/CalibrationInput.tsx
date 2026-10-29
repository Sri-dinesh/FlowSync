"use client";

import { useState } from "react";

type Selection =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; source: string; sha256: string; filename: string };

export default function CalibrationInput({ source, disabled, onChange }: {
  source: string;
  disabled: boolean;
  onChange: (json: string | undefined, blocked: boolean) => void;
}) {
  const [selection, setSelection] = useState<Selection>({ kind: "none" });
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  async function load(file: File) {
    setSelection({ kind: "loading" });
    onChange(undefined, true);
    try {
      if (file.size > 65536) throw new Error("Calibration files must be smaller than 64 KB.");
      const response = await fetch(`${API_BASE}/cctv/calibration/validate`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: await file.text(),
      });
      const value: unknown = await response.json();
      if (!response.ok) {
        const detail = typeof value === "object" && value !== null && "detail" in value
          ? JSON.stringify(value.detail) : "Invalid configuration.";
        throw new Error(detail);
      }
      if (typeof value !== "object" || value === null || !("calibration_json" in value)
          || typeof value.calibration_json !== "string" || !("sha256" in value)
          || typeof value.sha256 !== "string" || !("source" in value) || typeof value.source !== "string") {
        throw new Error("Unexpected calibration response.");
      }
      if (value.source !== source) throw new Error("The configuration source must exactly match the selected video path or URL.");
      setSelection({ kind: "ready", source: value.source, sha256: value.sha256, filename: file.name });
      onChange(value.calibration_json, false);
    } catch (error) {
      setSelection({ kind: "error", message: error instanceof Error ? error.message : "Calibration could not be loaded." });
      onChange(undefined, true);
    }
  }

  return (
    <fieldset disabled={disabled || selection.kind === "loading"} className="space-y-2 rounded-lg border border-white/15 p-3 text-xs text-white/70">
      <legend className="px-1 font-medium">Approach geometry (optional)</legend>
      <p>Import polygons and stop lines for this camera. Geometry is checked; counting accuracy still needs labeled video.</p>
      <label className="block space-y-1">
        <span>Calibration JSON</span>
        <input type="file" accept=".json,application/json" className="block w-full min-h-11 py-2 text-xs file:mr-2 file:rounded file:border-0 file:px-2 file:py-1"
          onChange={(event) => { const file = event.target.files?.[0]; if (file) void load(file); event.target.value = ""; }} />
      </label>
      {selection.kind === "loading" && <p role="status">Checking geometry…</p>}
      {selection.kind === "error" && <p role="alert" className="break-words text-rose-300">{selection.message}</p>}
      {selection.kind === "ready" && <p role="status" className="break-words text-emerald-300">{selection.filename} · geometry checked · {selection.sha256.slice(0, 12)}</p>}
      {selection.kind !== "none" && <button type="button" className="min-h-11 underline underline-offset-4"
        onClick={() => { setSelection({ kind: "none" }); onChange(undefined, false); }}>Remove calibration</button>}
      <p className="break-all text-white/50">Source: {source || "Select a video first"}</p>
    </fieldset>
  );
}

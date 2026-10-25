"use client";
import { memo, useState } from "react";
import { X, Download, Copy } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";
import { recordedSnapshot, snapshotCsv, snapshotLatex } from "@/lib/research-data";

export const ResearchExportModal = memo(function ResearchExportModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [tab, setTab] = useState<"json" | "csv" | "latex">("json");
  const [message, setMessage] = useState("");
  const frame = useResearchStore((s) => s.currentFrame);
  if (!isOpen) return null;
  const data = recordedSnapshot(frame);
  const content = !data ? "No recorded single-run telemetry. Start a run or replay before exporting."
    : tab === "json" ? JSON.stringify(data, null, 2)
    : tab === "csv" ? snapshotCsv(frame) ?? "" : snapshotLatex(frame) ?? "";
  const download = () => {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([content], { type: tab === "json" ? "application/json" : "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `flowsync_${data.experiment_id.replace(/[^a-zA-Z0-9_-]/g, "_")}.${tab === "latex" ? "tex" : tab}`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(content); setMessage("Copied"); }
    catch { setMessage("Clipboard unavailable. Use Download."); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="export-title" className="flex w-full max-w-2xl flex-col gap-4 rounded-lg border border-neutral-800 bg-neutral-950 p-6 text-white">
        <header className="flex items-center justify-between">
          <h2 id="export-title" className="text-sm font-medium">Export recorded snapshot</h2>
          <button autoFocus aria-label="Close export" onClick={onClose} className="p-3"><X className="h-4 w-4" /></button>
        </header>
        <p className="text-xs text-neutral-400">One application frame only. Missing provenance stays unknown. Comparative research tables require the headless evidence tools.</p>
        <div className="flex gap-2">
          {(["json", "csv", "latex"] as const).map((kind) => <button key={kind} aria-pressed={tab === kind} onClick={() => setTab(kind)} className="rounded border border-neutral-700 px-3 py-2 text-xs uppercase">{kind}</button>)}
        </div>
        <pre className="max-h-72 overflow-auto rounded border border-neutral-800 bg-black p-4 text-xs">{content}</pre>
        <div className="flex justify-between">
          <button disabled={!data} onClick={copy} className="flex items-center gap-2 rounded border border-neutral-700 px-3 py-2 text-xs disabled:opacity-40"><Copy className="h-4 w-4" />Copy</button>
          <button disabled={!data} onClick={download} className="flex items-center gap-2 rounded bg-indigo-600 px-3 py-2 text-xs disabled:opacity-40"><Download className="h-4 w-4" />Download</button>
        </div>
        <p role="status" className="text-xs text-neutral-400">{message}</p>
      </section>
    </div>
  );
});

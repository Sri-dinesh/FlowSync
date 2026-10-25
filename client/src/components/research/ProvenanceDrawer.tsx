"use client";
import { memo } from "react";
import { X } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";
import { recordedSnapshot } from "@/lib/research-data";

export const ProvenanceDrawer = memo(function ProvenanceDrawer() {
  const open = useResearchStore((s) => s.showProvenanceDrawer);
  const toggle = useResearchStore((s) => s.toggleProvenanceDrawer);
  const frame = useResearchStore((s) => s.currentFrame);
  if (!open) return null;
  const data = recordedSnapshot(frame);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70">
      <section role="dialog" aria-modal="true" aria-labelledby="provenance-title" className="flex h-full w-full max-w-xl flex-col gap-4 overflow-auto border-l border-neutral-800 bg-neutral-950 p-6 text-white">
        <header className="flex items-center justify-between">
          <h2 id="provenance-title" className="text-sm font-medium">Recorded provenance</h2>
          <button autoFocus aria-label="Close provenance" onClick={() => toggle(false)} className="p-3"><X className="h-4 w-4" /></button>
        </header>
        <p className="text-xs text-neutral-400">Values come from the backend frame. A missing hash or runtime identity is unknown. Live visualization and historical replays do not establish audited headless equivalence.</p>
        {data ? <pre className="whitespace-pre-wrap break-all rounded border border-neutral-800 bg-black p-4 text-xs">{JSON.stringify(data, null, 2)}</pre>
          : <p className="rounded border border-neutral-800 p-4 text-sm text-neutral-400">No single-run telemetry received. Start a simulation or select a recorded replay.</p>}
      </section>
    </div>
  );
});

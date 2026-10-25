"use client";
import { useState } from "react";
import Link from "next/link";
import Header from "@/components/layout/Header";
import { ResearchSubNav } from "@/components/research/ResearchSubNav";
import { ResearchPresentationMode } from "@/components/research/ResearchPresentationMode";
import { ResearchExportModal } from "@/components/research/ResearchExportModal";
import { ResearchRunsDashboard } from "@/components/research/ResearchRunsDashboard";
import { useResearchControllers } from "@/hooks/useResearchControllers";

export default function ResearchDashboardPage() {
  const [presentation, setPresentation] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const { controllers, error } = useResearchControllers();
  if (presentation) return <ResearchPresentationMode onExit={() => setPresentation(false)} />;
  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <Header />
      <ResearchSubNav onOpenPresentation={() => setPresentation(true)} onOpenExport={() => setExportOpen(true)} />
      <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6">
        <section className="space-y-4 rounded-lg border border-neutral-800 bg-neutral-900/60 p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">Simulation research workspace</p>
          <h1 className="text-2xl font-semibold">Inspect controller decisions and recorded runs</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-neutral-400">
            The interactive application visualizes the custom simulator. Audited checkpoint evaluation and SUMO studies run through separate headless tools.
            Their observation, reward and measurement contracts are documented in CONTENT.md.
          </p>
          <p className="text-sm text-amber-200">Live learned-controller execution is unavailable until checkpoint loading and the matching observed-input runtime are integrated. Recorded runs remain replayable.</p>
          <div className="flex flex-wrap gap-3">
            <Link className="rounded bg-white px-4 py-3 text-sm font-medium text-black" href="/research/experiment">Open experiment</Link>
            <Link className="rounded border border-neutral-700 px-4 py-3 text-sm" href="/research/compare">Compare classical controllers</Link>
            <Link className="rounded border border-neutral-700 px-4 py-3 text-sm" href="/research/replay">Replay a saved run</Link>
          </div>
        </section>
        <section className="rounded-lg border border-neutral-800 p-6">
          <h2 className="mb-3 text-sm font-medium">Backend controller availability</h2>
          {error ? <p role="alert" className="text-sm text-amber-200">{error}. Start the backend to load its catalog.</p>
            : controllers.length === 0 ? <p role="status" className="text-sm text-neutral-400">Loading controller catalog…</p>
            : <ul className="grid gap-3 sm:grid-cols-2">
              {controllers.map((c) => <li key={c.id} className="rounded border border-neutral-800 p-3 text-sm">
                <div className="flex justify-between gap-2"><span>{c.name}</span><span className="text-xs text-neutral-400">{c.available_live ? "Live" : "Replay / CLI"}</span></div>
                <p className="mt-2 text-xs text-neutral-400">{c.available_live ? c.description : c.unavailable_reason}</p>
              </li>)}
            </ul>}
        </section>
        <ResearchRunsDashboard />
        <p className="text-xs leading-relaxed text-neutral-500">Application metrics are exploratory telemetry. No hardware latency, field validation, formal safety guarantee or learned-controller superiority is implied. Offline SUMO artifacts are not imported as interactive runs.</p>
      </main>
      <ResearchExportModal isOpen={exportOpen} onClose={() => setExportOpen(false)} />
    </div>
  );
}

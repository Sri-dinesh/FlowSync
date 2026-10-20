"use client";

import React, { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ResearchReplayPage from "../../replay/page";

export default function SingleRunPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const runId = resolvedParams.id;

  return (
    <div>
      <div className="bg-indigo-950/40 border-b border-indigo-500/20 px-6 py-2 flex items-center justify-between text-xs font-mono">
        <span className="text-indigo-300">Direct Provenance Link: {runId}</span>
        <Link
          href="/research/replay"
          className="text-slate-400 hover:text-white underline flex items-center gap-1"
        >
          <ArrowLeft className="w-3 h-3" /> View All Runs
        </Link>
      </div>
      {/* Deep-link: preselects this run in the replay catalog */}
      <ResearchReplayPage initialRunId={runId} />
    </div>
  );
}

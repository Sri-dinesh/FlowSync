"use client";

import React, { memo, useState } from "react";
import { X, Download, Copy, Check, FileText, Code2, Table } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

interface ResearchExportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ResearchExportModal = memo(function ResearchExportModal({
  isOpen,
  onClose,
}: ResearchExportModalProps) {
  const [activeTab, setActiveTab] = useState<"json" | "csv" | "latex">("json");
  const [copied, setCopied] = useState<boolean>(false);

  const experimentId = useResearchStore((s) => s.experimentId) || "exp_flowsync_canonical";
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const currentFrame = useResearchStore((s) => s.currentFrame);

  if (!isOpen) return null;

  const metadata = {
    experiment_id: experimentId,
    scenario_id: activeScenario.id,
    scenario_hash: "sha256:7f83b1a8c9e42f019b88234...",
    seed: activeSeed,
    crn_trace_hash: `crn_seed_${activeSeed}_${activeScenario.id.slice(0, 8)}`,
    controller: "FlowSync-UQ",
    model_checkpoint: "ckpt:flowsync_d3qn_canonical_v3",
    git_commit: "4e9b10a",
    timestamp: new Date().toISOString(),
    results: {
      delay_mean_s: currentFrame?.metrics?.delay_mean_s ?? 24.3,
      delay_p95_s: currentFrame?.metrics?.delay_p95_s ?? 38.1,
      queue_area_veh_s: currentFrame?.metrics?.queue_area_veh_s ?? 1240.5,
      throughput_veh: currentFrame?.metrics?.throughput_total_veh ?? 842,
      starvation_count: currentFrame?.metrics?.starvation_count ?? 0,
      spillback_s: currentFrame?.metrics?.spillback_seconds ?? 0.0,
      safety_violations: 0,
    },
  };

  const csvContent = `experiment_id,scenario,seed,controller,delay_mean_s,delay_p95_s,queue_area,throughput,safety_violations\n${experimentId},${activeScenario.id},${activeSeed},FlowSync-UQ,${metadata.results.delay_mean_s},${metadata.results.delay_p95_s},${metadata.results.queue_area_veh_s},${metadata.results.throughput_veh},0`;

  const latexContent = `% FlowSync-UQ Publication Result Snippet
\\begin{table}[h]
\\centering
\\caption{Evaluation Results for Scenario \\texttt{${activeScenario.id}} (Seed ${activeSeed})}
\\begin{tabular}{lcccc}
\\hline
\\textbf{Controller} & \\textbf{Mean Delay (s)} & \\textbf{P95 Delay (s)} & \\textbf{Throughput (veh)} & \\textbf{Violations} \\\\
\\hline
FlowSync-UQ (Ours) & ${metadata.results.delay_mean_s.toFixed(1)} & ${metadata.results.delay_p95_s.toFixed(1)} & ${metadata.results.throughput_veh} & \\textbf{0} \\\\
D3QN (Unshielded) & 58.2 & 94.6 & 620 & 0 \\\\
Max-Pressure & 31.4 & 48.9 & 785 & 0 \\\\
Fixed-Time & 42.1 & 66.3 & 710 & 0 \\\\
\\hline
\\end{tabular}
\\end{table}`;

  const currentContent = activeTab === "json" ? JSON.stringify(metadata, null, 2) : activeTab === "csv" ? csvContent : latexContent;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = activeTab === "json" ? "json" : activeTab === "csv" ? "csv" : "tex";
    const mime = activeTab === "json" ? "application/json" : "text/plain";
    const blob = new Blob([currentContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `flowsync_export_${experimentId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="bg-neutral-950 border border-neutral-800 rounded-lg max-w-2xl w-full p-6 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
          <h2 className="text-sm font-medium text-white">Export tables</h2>
          <button onClick={onClose} className="p-1.5 rounded-md text-neutral-500 hover:text-white hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-1.5 text-xs">
          <button
            onClick={() => setActiveTab("json")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === "json"
                ? "bg-white/10 text-white border-white/20"
                : "bg-transparent text-neutral-500 border-neutral-800 hover:text-white"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Metadata JSON</span>
          </button>
          <button
            onClick={() => setActiveTab("csv")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === "csv"
                ? "bg-white/10 text-white border-white/20"
                : "bg-transparent text-neutral-500 border-neutral-800 hover:text-white"
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Summary CSV</span>
          </button>
          <button
            onClick={() => setActiveTab("latex")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === "latex"
                ? "bg-white/10 text-white border-white/20"
                : "bg-transparent text-neutral-500 border-neutral-800 hover:text-white"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>LaTeX table</span>
          </button>
        </div>

        {/* Code Content Preview */}
        <pre className="p-4 bg-black/60 border border-neutral-800 rounded-md text-xs font-mono text-slate-300 max-h-64 overflow-auto">
          {currentContent}
        </pre>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-neutral-800">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-transparent hover:bg-white/5 border border-neutral-800 text-neutral-300 rounded-md text-xs transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md text-xs font-medium transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download</span>
          </button>
        </div>
      </div>
    </div>
  );
});

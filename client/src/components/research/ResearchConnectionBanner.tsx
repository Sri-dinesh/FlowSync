"use client";

import React from "react";
import { Wifi, WifiOff, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useResearchStore } from "@/store/researchStore";
import { getFastApiUrls } from "@/lib/utils";

/**
 * Shared backend-connection status banner for all /research/* pages.
 * Explains in plain language what is wrong and how to fix it, instead of
 * leaving launch buttons silently disabled.
 */
export function ResearchConnectionBanner() {
  const isConnected = useResearchStore((s) => s.isWsConnected);
  const runStatus = useResearchStore((s) => s.runStatus);
  const errorMessage = useResearchStore((s) => s.errorMessage);
  const setRunStatus = useResearchStore((s) => s.setRunStatus);

  const { httpUrl } = getFastApiUrls();

  if (isConnected && runStatus !== "error") return null;

  return (
    <div
      role="alert"
      className={`rounded-lg border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
        runStatus === "error"
          ? "border-red-500/30 bg-red-500/[0.06]"
          : "border-amber-500/30 bg-amber-500/[0.06]"
      }`}
    >
      <div className="flex items-start gap-3">
        {runStatus === "error" ? (
          <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
        ) : isConnected ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
        ) : (
          <WifiOff className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
        )}
        <div className="space-y-1">
          <div className="text-sm font-medium text-white flex items-center gap-2">
            {runStatus === "error" ? (
              "Simulation failed to start"
            ) : (
              <>
                <Wifi className="w-3.5 h-3.5 text-amber-300" />
                Backend offline — simulations can&rsquo;t run yet
              </>
            )}
          </div>
          <p className="text-xs text-neutral-400 leading-relaxed max-w-3xl">
            {runStatus === "error" && errorMessage ? (
              <>
                <span className="text-red-300 font-mono tabular-nums">{errorMessage}</span>
                <br />
              </>
            ) : null}
            The 3D view needs the FastAPI backend at{" "}
            <span className="font-mono tabular-nums text-neutral-200">{httpUrl}</span> (REST +{" "}
            <span className="font-mono tabular-nums text-neutral-200">/ws/research</span> stream). Start
            it from the repo root — this notice clears on connect:
          </p>
          <code className="inline-block text-[11px] font-mono tabular-nums bg-black/50 border border-neutral-800 rounded-md px-2.5 py-1 text-neutral-200">
            uvicorn server.app.main:app --port 8000
          </code>
        </div>
      </div>
      {runStatus === "error" && (
        <button
          onClick={() => setRunStatus("idle")}
          className="shrink-0 px-2.5 py-1.5 rounded-md text-xs font-medium bg-transparent hover:bg-white/5 text-neutral-400 hover:text-white border border-neutral-800 transition-colors"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}

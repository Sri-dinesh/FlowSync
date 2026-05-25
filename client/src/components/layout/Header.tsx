"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { useSimulationStore } from "@/store/simulationStore";

export default function Header() {
  const isConnected = useSimulationStore((state) => state.isConnected);
  const mode = useSimulationStore((state) => state.mode);

  return (
    <header className="border-b border-white/10 bg-black/30 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400/70 via-cyan-300/40 to-amber-200/60 text-sm font-semibold text-black">
            FS
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold uppercase tracking-[0.2em] text-white/60">
              FlowSync
            </div>
            <div className="text-lg font-semibold text-white">
              Smart Traffic Control
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className={
              isConnected
                ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-100"
                : "border-rose-400/40 bg-rose-500/15 text-rose-100"
            }
          >
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
          <Badge
            variant="outline"
            className="border-white/15 bg-white/5 text-white/80"
          >
            Mode: {mode === "ai" ? "AI" : "Fixed"}
          </Badge>
        </div>
      </div>
    </header>
  );
}

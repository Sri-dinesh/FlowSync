"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { useSimulationStore } from "@/store/simulationStore";

export default function Header() {
  const isConnected = useSimulationStore((state) => state.isConnected);
  const mode = useSimulationStore((state) => state.mode);

  return (
    <header className="border-b border-white/10 bg-[#121212]">
      <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1a6bff] text-xs font-semibold text-white">
            FS
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-white">FlowSync</div>
            <div className="text-xs text-white/45">Smart Traffic Control</div>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={
              isConnected
                ? "border-emerald-500/40 bg-emerald-900/30 text-emerald-300"
                : "border-rose-500/40 bg-rose-900/20 text-rose-300"
            }
          >
            {isConnected ? "• Connected" : "• Disconnected"}
          </Badge>
          <Badge
            variant="outline"
            className="border-blue-500/30 bg-blue-900/20 text-blue-300"
          >
            {mode === "ai" ? "AI Mode" : "Fixed Mode"}
          </Badge>
        </div>
      </div>
    </header>
  );
}

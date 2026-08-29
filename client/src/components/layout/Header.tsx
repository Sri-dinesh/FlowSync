"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { useSimulationStore } from "@/store/simulationStore";

export default function Header() {
  const pathname = usePathname();
  const isSimulationConnected = useSimulationStore((state) => state.isConnected);
  const isCityConnected = useSimulationStore((state) => state.isCityConnected);
  const mode = useSimulationStore((state) => state.mode);

  const isConnected =
    pathname === "/city"
      ? isCityConnected
      : pathname === "/realworld"
      ? false // CCTV WebSocket managed independently in the page
      : isSimulationConnected;

  const navLinks = [
    { href: "/simulation", label: "🚦 Simulation", key: "simulation" },
    { href: "/city", label: "🏙️ City Grid", key: "city" },
    { href: "/realworld", label: "📡 Real World", key: "realworld" },
  ];

  return (
    <header className="border-b border-white/10 bg-[#121212]">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1a6bff] text-xs font-semibold text-white">
            FS
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-white">FlowSync</div>
            <div className="text-xs text-white/45">Smart Traffic Control</div>
          </div>
        </Link>

        <nav className="flex items-center gap-1">
          {navLinks.map(({ href, label, key }) => {
            const isActive =
              pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={key}
                href={href}
                className={`text-[11px] px-3 py-1.5 rounded-md border font-medium tracking-wide transition-all ${
                  isActive
                    ? "text-white bg-white/10 border-white/20"
                    : "text-white/40 hover:text-white/80 hover:bg-white/8 border-transparent hover:border-white/10"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          {pathname !== "/realworld" && (
            <Badge
              variant="outline"
              className={
                isConnected
                  ? "border-emerald-500/40 bg-emerald-900/30 text-emerald-300"
                  : "border-rose-500/40 bg-rose-900/20 text-rose-300"
              }
            >
              {isConnected ? "● Connected" : "○ Disconnected"}
            </Badge>
          )}
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

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { useSimulationStore } from "@/store/simulationStore";
import { useResearchStore } from "@/store/researchStore";
import { FlaskConical, BarChart3, Activity, Grid2X2, Video } from "lucide-react";

export default function Header() {
  const pathname = usePathname();
  const isSimulationConnected = useSimulationStore((state) => state.isConnected);
  const isCityConnected = useSimulationStore((state) => state.isCityConnected);
  const mode = useSimulationStore((state) => state.mode);
  const isResearchConnected = useResearchStore((state) => state.isWsConnected);
  const isResearch = pathname.startsWith("/research");

  const isConnected =
    isResearch ? isResearchConnected : pathname === "/city"
      ? isCityConnected
      : pathname === "/realworld"
      ? false // CCTV WebSocket managed independently in the page
      : isSimulationConnected;

  const navLinks = [
    { href: "/research", label: "Research", key: "research", icon: FlaskConical },
    { href: "/dashboard", label: "Dashboard", key: "dashboard", icon: BarChart3 },
    { href: "/simulation", label: "Simulation", key: "simulation", icon: Activity },
    { href: "/city", label: "City Grid", key: "city", icon: Grid2X2 },
    { href: "/realworld", label: "Video", key: "realworld", icon: Video },
  ];

  return (
    <header className="border-b border-white/10 bg-[#121212]">
      <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="flex shrink-0 items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1a6bff] text-xs font-semibold text-white">
            FS
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-white">FlowSync</div>
            <div className="text-xs text-white/45">Smart Traffic Control</div>
          </div>
        </Link>

        <nav aria-label="Main navigation" className="order-3 flex w-full min-w-0 items-center gap-1 overflow-x-auto lg:order-none lg:w-auto">
          {navLinks.map(({ href, label, key, icon: Icon }) => {
            const isActive =
              pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={key}
                href={href}
                prefetch={false}
                aria-current={isActive ? "page" : undefined}
                className={`flex min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap text-xs px-3 py-1.5 rounded-md border font-medium tracking-wide transition-all ${
                  isActive
                    ? "text-white bg-white/10 border-white/20"
                    : "text-white/40 hover:text-white/80 hover:bg-white/8 border-transparent hover:border-white/10"
                }`}
              >
                <Icon aria-hidden="true" className="h-3.5 w-3.5" />{label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-2 lg:ml-0">
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
            {pathname === "/realworld" ? "Observation only" : isResearch ? "Interactive" : mode === "ai" ? "AI Mode" : "Fixed Mode"}
          </Badge>
        </div>
      </div>
    </header>
  );
}

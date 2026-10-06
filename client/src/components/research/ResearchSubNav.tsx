"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FlaskConical,
  GitCompare,
  RotateCcw,
  Maximize2,
  Download,
} from "lucide-react";
import { useResearchStore } from "@/store/researchStore";

interface ResearchSubNavProps {
  onOpenPresentation?: () => void;
  onOpenExport?: () => void;
  showActions?: boolean;
}

export function ResearchSubNav({
  onOpenPresentation,
  onOpenExport,
  showActions = true,
}: ResearchSubNavProps) {
  const pathname = usePathname();
  const isWsConnected = useResearchStore((s) => s.isWsConnected);

  const navItems = [
    {
      href: "/research",
      label: "Overview",
      icon: BarChart3,
      exact: true,
      description: "Publication benchmarks & architecture",
    },
    {
      href: "/research/experiment",
      label: "Experiment",
      icon: FlaskConical,
      exact: false,
      description: "Live interactive simulation runner",
    },
    {
      href: "/research/compare",
      label: "Compare",
      icon: GitCompare,
      exact: false,
      description: "Synchronized dual-controller evaluation",
    },
    {
      href: "/research/replay",
      label: "Replay",
      icon: RotateCcw,
      exact: false,
      description: "Playback of saved runs",
    },
  ];

  return (
    <div className="border-b border-neutral-800 bg-[#0a0a0a]/90 backdrop-blur-md sticky top-0 z-20">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8 py-2">
        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 overflow-x-auto py-0.5">
          {navItems.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname === item.href || (item.href !== "/research" && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap border ${
                  isActive
                    ? "bg-white/10 text-white border-white/10"
                    : "text-neutral-500 hover:text-white hover:bg-white/5 border-transparent"
                }`}
                title={item.description}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Info & Actions */}
        <div className="flex items-center gap-2">
          {/* Stream status dot */}
          <span
            className="hidden md:inline-flex items-center gap-1.5 text-[11px] text-neutral-500"
            title={isWsConnected ? "Research stream connected" : "Research stream offline"}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isWsConnected ? "bg-emerald-400" : "bg-neutral-600"}`}
            />
            {isWsConnected ? "Live" : "Offline"}
          </span>

          {showActions && onOpenPresentation && (
            <button
              onClick={onOpenPresentation}
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
              title="High-contrast academic presentation view"
            >
              <Maximize2 className="h-3.5 w-3.5" />
              <span>Present</span>
            </button>
          )}

          {showActions && onOpenExport && (
            <button
              onClick={onOpenExport}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-white bg-white/10 hover:bg-white/15 border border-white/10 transition-colors"
              title="Export Table I, II, and VI CSV/LaTeX data"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

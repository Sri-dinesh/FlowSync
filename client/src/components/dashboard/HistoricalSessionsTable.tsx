"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  History,
  Play,
  Search,
  Video,
  Cpu,
  Zap,
  Clock,
  Sliders,
  Sparkles,
  Info,
  X,
  ChevronDown,
  ChevronUp,
  Trophy,
  Bot,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export interface SessionItem {
  session_id: string;
  created_at: string;
  timestamp_ms: number;
  duration_s: number;
  total_frames: number;
  total_vehicles: number;
  congestion_level: string;
  avg_fps: number;
  has_arrivals: boolean;
  mode?: "ai" | "greedy" | "fixed" | "manual" | "benchmark" | string;
  model_name?: string;
  model_episodes?: number | string;
  throughput?: number;
  throughput_pct?: number;
  avg_wait_s?: number;
  peak_queue?: number;
  performance_rating?: "OPTIMAL" | "EFFICIENT" | "MODERATE" | "CONGESTED" | string;
  level_of_service?: "A" | "B" | "C" | "D" | "E" | "F" | string;
  efficiency_gain_pct?: number;
  run_type?: "benchmark" | "cctv_replay" | "standalone" | string;
  benchmark_id?: string;
  benchmark_type?: "controller_comparison" | "model_comparison" | string;
  winner?: string;
  winner_label?: string;
  winner_episode?: number;
  improvements?: Record<string, number>;
  benchmark_modes?: string[];
  benchmark_results?: Record<
    string,
    {
      label?: string;
      model_id?: string;
      model_episode?: number;
      avg_wait_s?: number;
      avg_wait_time?: number;
      throughput?: number;
      total_passed?: number;
      peak_queue?: number;
      max_queue?: number;
      duration_seconds?: number;
    }
  >;
  scenario_id?: string;
  source_label?: string;
  is_cctv_replay?: boolean;
  is_finetuned?: boolean;
  finetune_scenario?: string | null;
}

const SCENARIO_NAMES: Record<string, string> = {
  rush_hour: "Rush Hour Corridor",
  heavy_left: "Heavy Left Turns",
  arterial_surge: "East-West Arterial",
  platoon_burst: "Platoon Congestion",
  uniform: "Balanced Grid",
};

export function formatScenarioName(slug?: string | null): string {
  if (!slug) return "";
  const clean = slug.toLowerCase().replace(/[\-_]/g, " ").trim();
  for (const [k, v] of Object.entries(SCENARIO_NAMES)) {
    if (clean.includes(k.replace(/_/g, " "))) return v;
  }
  return clean.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function checkIsFinetuned(session: SessionItem): { isFinetuned: boolean; scenario: string | null } {
  if (session.is_finetuned) {
    return { isFinetuned: true, scenario: session.finetune_scenario || null };
  }
  const text = `${session.model_name || ""} ${session.session_id || ""} ${session.winner_label || ""}`;
  if (text.includes("-ft-")) {
    const parts = text.split("-ft-")[1]?.split(/[\s:_\-]/)[0];
    return { isFinetuned: true, scenario: session.finetune_scenario || parts || null };
  }
  if (session.benchmark_results) {
    for (const [key, val] of Object.entries(session.benchmark_results)) {
      const vText = `${val.label || ""} ${val.model_id || ""} ${key}`;
      if (vText.includes("-ft-")) {
        const parts = vText.split("-ft-")[1]?.split(/[\s:_\-]/)[0];
        return { isFinetuned: true, scenario: parts || null };
      }
    }
  }
  return { isFinetuned: false, scenario: null };
}

interface DisplaySessionItem extends SessionItem {
  isBenchmarkGroup?: boolean;
  benchmarkRun?: {
    benchmark_id: string;
    winner: string;
    improvements: Record<string, number>;
    modes_results: Record<string, any>;
    child_sessions: Record<string, SessionItem>;
  };
}

interface Props {
  sessions: SessionItem[];
  benchmarks?: any[];
  initialModeFilter?: string;
}

function parseSessionDate(createdAt?: string, timestampMs?: number): Date | null {
  if (timestampMs && !isNaN(timestampMs) && timestampMs > 0) {
    const d = new Date(timestampMs);
    if (!isNaN(d.getTime())) return d;
  }
  if (!createdAt) return null;
  const sanitized =
    createdAt.includes(" ") && !createdAt.includes("T")
      ? createdAt.replace(" ", "T")
      : createdAt;
  const d = new Date(sanitized);
  return isNaN(d.getTime()) ? null : d;
}

function formatSessionFriendlyTime(
  createdAt?: string,
  timestampMs?: number
): {
  display: string;
  relative: string;
  full: string;
} {
  const d = parseSessionDate(createdAt, timestampMs);
  if (!d) {
    const fallback = createdAt || "Unknown time";
    return { display: fallback, relative: "", full: fallback };
  }
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  let relative = "";
  if (diffSec < 45 && diffSec >= -5) {
    relative = "Just now";
  } else if (diffMin < 60 && diffMin >= 0) {
    relative = `${diffMin}m ago`;
  } else if (diffHour < 24 && diffHour >= 0) {
    relative = `${diffHour}h ago`;
  } else if (diffDay === 1) {
    relative = "Yesterday";
  } else if (diffDay < 7 && diffDay > 1) {
    relative = `${diffDay}d ago`;
  } else {
    relative = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  const timeStr = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  const isToday = now.toDateString() === d.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday = yesterday.toDateString() === d.toDateString();
  let display = "";
  if (isToday) {
    display = `Today, ${timeStr}`;
  } else if (isYesterday) {
    display = `Yesterday, ${timeStr}`;
  } else if (now.getFullYear() === d.getFullYear()) {
    display = `${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}, ${timeStr}`;
  } else {
    display = `${d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}`;
  }
  const full = d.toLocaleString("en-US", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return { display, relative, full };
}

function formatDuration(seconds?: number): string {
  if (!seconds || isNaN(seconds) || seconds <= 0) return "0s";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const mins = Math.floor(s / 60);
  const remSec = s % 60;
  if (mins < 60) {
    return `${mins}m ${String(remSec).padStart(2, "0")}s`;
  }
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${String(remMins).padStart(2, "0")}m`;
}

function formatSessionTitle(session: SessionItem): {
  title: string;
  category: string;
  shortId: string;
} {
  const sid = session.session_id.toLowerCase();
  const mode = (session.mode || "ai").toLowerCase();
  const shortId =
    session.session_id.length > 12
      ? `${session.session_id.slice(0, 8)}…`
      : session.session_id;

  if (
    (session as DisplaySessionItem).isBenchmarkGroup ||
    session.run_type === "benchmark" ||
    sid.startsWith("bm_")
  ) {
    const scTitle = session.scenario_id
      ? `Scenario: ${session.scenario_id.toUpperCase()}`
      : "3-Mode Controller Benchmark";
    return {
      title: scTitle,
      category: "Benchmark",
      shortId,
    };
  }

  if (sid.startsWith("bench_")) {
    let modeLabel = "DQN AI";
    if (mode === "greedy") modeLabel = "Greedy Controller";
    else if (mode === "fixed") modeLabel = "Fixed Timer";
    else if (mode === "manual") modeLabel = "Manual Control";
    const epsLabel =
      mode === "ai" && session.model_episodes
        ? ` (${session.model_episodes} eps)`
        : "";
    return {
      title: `${modeLabel} Benchmark${epsLabel}`,
      category: "Benchmark",
      shortId,
    };
  }

  if (
    session.has_arrivals ||
    sid.includes("cctv") ||
    session.run_type === "cctv_replay"
  ) {
    return {
      title: "CCTV Digital Twin Replay",
      category: "Digital Twin",
      shortId,
    };
  }

  let modeName = "FlowSync DQN AI";
  if (mode === "greedy") modeName = "Greedy Adaptive";
  else if (mode === "fixed") modeName = "Fixed-Time Cycle";
  else if (mode === "manual") modeName = "Manual Override";
  const epsSuffix =
    mode === "ai" && session.model_episodes
      ? ` (${session.model_episodes} eps)`
      : "";
  return {
    title: `${modeName} Simulation${epsSuffix}`,
    category: "Simulation",
    shortId,
  };
}

function InlineInfoPopover({
  title,
  description,
  onClose,
}: {
  title: string;
  description: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className="absolute top-full mt-2 right-0 z-20 w-64 animate-in fade-in-0 zoom-in-95">
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3 shadow-2xl">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium text-white leading-tight pr-1">{title}</p>
          <button
            onClick={onClose}
            className="shrink-0 flex h-5 w-5 items-center justify-center rounded-md text-neutral-500 hover:text-white hover:bg-neutral-800 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-neutral-400">{description}</p>
      </div>
    </div>
  );
}

export default function HistoricalSessionsTable({
  sessions,
  benchmarks = [],
  initialModeFilter,
}: Props) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [modeFilter, setModeFilter] = useState(initialModeFilter || "ALL");
  const [episodeFilter, setEpisodeFilter] = useState("ALL");
  const [congestionFilter, setCongestionFilter] = useState("ALL");
  const [ratingFilter, setRatingFilter] = useState("ALL");
  const [activePopover, setActivePopover] = useState<"throughput" | "delay" | null>(null);
  const [expandedBenchmarkId, setExpandedBenchmarkId] = useState<string | null>(null);

  useEffect(() => {
    if (initialModeFilter) {
      setModeFilter(initialModeFilter);
    }
  }, [initialModeFilter]);

  // Consolidate benchmark sessions sharing a benchmark_id into unified multi-controller entries
  const consolidatedSessions = useMemo(() => {
    const list: DisplaySessionItem[] = [];
    const groupedBenchmarkIds = new Set<string>();

    // Index all benchmark child sessions by benchmark_id
    const bmChildren: Record<string, Record<string, SessionItem>> = {};
    for (const s of sessions) {
      const bid = s.benchmark_id;
      if (bid) {
        if (!bmChildren[bid]) bmChildren[bid] = {};
        const m = (s.mode || "ai").toLowerCase();
        bmChildren[bid][m] = s;
      }
    }

    // First inject consolidated benchmarks from `benchmarks` prop
    if (benchmarks && benchmarks.length > 0) {
      for (const bm of benchmarks) {
        const bid = bm.benchmark_id;
        if (!bid) continue;
        groupedBenchmarkIds.add(bid);
        const children = bmChildren[bid] || {};

        const isModelBm =
          bm.benchmark_type === "model_comparison" ||
          bid.startsWith("bm_model_") ||
          (bm.modes && bm.modes.some((m: string) => m.startsWith("model_")));

        if (isModelBm) {
          const resObj = bm.modes_results || {};
          const modelCount = Object.keys(resObj).length || 2;
          const winnerKey = bm.winner || Object.keys(resObj)[0];
          const winnerStats = resObj[winnerKey] || {};
          const maxQ = Math.max(
            ...Object.values(resObj).map((r: any) => r.max_queue ?? r.peak_queue ?? 0),
            0
          );
          const topWait = winnerStats.avg_wait_s ?? winnerStats.avg_wait_time ?? 0;
          const topVehs = winnerStats.throughput ?? winnerStats.total_passed ?? 0;

          list.push({
            session_id: bid,
            created_at: bm.created_at,
            timestamp_ms: bm.timestamp_ms,
            duration_s: bm.duration_seconds || 30.0,
            total_frames: Math.round((bm.duration_seconds || 30.0) * 10),
            total_vehicles: topVehs || 10,
            congestion_level: "MODERATE",
            avg_fps: 10.0,
            has_arrivals: false,
            mode: "benchmark",
            benchmark_type: "model_comparison",
            model_name: bm.model_name || `DQN Multi-Model Showdown (${modelCount} Checkpoints)`,
            model_episodes: bm.winner_episode ?? winnerStats.model_episode ?? bm.model_episodes,
            throughput: topVehs,
            avg_wait_s: topWait,
            peak_queue: maxQ,
            performance_rating: "OPTIMAL",
            level_of_service: topWait <= 10 ? "A" : topWait <= 20 ? "B" : "C",
            efficiency_gain_pct: bm.improvements?.[`${winnerKey}_wait_pct`] ?? 0,
            run_type: "benchmark",
            benchmark_id: bid,
            winner: winnerKey,
            winner_label: bm.winner_label || winnerStats.label,
            winner_episode: bm.winner_episode ?? winnerStats.model_episode,
            improvements: bm.improvements || {},
            benchmark_modes: bm.modes || Object.keys(resObj),
            benchmark_results: resObj,
            scenario_id: bm.scenario_id,
            isBenchmarkGroup: true,
            benchmarkRun: {
              benchmark_id: bid,
              winner: winnerKey,
              improvements: bm.improvements || {},
              modes_results: resObj,
              child_sessions: children,
            },
          });
          continue;
        }

        // Standard 3-controller showdown
        const aiStats = bm.modes_results?.ai || {};
        const fixedStats = bm.modes_results?.fixed || {};
        const greedyStats = bm.modes_results?.greedy || {};

        const maxQ = Math.max(
          aiStats.peak_queue ?? aiStats.max_queue ?? 0,
          fixedStats.peak_queue ?? fixedStats.max_queue ?? 0,
          greedyStats.peak_queue ?? greedyStats.max_queue ?? 0
        );

        const aiWait = aiStats.avg_wait_s ?? aiStats.avg_wait_time ?? 0;
        const totalVehs = (aiStats.throughput ?? 0) || 10;

        list.push({
          session_id: bid,
          created_at: bm.created_at,
          timestamp_ms: bm.timestamp_ms,
          duration_s: bm.duration_seconds || 30.0,
          total_frames: Math.round((bm.duration_seconds || 30.0) * 10),
          total_vehicles: totalVehs,
          congestion_level: "MODERATE",
          avg_fps: 10.0,
          has_arrivals: false,
          mode: "benchmark",
          benchmark_type: "controller_comparison",
          model_name: "FlowSync DQN vs Fixed vs Greedy",
          model_episodes: bm.model_episodes ?? 300,
          throughput: aiStats.throughput ?? aiStats.total_passed ?? 0,
          avg_wait_s: aiWait,
          peak_queue: maxQ,
          performance_rating: "OPTIMAL",
          level_of_service: aiWait <= 10 ? "A" : aiWait <= 20 ? "B" : "C",
          efficiency_gain_pct: bm.improvements?.ai_wait_pct ?? 0,
          run_type: "benchmark",
          benchmark_id: bid,
          winner: bm.winner || "ai",
          improvements: bm.improvements || {},
          benchmark_modes: bm.modes || ["ai", "fixed", "greedy"],
          benchmark_results: bm.modes_results || {},
          scenario_id: bm.scenario_id,
          isBenchmarkGroup: true,
          benchmarkRun: {
            benchmark_id: bid,
            winner: bm.winner || "ai",
            improvements: bm.improvements || {},
            modes_results: bm.modes_results || {},
            child_sessions: children,
          },
        });
      }
    }

    // Now process the raw sessions list
    for (const s of sessions) {
      if (s.benchmark_id && groupedBenchmarkIds.has(s.benchmark_id)) {
        // Child session already absorbed into consolidated benchmark row
        continue;
      }

      if (s.benchmark_id) {
        groupedBenchmarkIds.add(s.benchmark_id);
        const children = bmChildren[s.benchmark_id] || {};
        const bResults = s.benchmark_results || {};

        const isModelBm =
          s.benchmark_type === "model_comparison" ||
          s.benchmark_id.startsWith("bm_model_") ||
          Object.keys(bResults).some((k) => k.startsWith("model_"));

        if (isModelBm) {
          const resObj = bResults;
          const modelCount = Object.keys(resObj).length || 2;
          const winnerKey = s.winner || Object.keys(resObj)[0];
          const winnerStats = resObj[winnerKey] || {};
          const maxQ = Math.max(
            ...Object.values(resObj).map((r: any) => r.max_queue ?? r.peak_queue ?? 0),
            s.peak_queue ?? 0
          );
          const topWait = winnerStats.avg_wait_s ?? winnerStats.avg_wait_time ?? s.avg_wait_s ?? 0;
          const topVehs = winnerStats.throughput ?? winnerStats.total_passed ?? s.throughput ?? 0;

          list.push({
            ...s,
            session_id: s.benchmark_id,
            mode: "benchmark",
            benchmark_type: "model_comparison",
            model_name: s.model_name || `DQN Multi-Model Showdown (${modelCount} Checkpoints)`,
            throughput: topVehs,
            avg_wait_s: topWait,
            peak_queue: maxQ,
            isBenchmarkGroup: true,
            winner: winnerKey,
            winner_label: s.winner_label || winnerStats.label,
            winner_episode: s.winner_episode ?? winnerStats.model_episode,
            benchmarkRun: {
              benchmark_id: s.benchmark_id,
              winner: winnerKey,
              improvements: s.improvements || {},
              modes_results: bResults,
              child_sessions: children,
            },
          });
          continue;
        }

        const aiStats = bResults.ai || children.ai || {};
        const fixedStats = bResults.fixed || children.fixed || {};
        const greedyStats = bResults.greedy || children.greedy || {};

        const maxQ = Math.max(
          aiStats.peak_queue ?? aiStats.max_queue ?? s.peak_queue ?? 0,
          fixedStats.peak_queue ?? fixedStats.max_queue ?? 0,
          greedyStats.peak_queue ?? greedyStats.max_queue ?? 0
        );

        list.push({
          ...s,
          session_id: s.benchmark_id,
          mode: "benchmark",
          benchmark_type: "controller_comparison",
          peak_queue: maxQ,
          isBenchmarkGroup: true,
          benchmarkRun: {
            benchmark_id: s.benchmark_id,
            winner: s.winner || "ai",
            improvements: s.improvements || {},
            modes_results: bResults,
            child_sessions: children,
          },
        });
        continue;
      }

      // Regular standalone session or CCTV replay
      list.push(s);
    }

    return list;
  }, [sessions, benchmarks]);

  const uniqueEpisodes = useMemo(() => {
    const epsSet = new Set<number>();
    consolidatedSessions.forEach((s) => {
      if (s.model_episodes !== undefined && s.model_episodes !== null) {
        const num = Number(s.model_episodes);
        if (!isNaN(num) && num > 0) epsSet.add(num);
      } else if ((s.mode || "ai").toLowerCase() === "ai") {
        epsSet.add(300);
      }
    });
    if (epsSet.size === 0 && consolidatedSessions.length > 0) {
      [50, 100, 300, 500, 1000].forEach((e) => epsSet.add(e));
    }
    return Array.from(epsSet).sort((a, b) => a - b);
  }, [consolidatedSessions]);

  const handleModeFilterChange = (mode: string) => {
    setModeFilter(mode);
    if (mode !== "ALL" && mode !== "AI") {
      setEpisodeFilter("ALL");
    }
  };

  const filteredSessions = consolidatedSessions.filter((s) => {
    const term = searchTerm.toLowerCase().trim();
    const friendlyTitle = formatSessionTitle(s).title.toLowerCase();
    const matchesSearch =
      !term ||
      s.session_id.toLowerCase().includes(term) ||
      friendlyTitle.includes(term) ||
      (s.model_name && s.model_name.toLowerCase().includes(term)) ||
      (s.mode && s.mode.toLowerCase().includes(term));

    const sMode = (s.mode || "ai").toLowerCase();
    const isBm = s.isBenchmarkGroup || s.run_type === "benchmark" || s.session_id.startsWith("bench_");

    let matchesMode = modeFilter === "ALL";
    if (modeFilter === "BENCHMARKS") {
      matchesMode = isBm;
    } else if (modeFilter === "FINETUNED") {
      matchesMode = checkIsFinetuned(s).isFinetuned;
    } else if (modeFilter === "AI") {
      matchesMode = sMode === "ai" || isBm;
    } else if (modeFilter === "GREEDY") {
      matchesMode = sMode === "greedy" || (isBm && s.benchmark_results?.greedy !== undefined);
    } else if (modeFilter === "FIXED") {
      matchesMode = sMode === "fixed" || (isBm && s.benchmark_results?.fixed !== undefined);
    } else if (modeFilter === "MANUAL") {
      matchesMode = sMode === "manual";
    }

    const matchesEpisode =
      episodeFilter === "ALL" ||
      String(s.model_episodes ?? (sMode === "ai" ? 300 : "")) === episodeFilter;
    const matchesCongestion =
      congestionFilter === "ALL" || s.congestion_level === congestionFilter;
    const matchesRating =
      ratingFilter === "ALL" ||
      (s.performance_rating && s.performance_rating.toUpperCase() === ratingFilter);

    return matchesSearch && matchesMode && matchesEpisode && matchesCongestion && matchesRating;
  });

  const sortedSessions = [...filteredSessions].sort((a, b) => {
    const timeA = a.timestamp_ms || (parseSessionDate(a.created_at)?.getTime() ?? 0);
    const timeB = b.timestamp_ms || (parseSessionDate(b.created_at)?.getTime() ?? 0);
    return timeB - timeA;
  });

  const getModeBadge = (mode?: string, isBenchmark?: boolean) => {
    if (isBenchmark) {
      return {
        icon: <Trophy className="h-3 w-3 text-amber-400" />,
        label: "3-Mode Benchmark",
        className: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
      };
    }
    const m = (mode || "ai").toLowerCase();
    switch (m) {
      case "ai":
        return {
          icon: <Cpu className="h-3 w-3 text-indigo-400" />,
          label: "DQN AI",
          className: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
        };
      case "greedy":
        return {
          icon: <Zap className="h-3 w-3 text-emerald-400" />,
          label: "Greedy",
          className: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
        };
      case "fixed":
        return {
          icon: <Clock className="h-3 w-3 text-slate-400" />,
          label: "Fixed",
          className: "bg-slate-500/10 text-slate-300 border-slate-500/20",
        };
      case "manual":
        return {
          icon: <Sliders className="h-3 w-3 text-amber-400" />,
          label: "Manual",
          className: "bg-amber-500/10 text-amber-300 border-amber-500/20",
        };
      default:
        return {
          icon: <Video className="h-3 w-3 text-blue-400" />,
          label: m.toUpperCase(),
          className: "bg-blue-500/10 text-blue-300 border-blue-500/20",
        };
    }
  };

  const getRatingBadge = (rating?: string) => {
    const r = (rating || "MODERATE").toUpperCase();
    switch (r) {
      case "OPTIMAL":
        return {
          label: "OPTIMAL",
          className: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
        };
      case "EFFICIENT":
        return {
          label: "EFFICIENT",
          className: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
        };
      case "MODERATE":
        return {
          label: "MODERATE",
          className: "bg-amber-500/10 text-amber-300 border-amber-500/20",
        };
      case "CONGESTED":
      default:
        return {
          label: "CONGESTED",
          className: "bg-rose-500/10 text-rose-300 border-rose-500/20",
        };
    }
  };

  const getLosBadge = (los?: string) => {
    const l = (los || "C").toUpperCase();
    switch (l) {
      case "A":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "B":
        return "bg-teal-500/10 text-teal-400 border-teal-500/20";
      case "C":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "D":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "E":
        return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "F":
      default:
        return "bg-rose-500/15 text-rose-300 border-rose-500/25";
    }
  };

  const getCongestionBadge = (level: string) => {
    switch (level) {
      case "LOW":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "MODERATE":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "HIGH":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      default:
        return "bg-white/5 text-white/40 border-white/10";
    }
  };

  const handleLaunchReplay = (sessionId: string) => {
    router.push(`/realworld?session=${sessionId}`);
  };

  const toggleExpand = (id: string) => {
    setExpandedBenchmarkId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-neutral-800/80">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white text-black">
              <History className="h-3.5 w-3.5" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-white leading-none">History</h3>
              <p className="text-xs text-neutral-500 mt-1.5">
                {filteredSessions.length} sessions & benchmarks · newest first
              </p>
            </div>
          </div>
          <span className="hidden sm:inline-flex rounded-full bg-neutral-900 border border-neutral-800 px-3 py-1.5 text-xs font-mono text-neutral-400">
            {consolidatedSessions.length} total runs
          </span>
        </div>

        {/* Filters */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-600" />
            <input
              type="text"
              placeholder="Search runs"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 w-44 sm:w-52 rounded-full bg-neutral-900 border border-neutral-800 pl-9 pr-3 text-xs text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-700"
            />
          </div>
          <select
            value={modeFilter}
            onChange={(e) => handleModeFilterChange(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700 font-medium"
          >
            <option value="ALL">All Modes</option>
            <option value="FINETUNED">⚡ Fine-Tuned Runs</option>
            <option value="BENCHMARKS">🏆 3-Mode Benchmarks</option>
            <option value="AI">DQN AI</option>
            <option value="GREEDY">Greedy</option>
            <option value="FIXED">Fixed</option>
            <option value="MANUAL">Manual</option>
          </select>

          {(modeFilter === "ALL" || modeFilter === "AI") && (
            <select
              value={episodeFilter}
              onChange={(e) => setEpisodeFilter(e.target.value)}
              className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
            >
              <option value="ALL">All checkpoints</option>
              {uniqueEpisodes.map((ep) => (
                <option key={ep} value={String(ep)}>
                  {ep} eps
                </option>
              ))}
            </select>
          )}

          <select
            value={congestionFilter}
            onChange={(e) => setCongestionFilter(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
          >
            <option value="ALL">All density</option>
            <option value="LOW">Low</option>
            <option value="MODERATE">Moderate</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>

          <select
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
          >
            <option value="ALL">All status</option>
            <option value="OPTIMAL">Optimal</option>
            <option value="EFFICIENT">Efficient</option>
            <option value="MODERATE">Moderate</option>
            <option value="CONGESTED">Congested</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {consolidatedSessions.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-sm text-neutral-400">No session history yet</p>
          <p className="text-xs text-neutral-600 mt-1 max-w-sm mx-auto">
            Run a simulation or benchmark to populate history.
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <Button
              size="sm"
              onClick={() => router.push("/simulation")}
              className="h-8 rounded-full bg-white text-black hover:bg-neutral-200 text-xs"
            >
              <Play className="h-3 w-3 mr-1.5" />
              Simulation
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/realworld")}
              className="h-8 rounded-full border-neutral-800 bg-transparent text-neutral-400 hover:bg-neutral-900 hover:text-white text-xs"
            >
              <Video className="h-3 w-3 mr-1.5" />
              CCTV Twin
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1080px]">
            <thead>
              <tr className="border-b border-neutral-800/80 text-xs">
                <th className="py-3 px-6 font-normal text-neutral-500 w-[26%]">Run</th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[13%]">Model</th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[15%]">
                  <div className="relative inline-flex">
                    <button
                      onClick={() =>
                        setActivePopover(activePopover === "throughput" ? null : "throughput")
                      }
                      className="flex items-center gap-1.5 hover:text-white transition-colors"
                    >
                      <span>Throughput</span>
                      <span
                        className={`flex h-4 w-4 items-center justify-center rounded-full border text-[10px] transition-colors ${
                          activePopover === "throughput"
                            ? "bg-white text-black border-white"
                            : "border-neutral-700 bg-neutral-800 text-neutral-500 hover:bg-neutral-700 hover:text-white"
                        }`}
                      >
                        <Info className="h-2.5 w-2.5" />
                      </span>
                    </button>
                    {activePopover === "throughput" && (
                      <InlineInfoPopover
                        title="Throughput"
                        description="Vehicles cleared vs total demand. Higher is better."
                        onClose={() => setActivePopover(null)}
                      />
                    )}
                  </div>
                </th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[14%]">
                  <div className="relative inline-flex">
                    <button
                      onClick={() => setActivePopover(activePopover === "delay" ? null : "delay")}
                      className="flex items-center gap-1.5 hover:text-white transition-colors"
                    >
                      <span>Delay</span>
                      <span
                        className={`flex h-4 w-4 items-center justify-center rounded-full border text-[10px] transition-colors ${
                          activePopover === "delay"
                            ? "bg-white text-black border-white"
                            : "border-neutral-700 bg-neutral-800 text-neutral-500 hover:bg-neutral-700 hover:text-white"
                        }`}
                      >
                        <Info className="h-2.5 w-2.5" />
                      </span>
                    </button>
                    {activePopover === "delay" && (
                      <InlineInfoPopover
                        title="Delay · LOS"
                        description="LOS maps avg delay to A (≤10s) → F (>80s). Lower delay and better LOS = smoother flow."
                        onClose={() => setActivePopover(null)}
                      />
                    )}
                  </div>
                </th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[10%]">Status</th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[9%]">Queue</th>
                <th className="py-3 px-4 font-normal text-neutral-500 w-[8%]">Time</th>
                <th className="py-3 px-6 font-normal text-neutral-500 text-right w-[5%]">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/40">
              {sortedSessions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center">
                    <p className="text-sm text-neutral-500">No matching sessions</p>
                    <p className="text-xs text-neutral-600 mt-1">Adjust filters</p>
                  </td>
                </tr>
              ) : (
                sortedSessions.map((session) => {
                  const isBenchmark =
                    Boolean(session.isBenchmarkGroup) ||
                    session.run_type === "benchmark" ||
                    Boolean(session.benchmark_results);

                  const isExpanded = expandedBenchmarkId === session.session_id;
                  const { title } = formatSessionTitle(session);
                  const modeBadge = getModeBadge(session.mode, isBenchmark);
                  const rating = getRatingBadge(session.performance_rating);
                  const losClass = getLosBadge(session.level_of_service);
                  const isAI = (session.mode || "ai").toLowerCase() === "ai";
                  const throughput = session.throughput ?? session.total_vehicles;
                  const throughputPct =
                    session.throughput_pct ??
                    (session.total_vehicles > 0
                      ? Math.round((throughput / session.total_vehicles) * 100)
                      : 100);
                  const avgWait = session.avg_wait_s ?? 22.4;
                  const peakQueue = session.peak_queue ?? 0;
                  const sessionTime = formatSessionFriendlyTime(
                    session.created_at,
                    session.timestamp_ms
                  );
                  const formattedDuration = formatDuration(session.duration_s);

                  const bmResults = session.benchmark_results || {};
                  const isModelBenchmark =
                    session.benchmark_type === "model_comparison" ||
                    session.session_id.startsWith("bm_model_") ||
                    Object.keys(bmResults).some((k) => k.startsWith("model_"));

                  const bmAI = bmResults.ai;
                  const bmFixed = bmResults.fixed;
                  const bmGreedy = bmResults.greedy;

                  const aiWait = bmAI?.avg_wait_s ?? bmAI?.avg_wait_time;
                  const fixedWait = bmFixed?.avg_wait_s ?? bmFixed?.avg_wait_time;
                  const greedyWait = bmGreedy?.avg_wait_s ?? bmGreedy?.avg_wait_time;

                  const winner = session.winner || (isModelBenchmark ? Object.keys(bmResults)[0] : "ai");
                  const winnerName = isModelBenchmark
                    ? session.winner_label || (bmResults[winner]?.label ?? `Model ${session.winner_episode ?? winner}`)
                    : winner === "ai"
                    ? "FlowSync DQN AI"
                    : winner === "greedy"
                    ? "Greedy Controller"
                    : "Fixed Timer";

                  const bestWait = bmResults[winner]?.avg_wait_time ?? bmResults[winner]?.avg_wait_s ?? avgWait;
                  const winnerImpKey = `${winner}_wait_pct`;
                  const winnerImp = session.improvements?.[winnerImpKey];
                  const ftInfo = checkIsFinetuned(session);

                  return (
                    <tr
                      key={session.session_id}
                      className={`group transition-colors ${
                        isBenchmark
                          ? "hover:bg-neutral-900/70"
                          : "hover:bg-neutral-900/40"
                      } ${isExpanded ? "bg-neutral-900/80" : ""}`}
                    >
                      {/* Column 1: Run */}
                      <td className="py-5 px-6">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-white leading-tight">
                              {title}
                            </span>
                            {ftInfo.isFinetuned && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/35 px-2.5 py-0.5 text-[10px] font-semibold text-amber-300 shadow-sm shadow-amber-500/10">
                                <Zap className="h-2.5 w-2.5 text-amber-400" />
                                <span>Fine-Tuned Model</span>
                                {ftInfo.scenario && (
                                  <span className="text-amber-200/80 font-normal">
                                    · {formatScenarioName(ftInfo.scenario)}
                                  </span>
                                )}
                              </span>
                            )}
                            {isBenchmark && (
                              isModelBenchmark ? (
                                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                                  <Layers className="h-2.5 w-2.5 text-emerald-300" />
                                  Multi-Model Benchmark
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                                  <Sparkles className="h-2.5 w-2.5 text-amber-300" />
                                  Benchmark
                                </span>
                              )
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium border ${modeBadge.className}`}
                            >
                              {modeBadge.icon}
                              {modeBadge.label}
                            </span>

                            {isBenchmark && session.winner && (
                              <span
                                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium border ${
                                  isModelBenchmark
                                    ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                                    : winner === "ai"
                                    ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
                                    : winner === "greedy"
                                    ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                                    : "bg-slate-500/10 text-slate-300 border-slate-500/30"
                                }`}
                              >
                                <Trophy className="h-2.5 w-2.5 text-amber-400" />
                                <span>{winnerName} Won</span>
                              </span>
                            )}

                            <span className="text-xs text-neutral-500">
                              {sessionTime.display} · {sessionTime.relative}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Column 2: Model */}
                      <td className="py-5 px-4">
                        {isBenchmark ? (
                          isModelBenchmark ? (
                            <div className="space-y-1">
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-xs font-mono text-emerald-300">
                                <Bot className="h-3 w-3" />
                                DQN Checkpoints
                              </span>
                              <div className="text-xs text-neutral-400">
                                {Object.keys(bmResults).length} models compared
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              {ftInfo.isFinetuned ? (
                                <div className="flex items-center gap-1 flex-wrap">
                                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-xs font-mono text-amber-300">
                                    <Zap className="h-2.5 w-2.5 text-amber-400" />
                                    {session.model_episodes ? `${session.model_episodes} eps` : "FT"}
                                  </span>
                                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 font-semibold uppercase tracking-wider">
                                    Fine-Tuned
                                  </span>
                                </div>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-xs font-mono text-indigo-300">
                                  <Bot className="h-3 w-3" />
                                  {session.model_episodes ? `${session.model_episodes} eps` : "DQN AI"}
                                </span>
                              )}
                              <div className="text-xs text-neutral-400">
                                vs Fixed vs Greedy
                              </div>
                            </div>
                          )
                        ) : isAI ? (
                          ftInfo.isFinetuned ? (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1 flex-wrap">
                                <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-xs font-mono text-amber-300">
                                  <Zap className="h-2.5 w-2.5 text-amber-400" />
                                  {session.model_episodes ? `${session.model_episodes} eps` : "FT"}
                                </span>
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 font-semibold uppercase tracking-wider">
                                  Fine-Tuned
                                </span>
                              </div>
                              <div className="text-xs text-amber-200/90 truncate max-w-[130px]" title={session.model_name || ""}>
                                {session.model_name || "Specialized DQN"}
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              <span className="inline-flex items-center rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-xs font-mono text-indigo-300">
                                {session.model_episodes ?? 300} eps
                              </span>
                              <div className="text-xs text-neutral-500 truncate max-w-[120px]">
                                {session.model_name || "FlowSync DQN"}
                              </div>
                            </div>
                          )
                        ) : (
                          <span className="text-xs text-neutral-500">Deterministic</span>
                        )}
                      </td>

                      {/* Column 3: Throughput */}
                      <td className="py-5 px-4">
                        {isBenchmark ? (
                          isModelBenchmark ? (
                            <div className="space-y-1.5">
                              <div className="text-xs font-mono text-white flex items-center gap-1.5">
                                <span className="text-emerald-400 font-medium">
                                  Top: {bmResults[winner]?.total_passed ?? bmResults[winner]?.throughput ?? throughput} veh
                                </span>
                              </div>
                              <div className="text-[11px] text-neutral-500">
                                {Object.keys(bmResults).length} models evaluated
                              </div>
                            </div>
                          ) : (bmAI || bmFixed || bmGreedy) ? (
                            <div className="space-y-1.5">
                              <div className="text-xs font-mono text-white flex items-center gap-1.5">
                                <span className="text-indigo-400 font-medium">
                                  AI: {bmAI?.throughput ?? bmAI?.total_passed ?? "-"}
                                </span>
                                <span className="text-neutral-600">|</span>
                                <span className="text-slate-400 font-medium">
                                  Fix: {bmFixed?.throughput ?? bmFixed?.total_passed ?? "-"}
                                </span>
                                <span className="text-neutral-600">|</span>
                                <span className="text-emerald-400 font-medium">
                                  Gr: {bmGreedy?.throughput ?? bmGreedy?.total_passed ?? "-"}
                                </span>
                              </div>
                              <div className="text-[11px] text-neutral-500">
                                Vehicles cleared
                              </div>
                            </div>
                          ) : (
                            <div className="text-sm font-mono font-medium text-white">{throughput} veh</div>
                          )
                        ) : (
                          <div className="space-y-1.5">
                            <div className="text-sm font-mono font-medium text-white">
                              {throughput}
                              <span className="text-neutral-600 font-normal">
                                {" "}
                                / {session.total_vehicles}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="h-1 flex-1 max-w-[72px] bg-neutral-800 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    throughputPct >= 90
                                      ? "bg-emerald-500"
                                      : throughputPct >= 75
                                      ? "bg-amber-500"
                                      : "bg-rose-500"
                                  }`}
                                  style={{ width: `${Math.min(100, throughputPct)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono text-neutral-500">
                                {throughputPct}%
                              </span>
                            </div>
                          </div>
                        )}
                      </td>

                      {/* Column 4: Delay */}
                      <td className="py-5 px-4">
                        {isBenchmark ? (
                          isModelBenchmark ? (
                            <div className="space-y-1">
                              <div className="text-xs font-mono text-white flex items-center gap-1.5">
                                <span className="text-amber-400 font-semibold">
                                  Best: {bestWait.toFixed(1)}s
                                </span>
                              </div>
                              <div className="text-xs text-neutral-500">
                                {winnerImp !== undefined && winnerImp > 0 ? (
                                  <span className="text-emerald-400 font-medium">
                                    +{winnerImp}% vs baseline
                                  </span>
                                ) : (
                                  "DQN checkpoints"
                                )}
                              </div>
                            </div>
                          ) : (aiWait !== undefined || fixedWait !== undefined) ? (
                            <div className="space-y-1">
                              <div className="text-xs font-mono text-white flex items-center gap-1.5">
                                <span className="text-indigo-400 font-semibold">
                                  {aiWait !== undefined ? `${aiWait.toFixed(1)}s` : "-"}
                                </span>
                                <span className="text-neutral-600">|</span>
                                <span className="text-slate-400 font-semibold">
                                  {fixedWait !== undefined ? `${fixedWait.toFixed(1)}s` : "-"}
                                </span>
                                <span className="text-neutral-600">|</span>
                                <span className="text-emerald-400 font-semibold">
                                  {greedyWait !== undefined ? `${greedyWait.toFixed(1)}s` : "-"}
                                </span>
                              </div>
                              <div className="text-xs text-neutral-500">
                                {session.improvements?.ai_wait_pct !== undefined ? (
                                  <span
                                    className={
                                      session.improvements.ai_wait_pct > 0
                                        ? "text-emerald-400 font-medium"
                                        : "text-neutral-400"
                                    }
                                  >
                                    {session.improvements.ai_wait_pct > 0 ? "+" : ""}
                                    {session.improvements.ai_wait_pct}% AI vs fixed
                                  </span>
                                ) : (
                                  "avg wait per mode"
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="text-sm font-mono font-medium text-white">{avgWait.toFixed(1)}s</div>
                          )
                        ) : (
                          <div className="space-y-1">
                            <div className="text-sm font-mono font-medium text-white">
                              {avgWait.toFixed(1)}s
                            </div>
                            <span
                              className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-mono font-bold border ${losClass}`}
                            >
                              LOS {session.level_of_service ?? "C"}
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Column 5: Status */}
                      <td className="py-5 px-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium border ${rating.className}`}
                        >
                          {rating.label}
                        </span>
                      </td>

                      {/* Column 6: Queue */}
                      <td className="py-5 px-4">
                        <div className="text-sm font-mono text-white">{peakQueue}</div>
                        <div
                          className={`mt-1 inline-flex rounded-full px-1.5 py-0.5 text-xs border ${getCongestionBadge(
                            session.congestion_level
                          )}`}
                        >
                          {session.congestion_level}
                        </div>
                      </td>

                      {/* Column 7: Time */}
                      <td className="py-5 px-4">
                        <div className="text-xs font-mono text-white">{formattedDuration}</div>
                        <div className="text-xs text-neutral-600">
                          {isBenchmark ? "per mode" : `${session.total_frames} fr`}
                        </div>
                      </td>

                      {/* Column 8: Action */}
                      <td className="py-5 px-6 text-right">
                        {isBenchmark ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleExpand(session.session_id)}
                            className={`h-7 rounded-full text-xs px-3 transition-colors ${
                              isExpanded
                                ? "bg-indigo-600 text-white border-indigo-500 hover:bg-indigo-500"
                                : "border-neutral-800 bg-neutral-900 text-neutral-300 hover:bg-neutral-800 hover:text-white"
                            }`}
                          >
                            <span>Breakdown</span>
                            {isExpanded ? (
                              <ChevronUp className="h-3 w-3 ml-1" />
                            ) : (
                              <ChevronDown className="h-3 w-3 ml-1" />
                            )}
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleLaunchReplay(session.session_id)}
                            className="h-7 rounded-full border-neutral-800 bg-transparent text-neutral-300 hover:bg-white hover:text-black hover:border-white text-xs px-3"
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Replay
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>

          {/* Accordion Details for the Expanded Benchmark */}
          {expandedBenchmarkId && (
            <div className="p-4 sm:p-6 bg-neutral-950 border-t border-b border-indigo-500/20 space-y-4 animate-in fade-in-50 duration-200">
              {(() => {
                const target = sortedSessions.find((s) => s.session_id === expandedBenchmarkId);
                if (!target) return null;
                const targetFt = checkIsFinetuned(target);
                const bRes = target.benchmark_results || {};

                const isModelComparison =
                  target.benchmark_type === "model_comparison" ||
                  target.session_id.startsWith("bm_model_") ||
                  Object.keys(bRes).some((k) => k.startsWith("model_"));

                const winner = target.winner || (isModelComparison ? Object.keys(bRes)[0] : "ai");
                const winnerName = isModelComparison
                  ? target.winner_label || (bRes[winner]?.label ?? `Model ${target.winner_episode ?? winner}`)
                  : winner === "ai"
                  ? "FlowSync DQN AI"
                  : winner === "greedy"
                  ? "Greedy Controller"
                  : "Fixed Timer";

                const children = target.benchmarkRun?.child_sessions || {};

                if (isModelComparison) {
                  const winnerImpKey = `${winner}_wait_pct`;
                  const winnerImp = target.improvements?.[winnerImpKey];

                  return (
                    <div className="space-y-4">
                      {targetFt.isFinetuned && (
                        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-2.5">
                            <div className="h-7 w-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-300 shrink-0">
                              <Zap className="h-4 w-4 text-amber-400" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-amber-200">Fine-Tuned Checkpoints Evaluated</span>
                                {targetFt.scenario && (
                                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                    {formatScenarioName(targetFt.scenario)}
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-white/60">
                                Evaluates specialized scenario-adapted models against baseline checkpoints under identical traffic arrivals.
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      {/* Header Info */}
                      <div className="flex flex-wrap items-center justify-between gap-3 bg-neutral-900/60 p-3 rounded-xl border border-neutral-800">
                        <div className="flex items-center gap-2.5">
                          <Trophy className="h-4 w-4 text-amber-400" />
                          <div>
                            <div className="text-xs font-semibold text-white">
                              Multi-Model Benchmark Winner: {winnerName}
                              {target.winner_episode !== undefined && (
                                <span className="ml-2 font-mono text-[10px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full font-normal">
                                  {target.winner_episode} eps
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-neutral-400">
                              {winnerImp !== undefined && winnerImp > 0
                                ? `Delivered ${winnerImp}% delay reduction vs baseline checkpoint on identical traffic.`
                                : `Evaluated ${Object.keys(bRes).length} DQN AI model checkpoints under identical vehicle arrivals (CRN seed).`}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedBenchmarkId(null)}
                          className="h-7 text-xs text-neutral-400 hover:text-white"
                        >
                          <X className="h-3.5 w-3.5 mr-1" />
                          Close Breakdown
                        </Button>
                      </div>

                      {/* Model Cards in Responsive Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {Object.entries(bRes).map(([mKey, mData]) => {
                          const isMWin = mKey === winner;
                          const mWait = mData?.avg_wait_s ?? mData?.avg_wait_time ?? 0;
                          const mThru = mData?.throughput ?? mData?.total_passed ?? 0;
                          const mQueue = mData?.peak_queue ?? mData?.max_queue ?? 0;
                          const mGain = target.improvements?.[`${mKey}_wait_pct`];
                          const childSess = children[mKey];

                          return (
                            <div
                              key={mKey}
                              className={`rounded-xl p-4 border transition-all ${
                                isMWin
                                  ? "bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-500/5"
                                  : "bg-neutral-900/40 border-neutral-800"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <Bot className="h-4 w-4 text-emerald-400 shrink-0" />
                                  <span className="text-sm font-semibold text-white truncate">
                                    {mData.label || mKey}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                  {mData.model_episode !== undefined && (
                                    <span className="text-[10px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-mono">
                                      {mData.model_episode} eps
                                    </span>
                                  )}
                                  {isMWin ? (
                                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                                      <Trophy className="h-2.5 w-2.5" />
                                      WINNER
                                    </span>
                                  ) : null}
                                </div>
                              </div>

                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                                  <span className="text-[10px] text-neutral-500 block">Avg Delay</span>
                                  <span className="font-mono font-medium text-white text-base">
                                    {mWait.toFixed(1)}s
                                  </span>
                                </div>
                                <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                                  <span className="text-[10px] text-neutral-500 block">Throughput</span>
                                  <span className="font-mono font-medium text-white text-base">
                                    {mThru} vehs
                                  </span>
                                </div>
                                <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                                  <span className="text-[10px] text-neutral-500 block">Peak Queue</span>
                                  <span className="font-mono font-medium text-white text-base">
                                    {mQueue} cars
                                  </span>
                                </div>
                                <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                                  <span className="text-[10px] text-neutral-500 block">vs Baseline</span>
                                  <span
                                    className={`font-mono font-semibold text-base ${
                                      mGain && mGain > 0
                                        ? "text-emerald-400"
                                        : mGain && mGain < 0
                                        ? "text-rose-400"
                                        : "text-neutral-400"
                                    }`}
                                  >
                                    {mGain !== undefined ? (mGain > 0 ? `+${mGain}%` : `${mGain}%`) : "Baseline"}
                                  </span>
                                </div>
                              </div>

                              {childSess && (
                                <div className="mt-3 pt-3 border-t border-white/5 flex justify-end">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleLaunchReplay(childSess.session_id)}
                                    className="h-7 text-xs rounded-full border-emerald-500/30 text-emerald-300 hover:bg-emerald-600 hover:text-white"
                                  >
                                    <Play className="h-3 w-3 mr-1" />
                                    Replay
                                  </Button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                }

                const ai = bRes.ai;
                const fixed = bRes.fixed;
                const greedy = bRes.greedy;

                const aiWait = ai?.avg_wait_s ?? ai?.avg_wait_time ?? 0;
                const fixedWait = fixed?.avg_wait_s ?? fixed?.avg_wait_time ?? 0;
                const greedyWait = greedy?.avg_wait_s ?? greedy?.avg_wait_time ?? 0;

                const aiThru = ai?.throughput ?? ai?.total_passed ?? 0;
                const fixedThru = fixed?.throughput ?? fixed?.total_passed ?? 0;
                const greedyThru = greedy?.throughput ?? greedy?.total_passed ?? 0;

                const aiQueue = ai?.peak_queue ?? ai?.max_queue ?? 0;
                const fixedQueue = fixed?.peak_queue ?? fixed?.max_queue ?? 0;
                const greedyQueue = greedy?.peak_queue ?? greedy?.max_queue ?? 0;

                const isAIWinner = winner === "ai";
                const isFixedWinner = winner === "fixed";
                const isGreedyWinner = winner === "greedy";

                const aiGain =
                  target.improvements?.ai_wait_pct ??
                  (fixedWait > 0 && aiWait > 0
                    ? Number((((fixedWait - aiWait) / fixedWait) * 100).toFixed(1))
                    : 0);
                const greedyGain =
                  target.improvements?.greedy_wait_pct ??
                  (fixedWait > 0 && greedyWait > 0
                    ? Number((((fixedWait - greedyWait) / fixedWait) * 100).toFixed(1))
                    : 0);

                return (
                  <div className="space-y-4">
                    {/* Header Info */}
                    <div className="flex flex-wrap items-center justify-between gap-3 bg-neutral-900/60 p-3 rounded-xl border border-neutral-800">
                      <div className="flex items-center gap-2.5">
                        <Trophy className="h-4 w-4 text-amber-400" />
                        <div>
                          <div className="text-xs font-semibold text-white">
                            Benchmark Result:{" "}
                            {isAIWinner
                              ? "FlowSync DQN AI Won"
                              : isGreedyWinner
                              ? "Greedy Controller Won"
                              : "Fixed Timer Won"}
                          </div>
                          <p className="text-[11px] text-neutral-400">
                            {aiGain !== 0
                              ? `FlowSync DQN achieved ${aiGain > 0 ? "+" : ""}${aiGain}% delay reduction vs Fixed Timer baseline`
                              : "Comprehensive 3-controller performance evaluation on identical traffic seed."}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpandedBenchmarkId(null)}
                        className="h-7 text-xs text-neutral-400 hover:text-white"
                      >
                        <X className="h-3.5 w-3.5 mr-1" />
                        Close Breakdown
                      </Button>
                    </div>

                    {targetFt.isFinetuned && (
                      <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                        <div className="flex items-center gap-2.5">
                          <div className="h-7 w-7 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-300 shrink-0">
                            <Zap className="h-4 w-4 text-amber-400" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-amber-200">Fine-Tuned Model Active</span>
                              {targetFt.scenario && (
                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                  {formatScenarioName(targetFt.scenario)}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-white/60">
                              Tested using specialized policy weights adapted with reduced learning rate (1e-4) and warm exploration.
                            </p>
                          </div>
                        </div>
                        <span className="font-mono text-[10px] text-amber-300/80 bg-black/40 px-2.5 py-1 rounded-md border border-amber-500/20">
                          {target.model_name || "Specialized Policy"}
                        </span>
                      </div>
                    )}

                    {/* 3 Modes Side-by-Side Cards in STRICT Order: 1. DQN AI, 2. Fixed, 3. Greedy */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* 1. FlowSync DQN AI */}
                      <div
                        className={`rounded-xl p-4 border transition-all ${
                          isAIWinner
                            ? "bg-indigo-950/40 border-indigo-500/50 shadow-lg shadow-indigo-500/10"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-1.5">
                            <Cpu className="h-4 w-4 text-indigo-400" />
                            <span className="text-sm font-semibold text-white">
                              FlowSync DQN AI
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {targetFt.isFinetuned && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-full">
                                <Zap className="h-2.5 w-2.5 text-amber-400" />
                                Fine-Tuned
                              </span>
                            )}
                            {target.model_episodes && (
                              <span className="text-[10px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full font-mono">
                                {target.model_episodes} eps
                              </span>
                            )}
                            {isAIWinner ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                                <Trophy className="h-2.5 w-2.5" />
                                WINNER
                              </span>
                            ) : (
                              <span className="text-[10px] text-neutral-500 font-mono">DQN Agent</span>
                            )}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Avg Delay</span>
                            <span className="font-mono font-medium text-white text-base">
                              {aiWait.toFixed(1)}s
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Throughput</span>
                            <span className="font-mono font-medium text-white text-base">
                              {aiThru} vehs
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Peak Queue</span>
                            <span className="font-mono font-medium text-white text-base">
                              {aiQueue} cars
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">vs Fixed Baseline</span>
                            <span
                              className={`font-mono font-semibold text-base ${
                                aiGain > 0
                                  ? "text-emerald-400"
                                  : aiGain < 0
                                  ? "text-rose-400"
                                  : "text-neutral-400"
                              }`}
                            >
                              {aiGain > 0 ? `+${aiGain}%` : `${aiGain}%`}
                            </span>
                          </div>
                        </div>

                        {children.ai && (
                          <div className="mt-3 pt-3 border-t border-white/5 flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleLaunchReplay(children.ai.session_id)}
                              className="h-7 text-xs rounded-full border-indigo-500/30 text-indigo-300 hover:bg-indigo-600 hover:text-white"
                            >
                              <Play className="h-3 w-3 mr-1" />
                              Replay AI Run
                            </Button>
                          </div>
                        )}
                      </div>

                      {/* 2. Fixed Timer */}
                      <div
                        className={`rounded-xl p-4 border transition-all ${
                          isFixedWinner
                            ? "bg-slate-900/60 border-slate-500/50 shadow-lg"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-1.5">
                            <Clock className="h-4 w-4 text-slate-400" />
                            <span className="text-sm font-semibold text-white">Fixed Timer</span>
                          </div>
                          {isFixedWinner ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                              <Trophy className="h-2.5 w-2.5" />
                              WINNER
                            </span>
                          ) : (
                            <span className="text-[10px] text-neutral-500 font-mono">Baseline</span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Avg Delay</span>
                            <span className="font-mono font-medium text-white text-base">
                              {fixedWait.toFixed(1)}s
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Throughput</span>
                            <span className="font-mono font-medium text-white text-base">
                              {fixedThru} vehs
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Peak Queue</span>
                            <span className="font-mono font-medium text-white text-base">
                              {fixedQueue} cars
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">vs Fixed Baseline</span>
                            <span className="font-mono font-semibold text-base text-neutral-400">
                              0.0%
                            </span>
                          </div>
                        </div>

                        {children.fixed && (
                          <div className="mt-3 pt-3 border-t border-white/5 flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleLaunchReplay(children.fixed.session_id)}
                              className="h-7 text-xs rounded-full border-neutral-700 text-neutral-300 hover:bg-white hover:text-black"
                            >
                              <Play className="h-3 w-3 mr-1" />
                              Replay Fixed Run
                            </Button>
                          </div>
                        )}
                      </div>

                      {/* 3. Greedy Controller */}
                      <div
                        className={`rounded-xl p-4 border transition-all ${
                          isGreedyWinner
                            ? "bg-emerald-950/40 border-emerald-500/50 shadow-lg shadow-emerald-500/10"
                            : "bg-neutral-900/40 border-neutral-800"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-1.5">
                            <Zap className="h-4 w-4 text-emerald-400" />
                            <span className="text-sm font-semibold text-white">
                              Greedy Controller
                            </span>
                          </div>
                          {isGreedyWinner ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 px-2 py-0.5 rounded-full">
                              <Trophy className="h-2.5 w-2.5" />
                              WINNER
                            </span>
                          ) : (
                            <span className="text-[10px] text-neutral-500 font-mono">Actuated</span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Avg Delay</span>
                            <span className="font-mono font-medium text-white text-base">
                              {greedyWait.toFixed(1)}s
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Throughput</span>
                            <span className="font-mono font-medium text-white text-base">
                              {greedyThru} vehs
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">Peak Queue</span>
                            <span className="font-mono font-medium text-white text-base">
                              {greedyQueue} cars
                            </span>
                          </div>
                          <div className="bg-black/50 rounded-lg p-2.5 border border-white/5">
                            <span className="text-[10px] text-neutral-500 block">vs Fixed Baseline</span>
                            <span
                              className={`font-mono font-semibold text-base ${
                                greedyGain > 0
                                  ? "text-emerald-400"
                                  : greedyGain < 0
                                  ? "text-rose-400"
                                  : "text-neutral-400"
                              }`}
                            >
                              {greedyGain > 0 ? `+${greedyGain}%` : `${greedyGain}%`}
                            </span>
                          </div>
                        </div>

                        {children.greedy && (
                          <div className="mt-3 pt-3 border-t border-white/5 flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleLaunchReplay(children.greedy.session_id)}
                              className="h-7 text-xs rounded-full border-emerald-500/30 text-emerald-300 hover:bg-emerald-600 hover:text-white"
                            >
                              <Play className="h-3 w-3 mr-1" />
                              Replay Greedy Run
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

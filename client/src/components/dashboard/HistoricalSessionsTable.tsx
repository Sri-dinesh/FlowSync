"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  History,
  Play,
  Search,
  Filter,
  Video,
  Cpu,
  Zap,
  Clock,
  Sliders,
  Award,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  ArrowUpRight,
  RotateCcw,
  Activity,
  ArrowRight,
  Info,
} from "lucide-react";

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
  // Enhanced Evaluation & Telemetry
  mode?: "ai" | "greedy" | "fixed" | "manual" | string;
  model_name?: string;
  model_episodes?: number | string;
  throughput?: number;
  throughput_pct?: number;
  avg_wait_s?: number;
  peak_queue?: number;
  performance_rating?: "OPTIMAL" | "EFFICIENT" | "MODERATE" | "CONGESTED" | string;
  level_of_service?: "A" | "B" | "C" | "D" | "E" | "F" | string;
  efficiency_gain_pct?: number;
}

interface Props {
  sessions: SessionItem[];
}

/**
 * Safely parse date timestamp across ISO strings, SQL "YYYY-MM-DD HH:MM:SS", or epoch ms
 */
function parseSessionDate(createdAt?: string, timestampMs?: number): Date | null {
  if (timestampMs && !isNaN(timestampMs) && timestampMs > 0) {
    const d = new Date(timestampMs);
    if (!isNaN(d.getTime())) return d;
  }
  if (!createdAt) return null;
  const sanitized = createdAt.includes(" ") && !createdAt.includes("T")
    ? createdAt.replace(" ", "T")
    : createdAt;
  const d = new Date(sanitized);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format session creation time into human-friendly, concise, understandable format
 */
function formatSessionFriendlyTime(createdAt?: string, timestampMs?: number): {
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

/**
 * Format duration in seconds into intuitive minutes and seconds
 * e.g., 40 -> "40s", 120 -> "2m 00s", 1335.7 -> "22m 16s"
 */
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

/**
 * Generate a clear, human-understandable title and short identifier for each session
 */
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

  // 1. Multi-mode Benchmark evaluations
  if (sid.startsWith("bench_") || (session as any).run_type === "benchmark") {
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

  // 2. Real-World CCTV Digital Twin / Camera playback
  if (
    session.has_arrivals ||
    sid.includes("cctv") ||
    (session as any).run_type === "cctv_replay"
  ) {
    return {
      title: "CCTV Digital Twin Replay",
      category: "Digital Twin",
      shortId,
    };
  }

  // 3. Regular Simulation Runs
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

/**
 * Get comprehensive Highway Capacity Manual (HCM) Level of Service (LOS) description
 */
function getLosDescription(los?: string): string {
  const l = (los || "C").toUpperCase();
  switch (l) {
    case "A":
      return "LOS A: Free Flow (≤10s avg delay). Minimal wait time, optimal intersection performance.";
    case "B":
      return "LOS B: Stable Flow (10.1s - 20.0s avg delay). Good progression, minor queuing.";
    case "C":
      return "LOS C: Acceptable Flow (20.1s - 35.0s avg delay). Fair progression, standard urban target.";
    case "D":
      return "LOS D: Tolerable Flow (35.1s - 55.0s avg delay). Noticeable congestion, queues approaching capacity.";
    case "E":
      return "LOS E: Unstable Flow (55.1s - 80.0s avg delay). Operating at maximum junction capacity, long queues.";
    case "F":
    default:
      return "LOS F: Forced Breakdown (>80.0s avg delay). Severe delay, demand exceeds junction capacity.";
  }
}

export default function HistoricalSessionsTable({ sessions }: Props) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [modeFilter, setModeFilter] = useState("ALL");
  const [episodeFilter, setEpisodeFilter] = useState("ALL");
  const [congestionFilter, setCongestionFilter] = useState("ALL");
  const [ratingFilter, setRatingFilter] = useState("ALL");

  // Dynamic list of unique training episodes from sessions
  const uniqueEpisodes = useMemo(() => {
    const epsSet = new Set<number>();
    sessions.forEach((s) => {
      if (s.model_episodes !== undefined && s.model_episodes !== null) {
        const num = Number(s.model_episodes);
        if (!isNaN(num) && num > 0) epsSet.add(num);
      } else if ((s.mode || "ai").toLowerCase() === "ai") {
        epsSet.add(300);
      }
    });
    if (epsSet.size === 0 && sessions.length > 0) {
      [50, 100, 300, 500, 1000].forEach((e) => epsSet.add(e));
    }
    return Array.from(epsSet).sort((a, b) => a - b);
  }, [sessions]);

  const handleModeFilterChange = (mode: string) => {
    setModeFilter(mode);
    if (mode !== "ALL" && mode !== "AI") {
      setEpisodeFilter("ALL");
    }
  };

  const filteredSessions = sessions.filter((s) => {
    const term = searchTerm.toLowerCase().trim();
    const friendlyTitle = formatSessionTitle(s).title.toLowerCase();
    const matchesSearch =
      !term ||
      s.session_id.toLowerCase().includes(term) ||
      friendlyTitle.includes(term) ||
      (s.model_name && s.model_name.toLowerCase().includes(term)) ||
      (s.mode && s.mode.toLowerCase().includes(term));

    const sMode = (s.mode || "ai").toLowerCase();
    const matchesMode =
      modeFilter === "ALL" ||
      (modeFilter === "AI" && sMode === "ai") ||
      (modeFilter === "GREEDY" && sMode === "greedy") ||
      (modeFilter === "FIXED" && sMode === "fixed") ||
      (modeFilter === "MANUAL" && sMode === "manual");

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

  // Ensure sessions are sorted chronologically with newest first
  const sortedSessions = [...filteredSessions].sort((a, b) => {
    const timeA = a.timestamp_ms || (parseSessionDate(a.created_at)?.getTime() ?? 0);
    const timeB = b.timestamp_ms || (parseSessionDate(b.created_at)?.getTime() ?? 0);
    return timeB - timeA;
  });

  const getModeBadge = (mode?: string) => {
    const m = (mode || "ai").toLowerCase();
    switch (m) {
      case "ai":
        return {
          icon: <Cpu className="h-3 w-3 text-indigo-400" />,
          label: "DQN AI",
          className: "bg-indigo-500/10 text-indigo-300 border-indigo-500/25",
        };
      case "greedy":
        return {
          icon: <Zap className="h-3 w-3 text-emerald-400" />,
          label: "Greedy",
          className: "bg-emerald-500/10 text-emerald-300 border-emerald-500/25",
        };
      case "fixed":
        return {
          icon: <Clock className="h-3 w-3 text-slate-400" />,
          label: "Fixed Timer",
          className: "bg-slate-500/10 text-slate-300 border-slate-500/25",
        };
      case "manual":
        return {
          icon: <Sliders className="h-3 w-3 text-amber-400" />,
          label: "Manual",
          className: "bg-amber-500/10 text-amber-300 border-amber-500/25",
        };
      default:
        return {
          icon: <Video className="h-3 w-3 text-blue-400" />,
          label: m.toUpperCase(),
          className: "bg-blue-500/10 text-blue-300 border-blue-500/25",
        };
    }
  };

  const getRatingBadge = (rating?: string) => {
    const r = (rating || "MODERATE").toUpperCase();
    switch (r) {
      case "OPTIMAL":
        return {
          icon: <Award className="h-3 w-3 text-emerald-400" />,
          label: "OPTIMAL",
          sub: "Peak Flow",
          className: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
        };
      case "EFFICIENT":
        return {
          icon: <CheckCircle2 className="h-3 w-3 text-cyan-400" />,
          label: "EFFICIENT",
          sub: "High Throughput",
          className: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
        };
      case "MODERATE":
        return {
          icon: <Activity className="h-3 w-3 text-amber-400" />,
          label: "MODERATE",
          sub: "Minor Delay",
          className: "bg-amber-500/15 text-amber-300 border-amber-500/30",
        };
      case "CONGESTED":
      default:
        return {
          icon: <AlertTriangle className="h-3 w-3 text-rose-400" />,
          label: "CONGESTED",
          sub: "Queue Delay",
          className: "bg-rose-500/15 text-rose-300 border-rose-500/30",
        };
    }
  };

  const getLosBadge = (los?: string) => {
    const l = (los || "C").toUpperCase();
    switch (l) {
      case "A":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "B":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "C":
        return "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
      case "D":
        return "bg-amber-500/15 text-amber-300 border-amber-500/30";
      case "E":
        return "bg-orange-500/15 text-orange-400 border-orange-500/30";
      case "F":
      default:
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
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
        return "bg-white/10 text-white/50 border-white/20";
    }
  };

  const handleLaunchReplay = (sessionId: string) => {
    router.push(`/realworld?session=${sessionId}`);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md flex flex-col gap-5">
      {/* Table Header & Search Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <History className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-bold tracking-wider uppercase text-white">
              Historical Detection & Replay Sessions
            </h3>
            <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] font-mono text-white/60">
              {filteredSessions.length} recorded
            </span>
          </div>
          <p className="text-xs text-white/40 mt-1">
            Archived simulation runs, multi-mode benchmarks, and real-world CCTV camera recordings with deep evaluation metrics
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-white/30" />
            <input
              type="text"
              placeholder="Search session or model..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 w-44 sm:w-48 rounded-lg bg-black/40 border border-white/10 pl-8 pr-2.5 text-xs text-white placeholder:text-white/30 focus:border-indigo-500 focus:outline-none transition-colors"
            />
          </div>

          {/* Mode Filter */}
          <div className="relative">
            <select
              value={modeFilter}
              onChange={(e) => handleModeFilterChange(e.target.value)}
              className="h-8 rounded-lg bg-black/40 border border-white/10 px-2.5 text-xs text-white/80 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="ALL">All Modes</option>
              <option value="AI">DQN AI</option>
              <option value="GREEDY">Greedy</option>
              <option value="FIXED">Fixed Timer</option>
              <option value="MANUAL">Manual</option>
            </select>
          </div>

          {/* Model Episodes Filter (For AI or All modes) */}
          {(modeFilter === "ALL" || modeFilter === "AI") && (
            <div className="relative">
              <select
                value={episodeFilter}
                onChange={(e) => setEpisodeFilter(e.target.value)}
                className="h-8 rounded-lg bg-black/40 border border-indigo-500/30 px-2.5 text-xs text-indigo-300 focus:border-indigo-500 focus:outline-none transition-colors"
                title="Filter by DQN model training episodes"
              >
                <option value="ALL">All Episodes</option>
                {uniqueEpisodes.map((ep) => (
                  <option key={ep} value={String(ep)}>
                    {ep} Episodes
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Performance Rating Filter */}
          <div className="relative">
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value)}
              className="h-8 rounded-lg bg-black/40 border border-white/10 px-2.5 text-xs text-white/80 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="ALL">All Evaluations</option>
              <option value="OPTIMAL">Optimal</option>
              <option value="EFFICIENT">Efficient</option>
              <option value="MODERATE">Moderate</option>
              <option value="CONGESTED">Congested</option>
            </select>
          </div>

          {/* Congestion Filter */}
          <div className="relative">
            <select
              value={congestionFilter}
              onChange={(e) => setCongestionFilter(e.target.value)}
              className="h-8 rounded-lg bg-black/40 border border-white/10 px-2.5 text-xs text-white/80 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="ALL">All Congestion</option>
              <option value="LOW">Low</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fresh Reset Banner / Empty State */}
      {sessions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/15 bg-gradient-to-b from-indigo-950/20 to-transparent p-8 flex flex-col items-center justify-center text-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 shadow-lg shadow-indigo-500/10">
            <Sparkles className="h-6 w-6" />
          </div>
          <div className="max-w-md">
            <h4 className="text-base font-semibold text-white">
              Database Reset & Ready for Fresh Training
            </h4>
            <p className="text-xs text-white/50 mt-1.5 leading-relaxed">
              All legacy model checkpoints, simulation logs, and past telemetry records have been purged. You can train a new DQN model from episode 1, run simulation benchmarks, or ingest live CCTV footage.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => router.push("/training")}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-all active:scale-95"
            >
              <Cpu className="h-3.5 w-3.5" />
              <span>Start DQN Training</span>
            </button>
            <button
              onClick={() => router.push("/simulation")}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/15 text-white border border-white/10 transition-all active:scale-95"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Run Simulation</span>
            </button>
            <button
              onClick={() => router.push("/realworld")}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-white/70 border border-white/10 transition-all active:scale-95"
            >
              <Video className="h-3.5 w-3.5" />
              <span>CCTV Digital Twin</span>
            </button>
          </div>
        </div>
      ) : (
        /* Table */
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr className="border-b border-white/[0.06] text-[10px] font-semibold uppercase tracking-wider text-white/40">
                <th className="py-2.5 px-3">Simulation Run & Timing</th>
                <th className="py-2.5 px-3">AI Model / Policy</th>
                <th className="py-2.5 px-3">
                  <div
                    className="flex items-center gap-1 cursor-help group/th"
                    title="Throughput & Clearance: Total vehicles that successfully crossed and exited the intersection vs total arrival volume (e.g., 95 cleared of 100 total = 95% clearance efficiency)."
                  >
                    <span>Throughput & Clearance</span>
                    <Info className="h-3 w-3 text-white/40 group-hover/th:text-indigo-400 transition-colors" />
                  </div>
                </th>
                <th className="py-2.5 px-3">
                  <div
                    className="flex items-center gap-1 cursor-help group/th"
                    title="HCM Level of Service (LOS): International standard for intersection wait time (LOS A: ≤10s, B: ≤20s, C: ≤35s, D: ≤55s, E: ≤80s, F: >80s avg vehicle delay)."
                  >
                    <span>Avg Delay & LOS</span>
                    <Info className="h-3 w-3 text-white/40 group-hover/th:text-indigo-400 transition-colors" />
                  </div>
                </th>
                <th className="py-2.5 px-3">Performance Evaluation</th>
                <th className="py-2.5 px-3">Peak Queue</th>
                <th className="py-2.5 px-3">Run Duration</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03] text-xs">
              {sortedSessions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-white/30 text-xs">
                    No historical sessions found matching your filters.
                  </td>
                </tr>
              ) : (
                sortedSessions.map((session) => {
                  const sessionDetails = formatSessionTitle(session);
                  const modeBadge = getModeBadge(session.mode);
                  const ratingBadge = getRatingBadge(session.performance_rating);
                  const losClass = getLosBadge(session.level_of_service);
                  const isAI = (session.mode || "ai").toLowerCase() === "ai";
                  const throughput = session.throughput ?? session.total_vehicles;
                  const throughputPct = session.throughput_pct ?? (session.total_vehicles > 0 ? Math.round((throughput / session.total_vehicles) * 100) : 100);
                  const avgWait = session.avg_wait_s ?? 22.4;
                  const peakQueue = session.peak_queue ?? 0;
                  const effGain = session.efficiency_gain_pct ?? 0;
                  const sessionTime = formatSessionFriendlyTime(session.created_at, session.timestamp_ms);
                  const formattedDuration = formatDuration(session.duration_s);

                  return (
                    <tr
                      key={session.session_id}
                      className="hover:bg-white/[0.02] transition-colors group"
                    >
                      {/* Simulation Name, Mode & Timing */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white group-hover:text-indigo-300 transition-colors text-xs">
                              {sessionDetails.title}
                            </span>
                            <span
                              className="font-mono text-[9px] text-white/40 bg-white/[0.04] px-1.5 py-0.5 rounded border border-white/5 cursor-help"
                              title={`Full Session ID: ${session.session_id}`}
                            >
                              #{sessionDetails.shortId}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md border ${modeBadge.className}`}
                            >
                              {modeBadge.icon}
                              <span>{modeBadge.label}</span>
                            </span>
                            <span
                              className="inline-flex items-center gap-1 text-[10px] text-white/70 bg-white/[0.04] px-1.5 py-0.5 rounded border border-white/10 cursor-help transition-colors hover:bg-white/[0.08]"
                              title={`Recorded: ${sessionTime.full}`}
                            >
                              <Clock className="h-2.5 w-2.5 text-indigo-400" />
                              <span className="font-medium text-white/90">{sessionTime.display}</span>
                              {sessionTime.relative && (
                                <>
                                  <span className="text-white/20">•</span>
                                  <span className="text-white/50">{sessionTime.relative}</span>
                                </>
                              )}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* AI Model & Episodes */}
                      <td className="py-3 px-3">
                        {isAI ? (
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-1.5">
                              <span className="inline-flex items-center text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-indigo-500/15 border border-indigo-500/30 text-indigo-300">
                                <Sparkles className="h-2.5 w-2.5 mr-1 text-indigo-400" />
                                {session.model_episodes ? `${session.model_episodes} eps` : "300 eps"}
                              </span>
                            </div>
                            <span className="text-[10px] text-white/50 truncate max-w-[140px]" title={session.model_name || "FlowSync DQN"}>
                              {session.model_name || "FlowSync DQN"}
                            </span>
                          </div>
                        ) : (
                          <div className="flex flex-col">
                            <span className="text-[11px] text-white/60 font-medium">
                              Rule Baseline
                            </span>
                            <span className="text-[10px] text-white/30">
                              Deterministic
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Throughput & Clearance */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1">
                          <div
                            className="flex items-baseline gap-1.5 cursor-help"
                            title={`${throughput.toLocaleString()} vehicles cleared out of ${session.total_vehicles.toLocaleString()} total demand`}
                          >
                            <span className="font-mono font-bold text-white text-sm">
                              {throughput.toLocaleString()}
                            </span>
                            <span className="text-[10px] font-medium text-emerald-400">
                              cleared
                            </span>
                            <span className="text-[10px] text-white/40">
                              of {session.total_vehicles.toLocaleString()} total
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <div
                              className="h-1.5 w-16 bg-white/10 rounded-full overflow-hidden"
                              title={`Clearance efficiency: ${throughputPct}%`}
                            >
                              <div
                                className={`h-full rounded-full ${
                                  throughputPct >= 90
                                    ? "bg-emerald-500"
                                    : throughputPct >= 75
                                    ? "bg-amber-500"
                                    : "bg-rose-500"
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, throughputPct))}%` }}
                              />
                            </div>
                            <span className="font-mono text-[10px] text-white/70">
                              {throughputPct}% cleared
                            </span>
                            {session.duration_s > 0 && (
                              <span className="text-[9px] font-mono text-white/30 hidden sm:inline" title="Flow Rate">
                                · {Math.round((throughput / session.duration_s) * 60)} veh/min
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Avg Delay & Level of Service */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-bold text-white text-sm">
                              {avgWait.toFixed(1)}s
                            </span>
                            <span
                              className={`text-[9px] font-bold px-1.5 py-0.5 rounded border cursor-help ${losClass}`}
                              title={getLosDescription(session.level_of_service)}
                            >
                              LOS {session.level_of_service || "C"}
                            </span>
                          </div>
                          <span className="text-[10px] text-white/40">
                            avg wait / veh
                          </span>
                          {effGain !== 0 && (
                            <span
                              className={`text-[10px] font-medium ${
                                effGain > 0 ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {effGain > 0 ? `+${effGain}% vs fixed` : `${effGain}% vs fixed`}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Performance Evaluation */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1">
                          <span
                            className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-lg border w-fit shadow-xs ${ratingBadge.className}`}
                          >
                            {ratingBadge.icon}
                            <span>{ratingBadge.label}</span>
                          </span>
                          <span className="text-[10px] text-white/40">
                            {ratingBadge.sub}
                          </span>
                        </div>
                      </td>

                      {/* Peak Queue */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col">
                          <span className="font-mono font-bold text-white">
                            {peakQueue} <span className="text-[10px] font-normal text-white/40">veh</span>
                          </span>
                          <span
                            className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border w-fit mt-0.5 ${getCongestionBadge(
                              session.congestion_level
                            )}`}
                          >
                            {session.congestion_level}
                          </span>
                        </div>
                      </td>

                      {/* Run Duration */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-1.5 font-mono font-semibold text-white text-xs">
                            <Clock className="h-3 w-3 text-indigo-400/80" />
                            <span>{formattedDuration}</span>
                          </div>
                          <span className="text-[10px] text-white/40 font-mono">
                            {session.duration_s >= 60 ? `${Math.round(session.duration_s)}s · ` : ""}
                            {session.total_frames.toLocaleString()} frames
                          </span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => handleLaunchReplay(session.session_id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 hover:border-indigo-500/50 transition-all active:scale-95 shadow-sm"
                        >
                          <Play className="h-3 w-3 fill-indigo-300" />
                          <span>Replay in 3D</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

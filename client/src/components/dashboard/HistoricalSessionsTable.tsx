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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
  if (
    session.has_arrivals ||
    sid.includes("cctv") ||
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (session as any).run_type === "cctv_replay"
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getLosDescription(los?: string): string {
  const l = (los || "C").toUpperCase();
  switch (l) {
    case "A":
      return "LOS A: Free Flow (≤10s). Minimal wait, optimal performance.";
    case "B":
      return "LOS B: Stable Flow (10.1–20s). Good progression, minor queuing.";
    case "C":
      return "LOS C: Acceptable Flow (20.1–35s). Standard urban target.";
    case "D":
      return "LOS D: Tolerable (35.1–55s). Queues approaching capacity.";
    case "E":
      return "LOS E: Unstable (55.1–80s). Maximum capacity, long queues.";
    case "F":
    default:
      return "LOS F: Breakdown (>80s). Severe delay, demand exceeds capacity.";
  }
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

export default function HistoricalSessionsTable({ sessions }: Props) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [modeFilter, setModeFilter] = useState("ALL");
  const [episodeFilter, setEpisodeFilter] = useState("ALL");
  const [congestionFilter, setCongestionFilter] = useState("ALL");
  const [ratingFilter, setRatingFilter] = useState("ALL");
  const [activePopover, setActivePopover] = useState<"throughput" | "delay" | null>(null);

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
        return "bg-emerald-500/15 text-emerald-300 border-emerald-500/25";
      case "B":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "C":
        return "bg-cyan-500/10 text-cyan-300 border-cyan-500/20";
      case "D":
        return "bg-amber-500/10 text-amber-300 border-amber-500/20";
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

  return (
    <div className="rounded-xl border border-neutral-800 bg-[#0a0a0a] overflow-hidden">
      {/* Header — airy, balanced */}
      <div className="px-6 py-5 border-b border-neutral-800/80">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white text-black">
              <History className="h-3.5 w-3.5" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-white leading-none">History</h3>
              <p className="text-xs text-neutral-500 mt-1.5">
                {filteredSessions.length} sessions · newest first
              </p>
            </div>
          </div>
          <span className="hidden sm:inline-flex rounded-full bg-neutral-900 border border-neutral-800 px-3 py-1.5 text-xs font-mono text-neutral-400">
            {sessions.length} total
          </span>
        </div>

        {/* Filters — centered, balanced */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-600" />
            <input
              type="text"
              placeholder="Search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 w-44 sm:w-52 rounded-full bg-neutral-900 border border-neutral-800 pl-9 pr-3 text-xs text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-700"
            />
          </div>
          <select
            value={modeFilter}
            onChange={(e) => handleModeFilterChange(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
          >
            <option value="ALL">All modes</option>
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
              <option value="ALL">Episodes</option>
              {uniqueEpisodes.map((ep) => (
                <option key={ep} value={String(ep)}>
                  {ep}
                </option>
              ))}
            </select>
          )}
          <select
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
          >
            <option value="ALL">Rating</option>
            <option value="OPTIMAL">Optimal</option>
            <option value="EFFICIENT">Efficient</option>
            <option value="MODERATE">Moderate</option>
            <option value="CONGESTED">Congested</option>
          </select>
          <select
            value={congestionFilter}
            onChange={(e) => setCongestionFilter(e.target.value)}
            className="h-8 rounded-full bg-neutral-900 border border-neutral-800 px-3.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
          >
            <option value="ALL">Congestion</option>
            <option value="LOW">Low</option>
            <option value="MODERATE">Moderate</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </div>
      </div>

        {sessions.length === 0 ? (
          <div className="px-6 py-16 flex flex-col items-center justify-center text-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-neutral-900 border border-neutral-800 text-neutral-600">
              <Sparkles className="h-4 w-4" />
            </div>
            <h4 className="mt-3 text-sm font-medium text-white">No sessions yet</h4>
            <p className="mt-1 text-xs text-neutral-500 max-w-sm">
              Run a simulation or ingest CCTV to populate history.
            </p>
            <div className="mt-4 flex gap-2">
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
                          description="Vehicles cleared vs total demand. E.g., 95/100 = 95% efficiency. Higher is better."
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
                    const { title } = formatSessionTitle(session);
                    const modeBadge = getModeBadge(session.mode);
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

                    return (
                      <tr
                        key={session.session_id}
                        className="hover:bg-neutral-900/40 transition-colors"
                      >
                        <td className="py-5 px-6">
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-white leading-tight">
                              {title}
                            </div>
                            <div className="flex items-center gap-2">
                              <span
                                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium border ${modeBadge.className}`}
                              >
                                {modeBadge.icon}
                                {modeBadge.label}
                              </span>
                              <span className="text-xs text-neutral-500">
                                {sessionTime.display} · {sessionTime.relative}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="py-5 px-4">
                          {isAI ? (
                            <div className="space-y-1">
                              <span className="inline-flex items-center rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-xs font-mono text-indigo-300">
                                {session.model_episodes ?? 300} eps
                              </span>
                              <div className="text-xs text-neutral-500 truncate max-w-[120px]">
                                {session.model_name || "FlowSync DQN"}
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-neutral-500">Deterministic</span>
                          )}
                        </td>

                        <td className="py-5 px-4">
                          <div className="space-y-1.5">
                            <div className="text-sm font-mono font-medium text-white">
                              {throughput}
                              <span className="text-neutral-600 font-normal"> / {session.total_vehicles}</span>
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
                              <span className="text-xs font-mono text-neutral-500">{throughputPct}%</span>
                            </div>
                          </div>
                        </td>

                        <td className="py-5 px-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-mono font-medium text-white">
                                {avgWait.toFixed(1)}s
                              </span>
                              <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${losClass}`}>
                                {session.level_of_service || "C"}
                              </span>
                            </div>
                            <div className="text-xs text-neutral-500">
                              {session.efficiency_gain_pct
                                ? `${session.efficiency_gain_pct > 0 ? "+" : ""}${session.efficiency_gain_pct}% vs fixed`
                                : "avg delay"}
                            </div>
                          </div>
                        </td>

                        <td className="py-5 px-4">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium border ${rating.className}`}
                          >
                            {rating.label}
                          </span>
                        </td>

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

                        <td className="py-5 px-4">
                          <div className="text-xs font-mono text-white">{formattedDuration}</div>
                          <div className="text-xs text-neutral-600">{session.total_frames} fr</div>
                        </td>

                        <td className="py-5 px-6 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleLaunchReplay(session.session_id)}
                            className="h-7 rounded-full border-neutral-800 bg-transparent text-neutral-300 hover:bg-white hover:text-black hover:border-white text-xs px-3"
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Replay
                          </Button>
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

"use client";

import { useState } from "react";
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

export default function HistoricalSessionsTable({ sessions }: Props) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [modeFilter, setModeFilter] = useState("ALL");
  const [congestionFilter, setCongestionFilter] = useState("ALL");
  const [ratingFilter, setRatingFilter] = useState("ALL");

  const filteredSessions = sessions.filter((s) => {
    const term = searchTerm.toLowerCase().trim();
    const matchesSearch =
      !term ||
      s.session_id.toLowerCase().includes(term) ||
      (s.model_name && s.model_name.toLowerCase().includes(term)) ||
      (s.mode && s.mode.toLowerCase().includes(term));

    const sMode = (s.mode || "ai").toLowerCase();
    const matchesMode =
      modeFilter === "ALL" ||
      (modeFilter === "AI" && sMode === "ai") ||
      (modeFilter === "GREEDY" && sMode === "greedy") ||
      (modeFilter === "FIXED" && sMode === "fixed") ||
      (modeFilter === "MANUAL" && sMode === "manual");

    const matchesCongestion =
      congestionFilter === "ALL" || s.congestion_level === congestionFilter;

    const matchesRating =
      ratingFilter === "ALL" ||
      (s.performance_rating && s.performance_rating.toUpperCase() === ratingFilter);

    return matchesSearch && matchesMode && matchesCongestion && matchesRating;
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
              onChange={(e) => setModeFilter(e.target.value)}
              className="h-8 rounded-lg bg-black/40 border border-white/10 px-2.5 text-xs text-white/80 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="ALL">All Modes</option>
              <option value="AI">DQN AI</option>
              <option value="GREEDY">Greedy</option>
              <option value="FIXED">Fixed Timer</option>
              <option value="MANUAL">Manual</option>
            </select>
          </div>

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
                <th className="py-2.5 px-3">Session & Mode</th>
                <th className="py-2.5 px-3">AI Model / Policy</th>
                <th className="py-2.5 px-3">Throughput</th>
                <th className="py-2.5 px-3">Avg Delay & LOS</th>
                <th className="py-2.5 px-3">Performance Evaluation</th>
                <th className="py-2.5 px-3">Peak Queue</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.03] text-xs">
              {filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-white/30 text-xs">
                    No historical sessions found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => {
                  const modeBadge = getModeBadge(session.mode);
                  const ratingBadge = getRatingBadge(session.performance_rating);
                  const losClass = getLosBadge(session.level_of_service);
                  const isAI = (session.mode || "ai").toLowerCase() === "ai";
                  const throughput = session.throughput ?? session.total_vehicles;
                  const throughputPct = session.throughput_pct ?? (session.total_vehicles > 0 ? Math.round((throughput / session.total_vehicles) * 100) : 100);
                  const avgWait = session.avg_wait_s ?? 22.4;
                  const peakQueue = session.peak_queue ?? 0;
                  const effGain = session.efficiency_gain_pct ?? 0;

                  return (
                    <tr
                      key={session.session_id}
                      className="hover:bg-white/[0.02] transition-colors group"
                    >
                      {/* Session ID & Mode */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-white group-hover:text-indigo-300 transition-colors">
                              {session.session_id}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md border ${modeBadge.className}`}
                            >
                              {modeBadge.icon}
                              <span>{modeBadge.label}</span>
                            </span>
                            <span className="text-[10px] text-white/40">
                              {session.created_at.split(" ")[0]}
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

                      {/* Throughput */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-baseline gap-1">
                            <span className="font-mono font-bold text-white text-sm">
                              {throughput}
                            </span>
                            <span className="text-[10px] text-white/40">
                              / {session.total_vehicles} veh
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <div className="h-1.5 w-16 bg-white/10 rounded-full overflow-hidden">
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
                            <span className="font-mono text-[10px] text-white/60">
                              {throughputPct}%
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Avg Wait & Level of Service */}
                      <td className="py-3 px-3">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-bold text-white text-sm">
                              {avgWait}s
                            </span>
                            <span
                              className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${losClass}`}
                              title="Highway Capacity Manual Level of Service"
                            >
                              LOS {session.level_of_service || "C"}
                            </span>
                          </div>
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

                      {/* Duration */}
                      <td className="py-3 px-3 font-mono text-white/70 text-[11px]">
                        {session.duration_s}s
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

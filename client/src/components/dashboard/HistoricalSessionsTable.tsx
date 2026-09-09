"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { History, Play, Search, Filter, Video } from "lucide-react";

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
}

interface Props {
  sessions: SessionItem[];
}

export default function HistoricalSessionsTable({ sessions }: Props) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [congestionFilter, setCongestionFilter] = useState("ALL");

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch = s.session_id
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesCongestion =
      congestionFilter === "ALL" || s.congestion_level === congestionFilter;
    return matchesSearch && matchesCongestion;
  });

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
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md flex flex-col gap-4">
      {/* Table Header & Search Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-bold tracking-wider uppercase text-white">
              Historical Detection & Replay Sessions
            </h3>
            <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] font-mono text-white/60">
              {filteredSessions.length} recorded
            </span>
          </div>
          <p className="text-xs text-white/40 mt-0.5">
            Archived real-world CCTV camera recordings, live stream runs, and calibrated arrival schedules
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-white/30" />
            <input
              type="text"
              placeholder="Search session..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-8 w-44 rounded-lg bg-black/40 border border-white/10 pl-8 pr-2.5 text-xs text-white placeholder:text-white/30 focus:border-indigo-500 focus:outline-none transition-colors"
            />
          </div>

          {/* Congestion Filter */}
          <div className="relative">
            <select
              value={congestionFilter}
              onChange={(e) => setCongestionFilter(e.target.value)}
              className="h-8 rounded-lg bg-black/40 border border-white/10 px-2.5 text-xs text-white/80 focus:border-indigo-500 focus:outline-none transition-colors"
            >
              <option value="ALL">All Levels</option>
              <option value="LOW">Low</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06] text-[10px] font-semibold uppercase tracking-wider text-white/40">
              <th className="py-2.5 px-3">Session ID</th>
              <th className="py-2.5 px-3">Recorded At</th>
              <th className="py-2.5 px-3">Duration</th>
              <th className="py-2.5 px-3">Vehicles</th>
              <th className="py-2.5 px-3">Frames</th>
              <th className="py-2.5 px-3">Ingest FPS</th>
              <th className="py-2.5 px-3">Congestion</th>
              <th className="py-2.5 px-3 text-right">Digital Twin Action</th>
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
              filteredSessions.map((session) => (
                <tr
                  key={session.session_id}
                  className="hover:bg-white/[0.02] transition-colors group"
                >
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-white/5 border border-white/10 text-white/60">
                        <Video className="h-3 w-3" />
                      </div>
                      <span className="font-mono font-bold text-indigo-300">
                        {session.session_id}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-white/50 text-[11px]">
                    {session.created_at}
                  </td>
                  <td className="py-3 px-3 font-mono text-white/70">
                    {session.duration_s}s
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-mono font-bold text-white">
                      {session.total_vehicles}
                    </span>
                    <span className="text-[10px] text-white/40 ml-1">veh</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-white/50 text-[11px]">
                    {session.total_frames}
                  </td>
                  <td className="py-3 px-3 font-mono text-white/50 text-[11px]">
                    {session.avg_fps} fps
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${getCongestionBadge(
                        session.congestion_level
                      )}`}
                    >
                      {session.congestion_level}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => handleLaunchReplay(session.session_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 hover:border-indigo-500/50 transition-all active:scale-95 shadow-sm"
                    >
                      <Play className="h-3 w-3 fill-indigo-300" />
                      <span>Replay in 3D</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

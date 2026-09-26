"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import Header from "@/components/layout/Header";
import DashboardKpis, { DashboardOverviewData } from "@/components/dashboard/DashboardKpis";
import ModeComparisonChart, { ModeBenchmarks } from "@/components/dashboard/ModeComparisonChart";
import DirectionalFlowChart from "@/components/dashboard/DirectionalFlowChart";
import AIPolicyInsights from "@/components/dashboard/AIPolicyInsights";
import HistoricalSessionsTable, { SessionItem } from "@/components/dashboard/HistoricalSessionsTable";
import { BarChart3, RefreshCw, Sparkles, Layers, Activity } from "lucide-react";

interface DashboardPayload {
  overview: DashboardOverviewData;
  approach_totals: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  vehicle_type_counts: {
    car: number;
    truck: number;
    bus: number;
    motorcycle: number;
  };
  congestion_distribution: {
    LOW: number;
    MODERATE: number;
    HIGH: number;
    CRITICAL: number;
  };
  mode_benchmarks: ModeBenchmarks;
  phase_distribution: {
    phase: number;
    name: string;
    description: string;
    share_pct: number;
  }[];
  sessions: SessionItem[];
  benchmarks?: any[];
}

// Fallback data in case backend is offline during first boot
const DEFAULT_FALLBACK_DATA: DashboardPayload = {
  overview: {
    total_sessions: 0,
    total_vehicles_processed: 0,
    total_frames_processed: 0,
    total_footage_duration_s: 0.0,
    total_footage_hours: 0.0,
    avg_intersection_wait_s: 0.0,
    total_movement_occurrences: 0,
    peak_queue_observed: 0,
    avg_detection_fps: 0.0,
    avg_wait_reduction_pct: 0.0,
    inference_latency_ms: 0.0,
    ai_reliability_score: 0.0,
  },
  approach_totals: {
    north: 0,
    south: 0,
    east: 0,
    west: 0,
  },
  vehicle_type_counts: {
    car: 0,
    truck: 0,
    bus: 0,
    motorcycle: 0,
  },
  congestion_distribution: {
    LOW: 0,
    MODERATE: 0,
    HIGH: 0,
    CRITICAL: 0,
  },
  mode_benchmarks: {
    fixed: {
      name: "Fixed Timer",
      avg_wait_time: 0.0,
      throughput_rate: 0.0,
      max_queue_avg: 0.0,
      efficiency_score: 0.0,
      color: "#64748b",
      has_data: false,
    },
    greedy: {
      name: "Greedy Controller",
      avg_wait_time: 0.0,
      throughput_rate: 0.0,
      max_queue_avg: 0.0,
      efficiency_score: 0.0,
      color: "#10b981",
      has_data: false,
    },
    ai: {
      name: "FlowSync DQN AI",
      avg_wait_time: 0.0,
      throughput_rate: 0.0,
      max_queue_avg: 0.0,
      efficiency_score: 0.0,
      color: "#6366f1",
      has_data: false,
    },
    comparison: {
      wait_reduction_pct: 0.0,
      throughput_gain_pct: 0.0,
      queue_reduction_pct: 0.0,
    },
  },
  phase_distribution: [
    { phase: 0, name: "North-South Green", description: "Parallel straight & right movements", share_pct: 0.0 },
    { phase: 1, name: "East-West Green", description: "Parallel straight & right movements", share_pct: 0.0 },
    { phase: 2, name: "North-South Left Turn", description: "Protected left turns", share_pct: 0.0 },
    { phase: 3, name: "East-West Left Turn", description: "Protected left turns", share_pct: 0.0 },
  ],
  sessions: [],
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload>(DEFAULT_FALLBACK_DATA);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "benchmarks" | "sessions">("all");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const fetchDashboardData = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await fetch(`${API_BASE}/analytics/dashboard-summary`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      console.warn("Using fallback analytics data (backend unreachable):", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Header Navigation */}
      <Header />

      {/* Main Dashboard Container */}
      <main className="flex-1 w-full max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">
        {/* Top Title & Toolbar Bar */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6"
        >
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
                <BarChart3 className="h-5 w-5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Analytics & System Performance
              </h1>
            </div>
            <p className="mt-1 text-xs text-white/40 max-w-xl">
              {data.overview.total_sessions > 0
                ? `Real-time telemetry and historical insights aggregated across ${data.overview.total_sessions} simulation and digital twin runs.`
                : "Fresh database initialized. Real-time telemetry, controller benchmarks, and historical insights will populate as fresh simulations and training runs are executed."}
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-3">
            {/* View Mode Switcher */}
            <div className="flex rounded-xl bg-white/[0.03] border border-white/10 p-1 text-xs">
              <button
                onClick={() => setActiveTab("all")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === "all"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                    : "text-white/50 hover:text-white"
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab("benchmarks")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === "benchmarks"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                    : "text-white/50 hover:text-white"
                }`}
              >
                Benchmarks
              </button>
              <button
                onClick={() => setActiveTab("sessions")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                  activeTab === "sessions"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                    : "text-white/50 hover:text-white"
                }`}
              >
                History
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={fetchDashboardData}
              disabled={refreshing}
              className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] px-3.5 py-2 text-xs font-semibold text-white/80 hover:text-white transition-all active:scale-95 disabled:opacity-50"
              title="Refresh telemetry data"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshing ? "animate-spin text-indigo-400" : ""}`}
              />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </motion.div>

        {/* Section 1: Hero KPI Grid */}
        <section>
          <DashboardKpis data={data.overview} />
        </section>

        {/* Section 2: Mode Comparison & Approach Flow */}
        {(activeTab === "all" || activeTab === "benchmarks") && (
          <motion.section
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="flex flex-col gap-6"
          >
            <ModeComparisonChart data={data.mode_benchmarks} />
            <DirectionalFlowChart
              approachTotals={data.approach_totals}
              vehicleTypeCounts={data.vehicle_type_counts}
              congestionDistribution={data.congestion_distribution}
            />
          </motion.section>
        )}

        {/* Section 3: AI Policy & Phase Allocation */}
        {(activeTab === "all" || activeTab === "benchmarks") && (
          <motion.section
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
          >
            <AIPolicyInsights
              phaseDistribution={data.phase_distribution}
              reliabilityScore={data.overview.ai_reliability_score}
              latencyMs={data.overview.inference_latency_ms}
            />
          </motion.section>
        )}

        {/* Section 4: Historical Sessions & Replays Table */}
        <motion.section
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <HistoricalSessionsTable
            sessions={data.sessions}
            benchmarks={data.benchmarks}
            initialModeFilter={activeTab === "benchmarks" ? "BENCHMARKS" : undefined}
          />
        </motion.section>
      </main>
    </div>
  );
}

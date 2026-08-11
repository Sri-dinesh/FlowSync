"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Header from "@/components/layout/Header";
import VideoFeed from "@/components/realworld/VideoFeed";
import CCTVControls from "@/components/realworld/CCTVControls";
import LaneQueuePanel from "@/components/realworld/LaneQueuePanel";
import SignalDecisionPanel from "@/components/realworld/SignalDecisionPanel";
import CCTVMetrics from "@/components/realworld/CCTVMetrics";
import TrafficFlowChart from "@/components/realworld/TrafficFlowChart";
import dynamic from "next/dynamic";

const DigitalTwinShowdown = dynamic(
  () => import("@/components/realworld/DigitalTwinShowdown"),
  { ssr: false }
);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type CCTVFrameData = {
  frame_id: number;
  timestamp_ms: number;
  raw_counts: Record<string, number>;
  weighted_counts: Record<string, number>;
  vehicle_types: Record<string, number>;
  detection_fps: number;
  observation: number[];
  signal_phase: number;
  signal_phase_name: string;
  q_values: number[];
  confidence_pct: number;
  annotated_frame_b64: string | null;
  fixed_timer_phase: number | null;
  fixed_timer_phase_name: string | null;
  estimated_avg_wait: number;
  congestion_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  status: string;
};

interface ProcessingProgress {
  frame_id: number;
  total_frames: number | null;
  pct_complete: number | null;
  vehicles_detected_so_far: number;
}

interface TwinData {
  session_id: string;
  total_frames_processed: number;
  total_vehicles_detected: number;
  aggregate_counts: Record<string, number>;
  peak_counts: Record<string, number>;
  avg_counts: Record<string, number>;
}

type Tab = "live" | "twin";

export default function RealWorldPage() {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentFrame, setCurrentFrame] = useState<CCTVFrameData | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<string>("idle");
  const [frameHistory, setFrameHistory] = useState<CCTVFrameData[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<Tab>("live");

  // New states for redesigned flow
  const [processingProgress, setProcessingProgress] = useState<ProcessingProgress | null>(null);
  const [twinData, setTwinData] = useState<TwinData | null>(null);
  const [totalVehiclesDetected, setTotalVehiclesDetected] = useState(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(`${WS_URL}/ws/cctv`);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "video_progress") {
          setProcessingProgress({
            frame_id: data.frame_id,
            total_frames: data.total_frames ?? null,
            pct_complete: data.pct_complete ?? null,
            vehicles_detected_so_far: data.vehicles_detected_so_far ?? 0,
          });

        } else if (data.type === "cctv_frame") {
          const frame = data as CCTVFrameData;
          setCurrentFrame(frame);
          setFrameHistory((prev) => [...prev, frame].slice(-120));

        } else if (data.type === "pipeline_status") {
          const status = data.status ?? "idle";
          setPipelineStatus(status);

          if (data.session_id) setSessionId(data.session_id);

          // When processing completes (either completed or stopped with data)
          if ((status === "completed" || status === "stopped") && data.twin_data) {
            const td = data.twin_data as TwinData;
            setTwinData(td);
            setTotalVehiclesDetected(td.total_vehicles_detected ?? 0);
            setProcessingProgress(null);
            setPipelineStatus("completed");
          }
        }
      } catch {
        // ignore parse errors
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const sendCommand = useCallback(
    (command: string, payload: Record<string, unknown> = {}) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ command, payload }));
      }
    },
    []
  );

  const handleStartProcessing = useCallback(
    (videoPath: string) => {
      setProcessingProgress(null);
      setTwinData(null);
      setTotalVehiclesDetected(0);
      setCurrentFrame(null);
      setFrameHistory([]);
      sendCommand("start_processing", { video_path: videoPath });
    },
    [sendCommand]
  );

  const handleStop = useCallback(() => sendCommand("stop_processing"), [sendCommand]);

  const handleOpenInTwin = useCallback(() => {
    setActiveTab("twin");
  }, []);

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: "live", label: "Live View", icon: "📡" },
    { id: "twin", label: "Digital Twin", icon: "🌍" },
  ];

  // Use peak_counts for twin seeding (best single-frame snapshot)
  const twinCounts = twinData?.peak_counts
    ? Object.values(twinData.peak_counts).some((v) => v > 0)
      ? twinData.peak_counts
      : twinData.avg_counts
    : null;

  return (
    <div className="relative h-screen bg-[#0a0a0a] text-white flex flex-col overflow-hidden">
      {/* Header */}
      <div className="z-50 relative flex-none">
        <Header />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex w-full overflow-hidden">
        {/* ── Left column ──────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Tab bar */}
          <div className="flex items-center gap-1 px-4 pt-3 pb-2 flex-shrink-0">
            {TABS.map(({ id, label, icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`px-4 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  activeTab === id
                    ? "bg-white/10 border-white/20 text-white shadow-lg shadow-white/5"
                    : "border-transparent text-white/40 hover:text-white/70 hover:bg-white/5"
                }`}
              >
                <span className="mr-1.5">{icon}</span>
                {label}
                {id === "twin" && twinData && (
                  <span className="ml-1.5 px-1 py-0.5 text-[8px] bg-emerald-500/20 text-emerald-400 rounded font-bold">
                    READY
                  </span>
                )}
              </button>
            ))}

            {/* WS status indicator */}
            <div className="ml-auto flex items-center gap-2 text-[10px] text-white/30 pr-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isConnected
                    ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]"
                    : "bg-rose-500"
                }`}
              />
              {isConnected ? "WS Connected" : "Disconnected"}
            </div>
          </div>

          {/* Tab content area */}
          <div className="flex-1 flex flex-col min-h-0 px-3 pb-3 gap-3">
            {activeTab === "live" ? (
              <>
                {/* Video feed */}
                <div className="flex-1 min-h-0 relative">
                  <VideoFeed
                    frame={currentFrame}
                    isConnected={isConnected}
                    pipelineStatus={pipelineStatus}
                    processingProgress={processingProgress}
                  />
                  {/* Open in Digital Twin CTA */}
                  {twinData && pipelineStatus === "completed" && (
                    <button
                      onClick={handleOpenInTwin}
                      className="absolute bottom-4 right-4 px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-bold rounded-lg shadow-lg shadow-indigo-500/30 backdrop-blur transition-all flex items-center gap-2 border border-indigo-400/30 animate-pulse hover:animate-none"
                    >
                      <span>🌍</span> Open in Digital Twin →
                    </button>
                  )}
                </div>
                {/* Flow chart */}
                <div className="flex-shrink-0">
                  <TrafficFlowChart frames={frameHistory} />
                </div>
              </>
            ) : (
              <div className="flex-1 min-h-0 rounded-xl overflow-hidden border border-white/10 bg-black/50 flex flex-col">
                <DigitalTwinShowdown
                  initialCounts={twinCounts}
                  sessionId={twinData?.session_id}
                />
              </div>
            )}
          </div>
        </div>

        {/* ── Right sidebar ─────────────────────────────────────────────── */}
        <aside className="w-[400px] flex-shrink-0 flex flex-col h-full overflow-y-auto bg-black/60 backdrop-blur-xl border-l border-white/10 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent hover:scrollbar-thumb-white/30 shadow-2xl z-10">
          <div className="p-3 flex flex-col gap-3">
            <CCTVControls
              isConnected={isConnected}
              pipelineStatus={pipelineStatus}
              onStartProcessing={handleStartProcessing}
              onStop={handleStop}
              processingProgress={processingProgress}
              totalVehiclesDetected={totalVehiclesDetected}
            />
            <SignalDecisionPanel frame={currentFrame} />
            <LaneQueuePanel frame={currentFrame} />
            <CCTVMetrics frame={currentFrame} />
          </div>
        </aside>
      </div>
    </div>
  );
}

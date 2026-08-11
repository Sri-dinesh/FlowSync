"use client";

import type { CCTVFrameData } from "@/app/realworld/page";

interface Props {
  frame: CCTVFrameData | null;
  isConnected: boolean;
  pipelineStatus: string;
  processingProgress?: { pct_complete: number | null; frame_id: number; total_frames: number | null } | null;
}

export default function VideoFeed({
  frame,
  isConnected,
  pipelineStatus,
  processingProgress,
}: Props) {
  const hasFeed = frame?.annotated_frame_b64;

  return (
    <div className="h-full rounded-xl border border-white/10 bg-[#111] overflow-hidden flex flex-col">
      {/* ── Status bar ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06] bg-black/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected
                ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]"
                : "bg-rose-500"
            }`}
          />
          <span className="text-[11px] text-white/50 font-medium">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-white/35">
          {frame && (
            <>
              <span className="font-mono">
                Frame #{frame.frame_id}
              </span>
              <span className="font-mono">
                {frame.detection_fps.toFixed(1)} FPS
              </span>
            </>
          )}
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              pipelineStatus === "started"
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                : pipelineStatus === "stopped"
                ? "bg-white/5 text-white/30 border border-white/10"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
          >
            {pipelineStatus}
          </span>
        </div>
      </div>

      {/* ── Video frame ──────────────────────────────────────────── */}
      <div className="relative flex-1 flex items-center justify-center bg-black min-h-0">
        {hasFeed ? (
          <img
            src={`data:image/jpeg;base64,${frame.annotated_frame_b64}`}
            alt="CCTV annotated feed"
            className="max-w-full max-h-full object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-4 text-white/20">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-3xl">
              📡
            </div>
            <div className="text-sm font-medium text-center max-w-[280px]">
              {pipelineStatus === "roi_required"
                ? "ROI configuration required — switch to ROI Editor tab"
                : pipelineStatus === "started"
                ? "Awaiting first frame..."
                : "Upload a video and start processing to begin"}
            </div>
          </div>
        )}

        {/* Congestion overlay badge */}
        {frame && frame.status === "ok" && (
          <div className="absolute top-3 right-3">
            <div
              className={`px-2.5 py-1 rounded-full text-[11px] font-bold border backdrop-blur-md ${
                frame.congestion_level === "LOW"
                  ? "bg-emerald-900/70 text-emerald-300 border-emerald-500/40"
                  : frame.congestion_level === "MODERATE"
                  ? "bg-yellow-900/70 text-yellow-300 border-yellow-500/40"
                  : frame.congestion_level === "HIGH"
                  ? "bg-orange-900/70 text-orange-300 border-orange-500/40"
                  : "bg-red-900/70 text-red-300 border-red-500/40"
              }`}
            >
              {frame.congestion_level}
            </div>
          </div>
        )}

        {/* ROI required overlay */}
        {frame?.status === "roi_required" && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent px-4 py-4">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              ROI not configured — switch to the ROI Editor tab to define lane regions
            </div>
          </div>
        )}

        {/* Model not loaded overlay */}
        {frame?.status === "model_not_loaded" && (
          <div className="absolute top-3 left-3">
            <div className="px-2.5 py-1 rounded-full text-[10px] font-bold border backdrop-blur-md bg-amber-900/70 text-amber-300 border-amber-500/40">
              ⚠ YOLO model not loaded — showing raw feed
            </div>
          </div>
        )}

        {/* Processing progress overlay */}
        {pipelineStatus === "started" && processingProgress && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
            <div className="flex justify-between text-[10px] text-white/50 mb-1">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                YOLO Processing
              </span>
              <span className="font-mono">
                {processingProgress.pct_complete != null
                  ? `${processingProgress.pct_complete}%`
                  : `Frame ${processingProgress.frame_id}`}
              </span>
            </div>
            <div className="h-1 w-full rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-200"
                style={{ width: `${processingProgress.pct_complete ?? 0}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

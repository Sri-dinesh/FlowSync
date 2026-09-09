"use client";

import { useRef, useState } from "react";

interface ProcessingProgress {
  frame_id: number;
  total_frames: number | null;
  pct_complete: number | null;
  vehicles_detected_so_far: number;
}

interface Props {
  isConnected: boolean;
  pipelineStatus: string;
  onStartProcessing: (videoPath: string) => void;
  onStop: () => void;
  processingProgress: ProcessingProgress | null;
  totalVehiclesDetected?: number;
}

const PRESETS = [
  { name: "4 Corners Downtown", url: "https://www.youtube.com/watch?v=1H0iTzv2jiQ", flag: "🚦" },
  { name: "Jackson Hole Town Square", url: "https://www.youtube.com/watch?v=1EiC9bvVGnk", flag: "🏔️" },
];

export default function CCTVControls({
  isConnected,
  pipelineStatus,
  onStartProcessing,
  onStop,
  processingProgress,
  totalVehiclesDetected = 0,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sourceMode, setSourceMode] = useState<"file" | "stream">("stream");
  const [videoPath, setVideoPath] = useState("");
  const [streamUrl, setStreamUrl] = useState("https://www.youtube.com/watch?v=1H0iTzv2jiQ");
  const [uploading, setUploading] = useState(false);
  const [uploadedFilename, setUploadedFilename] = useState("");

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const isRunning = pipelineStatus === "started" || pipelineStatus === "processing";
  const isCompleted = pipelineStatus === "completed";

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/cctv/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setVideoPath(data.video_path);
      setUploadedFilename(data.filename || file.name);
    } catch (e) {
      console.error("Upload failed:", e);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const effectiveSource = sourceMode === "stream" ? streamUrl.trim() : videoPath;
  const pct = processingProgress?.pct_complete;
  const vehiclesFound = processingProgress?.vehicles_detected_so_far ?? totalVehiclesDetected;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Header with Mode Toggle */}
      <div className="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-1.5 p-0.5 rounded-lg bg-white/[0.04] border border-white/[0.06]">
          <button
            onClick={() => setSourceMode("stream")}
            className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-all ${
              sourceMode === "stream"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-white/40 hover:text-white/80"
            }`}
          >
            🔴 Live Stream
          </button>
          <button
            onClick={() => setSourceMode("file")}
            className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-all ${
              sourceMode === "file"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-white/40 hover:text-white/80"
            }`}
          >
            📁 Upload File
          </button>
        </div>

        {sourceMode === "stream" && (
          <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            0ms buffer
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col gap-3">
        {sourceMode === "stream" ? (
          /* Live YouTube / Stream Input */
          <div className="flex flex-col gap-2.5">
            <div>
              <label className="text-[11px] text-white/50 block mb-1 font-medium">
                YouTube Live / RTSP / HLS URL:
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={streamUrl}
                  onChange={(e) => setStreamUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  disabled={isRunning}
                  className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-white/20 focus:outline-none focus:border-blue-500/60 font-mono transition-all"
                />
                {streamUrl && !isRunning && (
                  <button
                    onClick={() => setStreamUrl("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white text-xs"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>

            {/* 1-Click Presets */}
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-white/30 uppercase tracking-wider font-semibold">
                Live Traffic Camera Presets:
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.name}
                    onClick={() => setStreamUrl(preset.url)}
                    disabled={isRunning}
                    className={`px-2 py-1.5 rounded-lg border text-[11px] font-medium text-left truncate transition-all ${
                      streamUrl === preset.url
                        ? "border-blue-500/50 bg-blue-500/15 text-white"
                        : "border-white/[0.08] bg-white/[0.02] text-white/50 hover:text-white/80 hover:bg-white/[0.05]"
                    }`}
                  >
                    <span className="mr-1">{preset.flag}</span>
                    <span className="truncate">{preset.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Drop zone for local files */
          <div
            className={`rounded-lg border-2 border-dashed p-5 text-center cursor-pointer transition-all duration-200 ${
              uploading
                ? "border-blue-500/50 bg-blue-500/5"
                : videoPath
                ? "border-emerald-500/40 bg-emerald-500/5"
                : "border-white/10 hover:border-white/25 hover:bg-white/[0.02]"
            }`}
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi,.mov,.mkv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
            />
            {uploading ? (
              <div className="text-blue-400 text-xs font-medium">
                <span className="animate-pulse">⏳</span> Uploading…
              </div>
            ) : videoPath ? (
              <div className="text-emerald-400 text-xs font-medium truncate">
                ✓ {uploadedFilename || videoPath.split("/").pop()?.split("\\").pop()}
              </div>
            ) : (
              <div className="text-white/25 text-xs">
                Drop video or click to upload
                <div className="text-[10px] text-white/15 mt-0.5">.mp4 · .avi · .mov · .mkv</div>
              </div>
            )}
          </div>
        )}

        {/* Progress indicator — visible while running */}
        {isRunning && (
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] text-white/40">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                {sourceMode === "stream" ? "Ingesting live stream…" : "Processing video…"}
              </span>
              <span className="font-mono">
                Frame #{processingProgress?.frame_id ?? 0}
                {processingProgress?.total_frames ? ` / ${processingProgress.total_frames}` : ""}
              </span>
            </div>
            {sourceMode === "file" && (
              <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300"
                  style={{ width: `${pct ?? 0}%` }}
                />
              </div>
            )}
            {vehiclesFound > 0 && (
              <p className="text-[10px] text-emerald-400/80 font-mono text-right">
                {vehiclesFound.toLocaleString()} vehicles tracked
              </p>
            )}
          </div>
        )}

        {/* Completion state for recorded videos */}
        {isCompleted && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 flex items-center gap-2">
            <span className="text-emerald-400 text-lg">✓</span>
            <div>
              <p className="text-[11px] text-emerald-300 font-semibold">Session Recorded</p>
              <p className="text-[10px] text-white/40">
                {totalVehiclesDetected.toLocaleString()} total vehicles ready for Digital Twin Showdown
              </p>
            </div>
          </div>
        )}

        {/* Start / Stop button */}
        <button
          onClick={() => {
            if (isRunning) {
              onStop();
            } else if (effectiveSource && isConnected) {
              onStartProcessing(effectiveSource);
            }
          }}
          disabled={!isConnected || (!isRunning && !effectiveSource)}
          className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
            isRunning
              ? "bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20"
              : isConnected && effectiveSource
              ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
              : "bg-white/[0.04] text-white/20 cursor-not-allowed border border-white/[0.06]"
          }`}
        >
          {isRunning
            ? "⏹ Stop Stream"
            : isCompleted
            ? "↺ Restart Stream"
            : sourceMode === "stream"
            ? "▶ Start Live Stream"
            : "▶ Start Processing"}
        </button>
      </div>
    </div>
  );
}

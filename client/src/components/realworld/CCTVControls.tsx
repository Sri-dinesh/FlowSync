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

export default function CCTVControls({
  isConnected,
  pipelineStatus,
  onStartProcessing,
  onStop,
  processingProgress,
  totalVehiclesDetected = 0,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [videoPath, setVideoPath] = useState("");
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

  const pct = processingProgress?.pct_complete;
  const vehiclesFound = processingProgress?.vehicles_detected_so_far ?? totalVehiclesDetected;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <h2 className="text-xs uppercase tracking-[0.14em] text-white/35 font-semibold">Video Source</h2>
      </div>

      <div className="p-4 flex flex-col gap-3">
        {/* Drop zone */}
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

        {/* Progress bar — visible while processing */}
        {isRunning && (
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] text-white/40">
              <span>Processing frames…</span>
              <span className="font-mono">
                {processingProgress?.frame_id ?? 0}
                {processingProgress?.total_frames ? ` / ${processingProgress.total_frames}` : ""}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300"
                style={{ width: `${pct ?? 0}%` }}
              />
            </div>
            {vehiclesFound > 0 && (
              <p className="text-[10px] text-white/30 text-right">
                {vehiclesFound.toLocaleString()} vehicles detected
              </p>
            )}
          </div>
        )}

        {/* Completion state */}
        {isCompleted && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 flex items-center gap-2">
            <span className="text-emerald-400 text-lg">✓</span>
            <div>
              <p className="text-[11px] text-emerald-300 font-semibold">Processing Complete</p>
              <p className="text-[10px] text-white/30">
                {totalVehiclesDetected.toLocaleString()} total vehicles detected
              </p>
            </div>
          </div>
        )}

        {/* Start / Stop button */}
        <button
          onClick={() => {
            if (isRunning) {
              onStop();
            } else if (videoPath && isConnected) {
              onStartProcessing(videoPath);
            }
          }}
          disabled={!isConnected || (!isRunning && !videoPath)}
          className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
            isRunning
              ? "bg-rose-600/80 hover:bg-rose-600 text-white shadow-lg shadow-rose-600/20"
              : isConnected && videoPath
              ? "bg-[#1a6bff] hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
              : "bg-white/[0.04] text-white/20 cursor-not-allowed border border-white/[0.06]"
          }`}
        >
          {isRunning ? "⏹ Stop Processing" : isCompleted ? "↺ Process Again" : "▶ Start Processing"}
        </button>
      </div>
    </div>
  );
}

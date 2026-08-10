"use client";

/**
 * ROIEditor — Canvas-based polygon drawing tool for lane ROI definition.
 *
 * Workflow:
 * 1. User picks a lane from the dropdown (e.g. "north_straight")
 * 2. Clicks on the canvas to place polygon vertices
 * 3. Right-clicks or presses Enter to close the polygon
 * 4. Repeats for all 12 lanes
 * 5. Clicks "Save ROI Config" → POSTs to /cctv/roi
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type MouseEvent,
} from "react";

const LANE_KEYS = [
  "north_straight", "north_left", "north_right",
  "south_straight", "south_left", "south_right",
  "east_straight",  "east_left",  "east_right",
  "west_straight",  "west_left",  "west_right",
] as const;

type LaneKey = (typeof LANE_KEYS)[number];

const LANE_COLORS: Record<string, string> = {
  north: "#34d399", south: "#f87171", east: "#60a5fa", west: "#fbbf24",
};

function getLaneColor(lane: string): string {
  const dir = lane.split("_")[0];
  return LANE_COLORS[dir] ?? "#ffffff";
}

type Point = [number, number]; // relative [0-1] coords
type PolygonMap = Partial<Record<LaneKey, Point[]>>;

interface Props {
  /** Base64-encoded JPEG preview frame from the video (used as background). */
  previewFrame: string | null;
  intersectionId: string;
  cameraId: string;
  frameWidth: number;
  frameHeight: number;
  onSaved?: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function ROIEditor({
  previewFrame,
  intersectionId,
  cameraId,
  frameWidth,
  frameHeight,
  onSaved,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const [selectedLane, setSelectedLane] = useState<LaneKey>("north_straight");
  const [polygons, setPolygons] = useState<PolygonMap>({});
  const [drawing, setDrawing] = useState<Point[]>([]);
  const [hoveredPt, setHoveredPt] = useState<Point | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Load preview frame as Image object once available
  useEffect(() => {
    if (!previewFrame) return;
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      redraw();
    };
    img.src = `data:image/jpeg;base64,${previewFrame}`;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewFrame]);

  // Fetch existing ROIs
  useEffect(() => {
    async function fetchROIs() {
      try {
        const res = await fetch(`${API_BASE}/cctv/roi/${intersectionId}/${cameraId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.rois) {
          const loaded: PolygonMap = {};
          data.rois.forEach((r: any) => {
            loaded[r.lane_id as LaneKey] = r.vertices;
          });
          setPolygons(loaded);
        }
      } catch (err) {
        console.error("Failed to load existing ROIs:", err);
      }
    }
    fetchROIs();
  }, [intersectionId, cameraId]);

  // ── Canvas redraw ────────────────────────────────────────────────────
  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    // Draw background frame
    if (imgRef.current) {
      ctx.drawImage(imgRef.current, 0, 0, W, H);
    } else {
      ctx.fillStyle = "#0a0a0a";
      ctx.fillRect(0, 0, W, H);
      // Draw grid pattern
      ctx.strokeStyle = "#ffffff08";
      ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
      for (let y = 0; y < H; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }
    }

    // Draw all saved polygons
    for (const [lane, pts] of Object.entries(polygons) as [LaneKey, Point[]][]) {
      if (!pts || pts.length < 2) continue;
      const color = getLaneColor(lane);
      ctx.save();
      ctx.globalAlpha = 0.2;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(pts[0][0] * W, pts[0][1] * H);
      for (let i = 1; i < pts.length; i++)
        ctx.lineTo(pts[i][0] * W, pts[i][1] * H);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 0.8;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      // Label
      const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
      const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
      ctx.globalAlpha = 0.9;
      ctx.fillStyle = color;
      ctx.font = "bold 10px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(lane.replace(/_/g, " "), cx * W, cy * H + 4);
      ctx.restore();

      // Vertex dots
      for (const [px, py] of pts) {
        ctx.beginPath();
        ctx.arc(px * W, py * H, 3, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }

    // Draw in-progress polygon
    if (drawing.length > 0) {
      const color = getLaneColor(selectedLane);
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(drawing[0][0] * W, drawing[0][1] * H);
      for (let i = 1; i < drawing.length; i++)
        ctx.lineTo(drawing[i][0] * W, drawing[i][1] * H);
      if (hoveredPt) ctx.lineTo(hoveredPt[0] * W, hoveredPt[1] * H);
      ctx.stroke();
      ctx.restore();

      for (const [px, py] of drawing) {
        ctx.beginPath();
        ctx.arc(px * W, py * H, 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.strokeStyle = "#000";
        ctx.lineWidth = 1;
        ctx.fill();
        ctx.stroke();
      }
    }
  }, [polygons, drawing, hoveredPt, selectedLane]);

  // Re-render whenever state changes
  useEffect(() => {
    redraw();
  }, [redraw]);

  // ── Mouse events ─────────────────────────────────────────────────────
  function toRel(e: MouseEvent<HTMLCanvasElement>): Point {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    // Use rect dimensions (CSS-rendered size) for coordinate mapping
    return [
      (e.clientX - rect.left) / rect.width,
      (e.clientY - rect.top) / rect.height,
    ];
  }

  function handleCanvasClick(e: MouseEvent<HTMLCanvasElement>) {
    if (e.button !== 0) return;
    const pt = toRel(e);
    setDrawing((prev) => [...prev, pt]);
  }

  function handleContextMenu(e: MouseEvent<HTMLCanvasElement>) {
    e.preventDefault();
    closePolygon();
  }

  function handleMouseMove(e: MouseEvent<HTMLCanvasElement>) {
    setHoveredPt(toRel(e));
  }

  function handleMouseLeave() {
    setHoveredPt(null);
  }

  function closePolygon() {
    if (drawing.length < 3) return;
    setPolygons((prev) => ({ ...prev, [selectedLane]: drawing }));
    setDrawing([]);
    // Auto-advance to next undefined lane
    const nextLane = LANE_KEYS.find(
      (k) => !polygons[k] && k !== selectedLane
    );
    if (nextLane) setSelectedLane(nextLane);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") closePolygon();
    if (e.key === "Escape") setDrawing([]);
    if (e.key === "Backspace") setDrawing((prev) => prev.slice(0, -1));
  }

  function deleteLane(lane: LaneKey) {
    setPolygons((prev) => {
      const next = { ...prev };
      delete next[lane];
      return next;
    });
  }

  // ── Save ──────────────────────────────────────────────────────────────
  async function saveROI() {
    const defined = Object.keys(polygons);

    const rois = defined.map((lane) => ({
      lane_id: lane,
      vertices: polygons[lane as LaneKey]!,
      color: getLaneColor(lane),
    }));

    const body = {
      intersection_id: intersectionId,
      camera_id: cameraId,
      frame_width: frameWidth,
      frame_height: frameHeight,
      rois,
    };

    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`${API_BASE}/cctv/roi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Save failed");

      const warnings: string[] = data.warnings ?? [];
      setSaveMsg(
        warnings.length > 0
          ? `Saved with warnings: ${warnings.join(", ")}`
          : `✓ ROI config saved (${defined.length}/12 lanes defined)`
      );
      onSaved?.();
    } catch (err) {
      setSaveMsg(`Error: ${(err as Error).message}`);
    } finally {
      setSaving(false);
    }
  }

  const definedCount = Object.keys(polygons).length;

  return (
    <div className="rounded-xl border border-white/10 bg-[#111] overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-sm font-semibold text-white">
            ROI Lane Editor
          </h2>
          <p className="text-[10px] text-white/30 mt-0.5">
            Click to add vertices · Right-click or Enter to close · Backspace to
            undo
          </p>
        </div>
        <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-white/45 font-mono">
          {definedCount}/12
        </span>
      </div>

      {/* Main area: canvas + sidebar */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Canvas */}
        <div className="flex-1 relative bg-black min-w-0">
          <canvas
            ref={canvasRef}
            width={640}
            height={480}
            className="w-full h-full object-contain cursor-crosshair"
            tabIndex={0}
            onClick={handleCanvasClick}
            onContextMenu={handleContextMenu}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onKeyDown={handleKeyDown}
          />
          {!previewFrame && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <p className="text-white/15 text-xs text-center px-4">
                Start processing a video — first frame will appear here as
                background
              </p>
            </div>
          )}
          {drawing.length > 0 && (
            <div className="absolute bottom-2 left-2 text-[10px] text-white/50 bg-black/70 backdrop-blur-sm px-2 py-1 rounded-md border border-white/[0.08]">
              {drawing.length} vertices · Right-click or Enter to close
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div
          className="flex flex-col border-l border-white/[0.06] overflow-y-auto flex-shrink-0"
          style={{ width: 200 }}
        >
          {/* Lane selector */}
          <div className="p-3 border-b border-white/[0.06] flex-shrink-0">
            <label className="text-[10px] text-white/30 uppercase tracking-wider font-medium block mb-1.5">
              Active Lane
            </label>
            <select
              value={selectedLane}
              onChange={(e) => {
                setSelectedLane(e.target.value as LaneKey);
                setDrawing([]);
              }}
              className="w-full rounded-lg bg-white/[0.04] border border-white/[0.08] px-2 py-1.5 text-xs text-white/80 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 transition-all"
            >
              {LANE_KEYS.map((lane) => (
                <option key={lane} value={lane}>
                  {polygons[lane] ? "✓ " : "  "}
                  {lane.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          {/* Defined polygons list */}
          <div className="flex-1 p-2 flex flex-col gap-0.5 overflow-y-auto min-h-0">
            {LANE_KEYS.map((lane) => {
              const defined = !!polygons[lane];
              const color = getLaneColor(lane);
              return (
                <div
                  key={lane}
                  className={`flex items-center justify-between px-2 py-1.5 rounded-lg text-[10px] cursor-pointer transition-all ${
                    selectedLane === lane
                      ? "bg-white/[0.08] text-white"
                      : defined
                      ? "text-white/55 hover:bg-white/[0.04]"
                      : "text-white/20 hover:bg-white/[0.03]"
                  }`}
                  onClick={() => {
                    setSelectedLane(lane);
                    setDrawing([]);
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{
                        backgroundColor: defined ? color : "#ffffff15",
                      }}
                    />
                    <span className="capitalize truncate">
                      {lane.replace(/_/g, " ")}
                    </span>
                  </div>
                  {defined && (
                    <button
                      className="text-white/15 hover:text-rose-400 transition-colors ml-1 text-sm leading-none"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteLane(lane);
                      }}
                      title="Delete"
                    >
                      ×
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div className="p-3 border-t border-white/[0.06] flex flex-col gap-2 flex-shrink-0">
            <button
              onClick={closePolygon}
              disabled={drawing.length < 3}
              className="w-full py-1.5 text-xs rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-white/50 hover:text-white disabled:opacity-25 disabled:cursor-not-allowed transition-all"
            >
              Close Polygon (Enter)
            </button>
            <button
              onClick={saveROI}
              disabled={saving}
              className="w-full py-1.5 text-xs rounded-lg bg-[#1a6bff] hover:bg-blue-500 text-white font-semibold disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-blue-600/20"
            >
              {saving ? "Saving..." : "Save ROI Config"}
            </button>
            {saveMsg && (
              <p
                className={`text-[10px] text-center leading-snug ${
                  saveMsg.startsWith("✓")
                    ? "text-emerald-400"
                    : "text-amber-400"
                }`}
              >
                {saveMsg}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

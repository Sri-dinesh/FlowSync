"use client";

import { useMemo, useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Trophy,
  Play,
  RotateCcw,
  Clock,
  Target,
  Bot,
  Activity,
  SlidersHorizontal,
  CheckCircle2,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckSquare,
  Square as SquareIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import type { SimBenchmarkProgress, SimBenchmarkResultsData } from "@/hooks/useSimulationSocket";

interface SimulationBenchmarkPanelProps {
  running: boolean;
  progress: SimBenchmarkProgress | null;
  results: SimBenchmarkResultsData | null;
  onStart: (durationSeconds: number, modes?: string[], modelId?: string, modelEpisode?: number) => void;
  onStartModelBenchmark?: (
    durationSeconds: number,
    models: Array<{ id: string; episodes?: number; version?: string; name?: string }>
  ) => void;
  onStop: () => void;
  onReset: () => void;
}

const PRESET_DURATIONS = [15, 30, 60, 120];

const BENCHMARK_MODES = ["ai", "fixed", "greedy"];

const MODE_CONFIG: Record<
  string,
  { label: string; shortLabel: string; icon: any; barColor: string }
> = {
  ai: {
    label: "FlowSync DQN AI",
    shortLabel: "DQN AI",
    icon: Bot,
    barColor: "#6366F1",
  },
  fixed: {
    label: "Fixed Timer",
    shortLabel: "FIXED",
    icon: Clock,
    barColor: "#64748B",
  },
  greedy: {
    label: "Greedy Policy",
    shortLabel: "GREEDY",
    icon: Target,
    barColor: "#10B981",
  },
};

const MODEL_PALETTE = [
  "#6366F1", // Indigo
  "#06B6D4", // Cyan
  "#10B981", // Emerald
  "#F59E0B", // Amber
  "#EC4899", // Pink
  "#8B5CF6", // Purple
  "#3B82F6", // Blue
  "#14B8A6", // Teal
];

export interface RLModelOption {
  id: string;
  name: string;
  version: string;
  episodes?: number;
  source?: string;
}

export default function SimulationBenchmarkPanel({
  running,
  progress,
  results,
  onStart,
  onStartModelBenchmark,
  onStop,
  onReset,
}: SimulationBenchmarkPanelProps) {
  // Benchmark type tab: 'controllers' (AI vs Fixed vs Greedy) or 'models' (Multiple DQN Checkpoints)
  const [benchmarkType, setBenchmarkType] = useState<"controllers" | "models">("controllers");
  const [duration, setDuration] = useState<number>(15);
  const [models, setModels] = useState<RLModelOption[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  useEffect(() => {
    async function fetchModels() {
      try {
        const res = await fetch(`${API_BASE}/training/models`);
        if (res.ok) {
          const payload = await res.json();
          const list: RLModelOption[] = payload.models ?? [];
          // Sort by episodes ascending so progression is intuitive
          list.sort((a, b) => {
            const epA = Number(a.episodes ?? a.version ?? 0);
            const epB = Number(b.episodes ?? b.version ?? 0);
            return epA - epB;
          });
          setModels(list);
          if (list.length > 0) {
            setSelectedModelId((prev) => prev || list[0].id);
            // Default multi-model selection: select up to first 3-4 models
            setSelectedModelIds((prev) => {
              if (prev.length > 0) return prev;
              if (list.length <= 3) return list.map((m) => m.id);
              // Pick first, middle, and latest
              return [list[0].id, list[Math.floor(list.length / 2)].id, list[list.length - 1].id];
            });
          }
        }
      } catch (err) {
        console.warn("Failed to fetch models for benchmark:", err);
      }
    }
    fetchModels();
  }, [API_BASE]);

  // Is this benchmark run or result a multi-model comparison?
  const isModelBenchmark = useMemo(() => {
    if (results?.benchmark_type === "model_comparison") return true;
    if (progress?.benchmark_type === "model_comparison") return true;
    if (results?.modes && results.modes.some((m) => m.startsWith("model_"))) return true;
    return false;
  }, [results, progress]);

  // Toggle model selection in multi-model checklist
  const toggleModelSelection = (id: string) => {
    setSelectedModelIds((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handleSelectAllModels = () => {
    setSelectedModelIds(models.map((m) => m.id));
  };

  const handleSelectMilestones = () => {
    if (models.length <= 4) {
      setSelectedModelIds(models.map((m) => m.id));
      return;
    }
    const step = Math.floor(models.length / 3);
    const chosen = [
      models[0].id,
      models[step].id,
      models[step * 2].id,
      models[models.length - 1].id,
    ];
    setSelectedModelIds(Array.from(new Set(chosen)));
  };

  const handleClearModels = () => {
    setSelectedModelIds([]);
  };

  const selectedModelsList = useMemo(() => {
    return models.filter((m) => selectedModelIds.includes(m.id));
  }, [models, selectedModelIds]);

  // Comparative bar chart data
  const chartData = useMemo(() => {
    if (!results || !results.results) return [];
    const modes = results.modes || Object.keys(results.results);
    return [
      {
        metric: "Vehicles Passed",
        ...Object.fromEntries(modes.map((m) => [m, results.results[m]?.total_passed ?? 0])),
      },
      {
        metric: "Avg Wait (s)",
        ...Object.fromEntries(modes.map((m) => [m, results.results[m]?.avg_wait_time ?? 0])),
      },
      {
        metric: "Max Queue",
        ...Object.fromEntries(modes.map((m) => [m, results.results[m]?.max_queue ?? 0])),
      },
    ];
  }, [results]);

  const winnerLabel = useMemo(() => {
    if (!results?.winner) return null;
    if (isModelBenchmark) {
      return (
        results.winner_label ||
        results.results[results.winner]?.label ||
        `Model ${results.winner_episode ?? results.winner} eps`
      );
    }
    return MODE_CONFIG[results.winner]?.label ?? results.winner.toUpperCase();
  }, [results, isModelBenchmark]);

  return (
    <div className="space-y-3.5 text-white">
      {/* 1. CONFIGURATION VIEW */}
      {!running && !results && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          {/* Header & Benchmark Category Switcher */}
          <div className="flex flex-col gap-2.5 border-b border-neutral-800 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                <span className="text-[11px] font-semibold text-neutral-300 uppercase tracking-wider">
                  Simulation Benchmark Mode
                </span>
              </div>
              <span className="text-[9px] font-mono text-neutral-400 bg-neutral-800/80 border border-neutral-700/60 px-2 py-0.5 rounded-md font-medium">
                {benchmarkType === "controllers" ? "3 Controllers • Fixed vs Greedy vs AI" : "DQN AI Only • Multi-Checkpoint"}
              </span>
            </div>

            {/* Toggle Pills */}
            <div className="grid grid-cols-2 p-1 bg-neutral-950/80 rounded-lg border border-neutral-800">
              <button
                type="button"
                onClick={() => setBenchmarkType("controllers")}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all ${
                  benchmarkType === "controllers"
                    ? "bg-neutral-800 text-white shadow-sm font-semibold border border-neutral-700/50"
                    : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
                }`}
              >
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                <span>⚔️ Controller Showdown</span>
              </button>
              <button
                type="button"
                onClick={() => setBenchmarkType("models")}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all ${
                  benchmarkType === "models"
                    ? "bg-neutral-800 text-white shadow-sm font-semibold border border-neutral-700/50"
                    : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
                }`}
              >
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
                <span>🤖 Multi-Model Showdown</span>
              </button>
            </div>
          </div>

          {/* DURATION SLIDER & PRESETS */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400 font-medium flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-neutral-500" />
                Duration per Phase
              </span>
              <span className="font-mono text-sm font-medium text-white tracking-tight">
                {duration}s{" "}
                <span className="text-neutral-500 text-[10px] font-normal font-sans">
                  (
                  {duration *
                    (benchmarkType === "controllers"
                      ? BENCHMARK_MODES.length
                      : Math.max(1, selectedModelIds.length))}
                  s total)
                </span>
              </span>
            </div>

            <div className="grid grid-cols-4 gap-1.5 p-1 bg-neutral-900 rounded-lg border border-neutral-800">
              {PRESET_DURATIONS.map((preset) => {
                const isSelected = duration === preset;
                return (
                  <button
                    key={preset}
                    onClick={() => setDuration(preset)}
                    className={`py-1.5 rounded-md text-xs font-mono font-medium transition-all ${
                      isSelected
                        ? "bg-neutral-800 text-white shadow-sm"
                        : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
                    }`}
                  >
                    {preset}s
                  </button>
                );
              })}
            </div>

            <div className="pt-1 px-1">
              <Slider
                min={10}
                max={120}
                step={5}
                value={[duration]}
                onValueChange={(val) => setDuration(val[0] ?? 15)}
                className="w-full"
              />
              <div className="flex justify-between text-[9px] font-mono text-neutral-600 mt-1">
                <span>10s</span>
                <span>60s</span>
                <span>120s</span>
              </div>
            </div>
          </div>

          {/* TAB 1: CONTROLLER SHOWDOWN PIPELINE */}
          {benchmarkType === "controllers" && (
            <>
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 space-y-2">
                <div className="text-[9px] uppercase tracking-wider text-neutral-500 font-medium flex items-center justify-between">
                  <span>Evaluation Pipeline (3 Controllers)</span>
                  <span className="font-mono text-neutral-400 font-normal">
                    {BENCHMARK_MODES.length} × {duration}s = {duration * BENCHMARK_MODES.length}s
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {BENCHMARK_MODES.map((m) => {
                    const cfg = MODE_CONFIG[m];
                    const Icon = cfg.icon;
                    return (
                      <div
                        key={m}
                        className="flex flex-col items-center justify-center p-2 rounded-lg bg-neutral-800/50 border border-neutral-700/60 text-center"
                      >
                        <Icon className="w-3.5 h-3.5 text-neutral-400 mb-1" />
                        <span className="text-[10px] font-medium text-neutral-300">
                          {cfg.shortLabel}
                        </span>
                        <span className="text-[9px] font-mono text-neutral-500 mt-0.5">
                          {duration}s
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Checkpoint selector for the AI phase */}
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3.5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-300 font-medium flex items-center gap-1.5">
                    <Bot className="w-3.5 h-3.5 text-indigo-400" />
                    DQN AI Active Checkpoint
                  </span>
                  {(() => {
                    const selected = models.find((m) => m.id === selectedModelId);
                    return selected ? (
                      <span className="font-mono text-[10px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full font-medium">
                        {selected.episodes ?? selected.version} eps
                      </span>
                    ) : null;
                  })()}
                </div>

                <select
                  value={selectedModelId}
                  onChange={(e) => setSelectedModelId(e.target.value)}
                  className="w-full rounded-lg bg-neutral-950 border border-neutral-800 px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 transition-colors font-medium"
                >
                  {models.length === 0 ? (
                    <option value="">Default FlowSync DQN Checkpoint</option>
                  ) : (
                    models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} — {m.episodes ?? m.version} eps ({m.source === "remote" ? "Cloud" : "Local"})
                      </option>
                    ))
                  )}
                </select>
                <p className="text-[10px] text-neutral-500 leading-tight">
                  Evaluates the chosen DQN policy against Fixed Timer and Greedy controller baselines.
                </p>
              </div>

              <Button
                className="w-full py-6 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                onClick={() => {
                  const selected = models.find((m) => m.id === selectedModelId);
                  let epNum: number | undefined;
                  if (selected?.episodes) {
                    epNum = Number(selected.episodes);
                  } else if (selected?.version) {
                    const parsed = parseInt(selected.version, 10);
                    if (!isNaN(parsed)) epNum = parsed;
                  }
                  onStart(duration, BENCHMARK_MODES, selectedModelId || undefined, epNum);
                }}
              >
                <Play className="w-3.5 h-3.5 fill-black" />
                Launch Controller Benchmark ({duration * BENCHMARK_MODES.length}s)
              </Button>
            </>
          )}

          {/* TAB 2: MULTI-MODEL SHOWDOWN (DQN AI MODE ONLY) */}
          {benchmarkType === "models" && (
            <>
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-xs font-semibold text-white">
                      Select Trained Checkpoints ({selectedModelIds.length} chosen)
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={handleSelectMilestones}
                      className="text-[10px] text-indigo-400 hover:text-indigo-300 font-medium px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 transition-colors"
                    >
                      Milestones
                    </button>
                    <button
                      type="button"
                      onClick={handleSelectAllModels}
                      className="text-[10px] text-neutral-400 hover:text-white px-2 py-0.5 rounded bg-neutral-800 transition-colors"
                    >
                      All
                    </button>
                    <button
                      type="button"
                      onClick={handleClearModels}
                      className="text-[10px] text-neutral-500 hover:text-neutral-300 px-1.5 py-0.5 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                <p className="text-[10px] text-neutral-400 leading-relaxed">
                  Every model in this showdown runs strictly in <strong className="text-white">DQN AI mode</strong> under identical vehicle arrival seeds to fairly compare learning progression across episodes.
                </p>

                {/* Checklist of available models */}
                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                  {models.length === 0 ? (
                    <div className="p-3 text-center text-xs text-neutral-500 border border-neutral-800 rounded-lg">
                      No trained models found. Train agents in the Training tab to generate checkpoints.
                    </div>
                  ) : (
                    models.map((m, idx) => {
                      const isSelected = selectedModelIds.includes(m.id);
                      const epCount = m.episodes ?? m.version;
                      const paletteColor = MODEL_PALETTE[idx % MODEL_PALETTE.length];

                      return (
                        <div
                          key={m.id}
                          onClick={() => toggleModelSelection(m.id)}
                          className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-all ${
                            isSelected
                              ? "bg-neutral-800/80 border-indigo-500/50 shadow-sm"
                              : "bg-neutral-950/60 border-neutral-800/70 hover:border-neutral-700"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-indigo-400 shrink-0" />
                            ) : (
                              <SquareIcon className="w-4 h-4 text-neutral-600 shrink-0" />
                            )}
                            <div className="min-w-0">
                              <div className="text-xs font-medium text-white truncate flex items-center gap-1.5">
                                <span
                                  className="w-2 h-2 rounded-full inline-block shrink-0"
                                  style={{ backgroundColor: paletteColor }}
                                />
                                <span className="truncate">{m.name}</span>
                              </div>
                              <div className="text-[10px] text-neutral-500 flex items-center gap-2 font-mono">
                                <span>{m.source === "remote" ? "Cloud" : "Local"}</span>
                                <span>•</span>
                                <span>ID: {m.id.slice(0, 16)}</span>
                              </div>
                            </div>
                          </div>

                          <span className="font-mono text-[11px] text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium shrink-0 ml-2">
                            {epCount} eps
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>

                {selectedModelIds.length < 2 && (
                  <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 shrink-0" />
                    <span>Please select at least 2 checkpoints to compare policy evolution.</span>
                  </div>
                )}
              </div>

              {/* Pipeline preview for selected models */}
              {selectedModelsList.length >= 2 && (
                <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 space-y-2">
                  <div className="text-[9px] uppercase tracking-wider text-neutral-500 font-medium flex items-center justify-between">
                    <span>Showdown Pipeline ({selectedModelsList.length} Checkpoints)</span>
                    <span className="font-mono text-neutral-400 font-normal">
                      {selectedModelsList.length} × {duration}s = {selectedModelsList.length * duration}s
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {selectedModelsList.map((m, i) => (
                      <div key={m.id} className="flex items-center gap-1">
                        <span className="text-[10px] font-mono px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-neutral-300 font-medium">
                          {m.episodes ?? m.version} eps
                        </span>
                        {i < selectedModelsList.length - 1 && (
                          <ArrowRight className="w-3 h-3 text-neutral-600" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Button
                disabled={selectedModelIds.length < 2}
                className="w-full py-6 bg-emerald-500 text-black hover:bg-emerald-400 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                onClick={() => {
                  if (onStartModelBenchmark) {
                    const toSend = selectedModelsList.map((m) => ({
                      id: m.id,
                      episodes: Number(m.episodes ?? m.version ?? 0),
                      version: m.version,
                      name: m.name,
                    }));
                    onStartModelBenchmark(duration, toSend);
                  }
                }}
              >
                <Play className="w-3.5 h-3.5 fill-black" />
                Run Multi-Model Benchmark ({selectedModelIds.length} Models • {selectedModelIds.length * duration}s)
              </Button>
            </>
          )}
        </div>
      )}

      {/* 2. LIVE RUNNING TELEMETRY HUD */}
      {running && progress && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              <span className="text-[11px] font-medium uppercase tracking-wider text-neutral-300">
                {isModelBenchmark
                  ? `Evaluating Model ${(progress.mode_index ?? 0) + 1} of ${progress.modes_total ?? 2}`
                  : `Running Controller ${(progress.mode_index ?? 0) + 1} of ${progress.modes_total ?? 3}`}
              </span>
            </div>
            <span className="font-mono text-xs font-medium text-white bg-neutral-800 border border-neutral-700 px-2 py-0.5 rounded-md">
              {progress.elapsed?.toFixed(1)}s / {progress.duration_seconds ?? duration}.0s
            </span>
          </div>

          {/* Active Model / Mode Highlight Banner */}
          <div className="p-3 rounded-lg bg-neutral-950/70 border border-neutral-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs font-semibold text-white">
                  {progress.current_model || MODE_CONFIG[progress.current_mode]?.label || progress.current_mode}
                </div>
                <div className="text-[10px] text-neutral-400 font-mono">
                  {isModelBenchmark
                    ? `DQN AI Policy Checkpoint • ${progress.current_episode ?? "?"} episodes`
                    : "Benchmark Phase Active"}
                </div>
              </div>
            </div>
            <div className="text-right font-mono">
              <div className="text-xs font-semibold text-emerald-400">
                {progress.passed_count ?? 0} passed
              </div>
              <div className="text-[10px] text-neutral-500">
                {progress.avg_wait ? `${progress.avg_wait}s avg wait` : "CRN Synchronized"}
              </div>
            </div>
          </div>

          {/* Phase progress chips */}
          <div className="flex flex-wrap gap-2">
            {(progress.modes_done || []).map((mKey) => (
              <span
                key={mKey}
                className="text-[10px] font-mono px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 flex items-center gap-1"
              >
                <CheckCircle2 className="w-3 h-3" />
                {mKey} ✓
              </span>
            ))}
            <span className="text-[10px] font-mono px-2.5 py-1 rounded-md bg-indigo-500/20 border border-indigo-500/40 text-indigo-200 animate-pulse flex items-center gap-1 font-semibold">
              <Activity className="w-3 h-3 text-indigo-400" />
              {progress.current_mode} ({progress.elapsed?.toFixed(0)}s)
            </span>
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-[9px] font-mono uppercase tracking-wider text-neutral-500">
              <span>Current Evaluation Progress</span>
              <span className="text-neutral-300 font-medium">
                {Math.min(
                  Math.round(
                    ((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration)) * 100
                  ),
                  100
                )}
                %
              </span>
            </div>
            <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden p-0.5 border border-neutral-700">
              <div
                className="h-full bg-indigo-400 rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min(
                    ((progress.elapsed ?? 0) / (progress.duration_seconds ?? duration)) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>

          <div className="pt-1 flex items-center justify-between border-t border-neutral-800">
            <span className="text-[9px] text-neutral-500 font-mono flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Strict DQN AI Simulation Loop (10Hz)
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-3 rounded-lg border-neutral-800 bg-neutral-900 text-red-400 hover:bg-neutral-800 hover:text-red-300 text-[10px] font-bold uppercase tracking-wider transition-all"
              onClick={onStop}
            >
              Abort Benchmark
            </Button>
          </div>
        </div>
      )}

      {/* 3. COMPREHENSIVE BENCHMARK RESULTS VIEW */}
      {!running && results && (
        <div className="space-y-3.5">
          {/* Victory Card */}
          {results.winner && (
            <div className="rounded-xl border border-amber-500/30 bg-neutral-900/90 p-4 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      <Trophy className="w-4 h-4" />
                    </span>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
                      {isModelBenchmark ? "Top Performing Model Checkpoint" : "Top Performance Policy"}
                    </span>
                  </div>
                  <div className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                    {winnerLabel}
                    {results.winner_episode !== undefined && (
                      <span className="text-xs font-mono font-normal text-amber-300/80 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                        {results.winner_episode} eps
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-neutral-300 leading-relaxed pt-0.5">
                    {isModelBenchmark ? (
                      (() => {
                        const winnerWaitKey = `${results.winner}_wait_pct`;
                        const impPct = results.improvements?.[winnerWaitKey];
                        if (impPct && impPct > 0) {
                          return `Achieved a ${impPct}% wait time reduction compared to the baseline training checkpoint under identical traffic.`;
                        }
                        return `Delivered the lowest average delay (${results.results[results.winner]?.avg_wait_time ?? 0}s) and highest clearing throughput.`;
                      })()
                    ) : (
                      results.improvements?.ai_wait_pct && results.improvements.ai_wait_pct > 0 && results.winner === "ai"
                        ? `Achieved ${results.improvements.ai_wait_pct}% lower average wait time compared to Fixed Timer baseline.`
                        : results.improvements?.greedy_wait_pct && results.improvements.greedy_wait_pct > 0 && results.winner === "greedy"
                        ? `Achieved ${results.improvements.greedy_wait_pct}% lower average wait time compared to Fixed Timer baseline.`
                        : `Demonstrated optimal vehicle flow and minimal congestion throughout the ${results.duration_seconds}s benchmark.`
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Model / Policy Performance Cards */}
          <div className="space-y-2">
            <div className="text-[9px] font-medium uppercase tracking-wider text-neutral-400 px-1 flex items-center justify-between">
              <span>
                {isModelBenchmark
                  ? `Checkpoint Performance (${results.duration_seconds}s per model)`
                  : `Policy Metrics (${results.duration_seconds}s per controller)`}
              </span>
              <span className="font-mono text-neutral-500 text-[10px]">
                {results.modes.length} evaluated
              </span>
            </div>

            {results.modes.map((modeKey, idx) => {
              const res = results.results[modeKey];
              const isWinner = modeKey === results.winner;
              const barColor = isModelBenchmark
                ? MODEL_PALETTE[idx % MODEL_PALETTE.length]
                : MODE_CONFIG[modeKey]?.barColor ?? "#fff";

              const label = isModelBenchmark
                ? res?.label ?? modeKey
                : MODE_CONFIG[modeKey]?.label ?? modeKey;

              const epDisplay = res?.model_episode ? `${res.model_episode} eps` : null;

              return (
                <div
                  key={modeKey}
                  className={`rounded-xl border p-3 transition-all ${
                    isWinner
                      ? "border-amber-500/40 bg-neutral-850 shadow-md"
                      : "border-neutral-800 bg-neutral-900/50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full inline-block"
                        style={{ backgroundColor: barColor }}
                      />
                      <span className={`text-xs font-semibold ${isWinner ? "text-white" : "text-neutral-200"}`}>
                        {label}
                      </span>
                      {epDisplay && (
                        <span className="font-mono text-[10px] text-neutral-400 bg-neutral-800 border border-neutral-700/60 px-2 py-0.2 rounded-full">
                          {epDisplay}
                        </span>
                      )}
                    </div>
                    {isWinner && (
                      <span className="text-[9px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-400 text-black shadow-sm font-mono flex items-center gap-1">
                        <Trophy className="w-2.5 h-2.5" />
                        WINNER
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-neutral-800">
                    <div className="bg-neutral-900/80 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-400 font-medium">Passed</div>
                      <div className={`text-xs font-mono font-semibold mt-0.5 ${isWinner ? "text-white" : "text-neutral-200"}`}>
                        {res?.total_passed ?? 0} <span className="text-[8px] font-normal text-neutral-500">veh</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900/80 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-400 font-medium">Avg Wait</div>
                      <div className={`text-xs font-mono font-semibold mt-0.5 ${isWinner ? "text-amber-300" : "text-neutral-200"}`}>
                        {res?.avg_wait_time ?? 0} <span className="text-[8px] font-normal text-neutral-500">s</span>
                      </div>
                    </div>

                    <div className="bg-neutral-900/80 rounded-lg p-2 text-center border border-neutral-800">
                      <div className="text-[8px] uppercase tracking-wider text-neutral-400 font-medium">Max Queue</div>
                      <div className="text-xs font-mono font-semibold mt-0.5 text-neutral-200">
                        {res?.max_queue ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Comparative Bar Chart */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-3.5">
            <p className="text-[9px] uppercase tracking-wider text-neutral-400 font-medium mb-3">
              Comparative Analysis
            </p>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="metric" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 9 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#0a0a0a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "11px",
                  }}
                  itemStyle={{ color: "rgba(255,255,255,0.9)" }}
                  labelStyle={{ color: "rgba(255,255,255,0.5)" }}
                />
                <Legend wrapperStyle={{ fontSize: "10px", color: "rgba(255,255,255,0.5)" }} />
                {results.modes.map((modeKey, idx) => {
                  const color = isModelBenchmark
                    ? MODEL_PALETTE[idx % MODEL_PALETTE.length]
                    : MODE_CONFIG[modeKey]?.barColor ?? "#fff";
                  const name = isModelBenchmark
                    ? results.results[modeKey]?.label ?? modeKey
                    : MODE_CONFIG[modeKey]?.shortLabel ?? modeKey;

                  return (
                    <Bar
                      key={modeKey}
                      name={name}
                      dataKey={modeKey}
                      fill={color}
                      radius={[3, 3, 0, 0]}
                    />
                  );
                })}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Action Row */}
          <div className="flex gap-2 pt-1">
            <Button
              className="flex-1 py-5 bg-white text-black hover:bg-neutral-200 font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 shadow-sm"
              onClick={() => {
                if (isModelBenchmark && onStartModelBenchmark) {
                  const toSend = selectedModelsList.map((m) => ({
                    id: m.id,
                    episodes: Number(m.episodes ?? m.version ?? 0),
                    version: m.version,
                    name: m.name,
                  }));
                  onStartModelBenchmark(results.duration_seconds || duration, toSend);
                } else {
                  const selected = models.find((m) => m.id === selectedModelId);
                  let epNum: number | undefined;
                  if (selected?.episodes) {
                    epNum = Number(selected.episodes);
                  } else if (selected?.version) {
                    const parsed = parseInt(selected.version, 10);
                    if (!isNaN(parsed)) epNum = parsed;
                  }
                  onStart(results.duration_seconds || duration, BENCHMARK_MODES, selectedModelId || undefined, epNum);
                }
              }}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Rerun ({results.duration_seconds}s each)
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-10 border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-all flex items-center gap-1.5"
              onClick={onReset}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Adjust
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Activity, Zap, Clock, TrendingUp, TrendingDown, Brain, CheckCircle2, Minus, RotateCcw, Sparkles, Sliders, Settings2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import AIStatusBadge from "@/components/dashboard/AIStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSimulationStore } from "@/store/simulationStore";
import type { TrainingMetric } from "@/types/simulation";
import { getFastApiUrls } from "@/lib/utils";

interface RLModel {
  id: string;
  name: string;
  version: string;
  source?: string;
  episodes?: number;
  is_finetuned?: boolean;
  scenario?: string | null;
}

const SCENARIO_PRESETS = [
  {
    id: "rush_hour",
    name: "Rush Hour Corridor",
    tag: "80% NS Surge",
    description: "North-South commuter corridor surge (80% NS volume, 20% EW cross streets). Teaches asymmetric priority.",
    icon: "🚗",
    defaultDirWeights: { north: 1.8, south: 1.8, east: 0.4, west: 0.4 },
    defaultTurnProbs: { straight: 60, left: 20, right: 20 },
    defaultLambda: 0.85,
    defaultMult: 1.2,
  },
  {
    id: "heavy_left",
    name: "Heavy Left Turns",
    tag: "50% Lefts",
    description: "50% left turns across all approaches. Forces the agent to specialize in Phase 2 & 3 protected arrows.",
    icon: "↩️",
    defaultDirWeights: { north: 1.0, south: 1.0, east: 1.0, west: 1.0 },
    defaultTurnProbs: { straight: 30, left: 50, right: 20 },
    defaultLambda: 0.75,
    defaultMult: 1.0,
  },
  {
    id: "arterial_surge",
    name: "East-West Arterial",
    tag: "EW Speed Corridor",
    description: "High-speed East-West main thoroughfare with light feeder arrivals. Maximizes green waves.",
    icon: "⚡",
    defaultDirWeights: { north: 0.35, south: 0.35, east: 1.9, west: 1.9 },
    defaultTurnProbs: { straight: 70, left: 15, right: 15 },
    defaultLambda: 0.90,
    defaultMult: 1.15,
  },
  {
    id: "platoon_burst",
    name: "Platoon Congestion",
    tag: "Near-Gridlock",
    description: "Dense platooned arrival bursts across all approaches demanding quick queue clearance.",
    icon: "🛑",
    defaultDirWeights: { north: 1.25, south: 1.25, east: 1.25, west: 1.25 },
    defaultTurnProbs: { straight: 50, left: 25, right: 25 },
    defaultLambda: 1.25,
    defaultMult: 1.3,
  },
  {
    id: "custom",
    name: "Custom Parameters",
    tag: "Manual Customizer",
    description: "Configure custom directional volumes, turning probabilities, and arrival rates tailored to any geometry.",
    icon: "🎛️",
    defaultDirWeights: { north: 1.5, south: 1.5, east: 0.5, west: 0.5 },
    defaultTurnProbs: { straight: 50, left: 30, right: 20 },
    defaultLambda: 0.8,
    defaultMult: 1.1,
  },
];

interface TrainingControlsProps {
  sendCommand: (command: Record<string, unknown>) => void;
  simulationId: string | null;
}

function MiniSparkline({ values, color, height = 32 }: { values: number[]; color: string; height?: number }) {
  const points = useMemo(() => {
    if (values.length < 2) return "";
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = Math.max(max - min, 1e-6);
    return values.map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    }).join(" ");
  }, [values, height]);

  if (!points) return <div className="h-8 w-full rounded bg-white/5" />;
  return (
    <svg viewBox={`0 0 100 ${height}`} className="w-full" preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" points={points} />
    </svg>
  );
}

/** Arrow showing if last value is better/worse than the one before */
function Trend({ values, higherIsBetter }: { values: number[]; higherIsBetter: boolean }) {
  if (values.length < 2) return <Minus className="h-3 w-3 text-white/30" />;
  const delta = values[values.length - 1] - values[values.length - 2];
  const improving = higherIsBetter ? delta > 0 : delta < 0;
  const neutral = Math.abs(delta) < 1e-6;
  if (neutral) return <Minus className="h-3 w-3 text-white/30" />;
  return improving
    ? <TrendingUp className="h-3 w-3 text-emerald-400" />
    : <TrendingDown className="h-3 w-3 text-rose-400" />;
}

/** Plain-English description of what the agent is currently doing */
function AgentPhaseDescription({
  epsilon,
  episode,
  isFinetuned,
  scenario,
}: {
  epsilon: number;
  episode: number;
  isFinetuned?: boolean;
  scenario?: string | null;
}) {
  if (episode === 0) return null;

  let phase: string;
  let desc: string;
  let color: string;

  if (isFinetuned) {
    if (epsilon > 0.18) {
      phase = "Scenario Adaptation";
      desc = `Exploring alternative phase actions on ${scenario ? scenario.replace(/_/g, " ") : "target scenario"} at 10x reduced LR`;
      color = "text-amber-300";
    } else if (epsilon > 0.08) {
      phase = "Policy Specialization";
      desc = `Blending pre-trained traffic heuristics with specialized ${scenario ? scenario.replace(/_/g, " ") : "scenario"} actions`;
      color = "text-orange-300";
    } else {
      phase = "Specialized Exploitation";
      desc = `Executing fine-tuned specialized policy on ${scenario ? scenario.replace(/_/g, " ") : "target distribution"}`;
      color = "text-emerald-300";
    }
  } else if (epsilon > 0.7) {
    phase = "Exploring";
    desc = "Taking mostly random actions to learn what's possible";
    color = "text-amber-300";
  } else if (epsilon > 0.3) {
    phase = "Learning";
    desc = "Mixing exploration with learned behaviour";
    color = "text-sky-300";
  } else if (epsilon > 0.1) {
    phase = "Refining";
    desc = "Mostly using learned policy, fine-tuning edge cases";
    color = "text-violet-300";
  } else {
    phase = "Exploiting";
    desc = "Near-fully relying on the trained policy";
    color = "text-emerald-300";
  }

  return (
    <div className="rounded-md border border-white/5 bg-white/3 px-2.5 py-2 space-y-0.5">
      <div className="flex items-center gap-1.5">
        <span className={`text-[10px] font-semibold uppercase tracking-wider ${color}`}>{phase}</span>
        <span className="text-[9px] text-white/30">ε={epsilon.toFixed(3)}</span>
      </div>
      <p className="text-[10px] text-white/50">{desc}</p>
    </div>
  );
}

function StatCard({
  icon,
  label,
  hint,
  value,
  color,
  sparkValues,
  sparkColor,
  higherIsBetter,
}: {
  icon: React.ReactNode;
  label: string;
  hint: string;
  value: string;
  color: string;
  sparkValues: number[];
  sparkColor: string;
  higherIsBetter: boolean;
}) {
  return (
    <div className="rounded-md border border-white/5 bg-white/3 px-2.5 py-2 space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          {icon}
          <span className="text-[9px] uppercase tracking-wider text-white/40">{label}</span>
        </div>
        <Trend values={sparkValues} higherIsBetter={higherIsBetter} />
      </div>
      <div className={`text-base font-bold leading-none ${color}`}>{value}</div>
      <p className="text-[9px] text-white/30 leading-tight">{hint}</p>
      <div className="h-8">
        <MiniSparkline values={sparkValues} color={sparkColor} height={32} />
      </div>
    </div>
  );
}

export default function TrainingControls({ sendCommand, simulationId }: TrainingControlsProps) {
  const isTraining = useSimulationStore((s) => s.isTraining);
  const trainingMetrics = useSimulationStore((s) => s.trainingMetrics);
  const setTraining = useSimulationStore((s) => s.setTraining);
  const queryClient = useQueryClient();

  const [showConfig, setShowConfig] = useState(false);
  const [trainingMode, setTrainingMode] = useState<"fresh" | "resume" | "finetune">("fresh");
  const [numEpisodes, setNumEpisodes] = useState(500);
  const [additionalEpisodes, setAdditionalEpisodes] = useState(500);
  const [resumeModelId, setResumeModelId] = useState<string>("");
  const [finetuneModelId, setFinetuneModelId] = useState<string>("");
  const [finetuneEpisodes, setFinetuneEpisodes] = useState(100);
  const [finetuneScenario, setFinetuneScenario] = useState<string>("rush_hour");
  const [finetuneLr, setFinetuneLr] = useState<number>(0.0001);
  const [finetuneEpsilon, setFinetuneEpsilon] = useState<number>(0.25);

  // Manual custom profile parameters
  const [customName, setCustomName] = useState("Custom Corridor");
  const [customDirWeights, setCustomDirWeights] = useState({
    north: 1.5,
    south: 1.5,
    east: 0.5,
    west: 0.5,
  });
  const [customTurnProbs, setCustomTurnProbs] = useState({
    straight: 50,
    left: 30,
    right: 20,
  });
  const [customBaseLambda, setCustomBaseLambda] = useState(0.8);
  const [customLambdaMult, setCustomLambdaMult] = useState(1.1);

  const [targetEpisodes, setTargetEpisodes] = useState<number | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [isLoadingModel, setIsLoadingModel] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadSuccess, setLoadSuccess] = useState(false);

  const startTimeRef = useRef<number | null>(null);
  const [epsPerMin, setEpsPerMin] = useState(0);

  const latest: TrainingMetric | null = trainingMetrics[trainingMetrics.length - 1] ?? null;
  const currentEpisode = latest?.episode ?? 0;
  const recentMetrics = useMemo(() => trainingMetrics.slice(-40), [trainingMetrics]);

  const isResumedRun = latest?.is_resumed ?? (latest?.start_episode ? latest.start_episode > 0 : false);
  const isFinetuneRun = latest?.is_finetuned ?? false;
  const sessionStartEp = latest?.start_episode ?? 0;
  const effectiveTargetEpisodes = latest?.target_episodes ?? targetEpisodes;

  const recentEpisodesRef = useRef<{ ep: number; t: number }[]>([]);

  // Speed tracking with smooth rolling window
  useEffect(() => {
    if (!isTraining) {
      recentEpisodesRef.current = [];
      startTimeRef.current = null;
      setTimeout(() => setEpsPerMin(0), 0);
      return;
    }
    if (startTimeRef.current === null) startTimeRef.current = Date.now();
    if (currentEpisode > 0) {
      const now = Date.now();
      const history = recentEpisodesRef.current;
      if (history.length === 0 || history[history.length - 1].ep !== currentEpisode) {
        history.push({ ep: currentEpisode, t: now });
      }
      if (history.length > 10) history.shift();

      if (history.length >= 2) {
        const oldest = history[0];
        const deltaEps = currentEpisode - oldest.ep;
        const deltaMins = (now - oldest.t) / 60_000;
        if (deltaEps > 0 && deltaMins > 0) {
          setEpsPerMin(deltaEps / deltaMins);
        }
      } else if (startTimeRef.current) {
        const sessionCompleted = isResumedRun ? Math.max(0, currentEpisode - sessionStartEp) : currentEpisode;
        if (sessionCompleted > 0) {
          const mins = (now - startTimeRef.current) / 60_000;
          if (mins > 0) setEpsPerMin(sessionCompleted / mins);
        }
      }
    }
  }, [currentEpisode, isTraining, isResumedRun, sessionStartEp]);

  // Auto-refresh model list when a checkpoint is saved
  useEffect(() => {
    const raw = trainingMetrics[trainingMetrics.length - 1] as unknown as Record<string, unknown> | null;
    if (raw && (raw as Record<string, unknown>).type === "checkpoint_saved") {
      queryClient.invalidateQueries({ queryKey: ["models"] });
    }
  }, [trainingMetrics, queryClient]);

  const progress = useMemo(() => {
    if (!effectiveTargetEpisodes) return 0;
    if (isResumedRun && effectiveTargetEpisodes > sessionStartEp) {
      return Math.min(1, Math.max(0, (currentEpisode - sessionStartEp) / (effectiveTargetEpisodes - sessionStartEp)));
    }
    return Math.min(1, currentEpisode / effectiveTargetEpisodes);
  }, [currentEpisode, effectiveTargetEpisodes, isResumedRun, sessionStartEp]);

  const eta = useMemo(() => {
    if (!isTraining || !effectiveTargetEpisodes || epsPerMin === 0) return null;
    const remaining = Math.max(0, effectiveTargetEpisodes - currentEpisode);
    const mins = remaining / epsPerMin;
    return mins < 1 ? "<1 min" : `~${Math.round(mins)} min`;
  }, [isTraining, effectiveTargetEpisodes, currentEpisode, epsPerMin]);

  const rewardHistory = recentMetrics.map((m) => m.total_reward);
  const waitHistory = recentMetrics.map((m) => m.avg_wait_time);
  const epsilonHistory = recentMetrics.map((m) => m.epsilon);
  const lossHistory = recentMetrics.map((m) => m.loss ?? 0);

  const { data: models = [], isLoading: modelsLoading } = useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const { httpUrl: baseUrl } = getFastApiUrls();
      if (!baseUrl) return [] as RLModel[];
      const res = await fetch(`${baseUrl}/training/models`);
      if (!res.ok) return [] as RLModel[];
      const payload = (await res.json()) as { models?: RLModel[] };
      return payload.models ?? [];
    },
    // Refresh every 30s so newly saved checkpoints appear without manual reload
    refetchInterval: 30_000,
  });

  // Calculate resume metadata from selected model
  const selectedResumeModel = useMemo(() => {
    return models.find((m) => m.id === resumeModelId) ?? null;
  }, [models, resumeModelId]);

  const resumeBaseEpisode = useMemo(() => {
    if (!selectedResumeModel) return 0;
    const v = parseInt(selectedResumeModel.version, 10);
    if (!isNaN(v) && v > 0) return v;
    if (selectedResumeModel.episodes && selectedResumeModel.episodes > 0) {
      return selectedResumeModel.episodes;
    }
    const match = selectedResumeModel.id.match(/:(\d+)$/);
    if (match) return parseInt(match[1], 10);
    return 0;
  }, [selectedResumeModel]);

  const estimatedResumeEpsilon = useMemo(() => {
    if (!resumeBaseEpisode) return 0.05;
    return Math.max(0.05, 1.0 * Math.pow(0.994, resumeBaseEpisode));
  }, [resumeBaseEpisode]);

  // Calculate fine-tune metadata from selected base model
  const selectedFinetuneModel = useMemo(() => {
    return models.find((m) => m.id === finetuneModelId) ?? null;
  }, [models, finetuneModelId]);

  const finetuneBaseEpisode = useMemo(() => {
    if (!selectedFinetuneModel) return 0;
    const v = parseInt(selectedFinetuneModel.version, 10);
    if (!isNaN(v) && v > 0) return v;
    if (selectedFinetuneModel.episodes && selectedFinetuneModel.episodes > 0) {
      return selectedFinetuneModel.episodes;
    }
    const match = selectedFinetuneModel.id.match(/:(\d+)$/);
    if (match) return parseInt(match[1], 10);
    return 0;
  }, [selectedFinetuneModel]);

  const startTraining = () => {
    if (trainingMode === "finetune") {
      if (!finetuneModelId || finetuneModelId === "__none") {
        setLoadError("Please select a base checkpoint to fine-tune.");
        return;
      }
      setTargetEpisodes(finetuneEpisodes);
      setTraining(true);
      startTimeRef.current = Date.now();

      const isCustom = finetuneScenario === "custom";
      const customProfilePayload = isCustom
        ? {
            id: "custom",
            name: customName.trim() || "Custom Corridor",
            description: `Custom traffic (${customTurnProbs.straight}% straight, ${customTurnProbs.left}% left, ${customTurnProbs.right}% right).`,
            directional_weights: customDirWeights,
            turn_probs: [
              customTurnProbs.straight / 100,
              customTurnProbs.left / 100,
              customTurnProbs.right / 100,
            ],
            base_lambda: customBaseLambda,
            lambda_multiplier: customLambdaMult,
          }
        : undefined;

      sendCommand({
        command: "start_training",
        mode: "finetune",
        num_episodes: finetuneEpisodes,
        resume_model_id: finetuneModelId,
        resume_episode: finetuneBaseEpisode,
        finetune_scenario: finetuneScenario,
        finetune_lr: finetuneLr,
        finetune_epsilon: finetuneEpsilon,
        custom_profile: customProfilePayload,
        simulation_id: simulationId ?? undefined,
      });
      setShowConfig(false);
    } else if (trainingMode === "resume") {
      if (!resumeModelId || resumeModelId === "__none") {
        setLoadError("Please select a checkpoint to resume training.");
        return;
      }
      const totalTarget = resumeBaseEpisode + additionalEpisodes;
      setTargetEpisodes(totalTarget);
      setTraining(true);
      startTimeRef.current = Date.now();
      sendCommand({
        command: "start_training",
        mode: "resume",
        num_episodes: additionalEpisodes,
        resume_model_id: resumeModelId,
        resume_episode: resumeBaseEpisode,
        simulation_id: simulationId ?? undefined,
      });
      setShowConfig(false);
    } else {
      setTargetEpisodes(numEpisodes);
      setTraining(true);
      startTimeRef.current = Date.now();
      sendCommand({
        command: "start_training",
        mode: "fresh",
        num_episodes: numEpisodes,
        simulation_id: simulationId ?? undefined,
      });
      setShowConfig(false);
    }
  };

  const stopTraining = () => {
    setTraining(false);
    sendCommand({ command: "stop_training" });
  };

  const loadModel = async (modelId: string) => {
    if (!modelId || modelId === "__none") return;
    const { httpUrl: baseUrl } = getFastApiUrls();
    if (!baseUrl) { setLoadError("FastAPI URL not configured."); return; }
    setIsLoadingModel(true);
    setLoadError(null);
    setLoadSuccess(false);
    try {
      const res = await fetch(`${baseUrl}/training/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId }),
      });
      if (res.ok) {
        setLoadSuccess(true);
        setTimeout(() => setLoadSuccess(false), 3000);
      } else {
        const p = await res.json().catch(() => null) as { detail?: string } | null;
        setLoadError(p?.detail ?? "Unable to load model.");
      }
    } catch {
      setLoadError("Unable to reach the training server.");
    } finally {
      setIsLoadingModel(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <AIStatusBadge isTraining={isTraining} currentEpisode={currentEpisode} targetEpisodes={effectiveTargetEpisodes} />
        {isTraining ? (
          <Button size="sm" variant="outline"
            className="border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
            onClick={stopTraining}>
            Stop Training
          </Button>
        ) : (
          <Button size="sm" onClick={() => setShowConfig((p) => !p)}
            className="bg-blue-600 hover:bg-blue-700 text-white">
            {showConfig ? "Close Config" : "Train Agent"}
          </Button>
        )}
      </div>

      {/* Config */}
      <AnimatePresence>
        {showConfig && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4 space-y-3">
              {/* Mode Tabs */}
              <div className="grid grid-cols-3 p-0.5 rounded-lg bg-black/40 border border-white/10 text-xs">
                <button
                  type="button"
                  onClick={() => setTrainingMode("fresh")}
                  className={`flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-all ${
                    trainingMode === "fresh"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Start Fresh
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTrainingMode("resume");
                    if (!resumeModelId && models.length > 0) {
                      setResumeModelId(models[0].id);
                    }
                  }}
                  className={`flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-all ${
                    trainingMode === "resume"
                      ? "bg-violet-600 text-white shadow-sm"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Resume
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTrainingMode("finetune");
                    if (!finetuneModelId && models.length > 0) {
                      setFinetuneModelId(models[0].id);
                    }
                  }}
                  className={`flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-all ${
                    trainingMode === "finetune"
                      ? "bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-sm font-semibold"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Zap className="h-3.5 w-3.5 text-amber-300" />
                  Fine-Tune
                </button>
              </div>

              {trainingMode === "fresh" ? (
                /* Fresh Training Form */
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs text-white/80 font-medium">Number of Episodes</label>
                      <span className="text-[10px] text-white/40">Default: 500</span>
                    </div>
                    <p className="text-[10px] text-white/40 mb-2 leading-relaxed">
                      Trains a new model starting from Episode 1. Uses teacher warm-start (greedy transitions) and decays exploration from ε=1.0 down to 0.05.
                    </p>
                    <div className="flex items-center gap-1.5 mb-2">
                      {[100, 300, 500, 1000].map((preset) => (
                        <button
                          key={preset}
                          type="button"
                          onClick={() => setNumEpisodes(preset)}
                          className={`px-2 py-1 rounded text-xs transition-colors ${
                            numEpisodes === preset
                              ? "bg-blue-500/20 text-blue-300 border border-blue-500/40"
                              : "bg-white/5 text-white/60 hover:bg-white/10 border border-white/5"
                          }`}
                        >
                          {preset} eps
                        </button>
                      ))}
                    </div>
                    <input
                      type="number"
                      min={10}
                      max={3000}
                      step={50}
                      className="w-full rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                      value={numEpisodes}
                      onChange={(e) => setNumEpisodes(Math.max(1, Number(e.target.value)))}
                    />
                  </div>

                  <div className="flex gap-2 pt-1">
                    <Button size="sm" onClick={startTraining} className="bg-blue-600 hover:bg-blue-700 text-white flex-1">
                      Start Fresh Training ({numEpisodes} eps)
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowConfig(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : trainingMode === "resume" ? (
                /* Resume Checkpoint Form */
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-white/80 font-medium mb-1">
                      Select Checkpoint to Resume
                    </label>
                    <p className="text-[10px] text-white/40 mb-2 leading-relaxed">
                      Pick any existing model checkpoint. Resumes training with all learned weights, optimizer state, and continued exploration rate intact.
                    </p>
                    {models.length === 0 ? (
                      <div className="rounded-md border border-dashed border-white/15 bg-white/5 p-3 text-center">
                        <p className="text-xs text-white/50 mb-2">No existing models available to resume.</p>
                        <Button size="sm" variant="outline" onClick={() => setTrainingMode("fresh")} className="text-xs">
                          Switch to Start Fresh
                        </Button>
                      </div>
                    ) : (
                      <Select
                        value={resumeModelId}
                        onValueChange={(v) => setResumeModelId(v)}
                      >
                        <SelectTrigger className="w-full border-white/15 bg-black/40 text-white/90 hover:bg-black/50 transition-colors">
                          <SelectValue placeholder="Choose a checkpoint to resume…" />
                        </SelectTrigger>
                        <SelectContent position="popper" className="z-[100] max-h-[220px] overflow-y-auto" sideOffset={5}>
                          {models.map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.name} — ep {m.version}
                              {m.source === "remote" ? " ☁ Supabase Cloud" : " 💾 Local"}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

                  {selectedResumeModel && (
                    <>
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-xs text-white/80 font-medium">Additional Episodes to Train</label>
                          <span className="text-[10px] text-violet-300 font-mono">+{additionalEpisodes} eps</span>
                        </div>
                        <div className="flex items-center gap-1.5 mb-2">
                          {[100, 300, 500, 1000].map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => setAdditionalEpisodes(preset)}
                              className={`px-2 py-1 rounded text-xs transition-colors ${
                                additionalEpisodes === preset
                                  ? "bg-violet-500/20 text-violet-300 border border-violet-500/40"
                                  : "bg-white/5 text-white/60 hover:bg-white/10 border border-white/5"
                              }`}
                            >
                              +{preset}
                            </button>
                          ))}
                        </div>
                        <input
                          type="number"
                          min={10}
                          max={2000}
                          step={50}
                          className="w-full rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                          value={additionalEpisodes}
                          onChange={(e) => setAdditionalEpisodes(Math.max(1, Number(e.target.value)))}
                        />
                      </div>

                      {/* Trajectory & Continuity Card */}
                      <div className="rounded-lg border border-violet-500/25 bg-violet-950/20 p-3 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/50">Trajectory Plan:</span>
                          <span className="font-semibold text-violet-200">
                            Ep {resumeBaseEpisode + 1} → {resumeBaseEpisode + additionalEpisodes}
                            <span className="text-white/40 ml-1 font-normal">(+{additionalEpisodes} eps)</span>
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/50">Exploration Continuity:</span>
                          <span className="font-mono text-amber-300 font-medium">
                            ε ≈ {estimatedResumeEpsilon.toFixed(3)}
                            <span className="text-white/35 font-sans ml-1 text-[10px]">
                              {estimatedResumeEpsilon <= 0.06 ? "(Exploiting policy)" : "(Refining policy)"}
                            </span>
                          </span>
                        </div>
                        <div className="pt-1.5 border-t border-white/5 flex flex-wrap gap-1.5 text-[9px]">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                            ✓ Weights & Optimizer Preserved
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-300">
                            ✓ Warmup Skipped (Starts Instantly)
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-violet-300">
                            ✓ Updates Same Model
                          </span>
                        </div>
                      </div>

                      <div className="flex gap-2 pt-1">
                        <Button
                          size="sm"
                          onClick={startTraining}
                          className="bg-violet-600 hover:bg-violet-700 text-white flex-1"
                        >
                          <RotateCcw className="h-3.5 w-3.5 mr-1" />
                          Resume Training (Ep {resumeBaseEpisode + 1} → {resumeBaseEpisode + additionalEpisodes})
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowConfig(false)}>
                          Cancel
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                /* Fine-Tuning Form */
                <div className="space-y-3.5">
                  <div>
                    <label className="block text-xs text-white/80 font-medium mb-1">
                      1. Select Base Model Checkpoint
                    </label>
                    <p className="text-[10px] text-white/40 mb-2 leading-relaxed">
                      Select a pre-trained model to adapt. Learned representations will be retained while the model specializes in the selected scenario.
                    </p>
                    {models.length === 0 ? (
                      <div className="rounded-md border border-dashed border-white/15 bg-white/5 p-3 text-center">
                        <p className="text-xs text-white/50 mb-2">No models available to fine-tune.</p>
                        <Button size="sm" variant="outline" onClick={() => setTrainingMode("fresh")} className="text-xs">
                          Start Fresh Training First
                        </Button>
                      </div>
                    ) : (
                      <Select
                        value={finetuneModelId}
                        onValueChange={(v) => setFinetuneModelId(v)}
                      >
                        <SelectTrigger className="w-full border-amber-500/20 bg-black/40 text-white/90 hover:bg-black/50 transition-colors">
                          <SelectValue placeholder="Choose base model to fine-tune…" />
                        </SelectTrigger>
                        <SelectContent position="popper" className="z-[100] max-h-[220px] overflow-y-auto" sideOffset={5}>
                          {models.map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.name} — ep {m.version}
                              {m.source === "remote" ? " ☁ Supabase Cloud" : " 💾 Local"}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

                  {selectedFinetuneModel && (
                    <>
                      {/* Scenario Presets Selector */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs text-white/80 font-medium">
                            2. Target Scenario Distribution
                          </label>
                          <span className="text-[10px] text-amber-400/80 font-medium">Specialized Regime</span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {SCENARIO_PRESETS.map((preset) => {
                            const isSelected = finetuneScenario === preset.id;
                            return (
                              <button
                                key={preset.id}
                                type="button"
                                onClick={() => {
                                  setFinetuneScenario(preset.id);
                                  if (preset.id === "custom") {
                                    setCustomName("Custom Corridor");
                                  } else {
                                    setCustomName(preset.name);
                                    setCustomDirWeights({ ...preset.defaultDirWeights });
                                    setCustomTurnProbs({ ...preset.defaultTurnProbs });
                                    setCustomBaseLambda(preset.defaultLambda);
                                    setCustomLambdaMult(preset.defaultMult);
                                  }
                                }}
                                className={`text-left p-2.5 rounded-lg border transition-all relative overflow-hidden ${
                                  isSelected
                                    ? "border-amber-500 bg-amber-950/40 shadow-sm shadow-amber-500/10"
                                    : "border-white/10 bg-black/30 hover:border-white/20 hover:bg-black/40"
                                } ${preset.id === "custom" ? "col-span-2 sm:col-span-1" : ""}`}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                                    <span>{preset.icon}</span>
                                    {preset.name}
                                  </span>
                                  <span className={`text-[9px] px-1 py-0.2 rounded border ${
                                    isSelected ? "bg-amber-500/20 text-amber-300 border-amber-500/40" : "bg-white/5 text-white/50 border-white/10"
                                  }`}>
                                    {preset.tag}
                                  </span>
                                </div>
                                <p className="text-[10px] text-white/50 leading-relaxed line-clamp-2">
                                  {preset.description}
                                </p>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Manual Customization Panel (shown when Custom Parameters selected) */}
                      {finetuneScenario === "custom" && (
                        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3.5 space-y-3 shadow-inner">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-200">
                              <Sliders className="h-3.5 w-3.5 text-amber-400" />
                              Manual Parameter Customizer
                            </div>
                            <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
                              User Defined Geometry
                            </span>
                          </div>

                          {/* Quick baseline prefill buttons */}
                          <div className="flex flex-wrap items-center gap-1 text-[10px] bg-black/30 p-2 rounded-lg border border-white/5">
                            <span className="text-white/40 mr-1 text-[10px]">Start from preset:</span>
                            {SCENARIO_PRESETS.filter((p) => p.id !== "custom").map((p) => (
                              <button
                                key={p.id}
                                type="button"
                                onClick={() => {
                                  setCustomName(p.name);
                                  setCustomDirWeights({ ...p.defaultDirWeights });
                                  setCustomTurnProbs({ ...p.defaultTurnProbs });
                                  setCustomBaseLambda(p.defaultLambda);
                                  setCustomLambdaMult(p.defaultMult);
                                }}
                                className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 text-white/70 hover:text-white border border-white/10 transition-colors text-[10px] flex items-center gap-1"
                              >
                                <span>{p.icon}</span>
                                <span>{p.name}</span>
                              </button>
                            ))}
                          </div>

                          {/* Custom Scenario Name */}
                          <div>
                            <label className="text-[10px] text-white/70 block mb-1 font-medium">
                              Custom Scenario Name
                            </label>
                            <input
                              type="text"
                              value={customName}
                              onChange={(e) => setCustomName(e.target.value)}
                              placeholder="e.g. Airport Highway Surge, Stadium Exit"
                              className="w-full rounded-md border border-white/10 bg-black/40 px-2.5 py-1.5 text-xs text-white placeholder:text-white/30 focus:outline-none focus:border-amber-500"
                            />
                          </div>

                          {/* Directional Traffic Weights */}
                          <div>
                            <div className="flex items-center justify-between mb-1.5">
                              <label className="text-[10px] text-white/70 font-medium">
                                Directional Flow Multipliers
                              </label>
                              <span className="text-[9px] text-white/40">Relative arrival volume</span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              {(["north", "south", "east", "west"] as const).map((dir) => {
                                const totalW =
                                  customDirWeights.north +
                                    customDirWeights.south +
                                    customDirWeights.east +
                                    customDirWeights.west || 1;
                                const pct = Math.round((customDirWeights[dir] / totalW) * 100);
                                return (
                                  <div
                                    key={dir}
                                    className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1"
                                  >
                                    <div className="flex items-center justify-between text-[10px]">
                                      <span className="capitalize font-semibold text-white/80">{dir}</span>
                                      <span className="font-mono text-amber-300 font-bold">
                                        {customDirWeights[dir].toFixed(1)}x
                                      </span>
                                    </div>
                                    <input
                                      type="range"
                                      min={0.1}
                                      max={3.0}
                                      step={0.1}
                                      value={customDirWeights[dir]}
                                      onChange={(e) => {
                                        const val = parseFloat(e.target.value);
                                        setCustomDirWeights((prev) => ({ ...prev, [dir]: val }));
                                      }}
                                      className="w-full accent-amber-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                                    />
                                    <div className="text-[9px] text-white/40 text-right font-mono">
                                      {pct}% flow
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          {/* Turning Movement Distribution */}
                          <div>
                            <div className="flex items-center justify-between mb-1.5">
                              <label className="text-[10px] text-white/70 font-medium">
                                Turning Probabilities (%)
                              </label>
                              <span className="text-[10px] text-amber-300 font-mono">
                                Total: {customTurnProbs.straight + customTurnProbs.left + customTurnProbs.right}%
                              </span>
                            </div>

                            {/* Visual stacked distribution bar */}
                            <div className="h-2 rounded-full overflow-hidden flex w-full mb-2 bg-neutral-800 border border-white/10">
                              <div
                                style={{
                                  width: `${Math.max(
                                    0,
                                    (customTurnProbs.straight /
                                      (customTurnProbs.straight +
                                        customTurnProbs.left +
                                        customTurnProbs.right || 1)) *
                                      100
                                  )}%`,
                                }}
                                className="bg-emerald-500 h-full transition-all"
                              />
                              <div
                                style={{
                                  width: `${Math.max(
                                    0,
                                    (customTurnProbs.left /
                                      (customTurnProbs.straight +
                                        customTurnProbs.left +
                                        customTurnProbs.right || 1)) *
                                      100
                                  )}%`,
                                }}
                                className="bg-amber-500 h-full transition-all"
                              />
                              <div
                                style={{
                                  width: `${Math.max(
                                    0,
                                    (customTurnProbs.right /
                                      (customTurnProbs.straight +
                                        customTurnProbs.left +
                                        customTurnProbs.right || 1)) *
                                      100
                                  )}%`,
                                }}
                                className="bg-sky-500 h-full transition-all"
                              />
                            </div>

                            <div className="grid grid-cols-3 gap-2">
                              <div className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="text-emerald-300 font-medium">Straight</span>
                                  <span className="font-mono text-white/80 font-bold">{customTurnProbs.straight}%</span>
                                </div>
                                <input
                                  type="range"
                                  min={0}
                                  max={100}
                                  step={5}
                                  value={customTurnProbs.straight}
                                  onChange={(e) => {
                                    const v = parseInt(e.target.value) || 0;
                                    setCustomTurnProbs((p) => ({ ...p, straight: v }));
                                  }}
                                  className="w-full accent-emerald-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                                />
                              </div>
                              <div className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="text-amber-300 font-medium">Left Turn</span>
                                  <span className="font-mono text-white/80 font-bold">{customTurnProbs.left}%</span>
                                </div>
                                <input
                                  type="range"
                                  min={0}
                                  max={100}
                                  step={5}
                                  value={customTurnProbs.left}
                                  onChange={(e) => {
                                    const v = parseInt(e.target.value) || 0;
                                    setCustomTurnProbs((p) => ({ ...p, left: v }));
                                  }}
                                  className="w-full accent-amber-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                                />
                              </div>
                              <div className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1">
                                <div className="flex items-center justify-between text-[10px]">
                                  <span className="text-sky-300 font-medium">Right Turn</span>
                                  <span className="font-mono text-white/80 font-bold">{customTurnProbs.right}%</span>
                                </div>
                                <input
                                  type="range"
                                  min={0}
                                  max={100}
                                  step={5}
                                  value={customTurnProbs.right}
                                  onChange={(e) => {
                                    const v = parseInt(e.target.value) || 0;
                                    setCustomTurnProbs((p) => ({ ...p, right: v }));
                                  }}
                                  className="w-full accent-sky-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                                />
                              </div>
                            </div>
                          </div>

                          {/* Arrival Rates & Intensity */}
                          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/5">
                            <div className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1">
                              <div className="flex items-center justify-between text-[10px]">
                                <span className="text-white/70">Base Arrival Rate (λ)</span>
                                <span className="font-mono text-amber-300 font-bold">
                                  {customBaseLambda.toFixed(2)} veh/s
                                </span>
                              </div>
                              <input
                                type="range"
                                min={0.2}
                                max={2.0}
                                step={0.05}
                                value={customBaseLambda}
                                onChange={(e) => setCustomBaseLambda(parseFloat(e.target.value))}
                                className="w-full accent-amber-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                              />
                            </div>
                            <div className="p-2 rounded-lg bg-black/40 border border-white/5 space-y-1">
                              <div className="flex items-center justify-between text-[10px]">
                                <span className="text-white/70">Surge Multiplier</span>
                                <span className="font-mono text-amber-300 font-bold">
                                  {customLambdaMult.toFixed(2)}x
                                </span>
                              </div>
                              <input
                                type="range"
                                min={0.8}
                                max={2.0}
                                step={0.05}
                                value={customLambdaMult}
                                onChange={(e) => setCustomLambdaMult(parseFloat(e.target.value))}
                                className="w-full accent-amber-500 h-1.5 bg-neutral-800 rounded-lg cursor-pointer"
                              />
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Fine-Tuning Duration */}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-xs text-white/80 font-medium">3. Fine-Tuning Duration</label>
                          <span className="text-[10px] text-amber-300 font-mono">{finetuneEpisodes} episodes</span>
                        </div>
                        <p className="text-[10px] text-white/40 mb-2 leading-relaxed">
                          Fine-tuning adapts rapidly (typically 50 to 150 episodes). Checkpoints are saved every 25 episodes.
                        </p>
                        <div className="flex items-center gap-1.5 mb-2">
                          {[50, 100, 150, 200].map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => setFinetuneEpisodes(preset)}
                              className={`px-2 py-1 rounded text-xs transition-colors ${
                                finetuneEpisodes === preset
                                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                  : "bg-white/5 text-white/60 hover:bg-white/10 border border-white/5"
                              }`}
                            >
                              {preset} eps
                            </button>
                          ))}
                        </div>
                        <input
                          type="number"
                          min={20}
                          max={500}
                          step={25}
                          className="w-full rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                          value={finetuneEpisodes}
                          onChange={(e) => setFinetuneEpisodes(Math.max(10, Number(e.target.value)))}
                        />
                      </div>

                      {/* Hyperparameter Controls */}
                      <div className="grid grid-cols-2 gap-2 pt-1">
                        <div className="p-2.5 rounded-lg border border-white/10 bg-black/30 space-y-1">
                          <div className="flex items-center justify-between">
                            <label className="text-[10px] text-white/70 font-medium">Learning Rate (α)</label>
                            <span className="text-[10px] text-amber-300 font-mono font-bold">
                              {finetuneLr.toExponential(1)}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 pt-0.5">
                            {[0.00005, 0.0001, 0.0002].map((lr) => (
                              <button
                                key={lr}
                                type="button"
                                onClick={() => setFinetuneLr(lr)}
                                className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                                  finetuneLr === lr
                                    ? "bg-amber-500/30 text-amber-200 border border-amber-500/50"
                                    : "bg-white/5 text-white/50 hover:bg-white/10"
                                }`}
                              >
                                {lr.toExponential(0)}
                              </button>
                            ))}
                          </div>
                          <p className="text-[9px] text-white/40 leading-snug">
                            Conservative rate prevents catastrophic forgetting.
                          </p>
                        </div>
                        <div className="p-2.5 rounded-lg border border-white/10 bg-black/30 space-y-1">
                          <div className="flex items-center justify-between">
                            <label className="text-[10px] text-white/70 font-medium">Exploration Reset (ε)</label>
                            <span className="text-[10px] text-amber-300 font-mono font-bold">
                              {finetuneEpsilon.toFixed(2)} → 0.05
                            </span>
                          </div>
                          <div className="flex items-center gap-1 pt-0.5">
                            {[0.15, 0.25, 0.35].map((eps) => (
                              <button
                                key={eps}
                                type="button"
                                onClick={() => setFinetuneEpsilon(eps)}
                                className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                                  finetuneEpsilon === eps
                                    ? "bg-amber-500/30 text-amber-200 border border-amber-500/50"
                                    : "bg-white/5 text-white/50 hover:bg-white/10"
                                }`}
                              >
                                {eps.toFixed(2)}
                              </button>
                            ))}
                          </div>
                          <p className="text-[9px] text-white/40 leading-snug">
                            Exploration reset discovers new scenario actions.
                          </p>
                        </div>
                      </div>

                      {/* Safety & Fork Lineage Card */}
                      <div className="rounded-lg border border-amber-500/25 bg-amber-950/20 p-3 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/50">Branched Target:</span>
                          <span className="font-semibold text-amber-200 font-mono text-[11px]">
                            {selectedFinetuneModel.id.slice(0, 10)}...-ft-
                            {finetuneScenario === "custom"
                              ? customName.toLowerCase().trim().replace(/[\s\-]+/g, "_") || "custom"
                              : finetuneScenario}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/50">Base Model Lineage:</span>
                          <span className="text-white/70 text-[11px]">
                            ep {finetuneBaseEpisode} weights preserved untouched
                          </span>
                        </div>
                        <div className="pt-1.5 border-t border-white/5 flex flex-wrap gap-1.5 text-[9px]">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                            ✓ Original Checkpoint Safe
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300">
                            ✓ Replay Buffer Primed on Scenario
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-300">
                            ✓ Benchmark Showdown Ready
                          </span>
                        </div>
                      </div>

                      <div className="flex gap-2 pt-1">
                        <Button
                          size="sm"
                          onClick={startTraining}
                          className="bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-white font-semibold flex-1 shadow-md shadow-amber-600/20"
                        >
                          <Zap className="h-3.5 w-3.5 mr-1 text-amber-200" />
                          Start Fine-Tuning ({finetuneEpisodes} eps)
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowConfig(false)}>
                          Cancel
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Live Training Panel */}
      <AnimatePresence>
        {(isTraining || currentEpisode > 0) && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="rounded-lg border border-white/10 bg-black/30 overflow-hidden">

            {/* Progress bar */}
            <div className="h-1 bg-white/5 w-full">
              <motion.div className="h-1 bg-emerald-400"
                animate={{ width: `${progress * 100}%` }}
                transition={{ ease: "linear", duration: 0.4 }} />
            </div>

            <div className="p-3 space-y-3">

              {/* Episode + speed + ETA */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <Brain className="h-3.5 w-3.5 text-violet-400" />
                  <span className="text-xs font-medium text-white">
                    Episode <span className="text-violet-300 font-bold">{currentEpisode}</span>
                    <span className="text-white/35"> / {effectiveTargetEpisodes ?? "—"}</span>
                  </span>
                  {latest?.is_finetuned ? (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                      <Zap className="h-2.5 w-2.5 text-amber-400" />
                      Fine-Tuning: {latest.finetune_scenario ? latest.finetune_scenario.replace(/_/g, " ") : "Specialized"}
                    </span>
                  ) : isResumedRun && sessionStartEp > 0 ? (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30">
                      Resumed from ep {sessionStartEp}
                    </span>
                  ) : null}
                </div>
                <div className="flex items-center gap-3 text-[10px] text-white/40">
                  {epsPerMin > 0 && (
                    <span className="flex items-center gap-1">
                      <Zap className="h-3 w-3 text-amber-400" />
                      {epsPerMin.toFixed(1)} ep/min
                    </span>
                  )}
                  {eta && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-sky-400" />
                      {eta}
                    </span>
                  )}
                </div>
              </div>

              {/* Agent phase description */}
              {latest && "epsilon" in latest && (
                <AgentPhaseDescription
                  epsilon={latest.epsilon}
                  episode={currentEpisode}
                  isFinetuned={latest.is_finetuned}
                  scenario={latest.finetune_scenario}
                />
              )}

              {/* Stat cards */}
              {latest && "total_reward" in latest && (
                <div className="grid grid-cols-2 gap-2">
                  <StatCard
                    icon={<TrendingUp className="h-3 w-3 text-sky-400" />}
                    label="Reward"
                    hint="Total score this episode. Higher = agent made better decisions."
                    value={latest.total_reward.toFixed(1)}
                    color={latest.total_reward >= 0 ? "text-sky-300" : "text-rose-300"}
                    sparkValues={rewardHistory}
                    sparkColor="#38bdf8"
                    higherIsBetter={true}
                  />
                  <StatCard
                    icon={<Clock className="h-3 w-3 text-orange-400" />}
                    label="Avg Wait"
                    hint="Mean time vehicles spent waiting. Lower = less congestion."
                    value={`${latest.avg_wait_time.toFixed(2)}s`}
                    color="text-orange-300"
                    sparkValues={waitHistory}
                    sparkColor="#fb923c"
                    higherIsBetter={false}
                  />
                  <StatCard
                    icon={<Activity className="h-3 w-3 text-yellow-400" />}
                    label="Exploration ε"
                    hint="Chance of random action. Starts at 1.0, decays to 0.05 as agent learns."
                    value={latest.epsilon.toFixed(3)}
                    color="text-yellow-300"
                    sparkValues={epsilonHistory}
                    sparkColor="#facc15"
                    higherIsBetter={false}
                  />
                  <StatCard
                    icon={<Zap className="h-3 w-3 text-violet-400" />}
                    label="Loss"
                    hint="How wrong the agent's predictions are. Should trend down over time."
                    value={latest.loss != null ? latest.loss.toFixed(4) : "warming up"}
                    color="text-violet-300"
                    sparkValues={lossHistory}
                    sparkColor="#a78bfa"
                    higherIsBetter={false}
                  />
                </div>
              )}

              {/* Throughput */}
              {latest && "throughput" in latest && (
                <div className="flex items-center justify-between rounded-md border border-white/5 bg-white/3 px-2.5 py-2">
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-white/40">Throughput</span>
                    <p className="text-[9px] text-white/25">Vehicles that cleared the intersection</p>
                  </div>
                  <span className="text-sm font-bold text-emerald-300">{latest.throughput}</span>
                </div>
              )}

              {/* Checkpoint notice */}
              {latest?.is_finetuned ? (
                <div className="text-[9px] text-amber-300/70 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-amber-400/60" />
                  Fine-tuned checkpoint saved every 25 episodes and at completion
                </div>
              ) : effectiveTargetEpisodes ? (
                <div className="text-[9px] text-white/25 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-white/20" />
                  Checkpoint saved every 50 episodes and at completion
                </div>
              ) : null}

              {/* Status */}
              {isTraining ? (
                latest?.is_finetuned ? (
                  <div className="flex items-center gap-1.5 text-[10px] text-amber-300">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Fine-Tuning on {latest.finetune_scenario ? latest.finetune_scenario.replace(/_/g, " ").toUpperCase() : "SCENARIO"} (α=1e-4) — policy specializing
                  </div>
                ) : isResumedRun ? (
                  <div className="flex items-center gap-1.5 text-[10px] text-violet-300">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
                    Resumed Training{latest?.steps ? ` — ${latest.steps} steps/ep` : " — continuing policy weights"}
                  </div>
                ) : latest?.buffer_ready === false ? (
                  <div className="flex items-center gap-1.5 text-[10px] text-amber-400/80">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Warming up replay buffer… ({latest?.steps ?? 0} steps)
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/80">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Training{latest?.steps ? ` — ${latest.steps} steps/ep` : " — metrics update after each episode"}
                  </div>
                )
              ) : currentEpisode > 0 ? (
                <div className="flex items-center gap-1.5 text-[10px] text-white/30">
                  <CheckCircle2 className="h-3 w-3" />
                  Complete — {currentEpisode} episode{currentEpisode !== 1 ? "s" : ""} {latest?.is_finetuned ? "fine-tuned" : "trained"}
                  {isResumedRun && sessionStartEp > 0 ? ` (+${Math.max(0, currentEpisode - sessionStartEp)} this run)` : ""}
                </div>
              ) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Load Model */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/50">Load Trained Model</span>
          {modelsLoading && <Loader2 className="h-3 w-3 animate-spin text-white/30" />}
        </div>
        <p className="text-[10px] text-white/25">
          Load a saved checkpoint to run the AI in simulation mode.
        </p>
        <Select value={selectedModelId}
          onValueChange={(v) => { setSelectedModelId(v); void loadModel(v); }}>
          <SelectTrigger className="w-full border-white/15 bg-black/40 text-white/70 hover:bg-black/50 transition-colors">
            <SelectValue placeholder="Select saved model…" />
          </SelectTrigger>
          <SelectContent position="popper" className="z-[100] max-h-[200px] overflow-y-auto" sideOffset={5}>
            {models.length === 0 ? (
              <SelectItem value="__none" disabled>No trained models yet</SelectItem>
            ) : (
              models.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.is_finetuned ? "⚡ " : ""}{m.name} — ep {m.version}
                  {m.scenario ? ` [${m.scenario.replace(/_/g, " ")}]` : ""}
                  {m.source === "remote" ? " ☁ Supabase Cloud" : " 💾 Local"}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>

        {/* Quick Shortcuts: Resume Training & Fine-Tune This Model */}
        {selectedModelId && selectedModelId !== "__none" && !isTraining && (
          <div className="grid grid-cols-2 gap-2 mt-1.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="border-violet-500/30 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 text-[11px] flex items-center justify-center gap-1 transition-all"
              onClick={() => {
                setTrainingMode("resume");
                setResumeModelId(selectedModelId);
                setShowConfig(true);
              }}
            >
              <RotateCcw className="h-3 w-3" />
              Resume Model
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 text-[11px] flex items-center justify-center gap-1 transition-all"
              onClick={() => {
                setTrainingMode("finetune");
                setFinetuneModelId(selectedModelId);
                setShowConfig(true);
              }}
            >
              <Zap className="h-3 w-3 text-amber-400" />
              Fine-Tune Model
            </Button>
          </div>
        )}

        {isLoadingModel && (
          <div className="flex items-center gap-2 text-xs text-white/60">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading checkpoint…
          </div>
        )}
        {loadSuccess && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Model loaded — switch to AI mode to use it
          </div>
        )}
        {loadError && (
          <div className="text-xs text-rose-300" role="alert">{loadError}</div>
        )}
      </div>
    </div>
  );
}

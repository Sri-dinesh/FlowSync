"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Activity, Zap, Clock, TrendingUp, TrendingDown, Brain, CheckCircle2, Minus } from "lucide-react";
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
}

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
function AgentPhaseDescription({ epsilon, episode }: { epsilon: number; episode: number }) {
  if (episode === 0) return null;

  let phase: string;
  let desc: string;
  let color: string;

  if (epsilon > 0.7) {
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
  const [numEpisodes, setNumEpisodes] = useState(500);
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

  // Speed tracking
  useEffect(() => {
    if (!isTraining) { startTimeRef.current = null; setEpsPerMin(0); return; }
    if (startTimeRef.current === null) startTimeRef.current = Date.now();
    if (currentEpisode > 0 && startTimeRef.current) {
      const mins = (Date.now() - startTimeRef.current) / 60_000;
      setEpsPerMin(mins > 0 ? currentEpisode / mins : 0);
    }
  }, [currentEpisode, isTraining]);

  // Auto-refresh model list when a checkpoint is saved
  // The trainer broadcasts { type: "checkpoint_saved" } over the training WS
  // which lands in trainingMetrics — filter it out here
  useEffect(() => {
    const raw = trainingMetrics[trainingMetrics.length - 1] as unknown as Record<string, unknown> | null;
    if (raw && (raw as Record<string, unknown>).type === "checkpoint_saved") {
      queryClient.invalidateQueries({ queryKey: ["models"] });
    }
  }, [trainingMetrics, queryClient]);

  const progress = useMemo(() => {
    if (!targetEpisodes) return 0;
    return Math.min(1, currentEpisode / targetEpisodes);
  }, [currentEpisode, targetEpisodes]);

  const eta = useMemo(() => {
    if (!isTraining || !targetEpisodes || epsPerMin === 0) return null;
    const mins = (targetEpisodes - currentEpisode) / epsPerMin;
    return mins < 1 ? "<1 min" : `~${Math.round(mins)} min`;
  }, [isTraining, targetEpisodes, currentEpisode, epsPerMin]);

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

  const startTraining = () => {
    setTargetEpisodes(numEpisodes);
    setTraining(true);
    startTimeRef.current = Date.now();
    sendCommand({ command: "start_training", num_episodes: numEpisodes, simulation_id: simulationId ?? undefined });
    setShowConfig(false);
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
        <AIStatusBadge isTraining={isTraining} currentEpisode={currentEpisode} targetEpisodes={targetEpisodes} />
        {isTraining ? (
          <Button size="sm" variant="outline"
            className="border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
            onClick={stopTraining}>
            Stop Training
          </Button>
        ) : (
          <Button size="sm" onClick={() => setShowConfig((p) => !p)}
            className="bg-blue-600 hover:bg-blue-700 text-white">
            Train Agent
          </Button>
        )}
      </div>

      {/* Config */}
      <AnimatePresence>
        {showConfig && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <div className="rounded-lg border border-white/10 bg-white/5 p-4 space-y-3">
              <div>
                <label className="block text-xs text-white/70 mb-1">Episodes</label>
                <p className="text-[10px] text-white/35 mb-2">
                  Each episode runs the intersection for up to 500 steps. More episodes = better agent, but takes longer.
                </p>
                <input type="number" min={1} max={2000}
                  className="w-full rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-white"
                  value={numEpisodes}
                  onChange={(e) => setNumEpisodes(Number(e.target.value))} />
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={startTraining}>Start Training</Button>
                <Button size="sm" variant="outline" onClick={() => setShowConfig(false)}>Cancel</Button>
              </div>
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
                <div className="flex items-center gap-1.5">
                  <Brain className="h-3.5 w-3.5 text-violet-400" />
                  <span className="text-xs font-medium text-white">
                    Episode <span className="text-violet-300 font-bold">{currentEpisode}</span>
                    <span className="text-white/35"> / {targetEpisodes ?? "—"}</span>
                  </span>
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
                <AgentPhaseDescription epsilon={latest.epsilon} episode={currentEpisode} />
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
              {targetEpisodes && (
                <div className="text-[9px] text-white/25 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-white/20" />
                  Checkpoint saved every 50 episodes and at completion
                </div>
              )}

              {/* Status */}
              {isTraining ? (
                <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/80">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Training — metrics update after each episode
                </div>
              ) : currentEpisode > 0 ? (
                <div className="flex items-center gap-1.5 text-[10px] text-white/30">
                  <CheckCircle2 className="h-3 w-3" />
                  Complete — {currentEpisode} episode{currentEpisode !== 1 ? "s" : ""} trained
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
                  {m.name} — ep {m.version}
                  {m.source === "remote" ? " ☁" : " 💾"}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
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

"use client";

import { useEffect, useState } from "react";
import {
  FlaskConical,
  Play,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  Cpu,
  Hash,
  Activity,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { useResearchStore } from "@/store/researchStore";
import { useResearchSocket } from "@/hooks/useResearchSocket";
import type {
  ResearchScenario,
  ResearchController,
  NoisePreset,
  NoisePresetKey,
} from "@/types/research";
import { getFastApiUrls } from "@/lib/utils";

export default function ResearchExperimentBuilder() {
  const activeScenario = useResearchStore((s) => s.activeScenario);
  const activeController = useResearchStore((s) => s.activeController);
  const activeSeed = useResearchStore((s) => s.activeSeed);
  const activeNoisePreset = useResearchStore((s) => s.activeNoisePreset);
  const speedMultiplier = useResearchStore((s) => s.speedMultiplier);
  const runStatus = useResearchStore((s) => s.runStatus);
  const setConfig = useResearchStore((s) => s.setConfig);
  const setSpeedMultiplier = useResearchStore((s) => s.setSpeedMultiplier);

  const { startExperiment, startPairedComparison, stop } = useResearchSocket();

  const [scenarios, setScenarios] = useState<ResearchScenario[]>([]);
  const [controllers, setControllers] = useState<ResearchController[]>([]);
  const [seeds, setSeeds] = useState<number[]>([]);
  const [noisePresets, setNoisePresets] = useState<NoisePreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [customSeedInput, setCustomSeedInput] = useState<string>("");
  const [isCustomSeed, setIsCustomSeed] = useState(false);

  useEffect(() => {
    const { httpUrl } = getFastApiUrls();
    async function loadMetadata() {
      try {
        const [scRes, ctrlRes, seedsRes, noiseRes] = await Promise.all([
          fetch(`${httpUrl}/research/scenarios`),
          fetch(`${httpUrl}/research/controllers`),
          fetch(`${httpUrl}/research/seeds`),
          fetch(`${httpUrl}/research/noise-presets`),
        ]);

        if (scRes.ok) {
          const scData = await scRes.json();
          setScenarios(scData.scenarios || []);
          if (!activeScenario && scData.scenarios?.length > 0) {
            // Default to first test scenario
            const defaultSc =
              scData.scenarios.find((s: ResearchScenario) => s.split === "test") ||
              scData.scenarios[0];
            setConfig({ scenario: defaultSc });
          }
        }

        if (ctrlRes.ok) {
          const ctrlData = await ctrlRes.json();
          setControllers(ctrlData.controllers || []);
        }

        if (seedsRes.ok) {
          const seedsData = await seedsRes.json();
          setSeeds(seedsData.seeds || [1101]);
        }

        if (noiseRes.ok) {
          const noiseData = await noiseRes.json();
          setNoisePresets(noiseData.presets || []);
        }
      } catch (err) {
        console.error("Failed to load research metadata:", err);
      } finally {
        setLoading(false);
      }
    }

    loadMetadata();
  }, [activeScenario, setConfig]);

  const handleLaunch = () => {
    if (!activeScenario) return;
    const finalSeed = isCustomSeed && customSeedInput ? parseInt(customSeedInput, 10) : activeSeed;
    const ctrlId =
      typeof activeController === "object" && activeController !== null
        ? activeController.id || "flowsync_uq"
        : activeController || "flowsync_uq";
    startExperiment(activeScenario.scenario_id, ctrlId, finalSeed, activeNoisePreset);
  };

  const handleLaunchPaired = () => {
    if (!activeScenario) return;
    const finalSeed = isCustomSeed && customSeedInput ? parseInt(customSeedInput, 10) : activeSeed;
    startPairedComparison(activeScenario.scenario_id, "d3qn", "flowsync_uq", finalSeed, activeNoisePreset);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-950/80 p-5 backdrop-blur-xl shadow-2xl flex flex-col gap-5 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/25 text-indigo-400">
            <FlaskConical className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white flex items-center gap-2">
              Research Experiment Builder
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-normal">
                CRN Synchronized
              </span>
            </h2>
            <p className="text-xs text-white/40 mt-0.5">
              Launch frozen IEEE submission scenarios under deterministic perception fault schedules
            </p>
          </div>
        </div>

        {runStatus === "running" && (
          <Button
            size="sm"
            variant="destructive"
            onClick={stop}
            className="flex items-center gap-1.5 text-xs font-mono"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Stop Experiment
          </Button>
        )}
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-white/40 font-mono animate-pulse">
          Loading frozen scenario catalog and research controller registry...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Scenario Selector */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-white/50 uppercase tracking-wider flex items-center justify-between">
              <span>1. Frozen Scenario</span>
              {activeScenario && (
                <span className="text-[9px] font-mono text-indigo-300">
                  SHA: {activeScenario.scenario_hash.slice(0, 8)}
                </span>
              )}
            </label>
            <select
              value={activeScenario?.scenario_id ?? ""}
              onChange={(e) => {
                const sc = scenarios.find((s) => s.scenario_id === e.target.value);
                if (sc) setConfig({ scenario: sc });
              }}
              className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            >
              {scenarios.map((sc) => (
                <option key={sc.scenario_id} value={sc.scenario_id} className="bg-neutral-900 text-white">
                  [{sc.split.toUpperCase()}] {sc.name} ({sc.duration_seconds}s)
                </option>
              ))}
            </select>
            {activeScenario && (
              <div className="text-[10px] text-white/40 flex items-center justify-between pt-1">
                <span>Split: <span className="text-white font-medium capitalize">{activeScenario.split}</span></span>
                <span>Duration: <span className="text-white font-mono">{activeScenario.duration_seconds}s</span></span>
              </div>
            )}
          </div>

          {/* 2. Controller Selector */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-white/50 uppercase tracking-wider">
              2. Signal Controller
            </label>
            <select
              value={typeof activeController === "object" && activeController !== null ? activeController.id : activeController}
              onChange={(e) => setConfig({ controller: e.target.value })}
              className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 font-medium"
            >
              {controllers.map((ctrl) => (
                <option key={ctrl.id} value={ctrl.id} className="bg-neutral-900 text-white">
                  {ctrl.name} {ctrl.is_proposed_method ? "★" : ""}
                </option>
              ))}
            </select>
            <div className="text-[10px] text-white/40 line-clamp-1 pt-1">
              {controllers.find((c) => c.id === (typeof activeController === "object" && activeController !== null ? activeController.id : activeController))?.description || "Active policy module"}
            </div>
          </div>

          {/* 3. Noise Disturbance Preset */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-white/50 uppercase tracking-wider">
              3. Perception Noise Profile
            </label>
            <select
              value={activeNoisePreset}
              onChange={(e) => setConfig({ noisePreset: e.target.value as NoisePresetKey })}
              className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            >
              {noisePresets.map((np) => (
                <option key={np.key} value={np.key} className="bg-neutral-900 text-white">
                  {np.label}
                </option>
              ))}
            </select>
            <div className="text-[10px] text-white/40 flex items-center gap-1.5 pt-1">
              {activeNoisePreset === "clean" ? (
                <span className="text-emerald-400">Nominal 100% camera visibility</span>
              ) : (
                <span className="text-amber-400 flex items-center gap-1">
                  <ShieldAlert className="h-3 w-3" /> Fault injection enabled
                </span>
              )}
            </div>
          </div>

          {/* 4. Seed Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-white/50 uppercase tracking-wider">
                4. Evaluation Seed
              </label>
              <button
                type="button"
                onClick={() => setIsCustomSeed(!isCustomSeed)}
                className="text-[9px] text-indigo-400 hover:underline"
              >
                {isCustomSeed ? "Use Frozen Seed" : "Custom Seed"}
              </button>
            </div>

            {isCustomSeed ? (
              <div>
                <input
                  type="number"
                  placeholder="Enter custom seed"
                  value={customSeedInput}
                  onChange={(e) => setCustomSeedInput(e.target.value)}
                  className="w-full rounded-xl border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-300 font-mono focus:outline-none"
                />
                <p className="text-[9px] text-amber-400/70 mt-1 flex items-center gap-1">
                  <AlertTriangle className="h-2.5 w-2.5" /> Non-publication debug run
                </p>
              </div>
            ) : (
              <select
                value={activeSeed}
                onChange={(e) => setConfig({ seed: parseInt(e.target.value, 10) })}
                className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 font-mono"
              >
                {seeds.map((s) => (
                  <option key={s} value={s} className="bg-neutral-900 text-white font-mono">
                    Seed {s} (CRN Synced)
                  </option>
                ))}
              </select>
            )}
            <div className="text-[10px] text-white/40 pt-1">
              Paired arrival schedule locked
            </div>
          </div>
        </div>
      )}

      {/* Speed & Execution Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-3 border-t border-white/[0.06]">
        {/* Speed Slider */}
        <div className="flex items-center gap-3 w-full sm:w-72">
          <span className="text-[11px] text-white/40 font-mono uppercase whitespace-nowrap">
            Speed: {speedMultiplier.toFixed(1)}x
          </span>
          <Slider
            value={[speedMultiplier]}
            min={0.5}
            max={5.0}
            step={0.5}
            onValueChange={(vals) => setSpeedMultiplier(vals[0] || 1.0)}
            className="flex-1"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          <Button
            size="sm"
            variant="outline"
            onClick={handleLaunchPaired}
            disabled={runStatus === "running" || loading}
            className="border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-semibold gap-1.5"
          >
            <Activity className="h-3.5 w-3.5 text-indigo-400" />
            Compare D3QN vs FlowSync-UQ
          </Button>

          <Button
            size="sm"
            onClick={handleLaunch}
            disabled={runStatus === "running" || loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold gap-1.5 shadow-lg shadow-indigo-600/30"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            Execute Single Run
          </Button>
        </div>
      </div>
    </div>
  );
}

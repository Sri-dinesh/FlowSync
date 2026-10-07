"use client";

import { useEffect, useRef, useState } from "react";
import {
  FlaskConical,
  Play,
  RotateCcw,
  ShieldAlert,
  Activity,
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

  const { startExperiment, startPairedComparison, stop, sendCommand } = useResearchSocket();

  const [scenarios, setScenarios] = useState<ResearchScenario[]>([]);
  const [controllers, setControllers] = useState<ResearchController[]>([]);
  const [seeds, setSeeds] = useState<number[]>([]);
  const [noisePresets, setNoisePresets] = useState<NoisePreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [customSeedInput, setCustomSeedInput] = useState<string>("");
  const [isCustomSeed, setIsCustomSeed] = useState(false);
  const { isConnected } = useResearchSocket();
  const didInitDefaults = useRef(false);

  useEffect(() => {
    const { httpUrl } = getFastApiUrls();
    let cancelled = false;
    async function loadMetadata() {
      try {
        setLoadError(null);
        const [scRes, ctrlRes, seedsRes, noiseRes] = await Promise.all([
          fetch(`${httpUrl}/research/scenarios`),
          fetch(`${httpUrl}/research/controllers`),
          fetch(`${httpUrl}/research/seeds`),
          fetch(`${httpUrl}/research/noise-presets`),
        ]);

        if (!cancelled && scRes.ok) {
          const scData = await scRes.json();
          const list = scData.scenarios || [];
          setScenarios(list);
          if (!didInitDefaults.current && list?.length > 0) {
            didInitDefaults.current = true;
            // Default to first test scenario only if the current selection
            // is missing from the catalog (e.g. stale default id).
            const currentId = useResearchStore.getState().activeScenario?.scenario_id;
            const stillValid = list.some((s: ResearchScenario) => s.scenario_id === currentId);
            if (!stillValid) {
              const defaultSc =
                list.find((s: ResearchScenario) => s.split === "test") || list[0];
              setConfig({ scenario: defaultSc });
            }
          }
        }

        if (!cancelled && ctrlRes.ok) {
          const ctrlData = await ctrlRes.json();
          setControllers(ctrlData.controllers || []);
        }

        if (!cancelled && seedsRes.ok) {
          const seedsData = await seedsRes.json();
          setSeeds(seedsData.seeds || [1101]);
        }

        if (!cancelled && noiseRes.ok) {
          const noiseData = await noiseRes.json();
          setNoisePresets(noiseData.presets || []);
        }

        if (!cancelled && (!scRes.ok || !ctrlRes.ok)) {
          setLoadError(
            `Backend unavailable at ${httpUrl}. Start it with: uvicorn server.app.main:app --port 8000`
          );
        }
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load research metadata:", err);
          setLoadError(
            `Cannot reach backend at ${httpUrl}. Start it with: uvicorn server.app.main:app --port 8000`
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadMetadata();
    return () => {
      cancelled = true;
    };
    // Intentionally run once: setConfig identity is stable, and depending on
    // activeScenario here would refetch the catalog on every selection change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const handleSpeedChange = (vals: number[]) => {
    const next = vals[0] || 1.0;
    setSpeedMultiplier(next);
    // Apply live to a running backend session (no-op if idle).
    if (runStatus === "running" || runStatus === "paused") {
      sendCommand({ command: "set_speed", speed: next });
    }
  };

  const handleRetryCatalog = () => {
    setLoading(true);
    setLoadError(null);
    didInitDefaults.current = true; // don't clobber user selection on retry
    const { httpUrl } = getFastApiUrls();
    Promise.all([
      fetch(`${httpUrl}/research/scenarios`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${httpUrl}/research/controllers`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${httpUrl}/research/seeds`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${httpUrl}/research/noise-presets`).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([sc, ctrl, seedsData, noise]) => {
        if (sc?.scenarios) setScenarios(sc.scenarios);
        if (ctrl?.controllers) setControllers(ctrl.controllers);
        if (seedsData?.seeds) setSeeds(seedsData.seeds);
        if (noise?.presets) setNoisePresets(noise.presets);
        if (!sc || !ctrl) {
          setLoadError(`Backend unavailable at ${httpUrl}. Start it with: uvicorn server.app.main:app --port 8000`);
        }
      })
      .catch(() =>
        setLoadError(`Cannot reach backend at ${httpUrl}. Start it with: uvicorn server.app.main:app --port 8000`)
      )
      .finally(() => setLoading(false));
  };

  const launchDisabledReason = loading
    ? "Loading scenario catalog…"
    : !isConnected
      ? "Waiting for backend stream — your run will queue and start on connect"
      : runStatus === "running" || runStatus === "starting"
        ? "A run is already in progress"
        : null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col gap-4 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-400">
            <FlaskConical className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-white flex items-center gap-2">
              Experiment setup
              <span className="rounded-full border border-neutral-700 bg-white/[0.03] px-2 py-0.5 text-[11px] text-neutral-400">
                Same traffic every run
              </span>
            </h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              Scenario, controller, camera fault and seed — then Execute below
            </p>
          </div>
        </div>

        {runStatus === "running" && (
          <Button
            size="sm"
            variant="destructive"
            onClick={stop}
            className="flex items-center gap-1.5 text-xs"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Stop
          </Button>
        )}
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-neutral-500 animate-pulse">
          Loading scenario catalog…
        </div>
      ) : loadError ? (
        <div className="rounded-md border border-red-500/30 bg-red-500/[0.06] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5 text-xs text-red-200">
            <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
            <div>
              <div className="font-medium text-white">Backend offline — catalog unavailable</div>
              <div className="text-red-200/70 font-mono text-[11px] mt-0.5">{loadError}</div>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={handleRetryCatalog} className="border-neutral-700 text-neutral-300 hover:bg-white/5 shrink-0">
            <RotateCcw className="h-3.5 w-3.5" /> Retry
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Scenario Selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-neutral-400 flex items-center justify-between">
              <span>Scenario</span>
              {activeScenario && (
                <span className="text-[11px] font-mono text-neutral-500" title={String(activeScenario.scenario_hash)}>
                  {String(activeScenario.scenario_hash).slice(0, 8)}
                </span>
              )}
            </label>
            <select
              value={activeScenario?.scenario_id ?? ""}
              onChange={(e) => {
                const sc = scenarios.find((s) => s.scenario_id === e.target.value);
                if (sc) setConfig({ scenario: sc });
              }}
              className="w-full rounded-md border border-neutral-800 bg-black/30 px-2.5 py-2 text-[13px] text-white focus:outline-none focus:border-neutral-600"
            >
              {scenarios.map((sc) => (
                <option key={sc.scenario_id} value={sc.scenario_id} className="bg-neutral-900 text-white">
                  [{sc.split.toUpperCase()}] {sc.name} ({sc.duration_seconds}s)
                </option>
              ))}
            </select>
            {activeScenario && (
              <div className="text-[11px] text-neutral-500 flex items-center justify-between pt-0.5">
                <span className="capitalize">{activeScenario.split} split</span>
                <span className="font-mono tabular-nums">{activeScenario.duration_seconds}s</span>
              </div>
            )}
          </div>

          {/* 2. Controller Selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-neutral-400">
              Controller
            </label>
            <select
              value={typeof activeController === "object" && activeController !== null ? activeController.id : activeController}
              onChange={(e) => setConfig({ controller: e.target.value })}
              className="w-full rounded-md border border-neutral-800 bg-black/30 px-2.5 py-2 text-[13px] text-white focus:outline-none focus:border-neutral-600"
            >
              {controllers.map((ctrl) => (
                <option key={ctrl.id} value={ctrl.id} className="bg-neutral-900 text-white">
                  {ctrl.name} {ctrl.is_proposed_method ? "★" : ""}
                </option>
              ))}
            </select>
            <div className="text-[11px] text-neutral-500 line-clamp-1 pt-0.5">
              {controllers.find((c) => c.id === (typeof activeController === "object" && activeController !== null ? activeController.id : activeController))?.description || "Active policy module"}
            </div>
          </div>

          {/* 3. Noise Disturbance Preset */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-neutral-400">
              Camera fault
            </label>
            <select
              value={activeNoisePreset}
              onChange={(e) => setConfig({ noisePreset: e.target.value as NoisePresetKey })}
              className="w-full rounded-md border border-neutral-800 bg-black/30 px-2.5 py-2 text-[13px] text-white focus:outline-none focus:border-neutral-600"
            >
              {noisePresets.map((np) => (
                <option key={np.key} value={np.key} className="bg-neutral-900 text-white">
                  {np.label}
                </option>
              ))}
            </select>
            <div className="text-[11px] text-neutral-500 flex items-center gap-1.5 pt-0.5">
              {activeNoisePreset === "clean" ? (
                <span className="text-emerald-300/90">Clean cameras</span>
              ) : (
                <span className="text-amber-300/90 flex items-center gap-1">
                  <ShieldAlert className="h-3 w-3" /> Fault injected
                </span>
              )}
            </div>
          </div>

          {/* 4. Seed Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-neutral-400">
                Seed
              </label>
              <button
                type="button"
                onClick={() => setIsCustomSeed(!isCustomSeed)}
                className="text-[11px] text-neutral-500 hover:text-white hover:underline"
              >
                {isCustomSeed ? "Use saved seed" : "Custom"}
              </button>
            </div>

            {isCustomSeed ? (
              <div>
                <input
                  type="number"
                  placeholder="Enter custom seed"
                  value={customSeedInput}
                  onChange={(e) => setCustomSeedInput(e.target.value)}
                  className="w-full rounded-md border border-neutral-800 bg-black/30 px-2.5 py-2 text-[13px] text-white font-mono tabular-nums focus:outline-none focus:border-neutral-600"
                />
                <p className="text-[11px] text-amber-300/70 mt-1 flex items-center gap-1">
                  <AlertTriangle className="h-2.5 w-2.5" /> Debug run, not a publication seed
                </p>
              </div>
            ) : (
              <select
                value={activeSeed}
                onChange={(e) => setConfig({ seed: parseInt(e.target.value, 10) })}
                className="w-full rounded-md border border-neutral-800 bg-black/30 px-2.5 py-2 text-[13px] text-white focus:outline-none focus:border-neutral-600 font-mono tabular-nums"
              >
                {seeds.map((s) => (
                  <option key={s} value={s} className="bg-neutral-900 text-white font-mono">
                    Seed {s}
                  </option>
                ))}
              </select>
            )}
            <div className="text-[11px] text-neutral-500 pt-0.5">
              Same seed = same traffic
            </div>
          </div>
        </div>
      )}

      {/* Speed & Execution Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-neutral-800">
        {/* Speed Slider */}
        <div className="flex items-center gap-3 w-full sm:w-64">
          <span className="text-xs text-neutral-500 whitespace-nowrap tabular-nums">
            {speedMultiplier.toFixed(1)}x speed
          </span>
          <Slider
            value={[speedMultiplier]}
            min={0.5}
            max={5.0}
            step={0.5}
            onValueChange={handleSpeedChange}
            className="flex-1"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col items-end gap-1.5 self-end sm:self-auto">
          <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleLaunchPaired}
            disabled={runStatus === "running" || runStatus === "starting" || loading}
            title={launchDisabledReason ?? "Run D3QN vs FlowSync-UQ side-by-side under identical traffic"}
            className="border-neutral-700 bg-transparent hover:bg-white/5 text-neutral-300 text-xs gap-1.5"
          >
            <Activity className="h-3.5 w-3.5" />
            Compare A/B
          </Button>

          <Button
            size="sm"
            onClick={handleLaunch}
            disabled={runStatus === "running" || runStatus === "starting" || loading}
            title={launchDisabledReason ?? "Start a single simulation run with the selected configuration"}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5"
          >
            {runStatus === "starting" ? (
              <>
                <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                Connecting…
              </>
            ) : runStatus === "running" ? (
              <>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Running
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                Run simulation
              </>
            )}
          </Button>
          </div>
          {!isConnected && !loading && (
            <span className="text-[11px] text-amber-300/90">
              Offline — the run queues and starts on reconnect.
            </span>
          )}
          {launchDisabledReason && isConnected && !loading && (
            <span className="text-[11px] text-neutral-500">{launchDisabledReason}</span>
          )}
        </div>
      </div>
    </div>
  );
}

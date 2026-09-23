"use client";

import { useCallback, useRef, useState } from "react";
import { RefreshCw, Trash2, Plus, ChevronDown, FlaskConical, Check, Lock, Flame, Zap } from "lucide-react";
import type { Scenario, ScenarioType } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

interface ScenarioSelectorProps {
  selected: Scenario | null;
  onSelect: (scenario: Scenario | null) => void;
}

const QUICK_PRESETS = [
  {
    key: "low",
    label: "Low Flow",
    sub: "λ 0.25 · 60s",
    match: (s: Scenario) => s.name.toLowerCase().includes("low") || (s.spawn_lambda <= 0.35 && !s.is_held_out),
  },
  {
    key: "moderate",
    label: "Moderate",
    sub: "λ 0.55 · 60s",
    match: (s: Scenario) => s.name.toLowerCase().includes("moderate") || (s.spawn_lambda > 0.35 && s.spawn_lambda <= 0.7 && !s.is_held_out && s.scenario_type !== "held_out"),
  },
  {
    key: "high",
    label: "Rush Hour",
    sub: "λ 0.90 · 90s",
    match: (s: Scenario) => s.name.toLowerCase().includes("high") || (s.spawn_lambda > 0.7 && s.spawn_lambda <= 1.1 && !s.is_held_out),
  },
  {
    key: "critical",
    label: "Gridlock",
    sub: "λ 1.40 · 120s",
    match: (s: Scenario) => s.name.toLowerCase().includes("critical") || s.name.toLowerCase().includes("gridlock") || s.spawn_lambda > 1.1,
  },
  {
    key: "held_out",
    label: "Held-Out",
    sub: "λ 0.70 · 60s",
    match: (s: Scenario) => s.is_held_out || s.scenario_type === "held_out" || s.name.toLowerCase().includes("held"),
  },
];

function generateSeed(): number {
  return Math.floor(Math.random() * 9_999_999) + 1;
}

export function ScenarioSelector({ selected, onSelect }: ScenarioSelectorProps) {
  const { scenarios, loading, createScenario, deleteScenario, seedDefaultScenarios } = useScenarios();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName]       = useState("");
  const [newSeed, setNewSeed]       = useState(generateSeed);
  const [newLambda, setNewLambda]   = useState(0.5);
  const [newDuration, setNewDuration] = useState(60);
  const [scenarioType, setScenarioType] = useState<ScenarioType>("standard");
  const [creating, setCreating]     = useState(false);
  const [deleting, setDeleting]     = useState(false);
  const [seeding, setSeeding]       = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleSeedDefaults = useCallback(async () => {
    setSeeding(true);
    await seedDefaultScenarios();
    setSeeding(false);
  }, [seedDefaultScenarios]);

  const handleSelectPreset = useCallback(async (presetKey: string) => {
    const preset = QUICK_PRESETS.find((p) => p.key === presetKey);
    if (!preset) return;

    let match = scenarios.find(preset.match);
    if (match) {
      onSelect(match);
      return;
    }

    // Auto-seed defaults if not found
    setSeeding(true);
    await seedDefaultScenarios();
    setSeeding(false);
  }, [scenarios, seedDefaultScenarios, onSelect]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setCreating(true);
    const isHeldOut = scenarioType === "held_out";
    const created = await createScenario(
      newName.trim(),
      newSeed,
      newLambda,
      newDuration,
      isHeldOut,
      scenarioType,
    );
    if (created) {
      onSelect(created);
      setShowCreate(false);
      setNewName("");
      setNewSeed(generateSeed());
      setNewLambda(0.5);
      setNewDuration(60);
      setScenarioType("standard");
    }
    setCreating(false);
  }, [newName, newSeed, newLambda, newDuration, scenarioType, createScenario, onSelect]);

  const handleDelete = useCallback(async () => {
    if (!selected) return;
    setDeleting(true);
    const ok = await deleteScenario(selected.id);
    if (ok) onSelect(null);
    setDeleting(false);
  }, [selected, deleteScenario, onSelect]);

  return (
    <div className="space-y-3">
      {/* ── 1-Click Evaluation Presets ─────────────────────────── */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] text-neutral-400 font-medium">
          <span className="flex items-center gap-1.5">
            <Zap size={12} className="text-violet-400" />
            Quick Presets
          </span>
          <button
            type="button"
            onClick={handleSeedDefaults}
            disabled={seeding || loading}
            className="text-[10px] text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={10} className={seeding ? "animate-spin" : ""} />
            {seeding ? "Seeding..." : "Reset Defaults"}
          </button>
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {QUICK_PRESETS.map((p) => {
            const matchScenario = scenarios.find(p.match);
            const isSelected = Boolean(selected && matchScenario && selected.id === matchScenario.id);
            return (
              <button
                key={p.key}
                type="button"
                onClick={() => handleSelectPreset(p.key)}
                className={`flex flex-col items-center justify-center p-2 rounded-lg border text-center transition-all ${
                  isSelected
                    ? "bg-violet-500/20 border-violet-500/60 text-white shadow-sm ring-1 ring-violet-500/40"
                    : "bg-neutral-900/80 border-neutral-800 text-neutral-300 hover:border-neutral-700 hover:bg-neutral-800/80"
                }`}
              >
                <span className="text-[11px] font-semibold tracking-tight truncate w-full">{p.label}</span>
                <span className="text-[9px] text-neutral-500 font-mono mt-0.5 truncate w-full">{p.sub}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Scenario Dropdown Row ─────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Dropdown */}
        <div className="relative flex-1" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen((o) => !o)}
            className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 hover:border-neutral-700 transition-colors text-sm text-white"
          >
            <span className="flex items-center gap-2 truncate">
              <FlaskConical size={13} className="text-neutral-500 shrink-0" />
              <span className={`truncate ${selected ? "text-white" : "text-neutral-500"}`}>
                {selected ? selected.name : "Random seed (default)"}
              </span>
              {selected?.is_held_out && (
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-neutral-800 text-neutral-300 border border-neutral-700 font-mono flex items-center gap-1">
                  <Lock size={9} /> Held-out
                </span>
              )}
            </span>
            <ChevronDown
              size={13}
              className={`shrink-0 text-neutral-500 transition-transform ${dropdownOpen ? "rotate-180" : ""}`}
            />
          </button>

          {dropdownOpen && (
            <div className="absolute z-50 mt-1 w-full rounded-xl border border-neutral-800 bg-neutral-900 shadow-2xl overflow-hidden max-h-80 overflow-y-auto">
              {/* None option */}
              <button
                type="button"
                onClick={() => { onSelect(null); setDropdownOpen(false); }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-neutral-800 transition-colors ${!selected ? "text-white" : "text-neutral-400"}`}
              >
                {!selected && <Check size={12} className="shrink-0" />}
                <span className={!selected ? "ml-0" : "ml-4"}>Random seed (default)</span>
              </button>

              {/* Divider */}
              {scenarios.length > 0 && <div className="border-t border-neutral-800 mx-3" />}

              {loading && (
                <div className="px-3 py-2 text-xs text-neutral-500">Loading…</div>
              )}

              {scenarios.length === 0 && !loading && (
                <div className="p-3 text-center space-y-2">
                  <div className="text-xs text-neutral-400">No scenarios found</div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleSeedDefaults}
                    disabled={seeding}
                    className="w-full text-xs border-violet-500/40 text-violet-300 bg-violet-500/10 hover:bg-violet-500/20"
                  >
                    <RefreshCw size={12} className={`mr-1.5 ${seeding ? "animate-spin" : ""}`} />
                    {seeding ? "Seeding Standard Scenarios..." : "Seed Standard Scenarios"}
                  </Button>
                </div>
              )}

              {scenarios.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => { onSelect(s); setDropdownOpen(false); }}
                  className={`w-full flex items-start gap-2 px-3 py-2 text-sm text-left hover:bg-neutral-800 transition-colors ${selected?.id === s.id ? "text-white bg-neutral-800/50" : "text-neutral-400"}`}
                >
                  {selected?.id === s.id
                    ? <Check size={12} className="mt-0.5 shrink-0 text-violet-400" />
                    : <span className="w-3 shrink-0" />
                  }
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="block truncate font-medium">{s.name}</span>
                      {s.is_held_out && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-purple-950/60 text-purple-300 border border-purple-800 font-medium flex items-center gap-0.5">
                          <Lock size={8} /> Held-out
                        </span>
                      )}
                      {s.scenario_type === "stress" && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-rose-950/60 text-rose-300 border border-rose-800 font-medium flex items-center gap-0.5">
                          <Flame size={8} /> Stress
                        </span>
                      )}
                    </span>
                    <span className="block text-[10px] text-neutral-500 font-mono mt-0.5">
                      seed {s.seed} · λ {s.spawn_lambda.toFixed(2)} veh/s · {s.duration_seconds}s
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* + New button */}
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 h-9 w-9 p-0 border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-white hover:bg-neutral-800"
          onClick={() => { setShowCreate((v) => !v); setDropdownOpen(false); }}
        >
          <Plus size={14} />
        </Button>

        {/* Delete button (only when scenario selected) */}
        {selected && (
          <Button
            variant="outline"
            size="sm"
            className="shrink-0 h-9 w-9 p-0 border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-red-400 hover:bg-neutral-800"
            onClick={handleDelete}
            disabled={deleting}
          >
            <Trash2 size={14} />
          </Button>
        )}
      </div>

      {/* ── Selected scenario info pill ───────────────────────────── */}
      {selected && (
        <div className="flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-lg bg-neutral-900 border border-neutral-800 text-[11px]">
          <span className="text-neutral-300 font-mono">seed {selected.seed}</span>
          <span className="text-neutral-700">·</span>
          <span className="text-neutral-500">λ={selected.spawn_lambda.toFixed(1)} veh/s</span>
          <span className="text-neutral-700">·</span>
          <span className="text-neutral-500">{selected.duration_seconds}s</span>
          {selected.is_held_out && (
            <>
              <span className="text-neutral-700">·</span>
              <span className="inline-flex items-center gap-1 text-neutral-400 font-medium">
                <Lock size={10} /> Held-out evaluation set
              </span>
            </>
          )}
          {selected.scenario_type === "stress" && (
            <>
              <span className="text-neutral-700">·</span>
              <span className="inline-flex items-center gap-1 text-neutral-400 font-medium">
                <Flame size={10} /> High-load stress scenario
              </span>
            </>
          )}
        </div>
      )}

      {/* ── Inline Create Form ────────────────────────────────────── */}
      {showCreate && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-4">
          <p className="text-[10px] uppercase tracking-widest text-neutral-500 font-semibold">
            New Scenario
          </p>

          {/* Scenario Type Selection */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-neutral-500 font-medium">Scenario Type</label>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setScenarioType("standard");
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition-all ${
                  scenarioType === "standard"
                    ? "border-neutral-700 bg-neutral-800 text-white"
                    : "border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-neutral-300"
                }`}
              >
                <Zap size={12} /> Standard
              </button>

              <button
                type="button"
                onClick={() => {
                  setScenarioType("stress");
                  if (newLambda < 1.2) setNewLambda(1.5);
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition-all ${
                  scenarioType === "stress"
                    ? "border-neutral-700 bg-neutral-800 text-white"
                    : "border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-neutral-300"
                }`}
              >
                <Flame size={12} /> Stress
              </button>

              <button
                type="button"
                onClick={() => {
                  setScenarioType("held_out");
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition-all ${
                  scenarioType === "held_out"
                    ? "border-neutral-700 bg-neutral-800 text-white"
                    : "border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-neutral-300"
                }`}
              >
                <Lock size={12} /> Held-Out
              </button>
            </div>
          </div>

          {/* Name */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-neutral-500 font-medium">Name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={scenarioType === "held_out" ? "e.g. Unseen Peak Flow Test" : "e.g. Rush Hour Stress Test"}
              maxLength={100}
              className="w-full px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-sm text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-700 transition-colors"
            />
          </div>

          {/* Seed */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-neutral-500 font-medium">Seed</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={newSeed}
                min={0}
                max={10000000}
                onChange={(e) => setNewSeed(Number(e.target.value))}
                className="flex-1 px-3 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-sm text-white font-mono focus:outline-none focus:border-neutral-700 transition-colors"
              />
              <Button
                variant="outline"
                size="sm"
                className="h-9 w-9 p-0 border-neutral-800 bg-neutral-900 text-neutral-500 hover:text-white"
                onClick={() => setNewSeed(generateSeed())}
              >
                <RefreshCw size={13} />
              </Button>
            </div>
          </div>

          {/* Spawn rate slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-neutral-500 font-medium">Spawn rate (λ)</label>
              <span className="text-[11px] text-neutral-300 font-mono">{newLambda.toFixed(1)} veh/s</span>
            </div>
            <Slider
              min={0.1}
              max={2.0}
              step={0.1}
              value={[newLambda]}
              onValueChange={(val) => setNewLambda(val[0] ?? 0.5)}
              className="w-full h-1.5 bg-neutral-800"
            />
            <div className="flex justify-between text-[10px] text-neutral-600">
              <span>Low 0.1</span>
              <span>High 2.0</span>
            </div>
          </div>

          {/* Duration slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-neutral-500 font-medium">Duration</label>
              <span className="text-[11px] text-neutral-300 font-mono">{newDuration}s</span>
            </div>
            <Slider
              min={10}
              max={300}
              step={10}
              value={[newDuration]}
              onValueChange={(val) => setNewDuration(val[0] ?? 60)}
              className="w-full h-1.5 bg-neutral-800"
            />
            <div className="flex justify-between text-[10px] text-neutral-600">
              <span>10s</span>
              <span>300s</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              className="flex-1 py-2 border-neutral-800 text-neutral-500 hover:text-white hover:bg-neutral-800"
              onClick={() => { setShowCreate(false); setNewName(""); }}
            >
              Cancel
            </Button>
            <Button
              className="flex-1 py-2 bg-white text-black hover:bg-neutral-200 font-semibold text-sm transition-colors"
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
            >
              {creating ? "Saving…" : "Save Scenario"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

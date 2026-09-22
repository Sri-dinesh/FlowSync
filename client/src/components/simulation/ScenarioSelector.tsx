"use client";

import { useCallback, useRef, useState } from "react";
import { RefreshCw, Trash2, Plus, ChevronDown, FlaskConical, Check, Lock, Flame, Zap } from "lucide-react";
import type { Scenario, ScenarioType } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";

interface ScenarioSelectorProps {
  selected: Scenario | null;
  onSelect: (scenario: Scenario | null) => void;
}

function generateSeed(): number {
  return Math.floor(Math.random() * 9_999_999) + 1;
}

export function ScenarioSelector({ selected, onSelect }: ScenarioSelectorProps) {
  const { scenarios, loading, createScenario, deleteScenario } = useScenarios();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName]       = useState("");
  const [newSeed, setNewSeed]       = useState(generateSeed);
  const [newLambda, setNewLambda]   = useState(0.5);
  const [newDuration, setNewDuration] = useState(60);
  const [scenarioType, setScenarioType] = useState<ScenarioType>("standard");
  const [creating, setCreating]     = useState(false);
  const [deleting, setDeleting]     = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

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

      {/* ── Scenario Dropdown Row ─────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Dropdown */}
        <div className="relative flex-1" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen((o) => !o)}
            className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/[0.06] border border-white/10 hover:border-white/20 transition-colors text-sm text-white"
          >
            <span className="flex items-center gap-2 truncate">
              <FlaskConical size={13} className="text-violet-400 shrink-0" />
              <span className={`truncate ${selected ? "text-white" : "text-white/40"}`}>
                {selected ? selected.name : "Random seed (default)"}
              </span>
              {selected?.is_held_out && (
                <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono flex items-center gap-1">
                  <Lock size={9} /> Held-out
                </span>
              )}
            </span>
            <ChevronDown
              size={13}
              className={`shrink-0 text-white/40 transition-transform ${dropdownOpen ? "rotate-180" : ""}`}
            />
          </button>

          {dropdownOpen && (
            <div className="absolute z-50 mt-1 w-full rounded-xl border border-white/10 bg-[#111] shadow-2xl overflow-hidden max-h-80 overflow-y-auto">
              {/* None option */}
              <button
                type="button"
                onClick={() => { onSelect(null); setDropdownOpen(false); }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-white/[0.06] transition-colors ${!selected ? "text-violet-400" : "text-white/50"}`}
              >
                {!selected && <Check size={12} className="shrink-0" />}
                <span className={!selected ? "ml-0" : "ml-4"}>Random seed (default)</span>
              </button>

              {/* Divider */}
              {scenarios.length > 0 && <div className="border-t border-white/[0.07] mx-3" />}

              {loading && (
                <div className="px-3 py-2 text-xs text-white/30">Loading…</div>
              )}

              {scenarios.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => { onSelect(s); setDropdownOpen(false); }}
                  className={`w-full flex items-start gap-2 px-3 py-2 text-sm text-left hover:bg-white/[0.06] transition-colors ${selected?.id === s.id ? "text-violet-300" : "text-white/80"}`}
                >
                  {selected?.id === s.id
                    ? <Check size={12} className="mt-0.5 shrink-0 text-violet-400" />
                    : <span className="w-3 shrink-0" />
                  }
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-2">
                      <span className="block truncate">{s.name}</span>
                      {s.is_held_out && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium flex items-center gap-0.5">
                          <Lock size={8} /> Held-out
                        </span>
                      )}
                      {s.scenario_type === "stress" && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium flex items-center gap-0.5">
                          <Flame size={8} /> Stress
                        </span>
                      )}
                    </span>
                    <span className="block text-[10px] text-white/30 font-mono mt-0.5">
                      seed {s.seed} · λ{s.spawn_lambda.toFixed(1)} · {s.duration_seconds}s
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* + New button */}
        <button
          type="button"
          title="Create new scenario"
          onClick={() => { setShowCreate((v) => !v); setDropdownOpen(false); }}
          className={`shrink-0 p-2 rounded-lg border transition-colors ${
            showCreate
              ? "border-violet-500/60 bg-violet-500/20 text-violet-300"
              : "border-white/10 bg-white/[0.05] text-white/50 hover:text-white/80 hover:border-white/20"
          }`}
        >
          <Plus size={14} />
        </button>

        {/* Delete button (only when scenario selected) */}
        {selected && (
          <button
            type="button"
            title={`Delete "${selected.name}"`}
            onClick={handleDelete}
            disabled={deleting}
            className="shrink-0 p-2 rounded-lg border border-white/10 bg-white/[0.05] text-white/40 hover:text-red-400 hover:border-red-500/30 disabled:opacity-40 transition-colors"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>

      {/* ── Selected scenario info pill ───────────────────────────── */}
      {selected && (
        <div className="flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-[11px]">
          <span className="text-violet-300 font-mono">seed {selected.seed}</span>
          <span className="text-white/20">·</span>
          <span className="text-white/50">λ={selected.spawn_lambda.toFixed(1)} veh/s</span>
          <span className="text-white/20">·</span>
          <span className="text-white/50">{selected.duration_seconds}s</span>
          {selected.is_held_out && (
            <>
              <span className="text-white/20">·</span>
              <span className="inline-flex items-center gap-1 text-amber-300 font-medium">
                <Lock size={10} /> Held-out evaluation set
              </span>
            </>
          )}
          {selected.scenario_type === "stress" && (
            <>
              <span className="text-white/20">·</span>
              <span className="inline-flex items-center gap-1 text-rose-300 font-medium">
                <Flame size={10} /> High-load stress scenario
              </span>
            </>
          )}
        </div>
      )}

      {/* ── Inline Create Form ────────────────────────────────────── */}
      {showCreate && (
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] p-4 space-y-4">
          <p className="text-[10px] uppercase tracking-widest text-violet-400/70 font-semibold">
            New Scenario
          </p>

          {/* Scenario Type Selection */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-white/40 font-medium">Scenario Type</label>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setScenarioType("standard");
                }}
                className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition-all ${
                  scenarioType === "standard"
                    ? "border-violet-500/50 bg-violet-500/20 text-violet-200"
                    : "border-white/10 bg-white/[0.03] text-white/50 hover:text-white/80"
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
                    ? "border-rose-500/50 bg-rose-500/20 text-rose-200"
                    : "border-white/10 bg-white/[0.03] text-white/50 hover:text-white/80"
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
                    ? "border-amber-500/50 bg-amber-500/20 text-amber-200"
                    : "border-white/10 bg-white/[0.03] text-white/50 hover:text-white/80"
                }`}
              >
                <Lock size={12} /> Held-Out
              </button>
            </div>
            {scenarioType === "held_out" && (
              <p className="text-[10px] text-amber-400/80 italic">
                Held-out scenarios test the policy on traffic conditions unseen during training.
              </p>
            )}
          </div>

          {/* Name */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-white/40 font-medium">Name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={scenarioType === "held_out" ? "e.g. Unseen Peak Flow Test" : "e.g. Rush Hour Stress Test"}
              maxLength={100}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.05] border border-white/10 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-violet-500/50 transition-colors"
            />
          </div>

          {/* Seed */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-white/40 font-medium">Seed</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={newSeed}
                min={0}
                max={10000000}
                onChange={(e) => setNewSeed(Number(e.target.value))}
                className="flex-1 px-3 py-2 rounded-lg bg-white/[0.05] border border-white/10 text-sm text-white font-mono focus:outline-none focus:border-violet-500/50 transition-colors"
              />
              <button
                type="button"
                title="Regenerate random seed"
                onClick={() => setNewSeed(generateSeed())}
                className="shrink-0 p-2 rounded-lg border border-white/10 bg-white/[0.05] text-white/50 hover:text-violet-300 hover:border-violet-500/30 transition-colors"
              >
                <RefreshCw size={13} />
              </button>
            </div>
          </div>

          {/* Spawn rate slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-white/40 font-medium">Spawn rate (λ)</label>
              <span className="text-[11px] text-violet-300 font-mono">{newLambda.toFixed(1)} veh/s</span>
            </div>
            <input
              type="range"
              min={0.1} max={2.0} step={0.1}
              value={newLambda}
              onChange={(e) => setNewLambda(Number(e.target.value))}
              className="w-full h-1.5 rounded-full accent-violet-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-white/25">
              <span>Low 0.1</span>
              <span>High 2.0</span>
            </div>
          </div>

          {/* Duration slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-white/40 font-medium">Duration</label>
              <span className="text-[11px] text-violet-300 font-mono">{newDuration}s</span>
            </div>
            <input
              type="range"
              min={10} max={300} step={10}
              value={newDuration}
              onChange={(e) => setNewDuration(Number(e.target.value))}
              className="w-full h-1.5 rounded-full accent-violet-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-white/25">
              <span>10s</span>
              <span>300s</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={() => { setShowCreate(false); setNewName(""); }}
              className="flex-1 py-2 rounded-lg border border-white/10 text-white/50 hover:text-white/80 text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="flex-1 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
            >
              {creating ? "Saving…" : "Save Scenario"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

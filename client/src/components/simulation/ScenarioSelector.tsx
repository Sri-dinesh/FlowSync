/**
 * ScenarioSelector — inline scenario picker + creator for the Benchmark card.
 *
 * Features:
 *  - Dropdown of saved scenarios (name, seed, λ, duration preview)
 *  - "+ New" expander: name input, auto-generated seed with Regenerate button,
 *    λ slider, duration slider
 *  - Delete button for selected scenario
 *  - Calls parent onSelect with the chosen scenario (or null for "random")
 */
"use client";

import { useCallback, useState } from "react";
import { RefreshCw, Trash2, Plus, ChevronDown, FlaskConical } from "lucide-react";
import type { Scenario } from "@/types/simulation";
import { useScenarios } from "@/hooks/useScenarios";

interface ScenarioSelectorProps {
  selected: Scenario | null;
  onSelect: (scenario: Scenario | null) => void;
}

function generateSeed(): number {
  return Math.floor(Math.random() * 10_000_000);
}

export function ScenarioSelector({ selected, onSelect }: ScenarioSelectorProps) {
  const { scenarios, loading, createScenario, deleteScenario, fetchScenarios } = useScenarios();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSeed, setNewSeed] = useState(generateSeed);
  const [newLambda, setNewLambda] = useState(0.5);
  const [newDuration, setNewDuration] = useState(60);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setCreating(true);
    const created = await createScenario(newName.trim(), newSeed, newLambda, newDuration);
    if (created) {
      onSelect(created);
      setShowCreate(false);
      setNewName("");
      setNewSeed(generateSeed());
      setNewLambda(0.5);
      setNewDuration(60);
    }
    setCreating(false);
  }, [newName, newSeed, newLambda, newDuration, createScenario, onSelect]);

  const handleDelete = useCallback(async () => {
    if (!selected) return;
    setDeleting(true);
    const ok = await deleteScenario(selected.id);
    if (ok) onSelect(null);
    setDeleting(false);
  }, [selected, deleteScenario, onSelect]);

  return (
    <div className="scenario-selector">
      {/* Header row */}
      <div className="scenario-header">
        <FlaskConical size={14} className="scenario-icon" />
        <span className="scenario-label">Scenario</span>
      </div>

      {/* Dropdown + action buttons */}
      <div className="scenario-controls">
        <div className="scenario-dropdown-wrapper">
          <button
            className="scenario-dropdown-btn"
            onClick={() => setDropdownOpen((o) => !o)}
            type="button"
          >
            <span className="scenario-dropdown-text">
              {selected ? selected.name : "— Random seed (default) —"}
            </span>
            <ChevronDown size={14} className={`scenario-chevron ${dropdownOpen ? "open" : ""}`} />
          </button>

          {dropdownOpen && (
            <div className="scenario-dropdown-menu">
              <button
                className="scenario-option scenario-option--none"
                onClick={() => { onSelect(null); setDropdownOpen(false); }}
              >
                — Random seed (default) —
              </button>
              {loading && <div className="scenario-option-loading">Loading…</div>}
              {scenarios.map((s) => (
                <button
                  key={s.id}
                  className={`scenario-option ${selected?.id === s.id ? "active" : ""}`}
                  onClick={() => { onSelect(s); setDropdownOpen(false); }}
                >
                  <span className="scenario-option-name">{s.name}</span>
                  <span className="scenario-option-meta">
                    seed {s.seed} · λ{s.spawn_lambda.toFixed(1)} · {s.duration_seconds}s
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Add / Delete */}
        <button
          className="scenario-icon-btn"
          title="Create new scenario"
          onClick={() => setShowCreate((v) => !v)}
          type="button"
        >
          <Plus size={14} />
        </button>
        {selected && (
          <button
            className="scenario-icon-btn scenario-icon-btn--danger"
            title="Delete selected scenario"
            onClick={handleDelete}
            disabled={deleting}
            type="button"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>

      {/* Selected scenario pill */}
      {selected && (
        <div className="scenario-pill">
          <span className="scenario-pill-hash">#{selected.seed}</span>
          <span className="scenario-pill-meta">λ={selected.spawn_lambda.toFixed(1)} · {selected.duration_seconds}s</span>
        </div>
      )}

      {/* Inline create form */}
      {showCreate && (
        <div className="scenario-create-form">
          <div className="scenario-form-row">
            <label className="scenario-form-label">Name</label>
            <input
              className="scenario-form-input"
              placeholder="e.g. Rush Hour Stress Test"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="scenario-form-row">
            <label className="scenario-form-label">Seed</label>
            <div className="scenario-seed-row">
              <input
                className="scenario-form-input scenario-seed-input"
                type="number"
                value={newSeed}
                min={0}
                max={10000000}
                onChange={(e) => setNewSeed(Number(e.target.value))}
              />
              <button
                className="scenario-regen-btn"
                title="Regenerate random seed"
                onClick={() => setNewSeed(generateSeed())}
                type="button"
              >
                <RefreshCw size={13} />
              </button>
            </div>
          </div>

          <div className="scenario-form-row">
            <label className="scenario-form-label">
              Spawn rate (λ) <span className="scenario-form-value">{newLambda.toFixed(1)} veh/s</span>
            </label>
            <input
              type="range"
              className="scenario-slider"
              min={0.1} max={2.0} step={0.1}
              value={newLambda}
              onChange={(e) => setNewLambda(Number(e.target.value))}
            />
            <div className="scenario-slider-labels">
              <span>Low 0.1</span><span>High 2.0</span>
            </div>
          </div>

          <div className="scenario-form-row">
            <label className="scenario-form-label">
              Duration <span className="scenario-form-value">{newDuration}s</span>
            </label>
            <input
              type="range"
              className="scenario-slider"
              min={10} max={300} step={10}
              value={newDuration}
              onChange={(e) => setNewDuration(Number(e.target.value))}
            />
            <div className="scenario-slider-labels">
              <span>10s</span><span>300s</span>
            </div>
          </div>

          <div className="scenario-form-actions">
            <button
              className="scenario-cancel-btn"
              onClick={() => setShowCreate(false)}
              type="button"
            >
              Cancel
            </button>
            <button
              className="scenario-save-btn"
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              type="button"
            >
              {creating ? "Saving…" : "Save Scenario"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

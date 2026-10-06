"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw, Search, X } from "lucide-react";
import { getFastApiUrls } from "@/lib/utils";
import type { ResearchController, ResearchScenario } from "@/types/research";

export interface ResearchRunRow {
  run_id: string;
  scenario: string;
  scenarioName: string;
  controller: string;
  controllerName: string;
  seed: number;
  noise: string;
  steps: number;
  duration_s: number;
  avg_delay: number;
  p95_delay: number;
  throughput: number;
  status: string;
  timestamp: string;
  has_trajectory: boolean;
}

const ALL = "__all__";

function toRow(r: Record<string, unknown>): ResearchRunRow {
  const steps = Number(r.num_steps ?? r.steps ?? 0);
  return {
    run_id: String(r.experiment_id ?? r.run_id ?? ""),
    scenario: String(r.scenario_id ?? r.scenario ?? ""),
    scenarioName: String(r.scenario_id ?? r.scenario ?? ""),
    controller: String(r.controller_name ?? r.controller ?? ""),
    controllerName: String(r.controller_name ?? r.controller ?? ""),
    seed: Number(r.seed ?? 0),
    noise: String(r.noise_preset ?? r.noise ?? "clean"),
    steps,
    duration_s: Number(r.duration_s ?? steps * 0.1),
    avg_delay: Number(r.avg_delay ?? 0),
    p95_delay: Number(r.p95_delay ?? 0),
    throughput: Number(r.throughput ?? 0),
    status: String(r.status ?? (r.has_trajectory ? "COMPLETED" : "UNKNOWN")),
    timestamp: String(r.timestamp ?? ""),
    has_trajectory: Boolean(r.has_trajectory ?? true),
  };
}

/**
 * Simulation runs dashboard for the /research overview.
 * Lists every saved run with seed, controller, scenario and results,
 * filterable by the same catalogs the experiment builder uses.
 */
export function ResearchRunsDashboard() {
  const [runs, setRuns] = useState<ResearchRunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [offline, setOffline] = useState(false);

  const [scenarios, setScenarios] = useState<ResearchScenario[]>([]);
  const [controllers, setControllers] = useState<ResearchController[]>([]);
  const [noiseKeys, setNoiseKeys] = useState<string[]>([]);

  const [query, setQuery] = useState("");
  const [scenarioFilter, setScenarioFilter] = useState(ALL);
  const [controllerFilter, setControllerFilter] = useState(ALL);
  const [noiseFilter, setNoiseFilter] = useState(ALL);

  const load = async (isRefresh = false) => {
    const { httpUrl } = getFastApiUrls();
    if (isRefresh) setRefreshing(true);
    try {
      const [runsRes, scRes, ctrlRes, noiseRes] = await Promise.all([
        fetch(`${httpUrl}/research/runs?limit=100`),
        fetch(`${httpUrl}/research/scenarios`),
        fetch(`${httpUrl}/research/controllers`),
        fetch(`${httpUrl}/research/noise-presets`),
      ]);
      if (!runsRes.ok) throw new Error(`runs HTTP ${runsRes.status}`);
      const payload = await runsRes.json();
      const list = Array.isArray(payload?.runs) ? payload.runs : [];

      const scMap = new Map<string, string>();
      if (scRes.ok) {
        const scData = await scRes.json();
        const scList = (scData.scenarios || []) as ResearchScenario[];
        setScenarios(scList);
        scList.forEach((s) => scMap.set(s.scenario_id, s.name));
      }
      const ctrlMap = new Map<string, string>();
      if (ctrlRes.ok) {
        const ctrlData = await ctrlRes.json();
        const ctrlList = (ctrlData.controllers || []) as ResearchController[];
        setControllers(ctrlList);
        ctrlList.forEach((c) => ctrlMap.set(c.id, c.name));
      }
      if (noiseRes.ok) {
        const noiseData = await noiseRes.json();
        setNoiseKeys(((noiseData.presets || []) as { key: string }[]).map((p) => p.key));
      }

      setRuns(
        (list as Record<string, unknown>[]).map(toRow).map((row) => ({
          ...row,
          scenarioName: scMap.get(row.scenario) ?? row.scenario,
          controllerName: ctrlMap.get(row.controller) ?? row.controller,
        })).filter((r) => r.run_id)
      );
      setOffline(false);
    } catch {
      setOffline(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    // Initial catalog + runs fetch on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  const noiseOptions = useMemo(() => {
    const fromRuns = Array.from(new Set(runs.map((r) => r.noise).filter(Boolean)));
    return Array.from(new Set([...noiseKeys, ...fromRuns]));
  }, [runs, noiseKeys]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return runs.filter((r) => {
      if (scenarioFilter !== ALL && r.scenario !== scenarioFilter) return false;
      if (controllerFilter !== ALL && r.controller !== controllerFilter) return false;
      if (noiseFilter !== ALL && r.noise !== noiseFilter) return false;
      if (q && !r.run_id.toLowerCase().includes(q) && !r.scenario.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [runs, query, scenarioFilter, controllerFilter, noiseFilter]);

  const hasFilters = query !== "" || scenarioFilter !== ALL || controllerFilter !== ALL || noiseFilter !== ALL;
  const clearFilters = () => {
    setQuery("");
    setScenarioFilter(ALL);
    setControllerFilter(ALL);
    setNoiseFilter(ALL);
  };

  const selectClass =
    "rounded-md border border-neutral-800 bg-black/30 px-2 py-1.5 text-xs text-white focus:outline-none focus:border-neutral-600 max-w-[160px]";

  return (
    <section className="bg-neutral-900/60 border border-neutral-800 rounded-lg p-5 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-neutral-800">
        <h2 className="text-sm font-medium text-white">
          Simulation runs{" "}
          <span className="text-neutral-500 font-normal tabular-nums">
            · {loading ? "…" : `${filtered.length} of ${runs.length}`}
          </span>
        </h2>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-neutral-400 hover:text-white hover:bg-white/5 border border-neutral-800 transition-colors disabled:opacity-50"
          title="Reload runs from backend"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters — same catalogs as the experiment builder */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-600 pointer-events-none" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search run id…"
            className="rounded-md border border-neutral-800 bg-black/30 pl-7 pr-2 py-1.5 text-xs text-white placeholder:text-neutral-600 focus:outline-none focus:border-neutral-600 w-44"
          />
        </div>
        <select value={scenarioFilter} onChange={(e) => setScenarioFilter(e.target.value)} className={selectClass} title="Filter by scenario">
          <option value={ALL}>All scenarios</option>
          {scenarios.map((s) => (
            <option key={s.scenario_id} value={s.scenario_id} className="bg-neutral-900">
              {s.name}
            </option>
          ))}
        </select>
        <select value={controllerFilter} onChange={(e) => setControllerFilter(e.target.value)} className={selectClass} title="Filter by controller">
          <option value={ALL}>All controllers</option>
          {controllers.map((c) => (
            <option key={c.id} value={c.id} className="bg-neutral-900">
              {c.name}
            </option>
          ))}
        </select>
        <select value={noiseFilter} onChange={(e) => setNoiseFilter(e.target.value)} className={selectClass} title="Filter by camera fault">
          <option value={ALL}>All faults</option>
          {noiseOptions.map((n) => (
            <option key={n} value={n} className="bg-neutral-900">
              {n}
            </option>
          ))}
        </select>
        {hasFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs text-neutral-500 hover:text-white transition-colors"
          >
            <X className="h-3 w-3" /> Clear
          </button>
        )}
      </div>

      {offline && runs.length === 0 && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/[0.06] p-3 text-xs text-amber-200/90">
          Backend offline — no runs to show. Start it, run a simulation on the experiment page, and it will appear here.
        </div>
      )}

      {loading ? (
        <div className="py-10 text-center text-xs text-neutral-500 animate-pulse">Loading runs…</div>
      ) : runs.length === 0 && !offline ? (
        <div className="py-10 px-4 text-center space-y-2">
          <p className="text-[13px] font-medium text-neutral-300">No saved runs yet</p>
          <p className="text-xs text-neutral-500">
            Finished simulations are saved automatically and listed here.
          </p>
          <Link
            href="/research/experiment"
            className="inline-flex items-center gap-1.5 mt-1 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
          >
            Run your first simulation <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-10 px-4 text-center space-y-2">
          <p className="text-[13px] font-medium text-neutral-300">No runs match these filters</p>
          <button onClick={clearFilters} className="text-xs text-neutral-400 hover:text-white underline underline-offset-2">
            Clear filters
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-left text-xs whitespace-nowrap">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-500 text-[11px]">
                <th className="pb-2.5 pr-4 font-medium">Run</th>
                <th className="pb-2.5 px-3 font-medium">Scenario</th>
                <th className="pb-2.5 px-3 font-medium">Controller</th>
                <th className="pb-2.5 px-3 font-medium">Seed</th>
                <th className="pb-2.5 px-3 font-medium">Fault</th>
                <th className="pb-2.5 px-3 font-medium text-right">Steps</th>
                <th className="pb-2.5 px-3 font-medium text-right">Avg</th>
                <th className="pb-2.5 px-3 font-medium text-right">P95</th>
                <th className="pb-2.5 px-3 font-medium text-right">Cleared</th>
                <th className="pb-2.5 px-3 font-medium">Status</th>
                <th className="pb-2.5 pl-3 font-medium">Saved</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/70">
              {filtered.map((run) => (
                <tr key={run.run_id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2.5 pr-4 max-w-[220px]">
                    <Link
                      href={`/research/runs/${run.run_id}`}
                      className="font-mono tabular-nums text-indigo-300 hover:text-indigo-200 hover:underline underline-offset-2 truncate block"
                      title={`${run.run_id} — open replay`}
                    >
                      {run.run_id}
                    </Link>
                  </td>
                  <td className="py-2.5 px-3 text-neutral-300 max-w-[200px] truncate" title={run.scenario}>
                    {run.scenarioName}
                  </td>
                  <td className="py-2.5 px-3 text-neutral-300 font-mono">{run.controller}</td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-neutral-200">{run.seed}</td>
                  <td className="py-2.5 px-3 font-mono text-neutral-400">{run.noise}</td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-neutral-400 text-right">{run.steps || "—"}</td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-white text-right">{run.avg_delay ? `${run.avg_delay.toFixed(2)}s` : "—"}</td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-neutral-400 text-right">{run.p95_delay ? `${run.p95_delay.toFixed(2)}s` : "—"}</td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-white text-right">{run.throughput || "—"}</td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`rounded-full border px-1.5 py-px text-[10px] ${
                        run.status === "COMPLETED"
                          ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/10"
                          : "text-neutral-400 border-neutral-700"
                      }`}
                    >
                      {run.status === "COMPLETED" ? "Done" : run.status}
                    </span>
                  </td>
                  <td className="py-2.5 pl-3 text-neutral-500 text-[11px]">
                    {run.timestamp ? new Date(run.timestamp).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

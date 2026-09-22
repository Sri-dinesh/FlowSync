/**
 * useScenarios — CRUD hook for named benchmark scenarios.
 *
 * Provides:
 *  - scenarios list (auto-fetched on mount)
 *  - createScenario(name, seed, spawnLambda, durationSeconds)
 *  - deleteScenario(id)
 *  - fetchRuns(scenarioId) → ScenarioRun[]
 */
import { useCallback, useEffect, useState } from "react";
import { getFastApiUrls } from "@/lib/utils";
import type { Scenario, ScenarioRun } from "@/types/simulation";

export function useScenarios() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { httpUrl } = getFastApiUrls();
  const BASE = `${httpUrl}/simulation/scenarios`;

  // ─── List ───────────────────────────────────────────────────────────────────
  const fetchScenarios = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(BASE);
      if (!res.ok) throw new Error(`GET /scenarios failed: ${res.status}`);
      const data: Scenario[] = await res.json();
      setScenarios(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }, [BASE]);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  // ─── Create ─────────────────────────────────────────────────────────────────
  const createScenario = useCallback(
    async (
      name: string,
      seed: number,
      spawnLambda: number,
      durationSeconds: number,
    ): Promise<Scenario | null> => {
      setError(null);
      try {
        const res = await fetch(BASE, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            seed,
            spawn_lambda: spawnLambda,
            duration_seconds: durationSeconds,
          }),
        });
        if (!res.ok) throw new Error(`POST /scenarios failed: ${res.status}`);
        const created: Scenario = await res.json();
        setScenarios((prev) => [created, ...prev]);
        return created;
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to create scenario");
        return null;
      }
    },
    [BASE],
  );

  // ─── Delete ─────────────────────────────────────────────────────────────────
  const deleteScenario = useCallback(
    async (id: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
        if (!res.ok && res.status !== 204)
          throw new Error(`DELETE /scenarios/${id} failed: ${res.status}`);
        setScenarios((prev) => prev.filter((s) => s.id !== id));
        return true;
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to delete scenario");
        return false;
      }
    },
    [BASE],
  );

  // ─── Fetch runs for one scenario ────────────────────────────────────────────
  const fetchRuns = useCallback(
    async (scenarioId: string): Promise<ScenarioRun[]> => {
      try {
        const res = await fetch(`${BASE}/${scenarioId}/runs`);
        if (!res.ok) throw new Error(`GET runs failed: ${res.status}`);
        return await res.json();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to fetch runs");
        return [];
      }
    },
    [BASE],
  );

  return {
    scenarios,
    loading,
    error,
    fetchScenarios,
    createScenario,
    deleteScenario,
    fetchRuns,
  };
}

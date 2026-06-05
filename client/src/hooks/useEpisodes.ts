import { useQuery } from "@tanstack/react-query";

/**
 * Fetch episodes for a given simulationId.
 * If simulationId is null, fetch the most recent episodes across all simulations
 * so the History tab is never empty even before the user starts a simulation.
 */
export const useEpisodes = (simulationId: string | null) =>
  useQuery({
    queryKey: ["episodes", simulationId],
    queryFn: async () => {
      const url = simulationId
        ? `/api/episodes?simulationId=${encodeURIComponent(simulationId)}`
        : `/api/episodes`;

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch episodes");
      return response.json();
    },
    // Always fetch — don't wait for a simulationId
    enabled: true,
    // Refresh every 10s while the tab is open so new episodes appear live
    refetchInterval: 10_000,
  });

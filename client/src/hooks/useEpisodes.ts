import { useQuery } from "@tanstack/react-query";

/**
 * Fetch episodes for a given simulationId.
 * If simulationId is null, fetch the most recent episodes across all simulations
 * so the History tab is never empty even before the user starts a simulation.
 */
export const useEpisodes = (
  simulationId: string | null,
  options?: { enabled?: boolean; refetchInterval?: number | false }
) =>
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
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 10_000,
  });

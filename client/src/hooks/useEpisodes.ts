import { useQuery } from "@tanstack/react-query";

export const useEpisodes = (simulationId: string | null) =>
  useQuery({
    queryKey: ["episodes", simulationId],
    enabled: Boolean(simulationId),
    queryFn: async () => {
      if (!simulationId) {
        return [];
      }

      const response = await fetch(
        `/api/episodes?simulationId=${encodeURIComponent(simulationId)}`,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch episodes");
      }

      return response.json();
    },
  });

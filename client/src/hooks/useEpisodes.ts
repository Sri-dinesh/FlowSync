import { useQuery } from "@tanstack/react-query";

export const useEpisodes = (simulationId: string | null) =>
  useQuery({
    queryKey: ["episodes", simulationId],
    queryFn: () =>
      fetch(`/api/episodes?simulationId=${encodeURIComponent(simulationId ?? "")}`)
        .then((r) => r.json()),
    enabled: Boolean(simulationId),
  });

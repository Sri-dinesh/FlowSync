import { useQuery } from "@tanstack/react-query";

export const useSimulations = () =>
  useQuery({
    queryKey: ["simulations"],
    queryFn: () => fetch("/api/simulations").then((r) => r.json()),
  });

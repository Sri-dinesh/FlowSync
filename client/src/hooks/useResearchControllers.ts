"use client";

import { useEffect, useState } from "react";
import { parseControllers } from "@/lib/research-data";
import { getFastApiUrls } from "@/lib/utils";
import type { ResearchController } from "@/types/research";

export function useResearchControllers() {
  const [controllers, setControllers] = useState<ResearchController[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const abort = new AbortController();
    const { httpUrl } = getFastApiUrls();
    fetch(`${httpUrl}/research/controllers`, { signal: abort.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Controller catalog unavailable");
        const payload: unknown = await response.json();
        setControllers(parseControllers(payload));
      })
      .catch((err: unknown) => {
        if (!abort.signal.aborted) setError(err instanceof Error ? err.message : "Controller catalog unavailable");
      });
    return () => abort.abort();
  }, []);
  return { controllers, error };
}

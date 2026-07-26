"use client";

import { useMemo, useState } from "react";
import { useSimulationStore } from "@/store/simulationStore";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useEpisodes } from "@/hooks/useEpisodes";

interface EpisodeHistoryProps {
  simulationId: string | null;
}

import { EpisodeRecord } from "@/types/simulation";
const PAGE_SIZE = 10;

export default function EpisodeHistory({ simulationId }: EpisodeHistoryProps) {
  const { data, isLoading, error } = useEpisodes(simulationId);
  const trainingMetrics = useSimulationStore((s) => s.trainingMetrics);
  const isTraining = useSimulationStore((s) => s.isTraining);

  // While training, also show live in-memory metrics that haven't been persisted yet
  const liveCount = useMemo(
    () => trainingMetrics.filter((m) => "total_reward" in m).length,
    [trainingMetrics],
  );

  const episodes = useMemo(() => (data ?? []) as EpisodeRecord[], [data]);
  const [page, setPage] = useState(0);

  const bestId = useMemo(() => {
    if (!episodes.length) return null;
    return [...episodes].sort((a, b) => b.totalReward - a.totalReward)[0]?.id ?? null;
  }, [episodes]);

  const pageCount = Math.max(1, Math.ceil(episodes.length / PAGE_SIZE));
  const pageData = episodes.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  if (isLoading) {
    return (
      <div className="flex h-[120px] items-center justify-center text-xs text-white/30">
        Loading episodes…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[120px] items-center justify-center text-xs text-rose-400/70">
        Failed to load episode history.
      </div>
    );
  }

  if (!episodes.length) {
    return (
      <div className="flex h-[160px] flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-black/20 text-center px-4 gap-2">
        <p className="text-sm text-white/40">No episodes recorded yet.</p>
        <p className="text-xs text-white/25">
          {isTraining
            ? `Training in progress — ${liveCount} episode${liveCount !== 1 ? "s" : ""} running. Records appear here after each episode completes.`
            : "Train the agent to see episode-by-episode results here."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Live training indicator */}
      {isTraining && (
        <div className="flex items-center gap-1.5 text-[10px] text-emerald-400/70">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
          Training active — table refreshes every 10s
        </div>
      )}

      <div className="rounded-lg border border-white/5 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/5 hover:bg-transparent">
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">Ep</TableHead>
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">Reward</TableHead>
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">Wait</TableHead>
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">Thru</TableHead>
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">ε</TableHead>
              <TableHead className="text-white/40 text-[10px] uppercase tracking-wider">Dur</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pageData.map((ep) => (
              <TableRow
                key={ep.id}
                className={`border-white/5 text-xs ${
                  ep.id === bestId
                    ? "bg-emerald-500/10 text-emerald-200"
                    : "text-white/60 hover:bg-white/3"
                }`}
              >
                <TableCell className="font-medium">{ep.episodeNumber}</TableCell>
                <TableCell className={ep.totalReward >= 0 ? "text-sky-400" : "text-rose-400"}>
                  {ep.totalReward.toFixed(1)}
                </TableCell>
                <TableCell>{ep.avgWaitTime.toFixed(1)}s</TableCell>
                <TableCell>{ep.throughput}</TableCell>
                <TableCell className="text-yellow-400/80">{ep.epsilon.toFixed(3)}</TableCell>
                <TableCell>{(ep.steps * 0.1).toFixed(0)}s</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between text-[10px] text-white/35">
        <span>{episodes.length} episode{episodes.length !== 1 ? "s" : ""} total</span>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-[10px] text-white/50 hover:text-white"
            onClick={() => setPage((p) => Math.max(p - 1, 0))}
            disabled={page === 0}
          >
            ← Prev
          </Button>
          <span className="text-white/30">{page + 1} / {pageCount}</span>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-[10px] text-white/50 hover:text-white"
            onClick={() => setPage((p) => Math.min(p + 1, pageCount - 1))}
            disabled={page >= pageCount - 1}
          >
            Next →
          </Button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";

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

interface EpisodeRecord {
  id: string;
  episodeNumber: number;
  totalReward: number;
  avgWaitTime: number;
  throughput: number;
  epsilon: number;
  steps: number;
}

const PAGE_SIZE = 10;

export default function EpisodeHistory({ simulationId }: EpisodeHistoryProps) {
  const { data } = useEpisodes(simulationId);
  const episodes = useMemo(() => (data ?? []) as EpisodeRecord[], [data]);
  const [page, setPage] = useState(0);

  const bestId = useMemo(() => {
    if (!episodes.length) {
      return null;
    }
    const best = [...episodes].sort((a, b) => b.totalReward - a.totalReward)[0];
    return best?.id ?? null;
  }, [episodes]);

  const pageCount = Math.ceil(episodes.length / PAGE_SIZE);
  const pageData = episodes.slice(
    page * PAGE_SIZE,
    page * PAGE_SIZE + PAGE_SIZE,
  );

  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Episode</TableHead>
            <TableHead>Reward</TableHead>
            <TableHead>Avg Wait</TableHead>
            <TableHead>Throughput</TableHead>
            <TableHead>Epsilon</TableHead>
            <TableHead>Duration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pageData.map((episode) => (
            <TableRow
              key={episode.id}
              className={
                episode.id === bestId
                  ? "bg-emerald-500/10 text-emerald-100"
                  : ""
              }
            >
              <TableCell>{episode.episodeNumber}</TableCell>
              <TableCell>{episode.totalReward.toFixed(1)}</TableCell>
              <TableCell>{episode.avgWaitTime.toFixed(1)}</TableCell>
              <TableCell>{episode.throughput}</TableCell>
              <TableCell>{episode.epsilon.toFixed(2)}</TableCell>
              <TableCell>{(episode.steps * 0.1).toFixed(1)}s</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between text-xs text-white/60">
        <span>
          Page {page + 1} of {pageCount || 1}
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
            disabled={page === 0}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((prev) => Math.min(prev + 1, pageCount - 1))}
            disabled={page >= pageCount - 1}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}

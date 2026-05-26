"use client";

import { Badge } from "@/components/ui/badge";

interface AIStatusBadgeProps {
  isTraining: boolean;
  currentEpisode: number;
  targetEpisodes: number | null;
}

export default function AIStatusBadge({
  isTraining,
  currentEpisode,
  targetEpisodes,
}: AIStatusBadgeProps) {
  if (isTraining) {
    return (
      <Badge
        className="border-amber-400/40 bg-amber-500/20 text-amber-100"
        variant="outline"
      >
        Training (Ep {currentEpisode}/{targetEpisodes ?? "-"})
      </Badge>
    );
  }

  if (currentEpisode > 0) {
    return (
      <Badge
        className="border-emerald-400/40 bg-emerald-500/20 text-emerald-100"
        variant="outline"
      >
        Ready
      </Badge>
    );
  }

  return (
    <Badge
      className="border-white/15 bg-white/5 text-white/70"
      variant="outline"
    >
      Idle
    </Badge>
  );
}

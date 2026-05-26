"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import AIStatusBadge from "@/components/dashboard/AIStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSimulationStore } from "@/store/simulationStore";

interface RLModel {
  id: string;
  name: string;
  version: string;
}

interface TrainingControlsProps {
  sendCommand: (command: Record<string, unknown>) => void;
  simulationId: string | null;
}

export default function TrainingControls({
  sendCommand,
  simulationId,
}: TrainingControlsProps) {
  const isTraining = useSimulationStore((state) => state.isTraining);
  const trainingMetrics = useSimulationStore((state) => state.trainingMetrics);
  const setTraining = useSimulationStore((state) => state.setTraining);

  const [showConfig, setShowConfig] = useState(false);
  const [numEpisodes, setNumEpisodes] = useState(500);
  const [targetEpisodes, setTargetEpisodes] = useState<number | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [isLoadingModel, setIsLoadingModel] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [trainInfo, setTrainInfo] = useState<string | null>(null);

  const { data: models = [] } = useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const baseUrl = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL;
      if (!baseUrl) {
        return [] as RLModel[];
      }

      const response = await fetch(`${baseUrl}/training/models`);
      if (!response.ok) {
        return [] as RLModel[];
      }

      const payload = (await response.json()) as { models?: RLModel[] };
      return payload.models ?? [];
    },
  });

  const currentEpisode = useMemo(() => {
    const latest = trainingMetrics[trainingMetrics.length - 1];
    return latest?.episode ?? 0;
  }, [trainingMetrics]);

  const progress = useMemo(() => {
    if (!isTraining || !targetEpisodes) {
      return 0;
    }
    return Math.min(1, currentEpisode / targetEpisodes);
  }, [currentEpisode, isTraining, targetEpisodes]);

  const startTraining = () => {
    setTargetEpisodes(numEpisodes);
    setTraining(true);
    setTrainInfo(
      "Training runs episodes in the background. A model checkpoint is saved at the end so you can load it.",
    );
    sendCommand({
      command: "start_training",
      num_episodes: numEpisodes,
      simulation_id: simulationId ?? undefined,
    });
    setShowConfig(false);
  };

  const stopTraining = () => {
    setTraining(false);
    sendCommand({ command: "stop_training" });
  };

  const loadModel = async (modelId: string) => {
    if (!modelId) {
      return;
    }

    const baseUrl = process.env.NEXT_PUBLIC_FASTAPI_HTTP_URL;
    if (!baseUrl) {
      setLoadError("FastAPI URL is not configured.");
      return;
    }

    setIsLoadingModel(true);
    setLoadError(null);
    try {
      const response = await fetch(`${baseUrl}/training/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        setLoadError(payload?.detail ?? "Unable to load the selected model.");
      }
    } catch {
      setLoadError("Unable to reach the training server.");
    } finally {
      setIsLoadingModel(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <AIStatusBadge
          isTraining={isTraining}
          currentEpisode={currentEpisode}
          targetEpisodes={targetEpisodes}
        />
        {isTraining ? (
          <Button
            size="sm"
            variant="outline"
            className="border-rose-500/30 bg-rose-500/10 text-rose-300"
            onClick={stopTraining}
          >
            Stop Training
          </Button>
        ) : (
          <Button size="sm" onClick={() => setShowConfig((prev) => !prev)}>
            Train Agent
          </Button>
        )}
      </div>
      {trainInfo && <p className="text-xs text-emerald-200/90">{trainInfo}</p>}

      {showConfig && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <label className="text-xs text-white/70">Episodes</label>
          <input
            type="number"
            min={1}
            max={2000}
            className="mt-2 w-full rounded-md border border-white/10 bg-black/40 px-3 py-2 text-sm text-white"
            value={numEpisodes}
            onChange={(event) => setNumEpisodes(Number(event.target.value))}
          />
          <div className="mt-3 flex gap-2">
            <Button size="sm" onClick={startTraining}>
              Start
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowConfig(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {isTraining && (
        <div>
          <div className="flex items-center justify-between text-xs text-white/45">
            <span>Episode Progress</span>
            <span>
              {currentEpisode}/{targetEpisodes ?? "-"}
            </span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-emerald-400/80"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      <div className="space-y-2">
        <div className="text-xs text-white/50">Load Model</div>
        <Select
          value={selectedModelId}
          onValueChange={(value) => {
            setSelectedModelId(value);
            loadModel(value);
          }}
        >
          <SelectTrigger className="w-full border-white/15 bg-black/40 text-white/70">
            <SelectValue placeholder="Select saved model" />
          </SelectTrigger>
          <SelectContent>
            {models.length === 0 && (
              <SelectItem value="__none" disabled>
                No trained models yet
              </SelectItem>
            )}
            {models.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                {model.name} v{model.version}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isLoadingModel && (
          <div className="flex items-center gap-2 text-xs text-white/60">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading checkpoint...
          </div>
        )}
        {loadError && (
          <div className="text-xs text-rose-200" role="status">
            {loadError}
          </div>
        )}
      </div>
    </div>
  );
}

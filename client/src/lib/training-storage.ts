type StorageOutcome = "local" | "cloud" | "unreported";

function storageOutcome(value: unknown, modelId: string, slot: number): StorageOutcome {
  if (
    value === null || typeof value !== "object" ||
    !("schema_version" in value) || value.schema_version !== "checkpoint_receipt_v1" ||
    !("model_id" in value) || value.model_id !== modelId ||
    !("checkpoint_slot" in value) || value.checkpoint_slot !== slot ||
    !("sha256" in value) || typeof value.sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.sha256) ||
    !("local_saved" in value) || value.local_saved !== true ||
    !("cloud_uploaded" in value) || typeof value.cloud_uploaded !== "boolean"
  ) return "unreported";
  return value.cloud_uploaded ? "cloud" : "local";
}

export function checkpointSaveStatus(value: unknown): string {
  if (
    value === null || typeof value !== "object" ||
    !("model_id" in value) || typeof value.model_id !== "string" ||
    !("episode" in value) || typeof value.episode !== "number" ||
    !Number.isInteger(value.episode) || value.episode < 0
  ) return "Checkpoint storage status unavailable";

  const outcome = storageOutcome("storage" in value ? value.storage : null, value.model_id, value.episode);
  const label = `Checkpoint at episode ${value.episode}`;
  if (outcome === "unreported") return `${label}: storage status not reported`;
  if (outcome === "local") return `${label} saved locally. Cloud upload failed.`;
  const alias = storageOutcome("selected_alias_storage" in value ? value.selected_alias_storage : null, value.model_id, 0);
  return alias === "local"
    ? `${label} saved locally and uploaded to cloud. Selected checkpoint alias remains local.`
    : `${label} saved locally and uploaded to cloud.`;
}

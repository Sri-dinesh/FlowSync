import io
from pathlib import Path
from typing import Any, Dict, List

import torch

from .supabase_service import supabase_client

BUCKET_NAME = "model-checkpoints"
LOCAL_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def _checkpoint_path(model_id: str, episode: int) -> str:
    return f"models/{model_id}/checkpoint_{episode}.pt"


def _local_checkpoint_path(model_id: str, episode: int) -> Path:
    return LOCAL_MODELS_DIR / model_id / f"checkpoint_{episode}.pt"


def save_checkpoint(model_id: str, episode: int, state_dict: Dict[str, Any]) -> None:
    local_path = _local_checkpoint_path(model_id, episode)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state_dict, local_path)

    path = _checkpoint_path(model_id, episode)
    buffer = io.BytesIO()
    torch.save(state_dict, buffer)
    buffer.seek(0)
    try:
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=buffer,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
    except Exception:
        # Local checkpoints are still available when Supabase storage is blocked.
        return


def load_checkpoint(model_id: str, episode: int) -> Dict[str, Any]:
    path = _checkpoint_path(model_id, episode)
    try:
        data = supabase_client.storage.from_(BUCKET_NAME).download(path)
        buffer = io.BytesIO(data)
        return torch.load(buffer, map_location="cpu")
    except Exception:
        local_path = _local_checkpoint_path(model_id, episode)
        return torch.load(local_path, map_location="cpu")


def list_checkpoints(model_id: str) -> List[str]:
    folder = f"models/{model_id}"
    try:
        items = supabase_client.storage.from_(BUCKET_NAME).list(
            folder,
            {
                "limit": 1000,
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if items:
            return [f"{folder}/{item['name']}" for item in items if item.get("name")]
    except Exception:
        pass

    local_dir = LOCAL_MODELS_DIR / model_id
    if not local_dir.exists():
        return []

    checkpoints = sorted(local_dir.glob("checkpoint_*.pt"))
    return [f"{folder}/{path.name}" for path in checkpoints]


def list_local_models() -> List[Dict[str, Any]]:
    if not LOCAL_MODELS_DIR.exists():
        return []

    models: List[Dict[str, Any]] = []
    for model_dir in LOCAL_MODELS_DIR.iterdir():
        if not model_dir.is_dir():
            continue

        checkpoints = sorted(model_dir.glob("checkpoint_*.pt"))
        if not checkpoints:
            continue

        latest_name = checkpoints[-1].name
        episode_text = latest_name[len("checkpoint_") : -len(".pt")]
        latest_episode = int(episode_text) if episode_text.isdigit() else 0

        models.append(
            {
                "id": model_dir.name,
                "name": f"Local {model_dir.name[:8]}",
                "version": str(latest_episode),
                "source": "local",
            }
        )

    return models

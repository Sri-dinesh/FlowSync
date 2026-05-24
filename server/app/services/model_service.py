import io
from typing import Any, Dict, List

import torch

from .supabase_service import supabase_client

BUCKET_NAME = "model-checkpoints"


def _checkpoint_path(model_id: str, episode: int) -> str:
    return f"models/{model_id}/checkpoint_{episode}.pt"


def save_checkpoint(model_id: str, episode: int, state_dict: Dict[str, Any]) -> None:
    path = _checkpoint_path(model_id, episode)
    buffer = io.BytesIO()
    torch.save(state_dict, buffer)
    buffer.seek(0)
    supabase_client.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=buffer,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )


def load_checkpoint(model_id: str, episode: int) -> Dict[str, Any]:
    path = _checkpoint_path(model_id, episode)
    data = supabase_client.storage.from_(BUCKET_NAME).download(path)
    buffer = io.BytesIO(data)
    return torch.load(buffer, map_location="cpu")


def list_checkpoints(model_id: str) -> List[str]:
    folder = f"models/{model_id}"
    items = supabase_client.storage.from_(BUCKET_NAME).list(
        folder,
        {
            "limit": 1000,
            "offset": 0,
            "sortBy": {"column": "name", "order": "asc"},
        },
    )
    if not items:
        return []
    return [f"{folder}/{item['name']}" for item in items if item.get("name")]

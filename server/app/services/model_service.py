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
    # supabase-py v2 upload() requires bytes, not a file-like object
    raw_bytes = buffer.getvalue()
    try:
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=raw_bytes,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Supabase storage upload failed for %s episode %d: %s", model_id, episode, exc
        )


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


def list_all_models() -> List[Dict[str, Any]]:
    """List models from the rl_models DB table, Supabase Storage, and local disk (deduplicated)."""
    import logging
    logger = logging.getLogger(__name__)
    models: Dict[str, Dict[str, Any]] = {}

    # --- Primary source: rl_models database table ---
    # save_model_metadata() always writes here, making this the most reliable source.
    try:
        result = supabase_client.table("rl_models").select("*").execute()
        rows = getattr(result, "data", []) or []
        for row in rows:
            model_id = row.get("id")
            if not model_id:
                continue
            total_ep = row.get("totalEpisodes") or 0
            version = row.get("version", str(total_ep))
            models[model_id] = {
                "id": model_id,
                "name": row.get("name") or f"Model {model_id[:8]}",
                "version": version,
                "source": "remote",
                "episodes": int(version) if str(version).isdigit() else total_ep,
                "avg_reward": row.get("avgReward"),
                "is_active": row.get("isActive", False),
            }
    except Exception:
        logger.warning("rl_models table query failed, falling back to storage listing", exc_info=True)

    # --- Secondary source: Supabase Storage bucket ---
    # Adds any models that exist in storage but were not recorded in rl_models.
    try:
        top_level = supabase_client.storage.from_(BUCKET_NAME).list("models")
        if top_level:
            for entry in top_level:
                model_id = entry.get("name")
                if not model_id:
                    continue
                if model_id in models:
                    # Already found in DB — skip to avoid overwriting richer metadata
                    continue
                folder = f"models/{model_id}"
                try:
                    checkpoints = supabase_client.storage.from_(BUCKET_NAME).list(
                        folder,
                        {"limit": 1000, "offset": 0, "sortBy": {"column": "name", "order": "asc"}},
                    )
                    if not checkpoints:
                        continue
                    episodes = []
                    for c in checkpoints:
                        name = c.get("name", "")
                        if name.startswith("checkpoint_") and name.endswith(".pt"):
                            ep_text = name[len("checkpoint_"):-len(".pt")]
                            if ep_text.isdigit():
                                episodes.append(int(ep_text))
                    if not episodes:
                        continue
                    latest_ep = max(episodes)
                    models[model_id] = {
                        "id": model_id,
                        "name": f"Model {model_id[:8]}",
                        "version": str(latest_ep),
                        "source": "remote",
                        "episodes": latest_ep,
                    }
                except Exception:
                    pass
    except Exception:
        logger.warning("Supabase storage listing failed", exc_info=True)

    # --- Tertiary source: local disk (dev / offline fallback) ---
    if LOCAL_MODELS_DIR.exists():
        for model_dir in LOCAL_MODELS_DIR.iterdir():
            if not model_dir.is_dir():
                continue
            checkpoints = sorted(model_dir.glob("checkpoint_*.pt"))
            if not checkpoints:
                continue
            latest_name = checkpoints[-1].name
            ep_text = latest_name[len("checkpoint_"):-len(".pt")]
            latest_ep = int(ep_text) if ep_text.isdigit() else 0
            model_id = model_dir.name
            if model_id not in models:
                models[model_id] = {
                    "id": model_id,
                    "name": f"Model {model_id[:8]}",
                    "version": str(latest_ep),
                    "source": "local",
                    "episodes": latest_ep,
                }

    # Sort by episode count descending so the most-trained model appears first
    return sorted(models.values(), key=lambda m: m["episodes"], reverse=True)


def list_local_models() -> List[Dict[str, Any]]:
    """Kept for backward compatibility — delegates to list_all_models."""
    return list_all_models()

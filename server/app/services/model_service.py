import datetime
import io
from pathlib import Path
from typing import Any, Dict, List
import time
from functools import wraps

import torch

from .supabase_service import supabase_client, retry_on_transient_error

BUCKET_NAME = "model-checkpoints"
LOCAL_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def _checkpoint_path(model_id: str, episode: int) -> str:
    clean_id = model_id.split(":")[0] if ":" in model_id else model_id
    return f"models/{clean_id}/checkpoint_{episode}.pt"


def _local_checkpoint_path(model_id: str, episode: int) -> Path:
    clean_id = model_id.split(":")[0] if ":" in model_id else model_id
    return LOCAL_MODELS_DIR / clean_id / f"checkpoint_{episode}.pt"


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
        import logging
        logging.getLogger(__name__).info(
            "Successfully uploaded checkpoint %s (%d bytes) to Supabase Storage bucket '%s'",
            path, len(raw_bytes), BUCKET_NAME
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
        checkpoint = torch.load(buffer, map_location="cpu")
    except Exception:
        local_path = _local_checkpoint_path(model_id, episode)
        checkpoint = torch.load(local_path, map_location="cpu")

    # Handle old format (raw state dict) vs new format (dict with keys)
    if isinstance(checkpoint, dict) and 'online_net' in checkpoint:
        return checkpoint  # new format
    else:
        # Old format — wrap it
        return {'online_net': checkpoint, 'target_net': checkpoint}


def list_checkpoints(model_id: str) -> List[str]:
    clean_id = model_id.split(":")[0] if ":" in model_id else model_id
    folder = f"models/{clean_id}"
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

    local_dir = LOCAL_MODELS_DIR / clean_id
    if not local_dir.exists():
        return []

    checkpoints = sorted(local_dir.glob("checkpoint_*.pt"))
    return [f"{folder}/{path.name}" for path in checkpoints]


@retry_on_transient_error(max_retries=3)
def _fetch_rl_models_from_db() -> List[Dict[str, Any]]:
    """Fetch RL model metadata from database with retry logic."""
    result = supabase_client.table("rl_models").select("*").execute()
    return getattr(result, "data", []) or []


def list_all_models() -> List[Dict[str, Any]]:
    """List all available model checkpoints from rl_models DB, Supabase Storage, and local disk."""
    import logging
    logger = logging.getLogger(__name__)
    models_dict: Dict[str, Dict[str, Any]] = {}

    # 1. Fetch metadata from rl_models database table
    db_meta: Dict[str, Dict[str, Any]] = {}
    try:
        rows = _fetch_rl_models_from_db()
        for row in rows:
            mid = row.get("id")
            if mid:
                db_meta[mid] = row
    except Exception:
        logger.warning("rl_models table query failed", exc_info=True)

    # 2. Collect all model IDs across DB, local disk, and remote storage
    all_model_ids = set(db_meta.keys())
    if LOCAL_MODELS_DIR.exists():
        for d in LOCAL_MODELS_DIR.iterdir():
            if d.is_dir():
                all_model_ids.add(d.name)

    try:
        top_level = supabase_client.storage.from_(BUCKET_NAME).list("models")
        if top_level:
            for entry in top_level:
                name = entry.get("name")
                if name:
                    all_model_ids.add(name)
    except Exception:
        pass

    # 3. For each model ID, discover all checkpoints
    for model_id in all_model_ids:
        row = db_meta.get(model_id, {})
        base_name = row.get("name") or f"Model {model_id[:8]}"
        created_at_str = row.get("createdAt")

        date_part = ""
        if created_at_str:
            try:
                dt = datetime.datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                date_part = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        episodes_found = set()
        remote_eps = set()

        # Check Supabase Storage
        folder = f"models/{model_id}"
        try:
            items = supabase_client.storage.from_(BUCKET_NAME).list(
                folder,
                {"limit": 1000, "offset": 0, "sortBy": {"column": "name", "order": "asc"}},
            )
            if items:
                for item in items:
                    name = item.get("name", "")
                    if name.startswith("checkpoint_") and name.endswith(".pt"):
                        ep_text = name[len("checkpoint_"):-len(".pt")]
                        if ep_text.isdigit():
                            ep_num = int(ep_text)
                            episodes_found.add(ep_num)
                            remote_eps.add(ep_num)
        except Exception:
            pass

        # Check Local Disk
        local_dir = LOCAL_MODELS_DIR / model_id
        if local_dir.exists():
            for p in local_dir.glob("checkpoint_*.pt"):
                ep_text = p.name[len("checkpoint_"):-len(".pt")]
                if ep_text.isdigit():
                    ep_num = int(ep_text)
                    episodes_found.add(ep_num)
                    if not date_part:
                        try:
                            dt = datetime.datetime.fromtimestamp(p.stat().st_mtime)
                            date_part = dt.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass

        if not date_part:
            date_part = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # If no checkpoint files were found, but DB had a row, preserve DB entry
        if not episodes_found and row:
            total_ep = row.get("totalEpisodes") or 0
            version = str(row.get("version", total_ep))
            models_dict[model_id] = {
                "id": model_id,
                "name": base_name,
                "version": version,
                "source": "remote",
                "in_cloud": True,
                "storage_location": "Supabase Cloud",
                "episodes": int(version) if version.isdigit() else total_ep,
                "avg_reward": row.get("avgReward"),
                "is_active": row.get("isActive", False),
            }
            continue

        # Completed final models for this run (ignore intermediate training checkpoints)
        if str(model_id).startswith("local-test") or str(model_id).startswith("test-"):
            continue

        sorted_eps = sorted(episodes_found, reverse=True)
        max_ep = sorted_eps[0] if sorted_eps else 0
        if max_ep <= 0:
            continue

        completed_episodes = [max_ep]
        for milestone in (2000, 1500, 1000, 500, 300, 200, 100):
            if milestone in episodes_found and milestone not in completed_episodes:
                completed_episodes.append(milestone)

        for ep in completed_episodes:
            key = f"{model_id}:{ep}"
            is_remote = ep in remote_eps
            is_local = (LOCAL_MODELS_DIR / model_id / f"checkpoint_{ep}.pt").exists()

            # If local exists but not in remote storage, auto-sync to Supabase Cloud Storage bucket
            if is_local and not is_remote:
                try:
                    local_pt = LOCAL_MODELS_DIR / model_id / f"checkpoint_{ep}.pt"
                    with open(local_pt, "rb") as lf:
                        raw_bytes = lf.read()
                    supabase_client.storage.from_(BUCKET_NAME).upload(
                        path=f"models/{model_id}/checkpoint_{ep}.pt",
                        file=raw_bytes,
                        file_options={"content-type": "application/octet-stream", "upsert": "true"},
                    )
                    is_remote = True
                    remote_eps.add(ep)
                    logger.info("Auto-synced local checkpoint %s to Supabase Cloud Storage bucket", local_pt)
                except Exception as sync_err:
                    logger.warning("Failed to auto-sync local checkpoint %s to Supabase: %s", key, sync_err)

            source = "remote" if is_remote else "local"

            is_finetuned = "-ft-" in model_id
            scenario_name = None
            if is_finetuned:
                parts = model_id.split("-ft-")
                scenario_raw = parts[-1] if len(parts) > 1 else ""
                scenario_clean = scenario_raw.replace("_", " ").title()
                scenario_name = scenario_clean
                label = f"⚡ FT [{scenario_clean}] - {ep}eps ({date_part})"
            else:
                label = f"Model {date_part} - {ep}eps"

            if ep == max_ep and row.get("avgReward") is not None:
                # Calibrated for both legacy positive rewards and modern delay-anchored rewards (-300 is excellent, -600 is fair, <-1000 is failing)
                r_val = float(row.get("avgReward") or 0)
                if r_val >= 150 or r_val >= -350:
                    status_word = "Excellent"
                elif r_val >= -600:
                    status_word = "Fair"
                else:
                    status_word = "Needs Tuning"
                if is_finetuned:
                    label = f"⚡ FT [{scenario_name}] - {ep}eps - {status_word}"
                else:
                    label = f"Model {date_part} - {ep}eps - {status_word}"

            models_dict[key] = {
                "id": key,
                "name": label,
                "version": str(ep),
                "source": source,
                "in_cloud": is_remote,
                "storage_location": "Supabase Cloud" if is_remote else "Local Disk",
                "episodes": ep,
                "avg_reward": row.get("avgReward") if ep == max_ep else None,
                "is_active": row.get("isActive", False) if ep == max_ep else False,
                "is_finetuned": is_finetuned,
                "scenario": scenario_name,
            }

    # Sort descending by episode count, then name
    return sorted(models_dict.values(), key=lambda m: (m["episodes"], m.get("name", "")), reverse=True)


def list_local_models() -> List[Dict[str, Any]]:
    """Kept for backward compatibility — delegates to list_all_models."""
    return list_all_models()

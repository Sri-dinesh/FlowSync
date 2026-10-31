import datetime
import hashlib
import io
from pathlib import Path
import re
import threading
from typing import Any, Dict, List
import time

import torch

from .artifact_files import write_bytes_atomic
from .checkpoint_loading import parse_model_request
from .supabase_service import supabase_client, retry_on_transient_error

BUCKET_NAME = "model-checkpoints"
LOCAL_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_MODEL_LIST_CACHE_TTL_SECONDS = 10.0
_model_list_lock = threading.Lock()
_model_list_cache: List[Dict[str, Any]] = []
_model_list_cache_deadline = 0.0
_LEGACY_REWARD_RATING_RE = re.compile(
    r"\s*-\s*(?:Excellent|Efficient|Fair|Poor|Failing|Needs Tuning)"
    r"(?=\s*(?:—|$))",
    re.IGNORECASE,
)


def _clean_model_name(value: Any, fallback: str) -> str:
    """Strip obsolete ratings derived from non-comparable raw rewards."""
    if not isinstance(value, str) or not value.strip():
        return fallback
    return _LEGACY_REWARD_RATING_RE.sub("", value).strip()


def _invalidate_model_list_cache() -> None:
    global _model_list_cache_deadline
    _model_list_cache_deadline = 0.0


def _checkpoint_path(model_id: str, episode: int) -> str:
    clean_id,_ = parse_model_request(model_id,episode)
    return f"models/{clean_id}/checkpoint_{episode}.pt"


def _local_checkpoint_path(model_id: str, episode: int) -> Path:
    clean_id,_ = parse_model_request(model_id,episode)
    root = LOCAL_MODELS_DIR.resolve()
    path = (root / clean_id / f"checkpoint_{episode}.pt").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Checkpoint path leaves local model storage")
    return path


def save_checkpoint(model_id: str, episode: int, state_dict: Dict[str, Any]) -> dict:
    local_path = _local_checkpoint_path(model_id, episode)
    path = _checkpoint_path(model_id, episode)
    buffer = io.BytesIO()
    torch.save(state_dict, buffer)
    raw_bytes = buffer.getvalue()
    write_bytes_atomic(local_path,raw_bytes)
    _invalidate_model_list_cache()
    uploaded = False
    try:
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=raw_bytes,
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
        uploaded = True
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
    receipt = {"schema_version":"checkpoint_receipt_v1","model_id":parse_model_request(model_id,episode)[0],
        "checkpoint_slot":episode,"sha256":hashlib.sha256(raw_bytes).hexdigest(),"size_bytes":len(raw_bytes),
        "local_saved":True,"cloud_uploaded":uploaded}
    return receipt


def load_checkpoint(model_id: str, episode: int, *, expected_sha256: str | None = None) -> Dict[str, Any]:
    path = _checkpoint_path(model_id, episode)
    local_path = _local_checkpoint_path(model_id,episode)
    if expected_sha256 is not None and (not isinstance(expected_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_sha256)):
        raise ValueError("Expected checkpoint SHA-256 must be 64 lowercase hexadecimal characters")
    if local_path.is_file():
        data,origin = local_path.read_bytes(),"local"
    else:
        data,origin = supabase_client.storage.from_(BUCKET_NAME).download(path),"supabase"
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Checkpoint bytes differ from the expected SHA-256")
    checkpoint = torch.load(io.BytesIO(data),map_location="cpu",weights_only=True)
    if not isinstance(checkpoint,dict):
        raise ValueError("Checkpoint must contain a state dictionary")
    checkpoint["storage_provenance"] = {"source":origin,"sha256":digest,"size_bytes":len(data),
        "model_id":parse_model_request(model_id,episode)[0],"checkpoint_slot":episode}
    return checkpoint


def list_checkpoints(model_id: str) -> List[str]:
    clean_id,_ = parse_model_request(model_id,None)
    folder = f"models/{clean_id}"
    names = set()
    try:
        items = supabase_client.storage.from_(BUCKET_NAME).list(
            folder,
            {
                "limit": 1000,
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        names.update(item["name"] for item in items if re.fullmatch(r"checkpoint_\d+\.pt",str(item.get("name",""))))
    except Exception:
        pass

    local_dir = _local_checkpoint_path(clean_id,0).parent
    names.update(path.name for path in local_dir.glob("checkpoint_*.pt") if re.fullmatch(r"checkpoint_\d+\.pt",path.name))
    return [f"{folder}/{name}" for name in sorted(names)]


@retry_on_transient_error(max_retries=3)
def _fetch_rl_models_from_db() -> List[Dict[str, Any]]:
    """Fetch RL model metadata from database with retry logic."""
    result = supabase_client.table("rl_models").select("*").execute()
    return getattr(result, "data", []) or []


def _list_all_models_uncached() -> List[Dict[str, Any]]:
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
    except Exception as exc:
        logger.warning("rl_models table query failed: %s", exc)

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
        base_name = _clean_model_name(
            row.get("name"), f"Model {model_id[:8]}"
        )
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

        # Slot zero is a selected-checkpoint alias. Its filename alone does
        # not establish how it was selected or whether validation was held out.
        if 0 in episodes_found:
            best_is_remote = 0 in remote_eps
            best_is_local = (
                LOCAL_MODELS_DIR / model_id / "checkpoint_0.pt"
            ).exists()
            models_dict[f"{model_id}:0"] = {
                "id": f"{model_id}:0",
                "name": f"{base_name} — Selected checkpoint (slot 0; {date_part})",
                "version": "best",
                "source": "remote" if best_is_remote else "local",
                "in_cloud": best_is_remote,
                "storage_location": (
                    "Supabase Cloud" if best_is_remote else "Local Disk"
                ),
                "episodes": 0,
                "checkpoint_episode": 0,
                "avg_reward": row.get("avgReward"),
                "is_active": row.get("isActive", False),
                "is_best": True,  # Legacy UI flag for slot zero, not validation evidence.
                "is_finetuned": "-ft-" in model_id,
                "sort_date": date_part,
            }

        completed_episodes = [max_ep]
        for milestone in (2000, 1500, 1000, 500, 300, 200, 100):
            if milestone in episodes_found and milestone not in completed_episodes:
                completed_episodes.append(milestone)

        for ep in completed_episodes:
            key = f"{model_id}:{ep}"
            is_remote = ep in remote_eps
            is_local = (LOCAL_MODELS_DIR / model_id / f"checkpoint_{ep}.pt").exists()

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
                "sort_date": date_part,
            }

    # Sort descending by episode count, then name
    return sorted(
        models_dict.values(),
        key=lambda m: (
            bool(m.get("is_best")),
            m.get("sort_date", "") if m.get("is_best") else "",
            m["episodes"],
            m.get("name", ""),
        ),
        reverse=True,
    )


def list_all_models() -> List[Dict[str, Any]]:
    """Return a short-lived, serialized model catalog.

    Multiple website panels poll this endpoint. Coalescing those reads prevents
    concurrent DB/storage discovery from hammering one Supabase connection.
    """
    global _model_list_cache, _model_list_cache_deadline
    now = time.monotonic()
    if _model_list_cache and now < _model_list_cache_deadline:
        return [dict(model) for model in _model_list_cache]

    with _model_list_lock:
        now = time.monotonic()
        if _model_list_cache and now < _model_list_cache_deadline:
            return [dict(model) for model in _model_list_cache]

        models = _list_all_models_uncached()
        _model_list_cache = [dict(model) for model in models]
        _model_list_cache_deadline = now + _MODEL_LIST_CACHE_TTL_SECONDS
        return [dict(model) for model in models]


def list_local_models() -> List[Dict[str, Any]]:
    """Kept for backward compatibility — delegates to list_all_models."""
    return list_all_models()

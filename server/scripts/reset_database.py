#!/usr/bin/env python3
"""
reset_database.py — Fresh Reset of Supabase Database, Storage & Local Models
=============================================================================
Safely deletes:
  - All records in Supabase tables: performance_metrics, traffic_logs, signal_states,
    episodes, simulations, rl_models.
  - All checkpoints in Supabase Storage bucket 'model-checkpoints'.
  - All local checkpoint folders in server/models/.
  - All local session recordings in server/data/sessions/.
  - All old generated chart files in server/scripts/charts/.
"""
import os
import sys
import shutil
from pathlib import Path

# Ensure working directory and sys.path is server
server_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(server_dir))
os.chdir(server_dir)

from app.services.supabase_service import supabase_client
from app.services.model_service import BUCKET_NAME, LOCAL_MODELS_DIR

TABLES_IN_ORDER = [
    "performance_metrics",
    "traffic_logs",
    "signal_states",
    "episodes",
    "simulations",
    "rl_models",
]


def reset_supabase_tables():
    print("\n--- 1. Resetting Supabase Database Tables ---")
    for table in TABLES_IN_ORDER:
        try:
            # In Supabase/PostgREST, delete all rows using .neq('id', '00000000-0000-0000-0000-000000000000') or gt zero
            res = supabase_client.table(table).select("id", count="exact").execute()
            count_before = res.count or len(res.data or [])
            
            # Delete in chunks or with broad filter
            supabase_client.table(table).delete().neq("id", "___nonexistent___").execute()
            
            res_after = supabase_client.table(table).select("id", count="exact").execute()
            count_after = res_after.count or len(res_after.data or [])
            print(f"  ✓ {table}: deleted {count_before} rows (remaining: {count_after})")
        except Exception as exc:
            print(f"  ⚠ {table}: error deleting rows: {exc}")


def reset_supabase_storage():
    print("\n--- 2. Resetting Supabase Storage Bucket ('model-checkpoints') ---")
    try:
        # List top level entries under 'models'
        top_items = supabase_client.storage.from_(BUCKET_NAME).list("models", {"limit": 1000})
        files_to_remove = []
        for item in (top_items or []):
            name = item.get("name")
            if not name or name == ".emptyFolderPlaceholder":
                continue
            # Check if directory or file
            sub_items = supabase_client.storage.from_(BUCKET_NAME).list(f"models/{name}", {"limit": 1000})
            if sub_items:
                for sub in sub_items:
                    sub_name = sub.get("name")
                    if sub_name:
                        files_to_remove.append(f"models/{name}/{sub_name}")
            files_to_remove.append(f"models/{name}")
        
        if files_to_remove:
            supabase_client.storage.from_(BUCKET_NAME).remove(files_to_remove)
            print(f"  ✓ Removed {len(files_to_remove)} files/paths from storage bucket")
        else:
            print("  ✓ Storage bucket was already empty")
    except Exception as exc:
        print(f"  ⚠ Storage bucket reset error: {exc}")


def reset_local_models():
    print("\n--- 3. Resetting Local Model Checkpoints ---")
    models_dir = Path(LOCAL_MODELS_DIR)
    if models_dir.exists():
        count = 0
        for item in models_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                count += 1
            elif item.is_file() and item.name.endswith(".pt"):
                item.unlink()
                count += 1
        print(f"  ✓ Removed {count} local model directories/files from {models_dir}")
    else:
        models_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created clean models directory at {models_dir}")


def reset_local_sessions():
    print("\n--- 4. Resetting Local Session Data ---")
    sessions_dir = server_dir / "data" / "sessions"
    if sessions_dir.exists():
        count = 0
        for item in sessions_dir.glob("*.json"):
            item.unlink()
            count += 1
        print(f"  ✓ Removed {count} session JSON files from {sessions_dir}")
    else:
        sessions_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created clean sessions directory at {sessions_dir}")


def reset_local_charts():
    print("\n--- 5. Cleaning Generated Charts ---")
    charts_dir = server_dir / "scripts" / "charts"
    if charts_dir.exists():
        count = 0
        for item in charts_dir.iterdir():
            if item.is_file() and (item.name.endswith(".png") or item.name.endswith(".json")):
                item.unlink()
                count += 1
        print(f"  ✓ Removed {count} old generated chart files from {charts_dir}")


if __name__ == "__main__":
    print("==================================================")
    print("FlowSync Clean Fresh Database & Model Reset")
    print("==================================================")
    reset_supabase_tables()
    reset_supabase_storage()
    reset_local_models()
    reset_local_sessions()
    reset_local_charts()
    print("\n✓ FRESH RESET COMPLETE: System is ready for clean training.")

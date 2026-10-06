"""
research.py — Research REST Router for FlowSync-UQ
===================================================
Provides authoritative research endpoints for:
- Frozen scenarios (manifest, splits, hashes)
- Available research controllers and capabilities
- Frozen CRN evaluation seeds
- Canonical noise disturbance presets
- Immutable publication benchmark results (results/final/)
- Recorded experiment run bundles and trajectories
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RESEARCH = _ROOT / "research"
_RESULTS_FINAL = _ROOT / "results" / "final"
_SCENARIOS_DIR = _RESEARCH / "scenarios"
_MANIFEST_PATH = _SCENARIOS_DIR / "manifest.json"
_SEEDS_PATH = _RESEARCH / "manifests" / "final_seed_manifest_v2.json"

router = APIRouter(prefix="/research", tags=["research"])


class NoiseConfigPayload(BaseModel):
    preset: str = "clean"
    miss_rate: float = 0.0
    burst_miss_prob: float = 0.0
    burst_miss_duration: int = 50
    false_positive_lambda: float = 0.0
    jitter_std: float = 0.0
    latency_ms: int = 0


@router.get("/scenarios")
def list_scenarios() -> Dict[str, Any]:
    """Return all 16 frozen research scenarios with splits, hashes, and configurations."""
    if not _MANIFEST_PATH.exists():
        raise HTTPException(status_code=404, detail="Scenario manifest not found")
    
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    scenarios_list = []
    for sc_id, meta in manifest.get("scenarios", {}).items():
        yaml_path = _RESEARCH / meta.get("file", "")
        duration_s = int(meta.get("duration_steps", 1200)) // 10
        scenarios_list.append({
            "scenario_id": sc_id,
            "name": meta.get("name", sc_id),
            "split": meta.get("split", "test"),
            "scenario_hash": meta.get("hash", ""),
            "duration_steps": meta.get("duration_steps", 1200),
            "duration_seconds": duration_s,
            "yaml_file": meta.get("file", ""),
            "exists": yaml_path.exists(),
        })
    
    return {
        "suite_version": manifest.get("suite_version", "1.0.0"),
        "total_scenarios": len(scenarios_list),
        "splits": manifest.get("splits", {}),
        "scenarios": scenarios_list,
    }


@router.get("/controllers")
def list_controllers() -> Dict[str, Any]:
    """Return available research controllers and their capabilities."""
    from ..controllers import CONTROLLER_REGISTRY, get_controller
    
    controllers = []
    unique_names = ["fixed", "greedy", "actuated", "max_pressure", "dqn", "d3qn", "flowsync_uq"]
    
    for name in unique_names:
        try:
            ctrl = get_controller(name)
            caps = ctrl.get_capabilities().to_dict()
            display_name = {
                "fixed": "Fixed-Time (Webster)",
                "greedy": "Greedy (Max-Queue)",
                "actuated": "Actuated (NEMA VAT)",
                "max_pressure": "Max-Pressure (Varaiya)",
                "dqn": "Deep Q-Network (DQN)",
                "d3qn": "Dueling Double DQN (D3QN)",
                "flowsync_uq": "FlowSync-UQ (Ours)",
            }.get(name, name)
            
            description = {
                "fixed": "Deterministic pre-timed round-robin phase cycling.",
                "greedy": "Max-Queue heuristic serving highest instantaneous backlog.",
                "actuated": "Vehicle-actuated gap-out logic with minimum and maximum green.",
                "max_pressure": "Proven analytical queue differential optimization without value approximation.",
                "dqn": "Deep Q-Network reinforcement learning without dueling architecture.",
                "d3qn": "Dueling Double Deep Q-Network with value-advantage decomposition.",
                "flowsync_uq": "Calibrated perception uncertainty estimation, hysteretic fallback, and safety shielding.",
            }.get(name, "")

            controllers.append({
                "id": name,
                "name": display_name,
                "description": description,
                "is_proposed_method": name == "flowsync_uq",
                "capabilities": caps,
            })
        except Exception as e:
            controllers.append({
                "id": name,
                "name": name,
                "description": str(e),
                "is_proposed_method": name == "flowsync_uq",
                "capabilities": {},
            })

    return {
        "controllers": controllers,
        "count": len(controllers),
    }


@router.get("/seeds")
def list_seeds() -> Dict[str, Any]:
    """Return frozen 20 seeds under CRN synchronization."""
    if not _SEEDS_PATH.exists():
        return {
            "seed_count": 20,
            "seeds": [1101 + i for i in range(20)],
            "pairing_methodology": "Common Random Numbers (CRN)",
            "default_seed": 1101,
        }
    
    with open(_SEEDS_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    return {
        "seed_count": manifest.get("seed_count", 20),
        "seeds": manifest.get("seeds", [1101 + i for i in range(20)]),
        "pairing_methodology": manifest.get("pairing_methodology", "CRN"),
        "default_seed": manifest.get("seeds", [1101])[0],
        "training_seeds_excluded": manifest.get("training_seeds_excluded", []),
    }


@router.get("/noise-presets")
def list_noise_presets() -> Dict[str, Any]:
    """Return standard perception fault presets."""
    from research.noise.fault_injector import FAULT_PRESETS
    
    presets = []
    for key, p in FAULT_PRESETS.items():
        label = {
            "clean": "Clean (Nominal)",
            "miss_05": "5% Missed Detections",
            "miss_10": "10% Missed Detections",
            "miss_20": "20% Missed Detections",
            "miss_30": "30% Missed Detections (Benchmark Standard)",
            "miss_40": "40% Severe Missed Detections",
            "burst_occlusion": "Burst Occlusion (Line-of-Sight Loss)",
            "latency_500ms": "500ms Sensor Latency Delay",
            "combined_stress": "Combined Multi-Fault Stress",
        }.get(key, key)
        
        presets.append({
            "key": key,
            "label": label,
            "profile": p.to_dict(),
        })
    
    return {"presets": presets}


@router.get("/summary")
def get_publication_summary() -> Dict[str, Any]:
    """Return immutable publication benchmark summary and statistical test report."""
    summary_path = _RESULTS_FINAL / "final_hardened_suite_summary.json"
    stat_path = _RESULTS_FINAL / "statistical_report_v2.json"
    env_path = _RESULTS_FINAL / "environment.json"

    summary_data = {}
    stat_data = {}
    env_data = {}

    if summary_path.exists():
        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    if stat_path.exists():
        stat_data = json.loads(stat_path.read_text(encoding="utf-8"))
    if env_path.exists():
        env_data = json.loads(env_path.read_text(encoding="utf-8"))

    return {
        "status": "frozen_publication_data",
        "benchmark_summary": summary_data,
        "statistical_report": stat_data,
        "provenance": env_data,
    }


@router.get("/runs")
def list_runs(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """List available immutable experiment bundles from results/."""
    results_dir = _ROOT / "results"
    runs = []

    # Check for run directories in results/
    for sub in results_dir.glob("exp_*"):
        if sub.is_dir() and (sub / "metadata.json").exists():
            try:
                meta = json.loads((sub / "metadata.json").read_text(encoding="utf-8"))
                metrics = {}
                if (sub / "metrics.json").exists():
                    metrics = json.loads((sub / "metrics.json").read_text(encoding="utf-8"))
                
                runs.append({
                    "experiment_id": meta.get("experiment_id", sub.name),
                    "scenario_id": meta.get("scenario_id", ""),
                    "controller_name": meta.get("controller_name", ""),
                    "seed": meta.get("seed", 0),
                    "timestamp": meta.get("timestamp", ""),
                    "git_commit": meta.get("git_commit", ""),
                    "avg_delay": metrics.get("avg_delay", 0.0),
                    "p95_delay": metrics.get("p95_delay", 0.0),
                    "throughput": metrics.get("total_vehicles_passed", 0),
                    "starvation_count": metrics.get("starvation_count", 0),
                    "has_trajectory": (sub / "trajectory.jsonl").exists(),
                    "has_events": (sub / "events.jsonl").exists(),
                })
            except Exception:
                continue

    # Also list frozen runs from results/final/ tables
    return {
        "total_runs": len(runs),
        "runs": sorted(runs, key=lambda r: r.get("timestamp", ""), reverse=True)[:limit],
    }


@router.get("/runs/{experiment_id}")
def get_run_details(experiment_id: str, include_trajectory: bool = Query(True)) -> Dict[str, Any]:
    """Return full bundle for an experiment: metadata, metrics, events, and trajectory."""
    target_dir = _ROOT / "results" / experiment_id
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")

    metadata = json.loads((target_dir / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((target_dir / "metrics.json").read_text(encoding="utf-8"))
    
    events = []
    if (target_dir / "events.jsonl").exists():
        with open(target_dir / "events.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

    trajectory = []
    if include_trajectory and (target_dir / "trajectory.jsonl").exists():
        with open(target_dir / "trajectory.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    trajectory.append(json.loads(line))

    return {
        "metadata": metadata,
        "metrics": metrics,
        "events": events,
        "trajectory": trajectory,
        "trajectory_point_count": len(trajectory),
    }


@router.get("/tables/{table_name}")
def get_latex_table(table_name: str) -> Dict[str, Any]:
    """Return raw LaTeX table source from results/final/."""
    clean_name = table_name.strip()
    if not clean_name.endswith(".tex"):
        clean_name = f"{clean_name}.tex"
    
    table_path = _RESULTS_FINAL / clean_name
    if not table_path.exists():
        raise HTTPException(status_code=404, detail=f"Table '{clean_name}' not found in results/final/")

    return {
        "table_name": clean_name,
        "content": table_path.read_text(encoding="utf-8"),
    }

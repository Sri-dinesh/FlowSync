"""
generate_scenarios.py — Build and Freeze the Canonical Research Scenario Suite
================================================================================
Task E1: Generates 14+ frozen scenario configurations across:
- Train Split: Baseline demand, balanced, asymmetric, bursts
- Validation Split: Moderate & heavy surges, turning variations, tuning scenarios
- Final Test Split: Frozen held-out OOD, near-gridlock, demand reversal, incidents
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from research.scenarios.scenario_schema import DemandProfile, ScenarioConfig

SCENARIOS_DIR = Path(__file__).parent


def create_canonical_scenarios() -> List[ScenarioConfig]:
    scenarios: List[ScenarioConfig] = []

    # TRAIN SPLIT (Policy learning & baseline training)
    scenarios.append(ScenarioConfig(
        scenario_id="train_low_balanced_01",
        split="train",
        name="Low Balanced Flow",
        description="Light uniform demand across all 4 approaches (0.2 veh/s total).",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.2,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="train_mod_balanced_01",
        split="train",
        name="Moderate Balanced Flow",
        description="Standard moderate traffic demand (0.5 veh/s total).",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.5,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="train_high_balanced_01",
        split="train",
        name="High Balanced Flow",
        description="Heavy balanced demand approaching capacity (0.8 veh/s total).",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.8,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="train_ns_asymmetric_01",
        split="train",
        name="North-South Arterial Priority",
        description="NS approaches carry 3x more traffic than EW cross streets.",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.5,
            directional_weights={"north": 1.5, "south": 1.5, "east": 0.5, "west": 0.5},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="train_ew_asymmetric_01",
        split="train",
        name="East-West Arterial Priority",
        description="EW approaches carry 3x more traffic than NS cross streets.",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.5,
            directional_weights={"north": 0.5, "south": 0.5, "east": 1.5, "west": 1.5},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="train_platoon_burst_01",
        split="train",
        name="Platoon Arrival Bursts",
        description="Periodic platoon surges on Northbound approach.",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.4,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
            burst_events=[
                {"start_step": 300, "end_step": 500, "multiplier": 2.5, "directions": ["north"]},
                {"start_step": 700, "end_step": 900, "multiplier": 2.5, "directions": ["south"]},
            ],
        ),
    ))

    # VALIDATION SPLIT (Hyperparameter selection, UQ calibration & tuning)
    scenarios.append(ScenarioConfig(
        scenario_id="val_oversaturated_01",
        split="validation",
        name="Validation Oversaturated",
        description="High volume exceeding lane discharge capacity (1.1 veh/s).",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=1.1,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="val_turning_heavy_01",
        split="validation",
        name="Validation Turning Heavy",
        description="High turning percentage: 40% left turns and 30% right turns.",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.6,
            turn_ratios={
                "north": {"straight": 0.30, "left": 0.40, "right": 0.30},
                "south": {"straight": 0.30, "left": 0.40, "right": 0.30},
                "east":  {"straight": 0.30, "left": 0.40, "right": 0.30},
                "west":  {"straight": 0.30, "left": 0.40, "right": 0.30},
            },
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="val_rush_hour_ramp_01",
        split="validation",
        name="Validation Rush Hour Ramp",
        description="Traffic volume progressively ramps from 0.3 to 0.9 veh/s.",
        duration_steps=1200,
        demand_profile=DemandProfile(
            base_lambda=0.6,
            burst_events=[
                {"start_step": 200, "end_step": 1000, "multiplier": 1.8, "directions": ["north", "south", "east", "west"]},
            ],
        ),
    ))

    # FINAL TEST SPLIT (FROZEN — Evaluated only after training/tuning freeze)
    scenarios.append(ScenarioConfig(
        scenario_id="test_clean_balanced_01",
        split="test",
        name="Test Benchmark Clean Balanced",
        description="Reference evaluation benchmark under balanced demand (0.6 veh/s).",
        duration_steps=1500,
        demand_profile=DemandProfile(base_lambda=0.6),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_near_gridlock_01",
        split="test",
        name="Test Near Gridlock Stress",
        description="Severe stress test: 1.3 veh/s demand creating heavy spillback risk.",
        duration_steps=1500,
        demand_profile=DemandProfile(
            base_lambda=1.3,
            directional_weights={"north": 1.2, "south": 1.2, "east": 1.0, "west": 1.0},
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_left_turn_surge_01",
        split="test",
        name="Test Left Turn Congestion",
        description="50% left turns on North/South approaches, testing protected phases.",
        duration_steps=1500,
        demand_profile=DemandProfile(
            base_lambda=0.7,
            turn_ratios={
                "north": {"straight": 0.35, "left": 0.50, "right": 0.15},
                "south": {"straight": 0.35, "left": 0.50, "right": 0.15},
                "east":  {"straight": 0.70, "left": 0.15, "right": 0.15},
                "west":  {"straight": 0.70, "left": 0.15, "right": 0.15},
            },
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_sudden_burst_01",
        split="test",
        name="Test Sudden Arterial Burst",
        description="Massive sudden surge (3.5x multiplier) on Eastbound corridor.",
        duration_steps=1500,
        demand_profile=DemandProfile(
            base_lambda=0.4,
            burst_events=[
                {"start_step": 400, "end_step": 800, "multiplier": 3.5, "directions": ["east"]},
            ],
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_demand_reversal_01",
        split="test",
        name="Test Commuter Demand Reversal",
        description="Morning inbound NS surge shifts abruptly to evening outbound EW surge.",
        duration_steps=1500,
        demand_profile=DemandProfile(
            base_lambda=0.6,
            burst_events=[
                {"start_step": 0, "end_step": 750, "multiplier": 2.2, "directions": ["north", "south"]},
                {"start_step": 750, "end_step": 1500, "multiplier": 2.2, "directions": ["east", "west"]},
            ],
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_incident_reduction_01",
        split="test",
        name="Test Incident Bottleneck",
        description="Downstream lane blockage on Westbound approach reducing capacity by 70%.",
        duration_steps=1500,
        demand_profile=DemandProfile(
            base_lambda=0.6,
            incident_events=[
                {"start_step": 300, "end_step": 1100, "direction": "west", "capacity_factor": 0.3},
            ],
        ),
    ))

    scenarios.append(ScenarioConfig(
        scenario_id="test_heldout_ood_01",
        split="test",
        name="Test Held-Out OOD Multi-Distribution",
        description="Completely unseen combination of asymmetric left turns, heavy bursts, and non-stationary volume.",
        duration_steps=2000,
        demand_profile=DemandProfile(
            base_lambda=0.85,
            directional_weights={"north": 1.4, "south": 0.6, "east": 1.3, "west": 0.7},
            turn_ratios={
                "north": {"straight": 0.20, "left": 0.60, "right": 0.20},
                "south": {"straight": 0.50, "left": 0.30, "right": 0.20},
                "east":  {"straight": 0.40, "left": 0.40, "right": 0.20},
                "west":  {"straight": 0.70, "left": 0.10, "right": 0.20},
            },
            burst_events=[
                {"start_step": 500, "end_step": 900, "multiplier": 2.8, "directions": ["north", "east"]},
            ],
        ),
    ))

    return scenarios


def save_all_scenarios() -> Dict[str, Any]:
    """Write scenario files to disk and generate split manifest."""
    scenarios = create_canonical_scenarios()
    manifest: Dict[str, Any] = {
        "suite_version": "1.0.0",
        "total_scenarios": len(scenarios),
        "splits": {"train": [], "validation": [], "test": []},
        "scenarios": {},
    }

    for sc in scenarios:
        split_dir = SCENARIOS_DIR / sc.split
        split_dir.mkdir(parents=True, exist_ok=True)
        file_path = split_dir / f"{sc.scenario_id}.yaml"
        sc.save(file_path)

        manifest["splits"][sc.split].append(sc.scenario_id)
        manifest["scenarios"][sc.scenario_id] = {
            "name": sc.name,
            "split": sc.split,
            "hash": sc.scenario_hash,
            "file": str(file_path.relative_to(SCENARIOS_DIR.parent)),
            "duration_steps": sc.duration_steps,
        }

    manifest_path = SCENARIOS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = save_all_scenarios()
    print(f"Generated {m['total_scenarios']} frozen scenarios.")
    for split, ids in m["splits"].items():
        print(f"  {split.upper()} ({len(ids)}): {', '.join(ids)}")

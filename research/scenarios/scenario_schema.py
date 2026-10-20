"""
scenario_schema.py — Frozen Scenario Definition and Hashing System
===================================================================
Provides strict schema validation and SHA-256 canonical hashing for
traffic scenarios across train, validation, and final test splits.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List
import yaml


@dataclass
class DemandProfile:
    """Traffic generation profile controlling arrival rate and turning movements."""
    base_lambda: float = 0.5  # veh/s
    directional_weights: Dict[str, float] = field(
        default_factory=lambda: {"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0}
    )
    turn_ratios: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "north": {"straight": 0.70, "left": 0.15, "right": 0.15},
            "south": {"straight": 0.70, "left": 0.15, "right": 0.15},
            "east":  {"straight": 0.70, "left": 0.15, "right": 0.15},
            "west":  {"straight": 0.70, "left": 0.15, "right": 0.15},
        }
    )
    burst_events: List[Dict[str, Any]] = field(default_factory=list)
    incident_events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ScenarioConfig:
    """
    Frozen scenario specification with immutable content hash.
    Guarantees reproducible traffic demand conditions.
    """
    scenario_id: str
    split: str  # "train", "validation", "test"
    name: str
    description: str = ""
    duration_steps: int = 1200  # 120s at 10 Hz
    topology: str = "single_intersection"  # or "city_grid_2x2"
    red_duration: float = 3.0
    demand_profile: DemandProfile = field(default_factory=DemandProfile)
    scenario_hash: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.demand_profile, dict):
            self.demand_profile = DemandProfile(**self.demand_profile)
        dp = self.demand_profile
        directions = {"north", "south", "east", "west"}
        if self.duration_steps <= 0 or not math.isfinite(self.red_duration) or self.red_duration < 0:
            raise ValueError("Invalid scenario duration or clearance")
        if set(dp.directional_weights) != directions or any(not math.isfinite(v) or v < 0 for v in dp.directional_weights.values()) or sum(dp.directional_weights.values()) <= 0:
            raise ValueError("Scenario requires nonnegative directional weights with positive total")
        if not math.isfinite(dp.base_lambda) or dp.base_lambda < 0:
            raise ValueError("Invalid demand rate")
        for direction in directions:
            ratios = dp.turn_ratios[direction]
            if set(ratios) != {"straight", "left", "right"} or any(not math.isfinite(v) or v < 0 for v in ratios.values()) or not math.isclose(sum(ratios.values()), 1.0):
                raise ValueError(f"Invalid turn ratios for {direction}")
        for event in dp.burst_events + dp.incident_events:
            if not 0 <= event["start_step"] < event["end_step"] <= self.duration_steps:
                raise ValueError("Event interval must be within scenario duration")
        for event in dp.burst_events:
            if set(event.get("directions", [])) - directions or not math.isfinite(event.get("multiplier", 1)) or event.get("multiplier", 1) < 0:
                raise ValueError("Invalid burst configuration")
        for event in dp.incident_events:
            if event["direction"] not in directions or not 0 <= event["capacity_factor"] <= 1:
                raise ValueError("Invalid incident configuration")
        if not self.scenario_hash:
            self.scenario_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Deterministic SHA-256 fingerprint over scenario parameters."""
        data = {
            "scenario_id": self.scenario_id,
            "split": self.split,
            "duration_steps": self.duration_steps,
            "topology": self.topology,
            "red_duration": self.red_duration,
            "demand": asdict(self.demand_profile),
        }
        canonical_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScenarioConfig:
        data_copy = dict(data)
        if "demand_profile" in data_copy and isinstance(data_copy["demand_profile"], dict):
            data_copy["demand_profile"] = DemandProfile(**data_copy["demand_profile"])
        return cls(**data_copy)

    @classmethod
    def load(cls, path: str | Path) -> ScenarioConfig:
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        return cls.from_dict(data)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in (".yaml", ".yml"):
            path.write_text(self.to_yaml(), encoding="utf-8")
        else:
            path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

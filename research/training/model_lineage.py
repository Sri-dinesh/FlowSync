"""
Model Lineage and Fine-Tuning Adaptation Tracker (Task 1A.16, Task G3).

Tracks checkpoint provenance, adaptation budget, zero-shot vs adapted performance,
and source-domain retention to measure catastrophic forgetting.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def compute_file_sha256(path: Path | str) -> str:
    """Computes SHA-256 checksum of a file."""
    p = Path(path)
    if not p.exists():
        return "non_existent_file"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class AdaptationConfig:
    target_scenario_id: str
    adaptation_episodes: int = 50
    learning_rate: float = 1e-4
    frozen_layers: List[str] = field(default_factory=list)
    replay_reset: bool = True
    exploration_reset: bool = True
    initial_epsilon: float = 0.2
    min_epsilon: float = 0.05
    seed: int = 42


@dataclass
class LineageRecord:
    lineage_id: str
    base_checkpoint_path: str
    base_checkpoint_hash: str
    adapted_checkpoint_path: str
    adapted_checkpoint_hash: str
    adaptation_config: Dict[str, Any]
    zero_shot_metrics: Dict[str, float] = field(default_factory=dict)
    adapted_metrics: Dict[str, float] = field(default_factory=dict)
    source_retention_metrics: Dict[str, float] = field(default_factory=dict)
    catastrophic_forgetting: Dict[str, float] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelLineageManager:
    """
    Manages model lineage metadata, ensuring reproducible adaptation
    and catastrophic forgetting measurement.
    """

    def __init__(self, lineage_dir: Path | str = "research/models/lineage"):
        self.lineage_dir = Path(lineage_dir)
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

    def record_adaptation(
        self,
        lineage_id: str,
        base_checkpoint_path: str,
        adapted_checkpoint_path: str,
        adaptation_config: AdaptationConfig,
        zero_shot_metrics: Dict[str, float],
        adapted_metrics: Dict[str, float],
        source_base_metrics: Dict[str, float],
        source_post_retention_metrics: Dict[str, float],
        created_at: str = "2026-09-30T10:00:00Z",
    ) -> LineageRecord:
        """
        Records an adaptation event, computing file hashes and catastrophic forgetting metrics.
        """
        base_hash = compute_file_sha256(base_checkpoint_path)
        adapted_hash = compute_file_sha256(adapted_checkpoint_path)

        # Catastrophic forgetting is quantified by degradation on the source domain
        # E.g. post_delay - base_delay. Positive means performance got worse on source domain.
        forgetting = {}
        for k in source_base_metrics:
            if k in source_post_retention_metrics:
                delta = source_post_retention_metrics[k] - source_base_metrics[k]
                rel_delta = delta / (abs(source_base_metrics[k]) + 1e-6)
                forgetting[f"{k}_delta"] = float(delta)
                forgetting[f"{k}_rel_degradation"] = float(rel_delta)

        record = LineageRecord(
            lineage_id=lineage_id,
            base_checkpoint_path=str(base_checkpoint_path),
            base_checkpoint_hash=base_hash,
            adapted_checkpoint_path=str(adapted_checkpoint_path),
            adapted_checkpoint_hash=adapted_hash,
            adaptation_config=asdict(adaptation_config),
            zero_shot_metrics=zero_shot_metrics,
            adapted_metrics=adapted_metrics,
            source_retention_metrics=source_post_retention_metrics,
            catastrophic_forgetting=forgetting,
            created_at=created_at,
        )

        out_file = self.lineage_dir / f"{lineage_id}.json"
        with open(out_file, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

        return record

    def load_record(self, lineage_id: str) -> Optional[LineageRecord]:
        out_file = self.lineage_dir / f"{lineage_id}.json"
        if not out_file.exists():
            return None
        with open(out_file, "r") as f:
            data = json.load(f)
        return LineageRecord(**data)

    def verify_integrity(self, record: LineageRecord) -> Dict[str, bool]:
        """
        Verifies that current checkpoint files match their recorded SHA-256 hashes.
        """
        current_base_hash = compute_file_sha256(record.base_checkpoint_path)
        current_adapted_hash = compute_file_sha256(record.adapted_checkpoint_path)

        return {
            "base_hash_valid": current_base_hash == record.base_checkpoint_hash,
            "adapted_hash_valid": current_adapted_hash == record.adapted_checkpoint_hash,
        }

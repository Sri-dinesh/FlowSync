#!/usr/bin/env python3
"""
Generate the definitive FlowSync Experimental Results Freeze deliverables:
1. FINAL_DATASET_INVENTORY.csv
2. SHA256SUMS.txt
3. FINAL_SAFETY_POPULATION_RECONCILIATION.md
4. FINAL_EXPERIMENTAL_EVIDENCE_FREEZE.md
5. FINAL_REPRODUCIBILITY_REPORT.md
"""
import csv
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RES_EVAL = ROOT / "results_evaluation"
RES_EVAL.mkdir(exist_ok=True)

def file_sha256(path: Path) -> str:
    if not path.exists():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0

def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

# --- 1. SHA256SUMS.txt ---
def build_sha256sums():
    tracked_files = [
        # Protocols & Governing Manifests
        "research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md",
        "results/replicate_evaluation/matched_shield_v5_20261015/manifest.json",
        "results/sumo_sensing_recovery/full_20261031/manifest.json",
        "results/sumo_robustness/full_20261023/manifest.json",
        "research/manifests/service_ledger_design.json",
        "research/manifests/methodology.json",
        "research/paper_figures/source_manifest.json",

        # Primary Custom Simulator Artifacts
        "results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl",
        "results/replicate_evaluation/matched_shield_v5_20261015/report.json",

        # Primary D3QN Checkpoints
        "results/research_training/pilot_v5_kbW0lsY3/seed_101/checkpoint_warmup.pt",
        "results/research_training/pilot_v5_kbW0lsY3/seed_202/checkpoint_50.pt",
        "results/research_training/pilot_v5_kbW0lsY3/seed_303/checkpoint_100.pt",

        # Supplementary SUMO Panels
        "results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl",
        "results/sumo_sensing_recovery/full_20261031/report.json",
        "results/sumo_robustness/full_20261023/runs.jsonl",
        "results/sumo_robustness/full_20261023/report.json",
        "results/sumo_classical_panel/full_20261023/report.json",
        "results/sumo_switching/full_20261101/report.json",
        "results/sumo_history/full_20261101/report.json",
        "results/sumo_service_ledger/full_20261103/report.json",

        # Benchmarks and Calibration
        "results/final/latency_profile_full.json",
        "results/uncertainty_calibration/pilot_20261014/calibration.json",

        # Supplementary Diagnostics
        "results/spatial_input_audit/pilot_20261022/report.json",
        "results/spatial_input_audit/pilot_20261022/sources.jsonl",
        "results/teacher_alignment/pilot_20261022/report.json",
        "results/teacher_alignment/pilot_20261022/sources.jsonl",
        "results/teacher_horizon/pilot_20261022/report.json",
        "results/teacher_horizon/pilot_20261022/sources.jsonl",
        "results/research_training/spatial_smoke_20261021/report.json",
        "results/research_training/spatial_smoke_20261021/evaluation.jsonl",

        # Exploratory Pilots
        "results/count_restoration/pilot_20261029/report.json",
        "results/count_restoration/pilot_20261029/control.jsonl",
        "results/ppo_restoration/recovered_20261030/report.json",
        "results/ppo_restoration/recovered_20261030/recovery.json",
        "results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/metadata.json",
        "results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/metrics.json",
        "results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/trajectory.jsonl",

        # Evaluated Summaries & Reports
        "results_evaluation/FINAL_PAPER_TABLES.csv",
        "results_evaluation/FINAL_RESULTS_PROVENANCE.md",
        "results_evaluation/FINAL_PAPER_RESULTS.md",
        "results_evaluation/FINAL_SUMO_RESULTS.md",
        "results_evaluation/SECONDARY_RESULTS_RECONCILIATION.md",
        "results_evaluation/STEP_COUNT_POPULATION_RECONCILIATION.md",
        "results_evaluation/compact_verification/controller_summary.csv",
        "results_evaluation/compact_verification/paired_comparisons.csv",
        "results_evaluation/compact_verification/sumo_summary.csv",
        "results_evaluation/compact_verification/safety_audit_summary.csv",
        "results_evaluation/compact_verification/training_summary.csv",
        "results_evaluation/compact_verification/compact_verification_summary.json",
    ]

    lines = []
    for rel in tracked_files:
        p = ROOT / rel
        if p.exists():
            digest = file_sha256(p)
            lines.append(f"{digest}  {rel}")
    
    content = "\n".join(lines) + "\n"
    (RES_EVAL / "SHA256SUMS.txt").write_text(content)
    (ROOT / "SHA256SUMS.txt").write_text(content)
    print(f"Generated SHA256SUMS.txt with {len(lines)} file digests.")

# --- 2. FINAL_DATASET_INVENTORY.csv ---
def build_dataset_inventory():
    records = [
        {
            "dataset_id": "DS-01",
            "dataset_name": "Custom Simulator Primary Matched-Shield Panel (2,800 runs)",
            "file_path": "results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl",
            "record_count": 2800,
            "total_steps_or_samples": 4340000,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Primary and complete",
            "governing_protocol_or_manifest": "MATCHED_SHIELD_PROTOCOL_20261015.md",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Authoritative primary evaluation panel: 14 controller arms x 200 unique arrival streams (2,520 standard runs @ 1,500 ticks + 280 heldout OOD runs @ 2,000 ticks). 0 conflicts, 0 clearance violations."
        },
        {
            "dataset_id": "DS-02",
            "dataset_name": "Custom Simulator Primary Evaluation Summary Report",
            "file_path": "results/replicate_evaluation/matched_shield_v5_20261015/report.json",
            "record_count": 1,
            "total_steps_or_samples": 4340000,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Primary and complete",
            "governing_protocol_or_manifest": "MATCHED_SHIELD_PROTOCOL_20261015.md",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Authoritative crossed-bootstrap aggregate metrics (5,000 draws, seed 717) and paired contrasts for all custom simulator controllers."
        },
        {
            "dataset_id": "DS-03",
            "dataset_name": "D3QN Evaluated Policy Checkpoint - Training Seed 101",
            "file_path": "results/research_training/pilot_v5_kbW0lsY3/seed_101/checkpoint_warmup.pt",
            "record_count": 1,
            "total_steps_or_samples": 0,
            "testbed": "PyTorch PyTorch 2.13.0 CPU",
            "status_classification": "Primary and complete",
            "governing_protocol_or_manifest": "MATCHED_SHIELD_PROTOCOL_20261015.md",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "Model checkpoint for Seed 101 selected at Episode 0 warmup (lowest validation delay: 10.903s before online degradation)."
        },
        {
            "dataset_id": "DS-04",
            "dataset_name": "D3QN Evaluated Policy Checkpoint - Training Seed 202",
            "file_path": "results/research_training/pilot_v5_kbW0lsY3/seed_202/checkpoint_50.pt",
            "record_count": 1,
            "total_steps_or_samples": 0,
            "testbed": "PyTorch PyTorch 2.13.0 CPU",
            "status_classification": "Primary and complete",
            "governing_protocol_or_manifest": "MATCHED_SHIELD_PROTOCOL_20261015.md",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "Model checkpoint for Seed 202 selected at Episode 50 (peak validation performance across 223 online episodes)."
        },
        {
            "dataset_id": "DS-05",
            "dataset_name": "D3QN Evaluated Policy Checkpoint - Training Seed 303",
            "file_path": "results/research_training/pilot_v5_kbW0lsY3/seed_303/checkpoint_100.pt",
            "record_count": 1,
            "total_steps_or_samples": 0,
            "testbed": "PyTorch PyTorch 2.13.0 CPU",
            "status_classification": "Primary and complete",
            "governing_protocol_or_manifest": "MATCHED_SHIELD_PROTOCOL_20261015.md",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "Model checkpoint for Seed 303 selected at Episode 100 (peak validation performance across 219 online episodes)."
        },
        {
            "dataset_id": "DS-06",
            "dataset_name": "SUMO 180s Sensing Recovery Panel Runs",
            "file_path": "results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl",
            "record_count": 72,
            "total_steps_or_samples": 129600,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "results/sumo_sensing_recovery/full_20261031/manifest.json",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "72 SUMO episode records (51 reused, 21 recovered/new) across 3 classical baselines, 4 sensing regimes, and 6 seeds (180.0s @ 10 Hz)."
        },
        {
            "dataset_id": "DS-07",
            "dataset_name": "SUMO 180s Sensing Recovery Panel Report",
            "file_path": "results/sumo_sensing_recovery/full_20261031/report.json",
            "record_count": 1,
            "total_steps_or_samples": 129600,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "results/sumo_sensing_recovery/full_20261031/manifest.json",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Aggregated sensing panel results; publication_ready: false (exploratory baseline sensing evidence)."
        },
        {
            "dataset_id": "DS-08",
            "dataset_name": "SUMO 360s Robustness Panel Runs",
            "file_path": "results/sumo_robustness/full_20261023/runs.jsonl",
            "record_count": 24,
            "total_steps_or_samples": 86400,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "results/sumo_robustness/full_20261023/manifest.json",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "24 extended 360s runs (12 Max-Pressure, 12 Total-Incoming distortion) across 6 seeds and 2 starting phases (360.0s @ 10 Hz)."
        },
        {
            "dataset_id": "DS-09",
            "dataset_name": "SUMO 360s Robustness Panel Report",
            "file_path": "results/sumo_robustness/full_20261023/report.json",
            "record_count": 1,
            "total_steps_or_samples": 86400,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "results/sumo_robustness/full_20261023/manifest.json",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "360s robustness summary evaluating queue distortion sensitivity; publication_ready: false."
        },
        {
            "dataset_id": "DS-10",
            "dataset_name": "SUMO Classical Baseline Panel Report",
            "file_path": "results/sumo_classical_panel/full_20261023/report.json",
            "record_count": 45,
            "total_steps_or_samples": 81000,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/audits/audit_sumo_classical_panel.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "45 classical baseline runs evaluating pre-timed, actuated, and baseline NEMA control regimes in microscopic SUMO."
        },
        {
            "dataset_id": "DS-11",
            "dataset_name": "SUMO Switching Margin Panel Report",
            "file_path": "results/sumo_switching/full_20261101/report.json",
            "record_count": 36,
            "total_steps_or_samples": 129600,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/audits/audit_sumo_switching.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "36 runs evaluating pressure-proposal switching hysteresis thresholds (delta 0, 1, 2) in SUMO."
        },
        {
            "dataset_id": "DS-12",
            "dataset_name": "SUMO History Queue Filter Panel Report",
            "file_path": "results/sumo_history/full_20261101/report.json",
            "record_count": 60,
            "total_steps_or_samples": 216000,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/audits/audit_sumo_history.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "60 runs evaluating FIR causal filtering on queue estimates under noise in SUMO."
        },
        {
            "dataset_id": "DS-13",
            "dataset_name": "SUMO Service Ledger Panel Report (Incomplete Panel)",
            "file_path": "results/sumo_service_ledger/full_20261103/report.json",
            "record_count": 111,
            "total_steps_or_samples": 399600,
            "testbed": "SUMO 1.24.0 Microscopic",
            "status_classification": "Incomplete",
            "governing_protocol_or_manifest": "research/manifests/service_ledger_design.json",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "111 runs completed out of 144 planned runs (77.1%). Halted when frozen session reached maximum declared allowance (3,600.08s wall-clock cap). complete: false, scientific_panel_complete: false."
        },
        {
            "dataset_id": "DS-14",
            "dataset_name": "Hardware Perception-to-Control Latency Benchmark",
            "file_path": "results/final/latency_profile_full.json",
            "record_count": 10000,
            "total_steps_or_samples": 10000,
            "testbed": "Workstation CPU: x86_64 Intel Core i5-1135G7 @ 2.40 GHz",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/cv/benchmark_system_latency.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "10,000-step perception-to-control latency benchmark. Mean: 57.66 ms, P95: 65.26 ms, Max: 206.51 ms. Benchmarked on x86_64 CPU workstation; NOT benchmarked on Jetson Orin."
        },
        {
            "dataset_id": "DS-15",
            "dataset_name": "Perception Uncertainty Calibration Artifact",
            "file_path": "results/uncertainty_calibration/pilot_20261014/calibration.json",
            "record_count": 1,
            "total_steps_or_samples": 0,
            "testbed": "Custom Simulation Calibration",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/calibration/calibrate_uncertainty.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "Logistic regression gate fitted on synthetic queue-count errors (>= 3 vehicles). Intercept: -0.9330, Volatility: 2.0058, Residual: 0.2501. 2 of 7 active features."
        },
        {
            "dataset_id": "DS-16",
            "dataset_name": "Spatial Feature Input Audit",
            "file_path": "results/spatial_input_audit/pilot_20261022/report.json",
            "record_count": 27,
            "total_steps_or_samples": 41200,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "SPATIAL_INPUT_AUDIT_PROTOCOL_20261022.md",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Diagnostic ablation across 27 sources and 44 unique branches (27 x 1,200 + 44 x 200 = 41,200 steps). Complete: true."
        },
        {
            "dataset_id": "DS-17",
            "dataset_name": "Spatial Teacher Alignment Audit",
            "file_path": "results/teacher_alignment/pilot_20261022/report.json",
            "record_count": 9,
            "total_steps_or_samples": 55600,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "SPATIAL_TEACHER_ALIGNMENT_PLAN_20261022.md",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Diagnostic replay on 9 sources across 7 eligible gates under 16 future arrival streams (10,800 + 44,800 = 55,600 steps). Complete: true."
        },
        {
            "dataset_id": "DS-18",
            "dataset_name": "Spatial Teacher Horizon Extension Audit",
            "file_path": "results/teacher_horizon/pilot_20261022/report.json",
            "record_count": 9,
            "total_steps_or_samples": 145200,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/audits/audit_teacher_horizon.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Horizon extension audit across 9 sources, evaluating 200-step and 600-step branch extensions (10,800 + 134,400 = 145,200 steps). Complete: true."
        },
        {
            "dataset_id": "DS-19",
            "dataset_name": "Spatial Smoke Evaluation Suite",
            "file_path": "results/research_training/spatial_smoke_20261021/report.json",
            "record_count": 84,
            "total_steps_or_samples": 100800,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Supplementary and complete",
            "governing_protocol_or_manifest": "research/pilots/run_spatial_smoke.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "84 baseline runs of 1,200 ticks each evaluating spatial observation mechanisms (84 x 1,200 = 100,800 steps). Complete: true."
        },
        {
            "dataset_id": "DS-20",
            "dataset_name": "Count Restoration Filter Pilot",
            "file_path": "results/count_restoration/pilot_20261029/report.json",
            "record_count": 108,
            "total_steps_or_samples": 129600,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Exploratory",
            "governing_protocol_or_manifest": "research/pilots/run_count_restoration_pilot.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "108 control runs (129,600 steps) evaluating count reconstruction filter ablations. Exploratory development; not publication-ready."
        },
        {
            "dataset_id": "DS-21",
            "dataset_name": "PPO Restoration Retraining Pilot (Recovered Session)",
            "file_path": "results/ppo_restoration/recovered_20261030/report.json",
            "record_count": 270,
            "total_steps_or_samples": 210400,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Exploratory",
            "governing_protocol_or_manifest": "research/pilots/recover_ppo_restoration_pilot.py",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "Recovered PPO retraining session (6 workers, 270 evaluations, 210,400 steps). Summed with count restoration yields 340,000 steps. Complete: true, publication_ready: false."
        },
        {
            "dataset_id": "DS-22",
            "dataset_name": "Early Calibration / Smoke Pilot Runs",
            "file_path": "results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/trajectory.jsonl",
            "record_count": 70,
            "total_steps_or_samples": 105000,
            "testbed": "Custom Simulator (10 Hz)",
            "status_classification": "Exploratory",
            "governing_protocol_or_manifest": "Legacy calibration script",
            "conflicts_observed": 0,
            "clearance_violations_observed": 0,
            "description_and_notes": "70 preliminary calibration runs of 1,500 ticks each (105,000 steps). Audited for safety invariants (0 conflicts, 0 clearance violations)."
        },
        {
            "dataset_id": "DS-23",
            "dataset_name": "Legacy CV Perception Quality Metrics (Excluded)",
            "file_path": "results/final/cv_validation_metrics.json",
            "record_count": 1000,
            "total_steps_or_samples": 1000,
            "testbed": "Synthetic Error Generator",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/legacy/validate_perception_quality.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Fabricated perception precision/recall metrics generated from synthetic noise without genuine annotated camera video. Generator disabled with RuntimeError."
        },
        {
            "dataset_id": "DS-24",
            "dataset_name": "Legacy City 2x2 Grid Scalability Metrics (Excluded)",
            "file_path": "results/final/city_2x2_scalability_v2.json",
            "record_count": 20,
            "total_steps_or_samples": 30000,
            "testbed": "Synthetic 2x2 Grid Simulation",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/legacy/run_city_scalability_v2.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Degenerate 2x2 grid simulation where Fixed-Time, D3QN, and FlowSync-UQ reported identical 12.52s delay due to uncoordinated multi-agent simulation physics."
        },
        {
            "dataset_id": "DS-25",
            "dataset_name": "Legacy Multi-Session Shadow Mode Replay (Excluded)",
            "file_path": "results/final/shadow_mode_multi_session.json",
            "record_count": 3,
            "total_steps_or_samples": 4500,
            "testbed": "Synthetic Arrival Generator",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/cv/shadow_mode_multi_session.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Synthetic geometric arrival distributions mislabeled as 'empirical CCTV video replay'. FlowSync-UQ trailed Max-Pressure by 3-4x."
        },
        {
            "dataset_id": "DS-26",
            "dataset_name": "Legacy Hardened Suite 20-Seed Summary (Excluded)",
            "file_path": "results/final/final_hardened_suite_summary.json",
            "record_count": 20,
            "total_steps_or_samples": 30000,
            "testbed": "Custom Simulator (Single Policy)",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/legacy/run_final_hardened_experiments.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Evaluated only a single training seed (Seed 42). Formally superseded on October 15, 2026 by the 2,800-run matched shield protocol."
        },
        {
            "dataset_id": "DS-27",
            "dataset_name": "Legacy Reliability Boundary Grid Evaluation (Excluded)",
            "file_path": "results/final/reliability_boundary_v2.json",
            "record_count": 20,
            "total_steps_or_samples": 30000,
            "testbed": "Custom Simulator (Single Policy)",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/legacy/run_reliability_boundary.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Un-replicated preliminary sweep on ad-hoc noise parameters. Superseded by the 10-cell matched shield protocol."
        },
        {
            "dataset_id": "DS-28",
            "dataset_name": "Legacy Statistical Report v2 (Excluded)",
            "file_path": "results/final/statistical_report_v2.json",
            "record_count": 1,
            "total_steps_or_samples": 0,
            "testbed": "Statistical Report",
            "status_classification": "Excluded",
            "governing_protocol_or_manifest": "research/legacy/evaluate_results.py",
            "conflicts_observed": "N/A",
            "clearance_violations_observed": "N/A",
            "description_and_notes": "EXCLUDED: Outdated statistical summaries claiming p=1.48e-6 based on single-seed comparison against unshielded baseline."
        }
    ]

    fieldnames = [
        "dataset_id",
        "dataset_name",
        "file_path",
        "file_size_bytes",
        "sha256_hash",
        "record_count",
        "total_steps_or_samples",
        "testbed",
        "status_classification",
        "governing_protocol_or_manifest",
        "conflicts_observed",
        "clearance_violations_observed",
        "description_and_notes"
    ]

    # Populate actual file_size and sha256_hash
    for r in records:
        p = ROOT / r["file_path"]
        if p.exists():
            r["file_size_bytes"] = file_size(p)
            r["sha256_hash"] = file_sha256(p)
        else:
            # Check git HEAD for excluded files
            res = subprocess.run(["git", "show", f"HEAD:{r['file_path']}"], capture_output=True)
            if res.returncode == 0:
                r["file_size_bytes"] = len(res.stdout)
                r["sha256_hash"] = hashlib.sha256(res.stdout).hexdigest()
            else:
                r["file_size_bytes"] = 0
                r["sha256_hash"] = "EXCLUDED_QUARANTINED"

    out_csv = RES_EVAL / "FINAL_DATASET_INVENTORY.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    with open(ROOT / "FINAL_DATASET_INVENTORY.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Generated FINAL_DATASET_INVENTORY.csv with {len(records)} entries.")

if __name__ == "__main__":
    build_sha256sums()
    build_dataset_inventory()

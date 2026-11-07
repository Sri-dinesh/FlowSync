# FlowSync – Final Experimental Evidence Freeze

**Status**: Authoritative & Cryptographically Sealed  
**Freeze Date**: November 2026  
**Repository Working Directory**: `FlowSync/`  
**Governing Authority**: Pre-Registered Protocols (`MATCHED_SHIELD_PROTOCOL_20261015.md`, et seq.)  
**Lead Verification Worker**: Independent Experimental Verification Worker  

---

## 1. Executive Freeze Declaration

This document constitutes the **Final Experimental Results Freeze** for the FlowSync research initiative. All experimental campaigns, raw simulation logs, model checkpoints, statistical pipeline outputs, and multi-testbed safety audits described herein are formally frozen.

### Strict Methodological Boundaries
1. **Preservation of Raw Data**: No raw simulation logs, checkpoint weights, or observation records have been modified, regenerated, or re-run.
2. **Multi-Seed Integrity**: The 2,800-run primary custom simulation panel reflects 3 independently trained D3QN seeds (101, 202, 303) across 20 matched traffic seeds and 10 scenario-condition cells.
3. **Multiplicity Control**: Multiplicity adjustments are governed by the pre-registered crossed bootstrap ($B = 5,000$, seed 717) and Holm-Bonferroni correction across all 19 comparisons ($N = 200$ cells, $df = 199$).
4. **No Premature Promotion**: No future experiments, real-video CCTV validations, or Jetson Orin hardware benchmarks are claimed to have been completed.
5. **Clear Experiment Taxonomy**: Every experiment conducted in the FlowSync program is explicitly classified under one of five exhaustive categories:
   - **Primary and complete**
   - **Supplementary and complete**
   - **Exploratory**
   - **Incomplete**
   - **Excluded**

---

## 2. Definitive Classification of All Experimental Campaigns

Every dataset and experiment in the FlowSync repository is classified according to the five pre-registered categories below:

### 2.1. Primary and Complete
*Rigorous, fully replicated, pre-registered confirmatory experiments forming the empirical foundation of the paper.*

1. **Custom Simulator Matched-Shield Evaluation Panel** (`DS-01`, `DS-02`):
   - **File Paths**: `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`, `report.json`
   - **Cryptographic Hash**: `1c675eca8526469aa7b54be18438440dddef55b501f609b578a74de4ef67892d` (runs.jsonl, 10,381,256 B)
   - **Volume**: 2,800 runs (14 controller arms $\times$ 200 matched arrival traces); 4,340,000 steps.
   - **Findings**:
     - Pre-registered Primary Contrast (`d3qn_shield_vs_max_pressure_shield`): Mean delay difference **$-0.050\,\mathrm{s}$** ($95\%$ crossed-bootstrap CI $[-0.219, +0.125]\,\mathrm{s}$, paired $t = -0.72$, Holm $p_{\mathrm{adj}} = 1.000$).
     - Clean Contrast: Mean delay difference **$-0.098\,\mathrm{s}$** ($95\%$ CI $[-0.299, +0.088]\,\mathrm{s}$).
     - Within-Run P95 Contrast: Mean difference **$-0.212\,\mathrm{s}$** ($95\%$ CI $[-0.920, +0.445]\,\mathrm{s}$).
     - Shield Delay Overhead: D3QN overhead $+0.476\,\mathrm{s}$ ($p < 10^{-11}$); Max-Pressure overhead $+0.439\,\mathrm{s}$ ($p < 10^{-8}$).
     - FlowSync-UQ Fallback Increment: Mean delay difference **$-0.015\,\mathrm{s}$** relative to Shielded D3QN ($p_{\mathrm{adj}} = 1.000$).
   - **Safety Audit**: 0 signal conflicts, 0 clearance violations across all 4,340,000 steps.
2. **Evaluated D3QN Checkpoints** (`DS-03`, `DS-04`, `DS-05`):
   - **Seed 101**: `checkpoint_warmup.pt` (Ep 0, validation delay 10.903s), SHA-256 `1cd49647...`
   - **Seed 202**: `checkpoint_50.pt` (Ep 50, peak validation performance), SHA-256 `a91e038d...`
   - **Seed 303**: `checkpoint_100.pt` (Ep 100, peak validation performance), SHA-256 `e0b830b4...`

---

### 2.2. Supplementary and Complete
*Rigorous secondary and diagnostic experiments conducted under frozen execution manifests that fully completed their planned runs.*

1. **SUMO 180s Sensing Recovery Panel** (`DS-06`, `DS-07`):
   - **File Path**: `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl`
   - **Cryptographic Hash**: `3db5b6e88b77727413276c92124c8b554be7d5bba68c5ef4831556f3622a65e4` (78,470 B)
   - **Volume**: 72 completed episodes (51 reused, 21 recovered); 129,600 steps.
   - **Findings**: Evaluated Max-Pressure and classical baselines under clean vs combined sensor faults in microscopic SUMO 1.24.0. Clean MP mean stopped wait: 6.304s; fault MP wait: 5.727s (11.50 phase switches vs 12.50 clean). 0 conflicts, 0 clearance violations.
2. **SUMO 360s Robustness Panel** (`DS-08`, `DS-09`):
   - **File Path**: `results/sumo_robustness/full_20261023/runs.jsonl`
   - **Cryptographic Hash**: `3f86ea08996236dd547b19714eb880064f8d043ccd9c623b3607034d962408fd` (62,514 B)
   - **Volume**: 24 completed runs (12 Max-Pressure, 12 Total-Incoming queue distortion); 86,400 steps.
   - **Findings**: System-wide P95 delay increased from 18.68s (MP) to 26.06s (+39.5%) under queue distortion. In asymmetric corridors, minor approach wait surged from 6.150s to 17.154s (+178.9%, P95 up +147.0%). 0 conflicts, 0 clearance violations.
3. **SUMO Classical Baseline Panel** (`DS-10`):
   - **File Path**: `results/sumo_classical_panel/full_20261023/report.json` (SHA-256 `7cd78ca4...`)
   - **Volume**: 45 completed runs; 81,000 steps. 0 conflicts, 0 clearance violations.
4. **SUMO Switching Margin Panel** (`DS-11`):
   - **File Path**: `results/sumo_switching/full_20261101/report.json` (SHA-256 `99ad2915...`)
   - **Volume**: 36 completed runs; 129,600 steps. 0 conflicts, 0 clearance violations.
5. **SUMO History Queue Filter Panel** (`DS-12`):
   - **File Path**: `results/sumo_history/full_20261101/report.json` (SHA-256 `123f44e1...`)
   - **Volume**: 60 completed runs; 216,000 steps. 0 conflicts, 0 clearance violations.
6. **Hardware Latency Benchmark** (`DS-14`):
   - **File Path**: `results/final/latency_profile_full.json` (SHA-256 `d38bd921...`)
   - **Volume**: 10,000 sequential steps on x86_64 CPU workstation (Intel Core i5-1135G7 @ 2.40 GHz).
   - **Findings**: Perception pipeline mean 57.23 ms (P95 64.81 ms); controller pipeline mean 0.43 ms (P95 0.45 ms); full pipeline mean 57.66 ms, P95 65.26 ms, Max 206.51 ms. Benchmarked on workstation CPU; NOT benchmarked on Jetson Orin embedded hardware.
7. **Perception Uncertainty Calibration Artifact** (`DS-15`):
   - **File Path**: `results/uncertainty_calibration/pilot_20261014/calibration.json` (SHA-256 `272d10a0...`)
   - **Scope**: Fitted on synthetic queue-count discrepancies ($\ge 3$ vehicles) in custom simulation. Logistic gate parameters: intercept $-0.9330$, count volatility $2.0058$, forecast residual $0.2501$; 2 of 7 active features.
8. **Spatial Feature Input & Teacher Diagnostic Audits** (`DS-16` to `DS-19`):
   - **File Paths**: `results/spatial_input_audit/`, `results/teacher_alignment/`, `results/teacher_horizon/`, `results/research_training/spatial_smoke_20261021/`
   - **Volume**: 342,800 steps across 4 diagnostic suites. 0 conflicts, 0 clearance violations.

---

### 2.3. Incomplete
*Experiments that were interrupted or halted prior to planned completion in accordance with frozen safety or budget limits.*

1. **SUMO Service Ledger Panel** (`DS-13`):
   - **File Path**: `results/sumo_service_ledger/full_20261103/report.json` (SHA-256 `5fd11192...`)
   - **Volume Completed**: Exactly **111 runs** completed out of **144 planned runs** ($77.1\%$).
   - **Execution Steps**: **399,600 steps** audited; 0 conflicts, 0 clearance violations.
   - **Reason for Incompletion**: The multi-session execution reached the declared wall-clock allowance limit of 3,600 seconds (`SessionBudgetExceeded` after 3,600.08 s). In accordance with protocol, the run was cleanly sealed as partial rather than completed.
   - **Status Flags**: `"complete": false`, `"scientific_panel_complete": false`, `"publication_ready": false`. Must NOT be cited as a complete confirmatory evaluation.

---

### 2.4. Exploratory
*Preliminary research pilots, retraining explorations, or smoke tests without pre-registered statistical power or confirmatory guarantees.*

1. **PPO & Count Restoration Pilots** (`DS-20`, `DS-21`):
   - **File Paths**: `results/count_restoration/pilot_20261029/` (108 runs, 129,600 steps), `results/ppo_restoration/recovered_20261030/` (270 evaluations, 210,400 steps).
   - **Total Audited Steps**: **340,000 steps**.
   - **Status**: Exploratory retraining pilots testing whether PPO policy updates or linear count estimators could rescue performance under noise. Both failed promotion criteria (`publication_ready: false`).
2. **Early Calibration / Smoke Pilots** (`DS-22`):
   - **File Path**: `results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/trajectory.jsonl`
   - **Volume**: 70 preliminary calibration runs $\times$ 1,500 ticks = **105,000 steps**.
   - **Status**: Smoke test verification of basic physics and lamp control. 0 conflicts, 0 clearance violations.

---

### 2.5. Excluded
*Legacy or un-replicated artifacts formally quarantined and excluded from all final paper claims, tables, and figures.*

1. **`results/final/cv_validation_metrics.json`** (`DS-23`, SHA-256 `76322b45...`):
   - **Status**: **FABRICATED / UNVERIFIED**.
   - **Rationale**: Mislabeled 1,000 annotated video frames and reported $r = 0.928$ correlation. Audit revealed the generating script fabricated numbers without video annotations; generator was disabled with RuntimeError. Excluded from paper.
2. **`results/final/city_2x2_scalability_v2.json`** (`DS-24`, SHA-256 `72537630...`):
   - **Status**: **DEGENERATE / UNRECONCILED**.
   - **Rationale**: Fixed-Time, D3QN, and FlowSync-UQ yielded identical 12.52s delay due to uncoordinated multi-agent simulation physics. Multi-intersection grid retained as Future Research.
3. **`results/final/shadow_mode_multi_session.json`** (`DS-25`, SHA-256 `20b14753...`):
   - **Status**: **SYNTHETIC / METHODOLOGICALLY FLAWED**.
   - **Rationale**: Mislabeled synthetic geometric arrivals (`rng.geometric`) as empirical CCTV replay. Excluded from paper.
4. **`results/final/final_hardened_suite_summary.json`** (`DS-26`, SHA-256 `a5b20781...`):
   - **Status**: **SUPERSEDED**.
   - **Rationale**: Evaluated only a single training seed (Seed 42). Formally superseded on October 15, 2026 by the 2,800-run matched shield protocol.
5. **`results/final/reliability_boundary_v2.json`** (`DS-27`, SHA-256 `904fe85e...`):
   - **Status**: **SUPERSEDED**. Single-policy un-replicated noise parameter sweep.
6. **`results/final/statistical_report_v2.json`** (`DS-28`, SHA-256 `babaf243...`):
   - **Status**: **SUPERSEDED**. Outdated $p = 1.48 \times 10^{-6}$ claim from comparing single seed against unshielded baseline.

---

## 3. Cryptographic Lineage & Integrity Registry

All 28 datasets and artifacts are cryptographically registered in `FINAL_DATASET_INVENTORY.csv` and `SHA256SUMS.txt`. The primary execution hashes are:

| Artifact Name | Path | Size (Bytes) | SHA-256 Hash |
|---|---|---:|---|
| **Primary Custom Sim Dataset** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` | 10,381,256 | `1c675eca8526469aa7b54be18438440dddef55b501f609b578a74de4ef67892d` |
| **Primary Replicate Report** | `results/replicate_evaluation/matched_shield_v5_20261015/report.json` | 41,800 | `46e8a6505dc36192b52038281555899fdaf401c07d99d233c0d095977920fcb9` |
| **SUMO 180s Sensing Dataset** | `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl` | 78,470 | `3db5b6e88b77727413276c92124c8b554be7d5bba68c5ef4831556f3622a65e4` |
| **SUMO 360s Robustness Dataset** | `results/sumo_robustness/full_20261023/runs.jsonl` | 62,514 | `3f86ea08996236dd547b19714eb880064f8d043ccd9c623b3607034d962408fd` |
| **Hardware Latency Benchmark** | `results/final/latency_profile_full.json` | 4,281 | `d38bd92135e90661a31b9d2d64dcc21538d04b2a28fadbe0e45677b9e1938560` |
| **Uncertainty Calibration** | `results/uncertainty_calibration/pilot_20261014/calibration.json` | 16,072 | `272d10a0968dc9be7a295f1f8baf7b53497da34a37b28ec76aa6fc635404e521` |
| **D3QN Checkpoint Ep 0** | `seed_101/checkpoint_warmup.pt` | 2,327,247 | `1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725` |
| **D3QN Checkpoint Ep 50** | `seed_202/checkpoint_50.pt` | 2,326,903 | `a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4` |
| **D3QN Checkpoint Ep 100** | `seed_303/checkpoint_100.pt` | 2,326,989 | `e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052` |

---

## 4. Itemized Multi-Testbed Safety Sample Summary

$$\begin{aligned}
\text{Primary Custom Simulator Panel (2,800 runs)} &= 4,340,000 \text{ steps} \\
\text{SUMO Microscopic Panels (6 panels, 348 runs)} &= 1,042,200 \text{ steps} \\
\text{Spatial Input \& Teacher Diagnostics (4 suites)} &= 342,800 \text{ steps} \\
\text{PPO \& Count Restoration Pilots (2 suites)} &= 340,000 \text{ steps} \\
\hline
\mathbf{Itemized\ Multi\text{-}Testbed\ Audited\ Total} &= \mathbf{6,065,000 \text{ steps}} \\
\text{Early Calibration / Smoke Pilots (70 runs)} &= 105,000 \text{ steps} \\
\hline
\mathbf{Reconciled\ Grand\ Reported\ Total} &= \mathbf{6,170,000 \text{ steps}}
\end{aligned}$$

Across all 6,170,000 audited steps:
- **Executed Signal Conflicts**: **0**
- **Clearance Interval Violations**: **0**
- **Safety Invariants Maintained**: **100.0%**

---

## 5. Explicit Negative Findings & Scientific Disclaimers

1. **Absence of Proof of Equivalence**: The primary confirmatory contrast ($\Delta = -0.050\,\mathrm{s}$, $95\%$ CI $[-0.219, +0.125]\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 1.000$) fails to reject the null hypothesis of equal stopped delay between Shielded D3QN and Shielded Max-Pressure. This failure to reject does **NOT** prove equivalence or non-inferiority.
2. **Safety Shield Overhead Tax**: The safety shield is essential for preventing signal conflicts and starvation, but incurs a measurable empirical overhead: $+0.476\,\mathrm{s}$ on D3QN ($p = 7.87 \times 10^{-12}$) and $+0.439\,\mathrm{s}$ on Max-Pressure ($p = 3.13 \times 10^{-8}$).
3. **No Detected Benefit for Fallback Switching**: FlowSync-UQ added $+0.015\,\mathrm{s}$ average delay relative to Shielded D3QN ($p_{\mathrm{adj}} = 1.000$). Under the synthetic sensor fault conditions evaluated, switching to Max-Pressure fallback maintained safety compliance without improving stopped delay.
4. **Conditional Checkpoint Inference**: Custom simulator replicate results condition inference on three selected checkpoints (Ep 0, Ep 50, Ep 100) and do not represent the entire distribution of RL training trajectories.
5. **Workstation Hardware Platform**: All latency benchmarks were conducted on an x86_64 CPU Linux laptop. No testing was performed on NVIDIA Jetson Orin embedded boards, and P99 latency spikes (164.43 ms) preclude deterministic hard real-time guarantees.
6. **Synthetic Uncertainty Calibration**: The uncertainty gate was fitted on synthetic queue-count discrepancies, not on physical camera sensor inputs.

---

## 6. Freeze Ratification

This experimental results freeze is ratified and sealed. All primary findings are reproducible from the frozen raw logs using `results_evaluation/compact_verification/reproduce_evaluation.py`. No additional simulations, re-evaluations, or data modifications are permitted under the pre-registered protocol.

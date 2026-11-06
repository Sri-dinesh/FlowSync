# FlowSync – Experimental Results Verification Report

**Verification Date**: November 2026  
**Auditor**: Independent Senior Experimental Verification Worker  
**Repository**: FlowSync (`personal-stuff/FlowSync`)  
**Scope**: Methodological audit, data provenance tracking, code-to-result reconciliation, and discrepancy identification.

---

## 1. Direct vs. Derived Verification Matrix

Every quantitative claim, table, and statistical metric reported in this evaluation was verified against primary experimental artifacts:

| Experimental Area | Primary Artifact File | Verification Method | Verification Status | Notes |
|---|---|---|---|---|
| **Custom Simulator Runs (2,800 runs)** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` | Direct recomputation from raw line-delimited JSON records | **DIRECTLY VERIFIED** | Recomputed mean, std, median, p25, p75, p95, min, max, throughput, queue area, service rate, starvation counts, and safety samples. |
| **Custom Simulator Contrasts** | `flowsync_paper_evidence/03_custom_simulator/paired_contrasts.csv` | Direct paired bootstrap resampling & frozen paired contrasts | **DIRECTLY VERIFIED** | Verified paired contrasts between all 8 controller configurations across 200 evaluation cells. |
| **SUMO 180s Sensing Panel (72 episodes)** | `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl` | Direct parsing of 72 episode records in collection | **DIRECTLY VERIFIED** | Recomputed stopped wait per requested vehicle, completed trips, switch onsets, and clean vs fault deltas. 51 reused, 21 recovered, 0 fresh. |
| **SUMO 360s Robustness Panel (24 runs)** | `results/sumo_robustness/full_20261023/report.json` | Direct inspection of 24 runs across 12 paired seed/start contexts | **DIRECTLY VERIFIED** | Recomputed 180s and 360s endpoints; verified minor-axis starvation under queue distortion. |
| **SUMO Service Ledger Panel (111 runs)** | `results/sumo_service_ledger/full_20261103/report.json` | Direct inspection of 111 completed runs and 399,600 samples | **DIRECTLY VERIFIED** | Verified session budget cap cutoff (111/144 planned runs) and service debt policies. |
| **SUMO History Panel (60 runs)** | `results/sumo_history/full_20261101/report.json` | Direct inspection of 60 completed runs and 216,000 samples | **DIRECTLY VERIFIED** | Verified FIR filtering and history tracking on queue estimates. |
| **SUMO Switching Margin Panel (36 runs)** | `results/sumo_switching/full_20261101/report.json` | Direct inspection of 36 completed runs and 129,600 samples | **DIRECTLY VERIFIED** | Verified hysteresis margin switching on pressure proposals. |
| **PPO Restoration Panel (36 runs)** | `results/paper_evidence/ppo_restoration_final_20261030/condition_summary.csv` | Direct parsing of 36 runs across 4 training stages | **DIRECTLY VERIFIED** | Confirmed PPO degradation from 9.056s to 9.555s; verified 10/270 reward-delay misalignments. |
| **Count Restoration Panel (18 runs)** | `results/paper_evidence/count_restoration_final_20261029/control_summary.csv` | Direct parsing of fitted restoration models across 3 seeds | **DIRECTLY VERIFIED** | Verified MAE reduction from 0.0784 to 0.0272; verified Bare MP (11.030s) beating restored D3QN (11.491s). |
| **Spatial Input Audit (27 sources, 44 branches)**| `research/docs/audits/SPATIAL_INPUT_AUDIT_RESULTS_20261022.md` | Direct parsing of 320 decision gates and Q-value margins | **DIRECTLY VERIFIED** | Confirmed 0/320 proposal changes when zeroing upstream spatial inputs. |
| **Teacher Alignment Diagnostic (7 gates)** | `research/docs/results/TEACHER_ALIGNMENT_RESULTS_20261022.md` | Direct inspection of forced upstream teacher branches | **DIRECTLY VERIFIED** | Confirmed upstream teacher switches worsen branch delay by +5.339 vehicle-seconds. |
| **Execution Latency Profile (10,000 steps)** | `results/final/latency_profile_full.json` | Direct inspection of JSON benchmark output and host telemetry | **DIRECTLY VERIFIED** | Recomputed component latency percentiles (P50, P90, P95, P99, Max) and inspected host hardware metadata. |
| **Uncertainty Calibration** | `results/uncertainty_calibration/pilot_20261014/calibration.json` | Direct inspection of logistic model weights, intercepts, thresholds | **DIRECTLY VERIFIED** | Verified active feature weights, calibration target, ROC-AUC, Brier score, and threshold seeds. |
| **Fallback Benefit Gate** | `results/benefit_gate/train_20261016/benefit_gate.json` | Direct inspection of secondary classifier model | **DIRECTLY VERIFIED** | Verified 186 training samples, 21.5% positive class balance, and feature coefficients. |
| **Training Lineage & Checkpoints** | `results/research_training/pilot_v5_kbW0lsY3/seed_*.log` | Direct line-by-line inspection of training and validation logs | **DIRECTLY VERIFIED** | Verified validation delays across episodes, Max-Pressure demonstration warmup, and checkpoint selection. |
| **Signal Safety Audit (6,170,000+ samples)** | Repository-wide simulation logs | Direct summation of executed conflict and clearance counters | **DIRECTLY VERIFIED** | Verified 0 executed conflicts and 0 clearance violations across 6,170,000+ executed simulated signal steps. |

---

## 2. Provenance of Experimental Runs

### A. Custom Simulator Panel (`matched_shield_v5_20261015`)
- **Total Runs**: 2,800 completed runs (0 failed, 0 duplicate).
- **Traffic Seeds**: 20 paired seeds (`81001` through `81020`).
- **Common Random Numbers (CRN)**: Verified. All controllers encounter identical arrival traces per seed, confirmed by matching `arrival_trace_hash` values in `runs.jsonl`.
- **Training Seeds**: 3 independent seeds (`101`, `202`, `303`).
- **Execution Date**: October 15, 2026.
- **Status**: Complete, intact, frozen evaluation dataset.

### B. SUMO Panels
1. **Sensing Panel (`full_20261031`)**: 72 episodes (3 controllers $\times$ 4 conditions $\times$ 6 seeds). 51 reused, 21 recovered, 0 fresh. Only classical baselines evaluated.
2. **Robustness Panel (`full_20261023`)**: 24 runs (6 seeds $\times$ 2 starts $\times$ 2 controllers). 86,400 signal samples. 180s and 360s endpoints.
3. **Classical Comparison (`classical_20261023`)**: 45 runs, 81,000 samples.
4. **History Panel (`full_20261101`)**: 60 runs, 216,000 samples.
5. **Switching Panel (`full_20261101`)**: 36 runs, 129,600 samples.
6. **Service Ledger Panel (`full_20261103`)**: 111 completed runs out of 144 planned runs (399,600 samples), stopped by frozen 3,600 s wall-clock session cap.

---

## 3. Discrepancies Between Code, Artifacts, and Manuscripts

The audit identified seven substantial discrepancies between actual implementations/artifacts and preliminary manuscript drafts/summaries:

### Discrepancy 1: Target Hardware Platform (x86_64 CPU vs. NVIDIA Jetson Orin)
- **Claimed in Manuscript**: End-to-end 95th-percentile execution latency of 65.26 ms on an embedded **NVIDIA Jetson Orin** board.
- **Actual Evidence in Artifact (`results/final/latency_profile_full.json`)**:
  - `hardware_specs.os_name`: `Linux`
  - `hardware_specs.os_release`: `7.0.10-arch1-1`
  - `hardware_specs.architecture`: `x86_64`
  - `hardware_specs.cuda_available`: `false`
  - `hardware_specs.device`: `cpu`
  - `hardware_specs.num_cpu_threads`: `4`
- **Correction**: All claims attributing this latency to Jetson Orin must be retracted. The measurement characterizes a commodity x86_64 CPU workstation running YOLOv8n and PyTorch CPU inference.

### Discrepancy 2: Reward Function Formulation
- **Claimed in Documentation / Config**: Reward function uses switch penalty of $-2.0$ and delay scaling of $-1.0 \times \text{delay}$.
- **Actual Implementation (`server/app/simulation/environment.py`, lines 151–185)**:
  - Delay scaled by 0.1 (`-float(delay_incurred) / 10.0`)
  - Total pressure penalty (`-total_curr * 0.05 * dt`)
  - Throughput reward (`+vehicles_passed * 0.10`)
  - Dynamic switch penalty (`-0.10` if prev phase pressure $> 0.5$ else `-0.03`)
  - Starvation penalty (`-0.10 * len(starved) * dt`)
  - Max-green penalty (`-0.10 * dt`)
- **Correction**: Update all mathematical descriptions of the MDP reward to reflect the 7 decomposed terms and actual scaling factors.

### Discrepancy 3: Regulatory Clearance Interval Definitions
- **Claimed in Paper Abstract**: Yellow interval $Y = 3.0\,\mathrm{s}$, All-Red clearance $R = 1.0\,\mathrm{s}$.
- **Actual Custom Simulator Values (`runs.jsonl`)**: Yellow $Y = 2.0\,\mathrm{s}$, All-Red $R = 3.0\,\mathrm{s}$ (Total = $5.0\,\mathrm{s}$).
- **Actual SUMO Values (`connections.con.xml`)**: Yellow $Y = 3.0\,\mathrm{s}$, All-Red $R = 1.0\,\mathrm{s}$ (Total = $4.0\,\mathrm{s}$).
- **Correction**: Explicitly distinguish clearance intervals between the custom simulator ($Y=2.0\,\mathrm{s}, R=3.0\,\mathrm{s}$) and SUMO ($Y=3.0\,\mathrm{s}, R=1.0\,\mathrm{s}$).

### Discrepancy 4: Fallback Dwell Duration Dynamics
- **Claimed in Manuscript Drafts**: Fallback dwell lasts 40 calls evaluated every 2 seconds, suggesting a minimum dwell of 80 to 100 seconds, matching the observed ~85 s mean duration.
- **Actual Implementation (`server/app/controllers/supervisor.py`, lines 78–120)**:
  - Supervisor is updated at **10 Hz (every 0.1 s tick)**, not every 2.0 seconds.
  - `min_dwell_steps = 40` corresponds to **4.0 seconds**.
  - The observed mean duration of **85.06 seconds** is an empirical consequence of **58.17% right-censoring**: in 178 of 306 activations, persistent synthetic noise prevented the uncertainty score from dropping below `threshold_low` (0.3707) for 10 consecutive ticks (`recovery_window_steps = 10`), holding fallback active until the 1,500-step (150 s) run finished.
- **Correction**: Clarify that minimum dwell is 4.0 seconds (40 ticks at 10 Hz) and that 85 s is an empirical mean reflecting episode termination under persistent faults.

### Discrepancy 5: Active Features in Uncertainty Calibration
- **Claimed in Manuscript**: Multi-feature uncertainty estimation fusing 7 vision, tracking, and telemetry features.
- **Actual Evidence in Artifact (`results/uncertainty_calibration/pilot_20261014/calibration.json`)**:
  - `count_volatility`: coefficient **+2.0058**
  - `forecast_residual`: coefficient **+0.2501**
  - Other 5 features: **0.0** (inactive)
- **Correction**: Disclose that only 2 features are actively utilized, and that calibration was trained against synthetic count errors rather than real video detector uncertainty.

### Discrepancy 6: Checkpoint Selection & RL Training Progression
- **Framed in Drafts**: D3QN iteratively learns an optimized traffic control policy via online RL that outperforms classical heuristics.
- **Actual Evidence in Logs (`results/research_training/pilot_v5_kbW0lsY3/seed_101.log`)**:
  - For Seed 101, the policy with the lowest validation delay was `checkpoint_warmup.pt` (Episode 0), produced immediately after Behavior Cloning on Max-Pressure demonstrations.
  - Throughout the subsequent 223 online RL training episodes, validation delay never surpassed this warmup benchmark.
  - PPO restoration experiments confirmed identical behavior: online PPO degraded from 9.056 s to 9.555 s.
- **Correction**: Acknowledge that D3QN and PPO function primarily as demonstration-cloned approximations of Max-Pressure, explaining why their performance closely tracks classical Max-Pressure without surpassing it.

### Discrepancy 7: SUMO Scope and Horizon Dynamics
- **Framed in Drafts**: SUMO results prove that imperfect sensing improves Max-Pressure performance.
- **Actual Evidence in 360s Extended Panel (`results/sumo_robustness/full_20261023/`)**:
  - In a 180s simulation, missed detections saved 1 switch (4.0s lost time).
  - At 360s, counting distortions raise P95 waiting by +39.5% and cause extreme minor-approach starvation: minor-approach mean delay increases from 6.15s to 17.15s (nearly 3x!).
- **Correction**: Retract the claim that imperfect sensing improves real-world performance; document the severe distributional starvation revealed by extended-horizon evaluation.

---

## 4. Missing or Unreliable Evidence

1. **Unevaluated Learned Controllers in Microscopic SUMO**:
   - Neither D3QN nor FlowSync-UQ was evaluated in SUMO 1.24.0. Claims regarding learned policy performance in SUMO are unevidenced.
2. **Absence of Edge Hardware Profile Artifacts**:
   - No benchmark logs, power measurements, or TensorRT engine profiles from NVIDIA Jetson Orin hardware exist in the repository.
3. **Unverified Camera Uncertainty Calibration**:
   - The uncertainty estimator was calibrated against a synthetic simulator discrepancy threshold ($\ge 3$ vehicles) rather than actual YOLOv8n object detection confidences or real-world video ground truth.
4. **Lack of Matched Training-Recipe Shield Ablation**:
   - The unshielded D3QN evaluation evaluated the *same* shielded checkpoint with the shield bypassed at inference time, rather than training an unshielded policy from scratch.

---

## 5. Final Verification Declaration

The evaluation results recorded in `FINAL_EXPERIMENT_RESULTS_EVALUATION.md` reflect the exact numerical reality of the experimental data generated across FlowSync. All findings have been reconciled against the underlying source code, configuration files, raw data records, and research status documents.

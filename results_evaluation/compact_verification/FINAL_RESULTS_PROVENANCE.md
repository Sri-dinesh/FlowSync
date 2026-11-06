# FlowSync – Experimental Results Provenance & Cryptographic Artifact Registry

**Document Purpose**: Definitive cryptographic lineage, data provenance, frozen protocol registry, and statistical methodology reference for all FlowSync experimental results.  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Evaluation Directory**: `results_evaluation/`  

---

## 1. Frozen Protocols & Authoritative Manifests

All primary experimental findings are governed by pre-registered, frozen execution protocols locked prior to simulation execution.

| Protocol / Manifest Name | File Path | File Size | SHA-256 Checksum | Scope & Governing Authority |
|---|---|---:|---|---|
| **Frozen Matched Shield Protocol** | `research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md` | 4,665 B | `e92e659c35adc051bf18c424223e47af6cc8cd1eea082e77b9fc896ad09d692b` | Authoritative pre-registered design; specifies the single confirmatory primary contrast (`d3qn_shield_vs_max_pressure_shield`), 20 traffic seeds, 10 scenario-condition cells, 3 training replicates, and crossed-bootstrap analysis. |
| **Matched Shield Execution Manifest** | `results/replicate_evaluation/matched_shield_v5_20261015/manifest.json` | 1,543,416 B | `4af8127418f08cbc80fe5715e92e24237564192f0a2d860e49798b17ad0f5a1a` | Complete job manifest locking input hashes, checkpoint paths, random seed sequences, and evaluation parameters for all 2,800 runs. |
| **Statistical Pipeline Script** | `research/evaluation/evaluate_replicates.py` | 15,929 B | `1995479550f8e2b2d13afc9145302ef6511aab22b86d7c4e67c4d5d51013f28b` | Implements `crossed_bootstrap(differences, draws=5000, seed=717)`, metric aggregation, and report generation. |
| **SUMO 180s Sensing Manifest** | `results/sumo_sensing_recovery/full_20261031/manifest.json` | 8,671 B | `a49874a0bf940a349a950fa3afd1fa51963b2d00a7c83766dfb8564a0f7c172a` | Manifest governing the 72-episode 180s SUMO sensing panel across 3 baseline controllers, 4 sensing conditions, and 6 seeds. |
| **SUMO 360s Robustness Manifest** | `results/sumo_robustness/full_20261023/manifest.json` | 8,529 B | `c9b2d5fceaf3b4e67df572d7b29133add0c5546702ec598b666619ce583b63e5` | Manifest governing the 24-run 360s SUMO robustness panel across 2 controllers, 6 seeds, and 2 initial phase contexts. |

---

## 2. Primary Raw Execution Datasets

Every numerical value reported in the paper is traced directly to one of the following raw execution records:

| Dataset / Artifact | File Path | File Size | SHA-256 Checksum | Number of Records / Content Summary |
|---|---|---:|---|---|
| **Custom Simulator Runs** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` | 10,381,256 B | `1c675eca8526469aa7b54be18438440dddef55b501f609b578a74de4ef67892d` | 2,800 line-delimited JSON run records; 14 controller arms $\times$ 200 unique arrival traces; 4,340,000 executed steps; 0 conflicts; 0 clearance violations. |
| **Custom Simulator Evaluation Report** | `results/replicate_evaluation/matched_shield_v5_20261015/report.json` | 41,800 B | `46e8a6505dc36192b52038281555899fdaf401c07d99d233c0d095977920fcb9` | Protocol-compliant aggregate metrics and 5,000-draw crossed-bootstrap confidence intervals for all controller comparisons. |
| **SUMO 180s Sensing Runs** | `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl` | 78,470 B | `3db5b6e88b77727413276c92124c8b554be7d5bba68c5ef4831556f3622a65e4` | 72 SUMO episode records (51 reused, 21 recovered/new); 129,600 signal steps; 0 conflicts; 0 clearance violations. |
| **SUMO 180s Sensing Report** | `results/sumo_sensing_recovery/full_20261031/report.json` | 15,880 B | `5357399a007b826d0e526c39a8e2a908b4dda584040ddb7f4ff31f1bffd2e7f6` | 180s sensing panel summary; `publication_ready: false` (exploratory sensing evidence). |
| **SUMO 360s Robustness Runs** | `results/sumo_robustness/full_20261023/runs.jsonl` | 62,514 B | `3f86ea08996236dd547b19714eb880064f8d043ccd9c623b3607034d962408fd` | 24 SUMO run records (12 Max-Pressure, 12 Total-Incoming queue distortion); 86,400 signal steps; 0 conflicts; 0 clearance violations. |
| **SUMO 360s Robustness Report** | `results/sumo_robustness/full_20261023/report.json` | 87,260 B | `1d3b6e7f9f2109e268cdd3821ef6c2046abf1de38350abecc351c5cc67799c5e` | 360s robustness panel summary; 180s prefix vs 360s primary endpoint metrics; `publication_ready: false`. |
| **Hardware Latency Profile** | `results/final/latency_profile_full.json` | 4,281 B | `d38bd92135e90661a31b9d2d64dcc21538d04b2a28fadbe0e45677b9e1938560` | Full perception-to-control timing profile across 10,000 steps on x86_64 CPU Linux platform (no Jetson Orin). |
| **Uncertainty Calibration Artifact** | `results/uncertainty_calibration/pilot_20261014/calibration.json` | 16,072 B | `272d10a0968dc9be7a295f1f8baf7b53497da34a37b28ec76aa6fc635404e521` | Calibrated logistic gate parameters on synthetic count errors: intercept $-0.9330$, count volatility $2.0058$, forecast residual $0.2501$, active features 2/7. |

---

## 3. Checkpoints & Model Provenance

The three D3QN policies evaluated in the custom simulator panel were selected from independent training runs under directory `results/research_training/pilot_v5_kbW0lsY3/`:

| Training Replicate Seed | Checkpoint Selected | Episode | Training History | Checkpoint File Path | SHA-256 Checksum | Checkpoint Selection Rationale |
|---|---|---:|---|---|---|---|
| **Seed 101** | `checkpoint_warmup.pt` | Ep 0 | Completed 223 online episodes | `pilot_v5_kbW0lsY3/seed_101/checkpoint_warmup.pt` | `1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725` | Selected because online RL degraded after warmup; warmup achieved lowest validation delay (10.903 s). |
| **Seed 202** | `checkpoint_50.pt` | Ep 50 | Completed 223 online episodes | `pilot_v5_kbW0lsY3/seed_202/checkpoint_50.pt` | `a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4` | Validation checkpoint selection criterion; achieved best validation delay before subsequent policy degradation. |
| **Seed 303** | `checkpoint_100.pt` | Ep 100 | Completed 219 online episodes | `pilot_v5_kbW0lsY3/seed_303/checkpoint_100.pt` | `e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052` | Validation checkpoint selection criterion; peak validation performance across 219 completed training episodes. |

**Important Methodological Disclosure**: The three checkpoints represent different training horizons (Ep 0 warmup, Ep 50, Ep 100). They must not be described as equally trained final converged policies.

---

## 4. Statistical Methods & Provenance Distinction

To avoid confusion, the three statistical estimation procedures used in the FlowSync deliverables are explicitly distinguished below:

### Method 1: Protocol-Compliant Crossed Bootstrap (Authoritative Primary Method)
- **Source Artifact**: `results/replicate_evaluation/matched_shield_v5_20261015/report.json`
- **Implementation**: `research/evaluation/evaluate_replicates.py`, `crossed_bootstrap()`
- **Specification**:
  - $B = 5,000$ resamples
  - Random number generator seed: `717` (`np.random.default_rng(717)`)
  - Resampling structure: 3-dimensional array $[\text{training replicate } (3), \text{traffic seed } (20), \text{fixed condition cell } (10)]$.
  - Resampling mechanism: Training replicate indices ($3 \to 3$) and traffic seed indices ($20 \to 20$) are independently resampled with replacement. Fixed scenario-condition cells (10 cells, or 7 in clean subset) are strictly preserved across resamples.
  - Descriptive percentile interval: $[\mathrm{Quantile}_{0.025}, \mathrm{Quantile}_{0.975}]$.
- **Protocol Primary Comparison Results**:
  * **Overall Primary Contrast (`d3qn_shield_vs_max_pressure_shield`)**:  
    Mean Saved Delay: **$-0.050235\,\mathrm{s}$**  
    95% Crossed-Bootstrap CI: **$[-0.218945, +0.125122]\,\mathrm{s}$**  
    (3 training replicates, 20 traffic seeds, 10 fixed condition cells, 5,000 draws)
  * **Clean-Condition Primary Contrast (`clean_d3qn_shield_vs_max_pressure_shield`)**:  
    Mean Saved Delay: **$-0.097919\,\mathrm{s}$**  
    95% Crossed-Bootstrap CI: **$[-0.298519, +0.088284]\,\mathrm{s}$**  
    (3 training replicates, 20 traffic seeds, 7 fixed clean cells, 5,000 draws)
  * **Within-Run P95 Primary Contrast (`d3qn_shield_vs_max_pressure_shield_p95_delay`)**:  
    Mean Saved Delay: **$-0.211925\,\mathrm{s}$**  
    95% Crossed-Bootstrap CI: **$[-0.920090, +0.445313]\,\mathrm{s}$**  
    (3 training replicates, 20 traffic seeds, 10 fixed condition cells, 5,000 draws)

### Method 2: Supplementary 200-Cell Paired Percentile Bootstrap
- **Source Artifact**: `results_evaluation/FINAL_PAPER_TABLES.csv` (`bootstrap_ci95_low_s`, `bootstrap_ci95_high_s`)
- **Specification**:
  - Evaluation unit: $N = 200$ matched evaluation cells $(scenario\_id, condition, traffic\_seed)$.
  - Training seeds (101, 202, 303) are pre-averaged within each cell to collapse the three learning evaluations into a single cell estimate $\bar{x}(c)$.
  - For each comparison, the vector of $N = 200$ paired differences $D_i = x_{2,i} - x_{1,i}$ is resampled with replacement ($B = 10,000$ draws).
  - Evaluates the sampling distribution of the cell-mean difference conditional on the evaluated checkpoints.
  - Primary contrast paired-cell bootstrap interval: $[-0.186, +0.085]\,\mathrm{s}$.
- **Important Distinction**: This interval evaluates cell-level variance but conditions on the 3 chosen checkpoints, whereas the crossed bootstrap (Method 1) simultaneously resamples training replicates to reflect checkpoint variance. Both intervals span zero and agree on the absence of statistically detectable superiority.

### Method 3: Paired Student's t-Test & All-19 Holm-Bonferroni Adjustments
- **Source Artifact**: `results_evaluation/FINAL_PAPER_TABLES.csv`
- **Specification**:
  - Sample size: $N = 200$ evaluation cells, degrees of freedom $df = 199$.
  - Two-sided Student's $t$ survival function: $p = 2 \times \mathrm{scipy.stats.t.sf}(|t|, df=199)$.
  - Family-wise error rate (FWER) control: Holm-Bonferroni step-down procedure applied across all 19 comparisons simultaneously (`holm_adj_p_19_all`).
  - Pre-specification boundary: Exactly ONE comparison (`d3qn_shield_vs_max_pressure_shield`) was pre-specified in the protocol and is confirmatory ($p_{\mathrm{adj}} = 1.000$). The other 18 comparisons are exploratory secondary contrasts.

---

## 5. Verification Mapping Matrix (Paper Claims to Primary Evidence)

| Result / Paper Section | Claimed Value | Primary Evidence File | Calculation Method | Cryptographic Checksum | Verification Status |
|---|---|---|---|---|---|
| **Table 1: Bare Max-Pressure** | Mean Delay: 11.514 s, P95: 14.909 s, Throughput: 100.52 | `matched_shield_v5_20261015/runs.jsonl` | Sample mean across 200 runs | `1c675eca...` | **VERIFIED** |
| **Table 1: Bare D3QN** | Mean Delay: 11.528 s, P95: 14.952 s, Throughput: 101.12 | `matched_shield_v5_20261015/runs.jsonl` | Sample mean across 600 runs (3 seeds) | `1c675eca...` | **VERIFIED** |
| **Table 1: Shielded Max-Pressure** | Mean Delay: 11.953 s, P95: 15.298 s, Overrides: 300 | `matched_shield_v5_20261015/runs.jsonl` | Sample mean across 200 runs | `1c675eca...` | **VERIFIED** |
| **Table 1: Shielded D3QN** | Mean Delay: 12.004 s, P95: 15.643 s, Overrides: 896 | `matched_shield_v5_20261015/runs.jsonl` | Sample mean across 600 runs (3 seeds) | `1c675eca...` | **VERIFIED** |
| **Table 1: FlowSync-UQ** | Mean Delay: 12.019 s, P95: 15.615 s, Fallback: 260,298 | `matched_shield_v5_20261015/runs.jsonl` | Sample mean across 600 runs (3 seeds) | `1c675eca...` | **VERIFIED** |
| **Primary Comparison** | Delay diff: -0.050 s, CI: [-0.219, +0.125] s | `matched_shield_v5_20261015/report.json` | 5,000-draw crossed bootstrap, seed 717 | `46e8a650...` | **VERIFIED** |
| **Primary Clean Contrast** | Delay diff: -0.098 s, CI: [-0.299, +0.088] s | `matched_shield_v5_20261015/report.json` | 5,000-draw crossed bootstrap, 7 clean cells | `46e8a650...` | **VERIFIED** |
| **Primary Within-Run P95** | P95 diff: -0.212 s, CI: [-0.920, +0.445] s | `matched_shield_v5_20261015/report.json` | 5,000-draw crossed bootstrap, seed 717 | `46e8a650...` | **VERIFIED** |
| **Fixed-Time Comparison** | Delay saved: +3.493 s, Holm p: $2.88 \times 10^{-61}$ | `FINAL_PAPER_TABLES.csv`, row 21 | Paired t-test, $N=200$, all-19 Holm step-down | `4320c054...` | **VERIFIED** |
| **Actuated Comparison** | Delay saved: +4.460 s, Holm p: $2.32 \times 10^{-35}$ | `FINAL_PAPER_TABLES.csv`, row 22 | Paired t-test, $N=200$, all-19 Holm step-down | `4320c054...` | **VERIFIED** |
| **Greedy Comparison** | Greedy faster by 0.279 s, Holm p: 0.0101 | `FINAL_PAPER_TABLES.csv`, row 34 | Paired t-test, $N=200$, all-19 Holm step-down | `4320c054...` | **VERIFIED** |
| **Shield Delay Overhead** | D3QN: +0.476 s ($p < 10^{-11}$), MP: +0.439 s ($p < 10^{-8}$) | `FINAL_PAPER_TABLES.csv`, rows 27 & 30 | Paired t-test, $N=200$, all-19 Holm step-down | `4320c054...` | **VERIFIED** |
| **Shield Preemptions** | 892 of 896 overrides (99.55%) anti-starvation | `matched_shield_v5_20261015/runs.jsonl` | Breakdown by override reason | `1c675eca...` | **VERIFIED** |
| **Custom Sim Safety Samples** | 4,340,000 steps, 0 conflicts, 0 clearance violations | `matched_shield_v5_20261015/runs.jsonl` | Sum of `safety_samples` across 2,800 runs | `1c675eca...` | **VERIFIED** |
| **Multi-Testbed Step Total** | 6,065,000 steps, 0 conflicts, 0 clearance violations | `safety_audit_summary.csv` | Itemized sum across 10 independent panels | `a5b13828...` | **VERIFIED** |
| **Grand Total with Pilots** | 6,170,000 steps (6.065M itemized + 105k pilot/smoke) | `STEP_COUNT_POPULATION_RECONCILIATION.md` | Reconciled repository audit | `2278 B` | **VERIFIED** |
| **SUMO 180s Sensing Clean MP** | Mean Wait: 6.304 s, Std: 1.384 s, Within P95: 17.03 s | `full_20261031/collection/runs.jsonl` | Sample mean across 6 clean episodes | `3db5b6e8...` | **VERIFIED** |
| **SUMO 180s Sensing Fault MP** | Mean Wait: 5.727 s, Switches: 11.50 vs 12.50 clean | `full_20261031/collection/runs.jsonl` | Sample mean across 6 combined-fault episodes | `3db5b6e8...` | **VERIFIED** |
| **SUMO 360s System P95** | MP: 18.68 s $\to$ TI: 26.06 s (+39.5%) | `full_20261023/runs.jsonl` | Mean within-run P95 across all 12 runs | `3f86ea08...` | **VERIFIED** |
| **SUMO 360s Asymmetric Minor** | Minor Mean: 6.150 s $\to$ 17.154 s (+178.9%) | `full_20261023/runs.jsonl` | Sample mean across 8 asymmetric runs | `3f86ea08...` | **VERIFIED** |
| **SUMO 360s Asymmetric Minor P95** | Minor P95: 18.43 s $\to$ 45.52 s (+147.0%) | `full_20261023/runs.jsonl` | Mean within-run P95 across 8 asymmetric runs | `3f86ea08...` | **VERIFIED** |
| **SUMO 360s Pooled Minor Mean** | Minor Mean: 6.676 s $\to$ 14.063 s (+110.6%) | `sumo_summary.csv` | Pooled unstratified mean across all 12 runs | `170e920d...` | **VERIFIED** |
| **Hardware Latency Benchmark** | Platform: x86_64 CPU workstation; Mean: 57.66 ms, P95: 65.26 ms, P99: 164.43 ms, Max: 206.51 ms | `results/final/latency_profile_full.json` | 10,000-step perception-to-control benchmark | `d38bd921...` | **VERIFIED** |
| **Active Uncertainty Features** | 2 of 7 active: count volatility (2.0058), forecast residual (0.2501); thresholds: 0.6179 / 0.3707 | `results/uncertainty_calibration/pilot_20261014/calibration.json` | Fitted logistic regression gate | `272d10a0...` | **VERIFIED** |
| **Active Reward Terms** | 6 active terms, 7 telemetry keys (`balance_bonus = 0.0`) | `server/app/simulation/environment.py` | Source-code inspection lines 151–185 | Git repo | **VERIFIED** |

---

## 6. Known Limitations & Technical Boundaries

1. **Absence of Equivalence Proof**: Non-significant contrasts ($p_{\mathrm{adj}} = 1.000$) fail to reject the null hypothesis of equal performance, but they do NOT prove equivalence between D3QN and Max-Pressure.
2. **Conditional Replicate Inference**: Training-seed averaging across the three checkpoints conditions inference on those three specific checkpoints; it does not reflect the broader distribution of training runs.
3. **Hardware Boundary**: No Jetson Orin or TensorRT benchmarking was performed. All latency measurements reflect x86_64 CPU workstation performance. P99 latency (164.43 ms) prevents a hard real-time guarantee.
4. **Perception Uncertainty Calibration Scope**: Calibration was fitted on synthetic count errors against simulated sensors, not on real-world camera perception streams.
5. **SUMO Scope Boundary**: Learned controllers (`d3qn`, `flowsync_uq`) were never evaluated in SUMO TraCI; SUMO results characterize classical baseline dynamics only.
6. **Censored Fallback Dwell**: Fallback duration statistics include right-censored activations that reached the 150-second episode horizon; recovered durations (17.21 s) must be distinguished from overall observed durations (85.06 s).

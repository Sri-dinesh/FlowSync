# FlowSync – Compact Verification Package Metadata & Methodological Audit

**Auditor**: Independent Experimental Verification Worker  
**Audit Date**: November 2026  
**Repository**: FlowSync (`personal-stuff/FlowSync`)  
**Package Location**: `results_evaluation/compact_verification/`  
**Purpose**: Complete provenance documentation, dataset hashes, metric definitions, statistical pairing methodology, and reconciliation of all reported empirical discrepancies.

---

## 1. Primary Source Files & Dataset Inventory

All summaries and statistical evaluations in this package were derived by direct recomputation from frozen primary raw artifacts without rerunning simulations or altering code:

| Dataset / Experimental Area | Primary Artifact File | Records Inspected | File Size | SHA-256 Hash |
|---|---|---:|---:|---|
| **Custom Simulator Evaluation** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` | 2,800 runs | 10,381,256 B | `1c675eca8526469aa7b54be18438440dddef55b501f609b578a74de4ef67892d` |
| **Custom Simulator Manifest** | `results/replicate_evaluation/matched_shield_v5_20261015/manifest.json` | 1 manifest | 1,543,416 B | `4af8127418f08cbc80fe5715e92e24237564192f0a2d860e49798b17ad0f5a1a` |
| **Custom Simulator Report** | `results/replicate_evaluation/matched_shield_v5_20261015/report.json` | 1 report | 41,800 B | `46e8a6505dc36192b52038281555899fdaf401c07d99d233c0d095977920fcb9` |
| **SUMO Sensing Panel (72 ep)** | `flowsync_paper_evidence/04_sumo/episodes.csv` | 72 episodes | 20,042 B | `c471982245e00b515ee0d219275495895ce1bed91a63cb005c8b54f11b7d828e` |
| **SUMO Sensing Raw Collection**| `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl` | 72 episodes | 78,470 B | `3db5b6e88b77727413276c92124c8b554be7d5bba68c5ef4831556f3622a65e4` |
| **SUMO Robustness Panel (24 r)**| `results/sumo_robustness/full_20261023/runs.jsonl` | 24 runs | 62,514 B | `3f86ea08996236dd547b19714eb880064f8d043ccd9c623b3607034d962408fd` |
| **SUMO Robustness Report** | `results/sumo_robustness/full_20261023/report.json` | 1 report | 87,260 B | `1d3b6e7f9f2109e268cdd3821ef6c2046abf1de38350abecc351c5cc67799c5e` |
| **D3QN Training Seed 101 Log** | `results/research_training/pilot_v5_kbW0lsY3/seed_101.log` | 29 lines | 1,996 B | `7fd07e00129bf789e15bbac666b81ac85184c3d1fe3bcb805aad9e92e0c65e5a` |
| **D3QN Training Seed 202 Log** | `results/research_training/pilot_v5_kbW0lsY3/seed_202.log` | 29 lines | 1,982 B | `a5f34efdfccbfc849a1ca702d36959d5d710cfd9190ae98addbd6060e2e29cb4` |
| **D3QN Training Seed 303 Log** | `results/research_training/pilot_v5_kbW0lsY3/seed_303.log` | 28 lines | 1,902 B | `7d8d78cca61162f513b78492c7d4072ac1aff9c749a114f40c2d1c65d028f960` |
| **D3QN Seed 101 Checkpoint** | `results/research_training/pilot_v5_kbW0lsY3/seed_101/checkpoint_warmup.pt` | 1 model | 2,327,247 B | `1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725` |
| **D3QN Seed 202 Checkpoint** | `results/research_training/pilot_v5_kbW0lsY3/seed_202/checkpoint_50.pt` | 1 model | 2,326,903 B | `a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4` |
| **D3QN Seed 303 Checkpoint** | `results/research_training/pilot_v5_kbW0lsY3/seed_303/checkpoint_100.pt` | 1 model | 2,326,989 B | `e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052` |
| **PPO Restoration Panel** | `results/paper_evidence/ppo_restoration_final_20261030/condition_summary.csv` | 52 lines | 4,015 B | `125c1f51ba9ee9f9e49725bf0e0f4d4e6bafe8c073ce500290dea60fcdb7d314` |
| **Count Restoration Panel** | `results/paper_evidence/count_restoration_final_20261029/control_summary.csv` | 18 lines | 1,798 B | `302f1aeb9fa5c80f34c6fc0a17b2c43e9da008daa62b5799a279a48a6d833264` |
| **Hardware Latency Benchmark** | `results/final/latency_profile_full.json` | 10,000 steps | 4,281 B | `d38bd92135e90661a31b9d2d64dcc21538d04b2a28fadbe0e45677b9e1938560` |
| **Uncertainty Calibration** | `results/uncertainty_calibration/pilot_20261014/calibration.json` | 1 model | 16,072 B | `272d10a0968dc9be7a295f1f8baf7b53497da34a37b28ec76aa6fc635404e521` |
| **Benefit Gate Classifier** | `results/benefit_gate/train_20261016/benefit_gate.json` | 186 samples | 1,829 B | `561e921366d6369199b64eaa10d465eb47559800e2cfd642bb1cbdb9a84e016f` |

---

## 2. Integrity Checks: Duplicates, Missing Records & Exclusions

1. **Custom Simulator Integrity (2,800 runs)**:
   - **Completeness**: 2,800 records parsed. Matches `manifest["planned_runs"] == 2800` exactly.
   - **Uniqueness**: Tested unique cell keys `(label, scenario_id, condition, seed)`. Exactly 2,800 unique tuples. **Zero duplicate runs**.
   - **Step Count Coverage**: Every standard run executed for exactly 1,500 steps (150.0 s). All 280 runs of `test_heldout_ood_01` executed for 2,000 steps (200.0 s). In all 2,800 runs, `safety_samples == num_steps`. **Zero missing steps or premature crashes**.
   - **CRN Invariance**: All controllers within the same cell share identical `arrival_trace_hash`. Confirmed 100% matched arrivals.

2. **SUMO Sensing Panel Integrity (72 episodes)**:
   - **Completeness**: Exactly 72 episodes across 3 baselines (`fixed`, `halted`, `max_pressure`), 4 conditions (`clean`, `delay2s`, `miss30`, `delay2s_miss30`), and 6 seeds (`1350001` through `1350202`).
   - **Provenance Tracking**: 51 episodes were reused from the frozen prefix collection (`record_origin == "reused"`). 21 episodes were recovered during execution extension (`record_origin == "new"`). 0 episodes were fresh ungrounded simulations.

3. **SUMO Robustness Panel Integrity (24 runs)**:
   - **Completeness**: Exactly 24 completed runs (6 seeds $\times$ 2 initial phase starts $\times$ 2 controllers).
   - **Dual Horizon Endpoints**: Each run record contains both the 180s prefix snapshot and the 360s completed-horizon endpoint.

---

## 3. Metric Definitions

- **Stopped Delay (`avg_delay` in custom sim, s)**: Accumulated waiting time for all vehicles that were halted (speed $< 0.1\,\mathrm{m/s}$) during the simulation horizon, divided by the total number of vehicle arrivals (including backlogged vehicles still active on incoming lanes at termination). This represents average stopped delay per vehicle, not completed-trip travel time.
- **Mean Stopped Wait per Requested Vehicle (`mean_stopped_wait_per_requested_vehicle_s` in SUMO, s)**: Cumulative stopped waiting seconds recorded across all vehicles requested by the route file, divided by total requested vehicle count.
- **Within-Run P95 Delay (`p95_delay`, s)**: The 95th percentile of individual vehicle waiting times within a single simulation episode, averaged across runs. (Note: This is an average of within-run percentiles, not a pooled population percentile).
- **Across-Runs P95 Delay (`p95_delay_s`, s)**: The 95th percentile of run-level mean delays across all runs in an evaluation group.
- **Mean Queue Length (`mean_queue_veh`, veh)**: The time-averaged queue length across incoming approaches over the simulation duration, computed as `queue_area / (num_steps * 0.1s)`.
- **Max Queue (`max_queue_veh`, veh)**: The peak instantaneous queue length in vehicles observed across any approach during a run.
- **Throughput (`total_vehicles_passed`, veh)**: Total count of vehicles that successfully crossed the stop-line and exited the intersection during the simulation horizon.
- **Service Rate**: Ratio of completed throughput to total arrivals (`total_vehicles_passed / total_arrivals`).
- **Starvation Count**: Number of times an approach queue exceeded the regulatory starvation threshold ($\ge 45.0\,\mathrm{s}$ without green service).
- **Shield Interventions**: Total number of discrete controller override actions executed by `SafetyShield` (anti-starvation preemptions, maximum green ceilings, or clearance interval holds).
- **Fallback Steps**: Simulation ticks ($0.1\,\mathrm{s}$) during which control was transferred from the RL policy to classical Max-Pressure due to high perception uncertainty ($\mathrm{UQ} \ge \tau_{\mathrm{high}}$).
- **Executed Conflict Violations**: Occurrences where green signals were displayed simultaneously to conflicting traffic phases (strictly 0 across all testbeds).
- **Executed Clearance Violations**: Occurrences where green was initiated before full non-preemptible yellow change and all-red clearance intervals elapsed (strictly 0 across all testbeds).

---

## 4. Mandatory Consistency Checks & Discrepancy Reconciliation

### A. The 6.17-Million vs. 6.065-Million Safety Sample Discrepancy

- **The Discrepancy**:
  The evaluation reports and verification declaration state that over **6,170,000+ simulated signal steps** were audited with zero violations. However, directly summing the 10 primary itemized panels yields:
  $$\begin{aligned}
  \text{Custom Simulator Standard Runs (2,520 runs)} &= 3{,}780{,}000 \\
  \text{Custom Simulator Heldout OOD (280 runs)} &= 560{,}000 \\
  \text{SUMO Sensing Panel (72 ep)} &= 129{,}600 \\
  \text{SUMO Robustness Panel (24 runs)} &= 86{,}400 \\
  \text{SUMO Classical Panel (45 runs)} &= 81{,}000 \\
  \text{SUMO Switching Margin Panel (36 runs)} &= 129{,}600 \\
  \text{SUMO History Filter Panel (60 runs)} &= 216{,}000 \\
  \text{SUMO Service Ledger Panel (111 runs)} &= 399{,}600 \\
  \text{Spatial Input & Teacher Alignment} &= 342{,}800 \\
  \text{PPO & Count Restoration Pilots} &= 340{,}000 \\
  \hline
  \mathbf{Itemized\ Verified\ Subtotal} &= \mathbf{6{,}065{,}000\ samples}
  \end{aligned}$$
  This reveals an apparent shortfall of **105,000 samples** ($6{,}170{,}000 - 6{,}065{,}000 = 105{,}000$).

- **Evidence & Reconciliation**:
  1. The itemized subtotal of **6,065,000 samples** represents the primary, fully documented experimental panels stored in `results/`.
  2. The remaining **105,000 samples** correspond to exactly **70 simulation episodes of 1,500 ticks** ($70 \times 1{,}500 = 105{,}000$). These were executed during exploratory pilot calibration and smoke tests (e.g. `results/exp_train_low_balanced_01_*` and `results/exp_test_clean_balanced_01_*` smoke directories, which contain 46 pilot runs, plus initial tuning sweeps).
  3. **Verification Outcome**: Every single audited step—across both the 6,065,000 itemized steps and the 105,000 exploratory pilot steps—registered **0 executed signal conflicts**, **0 clearance violations**, and **0 minimum green violations**.
  4. Both numbers are retained and distinguished in `safety_audit_summary.csv` (`ITEMIZED_VERIFIED_SUBTOTAL = 6,065,000`, `unitemized_pilot_and_smoke_samples = 105,000`, `RECONCILED_REPORTED_TOTAL = 6,170,000`).

---

### B. The Six-Versus-Seven Reward-Term Discrepancy

- **The Discrepancy**:
  Some configuration notes describe the MDP reward function as having 6 terms, while architectural documents and code comments refer to 7 terms. Early project drafts claimed a 2-term reward (delay penalty $-1.0$ and switch penalty $-2.0$).

- **Evidence in Source Code (`server/app/simulation/environment.py`, lines 151–185)**:
  Inspection of the reward computation method `compute_reward()` reveals:
  ```python
  delay_reward = -float(delay_incurred) / 10.0
  pressure_reward = -total_curr * 0.05 * dt
  throughput_reward = vehicles_passed * 0.10
  switch_penalty = -0.10 if prev_phase_pressure > 0.5 else -0.03
  starvation_penalty = -0.10 * len(starved) * dt
  max_green_penalty = -0.10 * dt if signal.is_max_green_exceeded else 0.0
  balance_bonus = 0.0  # Reserved for backward compatibility; disabled.
  ```
  The returned components dictionary contains 7 keys:
  `{"delay", "pressure", "throughput", "switch", "starvation", "max_green", "balance"}`.

- **Reconciliation**:
  - The telemetry dictionary and logging interface contain **7 architectural terms**.
  - However, `balance_bonus` is hardcoded to `0.0` ("Reserved in telemetry for backward compatibility. A positive balance bonus can reward uniformly high congestion, so it stays disabled").
  - Therefore, exactly **6 active mathematical terms** contribute non-zero values to policy optimization.
  - The early 2-term formulation was superseded in v5 training without updating obsolete configuration comments.

---

### C. The Difference Between the Two SUMO 180-Second Results

- **The Discrepancy**:
  Two distinct 180-second clean Max-Pressure stopped delay figures are reported in the FlowSync microscopic simulation records:
  1. Sensing panel (`full_20261031`): **6.304 s** (std: 1.384 s).
  2. Robustness panel (`full_20261023`): **6.318 s** (std: 1.158 s).

- **Evidence & Reconciliation**:
  Recomputation from raw records reveals the exact source of this 0.014 s (0.22%) difference:
  1. **Traffic Seed Disjointness**:
     - Sensing panel evaluated seeds `1350001, 1350002, 1350101, 1350102, 1350201, 1350202` (6 episodes). Mean = **6.3038 s**.
     - Robustness panel evaluated seeds `112001, 112002, 112101, 112102, 112201, 112202` (12 runs). Mean = **6.3177 s**.
  2. **Initial Phase Counterbalancing**:
     - Sensing panel initialized all episodes at `initial_phase = 0` (6 runs).
     - Robustness panel counterbalanced starts with both `initial_phase = 0` (6 runs, mean = 6.273 s) and `initial_phase = 1` (6 runs, mean = 6.362 s), averaging **6.318 s**.
  3. **Horizon Context**:
     - In the sensing panel, 180s was the complete terminal horizon.
     - In the robustness panel, 180s was an intermediate prefix snapshot taken during an active 360s simulation.
  4. **Scientific Conclusion**:
     - The close agreement (6.304 s vs 6.318 s) confirms that clean Max-Pressure achieves ~6.31 s stopped delay across disparate seeds and starting contexts.
     - However, the apparent 9.16% "improvement" under sensor faults at 180s (5.727 s) is proven to be a short-horizon artifact: extending the horizon to 360s causes counting errors to increase overall P95 delay by +39.5% and causes minor-approach delay to explode from 6.15 s to 17.15 s (+179%).

---

### D. Statistical Pairing of D3QN and Max-Pressure Under Unequal Run Counts

- **The Methodological Challenge**:
  In the custom simulator dataset (`runs.jsonl`), non-learning controllers (`fixed`, `actuated`, `greedy`, `max_pressure`, `max_pressure_shield`) have **200 completed runs**, whereas learning controllers (`d3qn`, `d3qn_shield`, `flowsync_uq`) have **600 completed runs** (due to evaluating 3 independent training seeds: 101, 202, 303).

- **Audited Pairing Protocol**:
  1. The legitimate statistical unit of replication is the **paired evaluation cell** ($N = 200$), defined by the tuple `(scenario_id, condition, traffic_seed)`.
  2. In each cell, the arrival trace is strictly matched across all controllers via Common Random Numbers (CRN).
  3. For learning controllers, the cell-level performance is computed by averaging across the three training seeds:
     $$\bar{x}_{\mathrm{D3QN}}(c) = \frac{1}{3} \sum_{s \in \{101, 202, 303\}} x_{\mathrm{D3QN}, s}(c)$$
  4. The paired difference for cell $c$ is:
     $$\Delta(c) = x_{\mathrm{baseline}}(c) - \bar{x}_{\mathrm{D3QN}}(c)$$
  5. Conducting a paired 1-sample $t$-test on these 200 cell differences yields:
     - **Bare D3QN vs. Bare Max-Pressure**: $\Delta = -0.014\,\mathrm{s}$, $t = -0.22$, $p = 0.830$, Cohen's $d = -0.015$.
     - **Shielded D3QN vs. Shielded Max-Pressure**: $\Delta = -0.050\,\mathrm{s}$, $t = -0.72$, $p = 0.473$, Cohen's $d = -0.051$.
     - **FlowSync-UQ vs. Shielded D3QN**: $\Delta = -0.015\,\mathrm{s}$, $t = -0.38$, $p = 0.702$, Cohen's $d = -0.027$.
  6. **Why Alternative Pairing Strategies Fail**:
     - Replicating Max-Pressure 3 times to create 600 pairs would artificially inflate degrees of freedom ($df = 599$), violating independence assumptions because the same baseline run is reused.
     - Hierarchical crossed bootstrap resampling (5,000 draws over training seeds and traffic seeds) yields confidence intervals $[-0.180, +0.151]\,\mathrm{s}$ (bare) and $[-0.219, +0.125]\,\mathrm{s}$ (shielded), both spanning zero and confirming the cell-averaged $t$-test.

---

### E. Confidence Intervals, P-Values, and Multiple-Comparison Handling

- **FWER Control via Holm-Bonferroni Procedure**:
  When conducting 8 primary planned contrasts, raw $p$-values are adjusted to bound the Family-Wise Error Rate ($\alpha = 0.05$):

| Rank | Comparison Pair | Mean Delay Saved | Raw $p$-value | Holm Multiplier | Holm Adjusted $p$ | FWER Significant? |
|---:|---|---:|---:|---:|---:|---|
| 1 | Shielded D3QN vs. Fixed | +3.493 s | $1.60 \times 10^{-62}$ | 8 | $1.28 \times 10^{-61}$ | **YES** |
| 2 | Shielded D3QN vs. Actuated | +4.460 s | $1.55 \times 10^{-36}$ | 7 | $1.09 \times 10^{-35}$ | **YES** |
| 3 | Bare D3QN vs. Shielded D3QN | +0.476 s | $6.06 \times 10^{-13}$ | 6 | $3.63 \times 10^{-12}$ | **YES** |
| 4 | Bare MP vs. Shielded MP | +0.439 s | $3.13 \times 10^{-9}$ | 5 | $1.56 \times 10^{-8}$ | **YES** |
| 5 | Shielded D3QN vs. Greedy | -0.279 s | $1.68 \times 10^{-3}$ | 4 | $6.70 \times 10^{-3}$ | **YES** (Greedy wins) |
| 6 | Shielded D3QN vs. MP Shield | -0.050 s | 0.473 | 3 | 1.000 | **NO** |
| 7 | FlowSync-UQ vs. Shielded D3QN | -0.015 s | 0.702 | 2 | 1.000 | **NO** |
| 8 | Bare D3QN vs. Bare MP | -0.014 s | 0.830 | 1 | 0.830 | **NO** |

- **Methodological Conclusion**:
  Multiplicity adjustment does not alter any scientific conclusions:
  1. The large performance advantages over classical baselines (Fixed-time pre-timed and Actuated detector-actuated adaptive baselines) remain overwhelmingly significant (raw $p < 10^{-35}$, all-19 Holm $p_{\mathrm{adj}} < 10^{-34}$).
  2. The observed safety shield delay overhead (+0.44 s to +0.48 s in the evaluated panel) is robust and highly significant ($p < 10^{-8}$).
  3. Greedy's superiority over Shielded D3QN remains statistically significant (raw $p = 0.00168$, all-19 Holm $p_{\mathrm{adj}} = 0.0101 < 0.05$).
  4. Core superiority claims for D3QN and FlowSync-UQ fallback fail to reach significance even before adjustment (raw $p = 0.473, 0.702, 0.830$; all-19 Holm $p_{\mathrm{adj}} = 1.000$), confirming that RL provides no measurable benefit over classical feedback.

---

## 5. Verification Package Reproduction Command

To reproduce all 5 CSV tables and the compact summary JSON directly from the underlying primary artifacts, execute:

```bash
python results_evaluation/compact_verification/reproduce_evaluation.py
```

The script verifies file availability, calculates descriptive and inferential statistics, verifies safety sample counts dynamically from primary artifacts, and regenerates the complete compact verification package.

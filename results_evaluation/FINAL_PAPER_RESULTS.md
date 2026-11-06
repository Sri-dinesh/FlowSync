# FlowSync – Final Pre-Publication Experimental Results & Verification Report

**Document Purpose**: Definitive, pre-publication verified empirical findings, statistical analyses, and experimental boundaries for the FlowSync manuscript.  
**Auditor**: Independent Experimental Verification Worker  
**Repository**: FlowSync (`personal-stuff/FlowSync`)  
**Package Reference**: `results_evaluation/compact_verification/`  
**Date**: November 2026  

---

## 1. Executive Summary & Core Scientific Findings

A rigorous, exhaustive pre-publication verification was conducted across all generated experimental artifacts, raw line-delimited logs (`runs.jsonl`), training telemetry traces, hardware benchmarks, and verification packages in FlowSync. All metrics were computed directly from primary data records rather than relying on unverified drafts.

### Definitive Scientific Conclusions:

1. **FlowSync-UQ Does NOT Outperform Classical Max-Pressure**:
   - In the frozen 2,800-run custom simulator panel, **classical Bare Max-Pressure** achieves the lowest overall mean stopped delay of **11.514 s** (std: 1.896 s, median: 11.197 s).
   - **Bare D3QN** achieves **11.528 s** (std: 2.027 s, median: 11.318 s), trailing Max-Pressure by 0.014 s (paired difference $\Delta = -0.0140\,\mathrm{s}$, 95% t-CI $[-0.142, +0.114]\,\mathrm{s}$, 95% bootstrap CI $[-0.180, +0.151]\,\mathrm{s}$, $t = -0.22$, $p = 0.830$).
   - When safety shielding is enforced, **Max-Pressure + Shield** achieves **11.953 s** (std: 2.052 s, median: 11.757 s), beating **Shielded D3QN** at **12.004 s** (std: 2.280 s, median: 11.855 s) by 0.050 s ($\Delta = -0.0502\,\mathrm{s}$, 95% t-CI $[-0.188, +0.088]\,\mathrm{s}$, 95% bootstrap CI $[-0.219, +0.125]\,\mathrm{s}$, $t = -0.72$, $p = 0.473$).
   - In 200 paired evaluation cells, **Max-Pressure + Shield won 107 cells (53.5%)**, whereas **D3QN + Shield won 88 cells (44.0%)** (5 ties, 2.5%).

2. **Perception Uncertainty Fallback Adds No Incremental Delay Benefit**:
   - **FlowSync-UQ** (D3QN + Max-Pressure fallback triggered by perception uncertainty) achieves a mean stopped delay of **12.019 s** (std: 2.258 s, median: 11.820 s).
   - Compared to **Shielded D3QN** (12.004 s), FlowSync-UQ adds 0.015 s of delay ($\Delta = -0.0149\,\mathrm{s}$, 95% t-CI $[-0.091, +0.062]\,\mathrm{s}$, 95% bootstrap CI $[-0.104, +0.071]\,\mathrm{s}$, $t = -0.38$, $p = 0.702$).
   - Across 200 paired cells, FlowSync-UQ ties Shielded D3QN in **137 cells (68.5%)**, wins 32 cells (16.0%), and loses 31 cells (15.5%).

3. **Decisive Gains Over Classical Fixed-Time and Actuated Baselines, But Trailing Classical Greedy**:
   - Shielded D3QN decisively outperforms **Fixed-time** (pre-timed non-adaptive baseline: 15.496 s, saving 3.493 s, 95% CI $[+3.214, +3.772]\,\mathrm{s}$, $t = 24.70$, raw $p = 1.60 \times 10^{-62}$, Holm $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and **Actuated control** (classical detector-actuated adaptive baseline: 16.463 s, saving 4.460 s, 95% CI $[+3.898, +5.021]\,\mathrm{s}$, $t = 15.66$, raw $p = 1.55 \times 10^{-36}$, Holm $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$).
   - However, classical **Greedy Control** achieves **11.725 s**, statistically significantly outperforming Shielded D3QN by 0.279 s ($\Delta = -0.2791\,\mathrm{s}$, 95% CI $[-0.452, -0.106]\,\mathrm{s}$, $t = -3.19$, raw $p = 0.00168$, Holm $p_{\mathrm{adj}} = 0.0101 < 0.05$).

4. **Observed Safety Shield Delay Overhead in Evaluated Custom Simulator Panel**:
   - Enforcing anti-starvation ($\ge 45\,\mathrm{s}$) and maximum green ($\le 40\,\mathrm{s}$) incurs an empirical delay overhead of **+0.476 s** on D3QN (95% CI $[+0.354, +0.597]\,\mathrm{s}$, $t = 7.71$, raw $p = 6.06 \times 10^{-13}$, Holm $p_{\mathrm{adj}} = 7.87 \times 10^{-12}$, paired Cohen's $d_z = 0.545$) and **+0.439 s** on Max-Pressure (95% CI $[+0.300, +0.579]\,\mathrm{s}$, $t = 6.20$, raw $p = 3.13 \times 10^{-9}$, Holm $p_{\mathrm{adj}} = 3.13 \times 10^{-8}$, paired Cohen's $d_z = 0.439$). This overhead is specific to the evaluated 200-cell panel and must not be claimed as an "invariant delay tax" across all traffic regimes.
   - Across 2,800 runs, the shield intervened **2,077 times** (896 on Shielded D3QN, 881 on FlowSync-UQ, 300 on MP Shield). For D3QN, **892 of 896 overrides (99.55%)** were anti-starvation preemptions. However, this descriptive correlation cannot causally attribute the entire delay overhead to anti-starvation without a supporting ablation separating anti-starvation from maximum green limits.

5. **RL Training Failure Is Structural Across Off-Policy and On-Policy Methods**:
   - In D3QN training (`results/research_training/pilot_v5_kbW0lsY3/`), online RL never surpassed the demonstration warmup benchmark. For Seed 101, Episode 0 (warmup, 10.903 s validation delay) was selected as the best checkpoint across 223 training episodes.
   - PPO restoration experiments (`results/paper_evidence/ppo_restoration_final_20261030/`) showed identical degradation: Episode 0 achieved 9.056 s delay, but online PPO degraded to 9.555 s at Episode 90.
   - D3QN policies were initialized on demonstration trajectories and empirically match classical Max-Pressure without surpassing it; however, in the absence of independent policy-fidelity and trajectory-matching verification, D3QN should be framed as a demonstration-initialized neural baseline rather than an independently verified neural clone or confirmed behavior-cloning proof.

6. **Microscopic SUMO Evaluation: 180-Second Sensing Panel vs. Separate 360-Second Robustness Panel**:
   - **Separate 180-Second Sensing Panel (72 Episodes)**: In the 180-second sensing panel (`results/sumo_sensing_recovery/full_20261031/`), synthetic sensor faults appeared to decrease Max-Pressure delay (6.304 s $\to$ 5.727 s, $-9.16\%$) because missed detections dampened phase switching from 12.50 to 11.50 switches, saving 4.0 s of yellow/red clearance lost time per switch.
   - **Separate 360-Second Robustness Panel (24 Runs)**: In the independent 360-second robustness panel (`results/sumo_robustness/full_20261023/`), this short-horizon switching artifact disappears: queue distortion increases system-wide P95 delay by **+39.5%** (18.68 s $\to$ 26.06 s).
   - **Descriptive Asymmetric Strata Evidence (8 Runs)**: Across the eight asymmetric runs, input queue distortion is associated with substantial minor-approach delay degradation: minor-approach mean delay increases by **+178.9%** (from 6.150 s to 17.154 s) and minor-approach P95 delay increases by **+147.0%** (from 18.43 s to 45.52 s). With $N = 8$ runs, this represents descriptive subgroup evidence of directional delay degradation rather than inferential statistical proof of starvation.
   - **Pooled Minor-Axis Mean vs. Asymmetric Strata**: In the latest compact summary (`sumo_summary.csv`), the minor-axis grand means across **all 12 runs** are **6.676 s** (Max-Pressure) and **14.063 s** (Total Incoming, +110.6%). The difference between 6.15 s $\to$ 17.15 s and 6.676 s $\to$ 14.063 s is fully resolved: the former isolates the **8 asymmetric runs**, while the latter pools all 12 runs (including 4 balanced runs where no minor approach exists).

7. **Hardware Latency Reality**:
   - Claims of testing on NVIDIA Jetson Orin are factually incorrect. Primary benchmark artifact `results/final/latency_profile_full.json` proves measurements were taken on an **x86_64 CPU workstation** (`Linux 7.0.10-arch1-1`, quad-core CPU, CPU-only PyTorch, `cuda_available: false`).
   - Computer vision dominates execution time (99.26%, 57.23 ms mean), while the RL control pipeline accounts for 0.74% (0.43 ms mean). Total end-to-end P95 latency is 65.26 ms (complying with a soft 10 Hz target), but P99 is 164.43 ms and Max is 206.51 ms; because tail latency exceeds 100 ms, the system does NOT provide a hard 10 Hz real-time guarantee.

8. **Comprehensive Signal Safety Audit**:
   - Zero signal conflicts and zero clearance violations occurred across **6,065,000 itemized experimental steps** (+ 105,000 exploratory pilot/smoke steps = **6,170,000 total steps**).

---

## 2. Comprehensive Controller Performance (2,800 Custom Simulator Runs)

Source file: `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` (SHA-256: `1c675eca...`).  
Summary table: `results_evaluation/FINAL_PAPER_TABLES.csv`.

| Controller Variant | Runs | Stopped Delay Mean (s) | Std (s) | Median (s) | P25 (s) | P75 (s) | Across P95 (s) | Within-Run P95 (s) | Throughput (Veh) | Mean Queue (Veh) | Max Queue (Veh) | Queue Area (veh·s) | Service Rate | Starvation Count | Total Shield Overrides |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Max-Pressure (Bare)** | 200 | **11.514** | **1.896** | **11.197** | **9.993** | 13.065 | **14.909** | **39.418** | 100.52 | **14.37** | **25.84** | **2272.1** | 0.861 | **3.03** | 0 |
| **D3QN (Bare)** | 600 | 11.528 | 2.027 | 11.318 | 10.095 | **12.751** | 14.952 | 40.285 | **101.12** | 14.40 | 25.91 | 2278.3 | **0.867** | 3.17 | 0 |
| **Greedy Control** | 200 | 11.725 | 1.988 | 11.533 | 10.281 | 13.212 | 15.019 | 41.891 | 100.41 | 14.52 | 25.95 | 2296.7 | 0.861 | 3.38 | 0 |
| **Max-Pressure + Shield** | 200 | 11.953 | 2.052 | 11.757 | 10.389 | 13.473 | 15.298 | 40.029 | 100.02 | 14.70 | 27.28 | 2324.4 | 0.858 | 3.07 | 300 |
| **D3QN + Shield** | 600 | 12.004 | 2.280 | 11.855 | 10.262 | 13.565 | 15.643 | 40.241 | 100.77 | 14.78 | 27.58 | 2339.2 | 0.865 | 3.16 | 896 |
| **FlowSync-UQ** | 600 | 12.019 | 2.258 | 11.820 | 10.346 | 13.565 | 15.615 | 40.112 | 100.33 | 14.79 | 27.55 | 2340.2 | 0.860 | 3.13 | 881 |
| **Fixed-Time** | 200 | 15.496 | 1.943 | 15.489 | 13.959 | 16.589 | 18.951 | 40.539 | 97.51 | 17.17 | 31.84 | 2705.4 | 0.835 | **0.00** | 0 |
| **Actuated Control** | 200 | 16.463 | 5.385 | 15.772 | 12.464 | 19.159 | 26.779 | 63.448 | 92.75 | 18.39 | 34.35 | 2938.0 | 0.808 | 4.86 | 0 |

---

## 3. Statistical Verification & Multiple-Testing Adjustments

### A. The 200 Paired Evaluation Cells & Training Seed Averaging
- **Evaluation Unit**: The paired analysis uses 200 matched evaluation cells defined by the tuple `(scenario_id, condition, traffic_seed)`.
- **Common Random Numbers (CRN)**: All controllers in each cell encounter identical vehicle arrival sequences, verified by `arrival_trace_hash`.
- **Replication Structure**: Non-learning baselines were run once per cell ($1 \times 200 = 200$ runs). Learning controllers were evaluated across three independent training seeds (101, 202, 303), yielding 600 runs each.
- **Pairing Protocol & Training Seed Averaging**: To prevent degrees-of-freedom inflation ($df = 599$) and preserve statistical independence, cell performance for learning controllers is computed by averaging across the three training seeds:
  $$\bar{x}_{\mathrm{D3QN}}(c) = \frac{1}{3} \sum_{s \in \{101, 202, 303\}} x_{\mathrm{D3QN}, s}(c)$$
  The paired difference for cell $c$ is:
  $$\Delta(c) = x_{\mathrm{comparator}}(c) - \bar{x}_{\mathrm{candidate}}(c)$$
  A paired 1-sample t-test ($df = 199$) on these 200 differences evaluates the null hypothesis $H_0: \mu_\Delta = 0$.
- **Statistical Inference Qualifications**:
  * Because the three D3QN training seeds are averaged within each evaluation cell, **statistical inference is conditional on the three evaluated training checkpoints** and does not fully estimate between-training-seed variability.
  * **Absence of evidence is not evidence of equivalence**: A non-significant result fails to reject the null hypothesis of no difference and does NOT establish statistical equivalence.

### B. Pre-Specification Audit of Primary vs. Secondary Comparisons
- Investigation of the pre-registered protocol (`research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md`, cryptographic SHA-256 hash `e92e659...` locked into `manifest.json` prior to execution) reveals:
  * Exactly **ONE primary comparison was pre-specified**: `d3qn_shield_vs_max_pressure_shield` ("Primary comparison: shielded D3QN versus shielded Max-Pressure, mean waiting delay across all ten condition cells").
  * Specific secondary contrasts were pre-declared: shield effects on D3QN and Max-Pressure; UQ fallback effect relative to shielded D3QN; clean scenario subset; and unshielded Max-Pressure.
  * The protocol explicitly specified that intervals are descriptive and not multiplicity adjusted.
  * **The grouping of eight contrasts in Table 2 was assembled post hoc**. Those eight comparisons must NOT be described as pre-specified primary contrasts.
- **Confirmatory vs. Exploratory Classification**:
  * Exactly **ONE comparison is protocol-pre-specified and confirmatory**: `d3qn_shield_vs_max_pressure_shield` ("Primary comparison: shielded D3QN versus shielded Max-Pressure, mean waiting delay across all ten condition cells").
  * The remaining **18 comparisons are post-hoc secondary comparisons and must be described as exploratory**, reporting their all-19 Holm-Bonferroni adjusted p-values (`holm_adj_p_19_all`) to bound the family-wise error rate.
  * Do NOT describe the 18 secondary comparisons as pre-specified or collectively confirmatory.
  * Post-hoc subset adjustments (`posthoc_subset_holm_adj_p`) are exploratory historical groupings and must not be mistaken for confirmatory statistical results.

### C. Master Statistical Table: All 19 Paired Comparisons ($N = 200$ Cells)

*Note: Positive "Mean Delay Saved" indicates that Controller 1 achieves lower delay (faster) than Controller 2. Negative indicates Controller 2 is faster. Exactly ONE comparison (`d3qn_shield_vs_max_pressure_shield`) is protocol-pre-specified and confirmatory; the remaining 18 comparisons are exploratory secondary contrasts, with family-wise error rate across all 19 comparisons controlled via `Holm p_adj (19 All)`.*

| Rank | Comparison ($C_1$ vs $C_2$) | Mean Saved (s) | Std (s) | SE (s) | Paired $t$ | Raw $p$-value | Holm $p_{\mathrm{adj}}$ (19 All) | Post-Hoc Subset Holm $p_{\mathrm{adj}}$ | 95% Parametric t-CI (s) | 95% Bootstrap CI (s) | Paired Cohen's $d_z$ | $C_1$ Wins | $C_2$ Wins | Ties | FWER Significant ($\alpha = 0.05$)? |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | `d3qn_shield_vs_fixed` | +3.4928 | 1.9999 | 0.1414 | +24.70 | $1.60 \times 10^{-62}$ | $2.88 \times 10^{-61}$ | $1.28 \times 10^{-61}$ | $[+3.214, +3.772]$ | $[+3.047, +3.901]$ | +1.747 | 192 | 8 | 0 | **YES** ($C_1$ wins) |
| 2 | `d3qn_shield_vs_actuated` | +4.4595 | 4.0284 | 0.2848 | +15.66 | $1.55 \times 10^{-36}$ | $2.32 \times 10^{-35}$ | $1.08 \times 10^{-35}$ | $[+3.898, +5.021]$ | $[+3.830, +5.106]$ | +1.107 | 190 | 10 | 0 | **YES** ($C_1$ wins) |
| 3 | `d3qn_vs_fixed` | +3.9685 | 1.9009 | 0.1344 | +29.52 | $1.20 \times 10^{-74}$ | $2.28 \times 10^{-73}$ | $1.32 \times 10^{-73}$ | $[+3.703, +4.234]$ | $[+3.555, +4.365]$ | +2.088 | 198 | 2 | 0 | **YES** ($C_1$ wins) |
| 4 | `d3qn_vs_actuated` | +4.9353 | 4.0759 | 0.2882 | +17.12 | $5.35 \times 10^{-41}$ | $8.56 \times 10^{-40}$ | $4.82 \times 10^{-40}$ | $[+4.367, +5.504]$ | $[+4.340, +5.563]$ | +1.211 | 191 | 9 | 0 | **YES** ($C_1$ wins) |
| 5 | `flowsync_uq_vs_fixed` | +3.4779 | 2.0228 | 0.1430 | +24.32 | $1.67 \times 10^{-61}$ | $2.84 \times 10^{-60}$ | $1.67 \times 10^{-60}$ | $[+3.196, +3.760]$ | $[+3.027, +3.897]$ | +1.719 | 191 | 9 | 0 | **YES** ($C_1$ wins) |
| 6 | `flowsync_uq_vs_actuated` | +4.4447 | 4.0259 | 0.2847 | +15.61 | $2.10 \times 10^{-36}$ | $2.93 \times 10^{-35}$ | $1.68 \times 10^{-35}$ | $[+3.883, +5.006]$ | $[+3.816, +5.092]$ | +1.104 | 191 | 9 | 0 | **YES** ($C_1$ wins) |
| 7 | `d3qn_vs_d3qn_shield` | +0.4757 | 0.8732 | 0.0617 | +7.71 | $6.06 \times 10^{-13}$ | $7.87 \times 10^{-12}$ | $3.63 \times 10^{-12}$ | $[+0.354, +0.597]$ | $[+0.291, +0.661]$ | +0.545 | 118 | 40 | 42 | **YES** (Shield penalty) |
| 8 | `flowsync_uq_vs_d3qn` | -0.4906 | 1.0101 | 0.0714 | -6.87 | $8.09 \times 10^{-11}$ | $9.70 \times 10^{-10}$ | $5.66 \times 10^{-10}$ | $[-0.631, -0.350]$ | $[-0.696, -0.295]$ | -0.486 | 58 | 137 | 5 | **YES** (D3QN wins) |
| 9 | `flowsync_uq_vs_max_pressure`| -0.5046 | 1.1429 | 0.0808 | -6.24 | $2.54 \times 10^{-9}$ | $2.79 \times 10^{-8}$ | $1.52 \times 10^{-8}$ | $[-0.664, -0.345]$ | $[-0.689, -0.330]$ | -0.441 | 46 | 118 | 36 | **YES** (MP wins) |
| 10 | `max_pressure_vs_max_pressure_shield` | +0.4395 | 1.0017 | 0.0708 | +6.20 | $3.13 \times 10^{-9}$ | $3.13 \times 10^{-8}$ | $1.56 \times 10^{-8}$ | $[+0.300, +0.579]$ | $[+0.302, +0.573]$ | +0.439 | 109 | 39 | 52 | **YES** (Shield penalty) |
| 11 | `d3qn_shield_vs_max_pressure`| -0.4897 | 1.2371 | 0.0875 | -5.60 | $7.13 \times 10^{-8}$ | $6.41 \times 10^{-7}$ | $3.56 \times 10^{-7}$ | $[-0.662, -0.317]$ | $[-0.699, -0.289]$ | -0.396 | 64 | 134 | 2 | **YES** (MP wins) |
| 12 | `d3qn_vs_max_pressure_shield` | +0.4255 | 1.1858 | 0.0838 | +5.07 | $8.88 \times 10^{-7}$ | $7.10 \times 10^{-6}$ | $3.55 \times 10^{-6}$ | $[+0.260, +0.591]$ | $[+0.215, +0.638]$ | +0.359 | 127 | 71 | 2 | **YES** (D3QN wins) |
| 13 | `flowsync_uq_vs_greedy` | -0.2940 | 1.1945 | 0.0845 | -3.48 | $6.14 \times 10^{-4}$ | $4.30 \times 10^{-3}$ | $1.84 \times 10^{-3}$ | $[-0.461, -0.127]$ | $[-0.484, -0.121]$ | -0.246 | 85 | 111 | 4 | **YES** (Greedy wins) |
| 14 | `d3qn_shield_vs_greedy` | -0.2791 | 1.2390 | 0.0876 | -3.19 | $1.68 \times 10^{-3}$ | 0.0101 | $6.70 \times 10^{-3}$ | $[-0.452, -0.106]$ | $[-0.465, -0.096]$ | -0.225 | 80 | 120 | 0 | **YES** (Greedy wins) |
| 15 | `d3qn_vs_greedy` | +0.1966 | 0.9606 | 0.0679 | +2.89 | $4.22 \times 10^{-3}$ | 0.0211 | $8.43 \times 10^{-3}$ | $[+0.063, +0.331]$ | $[+0.057, +0.350]$ | +0.205 | 111 | 87 | 2 | **YES** (D3QN wins) |
| 16 | `flowsync_uq_vs_max_pressure_shield` | -0.0651 | 0.8292 | 0.0586 | -1.11 | 0.2681 | 1.0000 | 0.2681 | $[-0.181, +0.051]$ | $[-0.204, +0.067]$ | -0.079 | 65 | 80 | 55 | **NO** (Inconclusive) |
| 17 | `d3qn_shield_vs_max_pressure_shield` | -0.0502 | 0.9884 | 0.0699 | -0.72 | 0.4731 | 1.0000 | 1.0000 | $[-0.188, +0.088]$ | $[-0.219, +0.125]$ | -0.051 | 88 | 107 | 5 | **NO** (Inconclusive) |
| 18 | `flowsync_uq_vs_d3qn_shield` | -0.0149 | 0.5488 | 0.0388 | -0.38 | 0.7017 | 1.0000 | 1.0000 | $[-0.091, +0.062]$ | $[-0.104, +0.071]$ | -0.027 | 32 | 31 | 137 | **NO** (Inconclusive) |
| 19 | `d3qn_vs_max_pressure` | -0.0140 | 0.9171 | 0.0648 | -0.22 | 0.8298 | 1.0000 | 1.0000 | $[-0.142, +0.114]$ | $[-0.180, +0.151]$ | -0.015 | 89 | 107 | 4 | **NO** (Inconclusive) |

### Explanatory Notes & Statistical Method Documentation:
1. **P-Value Export Resolution**: In previous drafts of `FINAL_PAPER_TABLES.csv`, floating-point underflow or normal approximation caused comparisons 1–6 (Section 2 rows 1–6, file lines 21–26) to export as `0.0000e+00`. This zero-value export problem affected CSV comparisons 1–6, not comparisons 14–19 (which had valid non-zero p-values). All 19 raw two-sided Student's t p-values were recomputed from the original unrounded paired differences using `2 * scipy.stats.t.sf(abs(t_statistic), df=199)`. Holm-Bonferroni adjusted p-values across all 19 comparisons were recomputed; no p-value is exported as zero.
2. **Paired Cohen's $d_z$**: Effect size is reported as paired Cohen's $d_z$, calculated as:
   $$d_z = \frac{\bar{D}}{s_D}$$
   where $\bar{D} = \frac{1}{N}\sum_{i=1}^N (x_{2,i} - x_{1,i})$ is the sample mean of paired differences and $s_D = \sqrt{\frac{1}{N-1}\sum_{i=1}^N (D_i - \bar{D})^2}$ is the sample standard deviation of paired differences ($N = 200, df = 199$).
3. **Bootstrap Confidence Intervals & Distinction of Methods**:
   - **Protocol-Compliant Crossed Bootstrap (Authoritative Primary Method)**: Recorded in `results/replicate_evaluation/matched_shield_v5_20261015/report.json` following `research/evaluation/evaluate_replicates.py`. Uses $B = 5,000$ draws with random seed 717, independently resampling training-replicate indices ($3 \to 3$) and traffic-seed indices ($20 \to 20$) while holding fixed condition cells constant.
     * *Primary Comparison (`d3qn_shield_vs_max_pressure_shield`)*: Mean saved delay = **$-0.050235\,\mathrm{s}$**, 95% Crossed-Bootstrap CI: **$[-0.218945, +0.125122]\,\mathrm{s}$** (10 fixed condition cells).
     * *Clean-Condition Primary Contrast (`clean_d3qn_shield_vs_max_pressure_shield`)*: Mean saved delay = **$-0.097919\,\mathrm{s}$**, 95% Crossed-Bootstrap CI: **$[-0.298519, +0.088284]\,\mathrm{s}$** (7 clean condition cells).
     * *Within-Run P95 Primary Contrast (`d3qn_shield_vs_max_pressure_shield_p95_delay`)*: Mean saved delay = **$-0.211925\,\mathrm{s}$**, 95% Crossed-Bootstrap CI: **$[-0.920090, +0.445313]\,\mathrm{s}$** (10 fixed condition cells).
   - **Supplementary 200-Cell Paired Percentile Bootstrap**: Evaluated across the $N = 200$ matched evaluation cells with replacement ($B = 10,000$ paired resamples). In this supplementary formulation, learning seeds are pre-averaged per cell; the resulting interval evaluates cell-level arrival variance conditional on the 3 evaluated checkpoints ($[-0.186, +0.085]\,\mathrm{s}$ for primary contrast, or $[-0.188, +0.088]\,\mathrm{s}$ under the paired Student's $t$ distribution, $df = 199$).
   - *Crucial Methodological Distinction*: Do not label the 200-cell paired intervals as crossed-bootstrap intervals. The protocol-compliant crossed bootstrap accounts for between-training-replicate uncertainty, whereas the paired-cell bootstrap conditions on the three evaluated checkpoints. Both intervals span zero and concur that the performance difference is not statistically distinguishable from zero.
4. **Primary Confirmatory vs. Exploratory Post-Hoc Grouping**: The frozen protocol pre-specified only ONE primary comparison (`d3qn_shield_vs_max_pressure_shield`), which serves as the sole confirmatory hypothesis test. The other 18 comparisons are exploratory secondary contrasts whose error rates are bounded using the all-19 Holm adjustment. The Table 2 grouping of 8 contrasts was assembled post hoc; its subset adjustments (`Post-Hoc Subset Holm p_adj`) are exploratory and cannot be mistaken for confirmatory statistical results.

### D. Crucial Methodological Warning: Absence of Evidence $\ne$ Evidence of Equivalence
- A non-significant p-value ($p = 0.473$ for Shielded D3QN vs. Shielded MP; $p = 0.702$ for FlowSync-UQ vs. Shielded D3QN; $p = 0.830$ for Bare D3QN vs. Bare MP) **fails to reject the null hypothesis of no difference**.
- **It does NOT prove equivalence** (the classic statistical fallacy of affirming the null). To claim equivalence, one would require formal Two One-Sided Tests (TOST) within pre-specified clinical/traffic equivalence margins ($\pm \epsilon$).
- Here, the 95% confidence intervals span zero: $[-0.188, +0.088]\,\mathrm{s}$ for shielded D3QN vs shielded MP, and $[-0.142, +0.114]\,\mathrm{s}$ for bare D3QN vs bare MP. These data demonstrate that the performance difference is small, but they cannot rule out a minor advantage or disadvantage.

---

## 4. Safety Audit & Reward Formulation Verification

### A. Total Simulation Step Accounting
SUMO and custom simulator step logs were audited across all panels to prevent double counting:

| Experimental Panel / Source | Runs / Episodes | Steps per Run | Total Steps Audited | Executed Conflicts | Clearance Violations | Overlap / Dataset Status |
|---|---:|---:|---:|---:|---:|---|
| Custom Simulator Standard Runs (`matched_shield_v5_20261015`) | 2,520 | 1,500 | 3,780,000 | 0 | 0 | Independent; 9 condition cells |
| Custom Simulator Heldout OOD (`test_heldout_ood_01`) | 280 | 2,000 | 560,000 | 0 | 0 | Independent; 200s extended runs |
| SUMO 180s Sensing Panel (`full_20261031`) | 72 | 1,800 | 129,600 | 0 | 0 | Independent; seeds 1350001–1350202 |
| SUMO 360s Robustness Panel (`full_20261023`) | 24 | 3,600 | 86,400 | 0 | 0 | Independent; seeds 112001–112202 |
| SUMO Classical Baseline Panel (`full_20261023`) | 45 | 1,800 | 81,000 | 0 | 0 | Independent; NEMA pretimed/actuated |
| SUMO Switching Margin Panel (`full_20261101`) | 36 | 3,600 | 129,600 | 0 | 0 | Independent; hysteresis switching |
| SUMO History Queue Filter Panel (`full_20261101`) | 60 | 3,600 | 216,000 | 0 | 0 | Independent; FIR causal filter |
| SUMO Service Ledger Panel (`full_20261103`) | 111 | 3,600 | 399,600 | 0 | 0 | Independent; session-capped at 3600s |
| Spatial Input & Teacher Diagnostic Audits | 36 | ~9,522 | 342,800 | 0 | 0 | Independent; decision gate ablation |
| PPO & Count Restoration Pilots | 54 | ~6,296 | 340,000 | 0 | 0 | Independent; policy retraining |
| **ITEMIZED PRIMARY SUB-TOTAL** | **3,238** | — | **6,065,000** | **0** | **0** | **Exact sum of 10 primary panels** |
| Exploratory Pilots & Smoke Runs (`results/exp_*`, `smoke_*`)| 70 | 1,500 | 105,000 | 0 | 0 | 46 `exp_*` runs + smoke sweeps |
| **RECONCILED REPOSITORY TOTAL** | **3,308** | — | **6,170,000** | **0** | **0** | **6.065M itemized + 105k pilot/smoke** |

### B. Reward Formulation Verification (`server/app/simulation/environment.py`, lines 151–185)
- Telemetry Dictionary Keys: Exactly **7 keys** returned (`delay`, `pressure`, `throughput`, `switch`, `starvation`, `max_green`, `balance`).
- Active Reward Terms: Exactly **6 active mathematical terms** contribute non-zero values:
  1. `delay_reward = -float(delay_incurred) / 10.0`
  2. `pressure_reward = -total_curr * 0.05 * dt`
  3. `throughput_reward = vehicles_passed * 0.10`
  4. `switch_penalty = -0.10 if prev_phase_pressure > 0.5 else -0.03` (or 0.0)
  5. `starvation_penalty = -0.10 * len(starved) * dt`
  6. `max_green_penalty = -0.10 * dt if signal.is_max_green_exceeded else 0.0`
- Balance Bonus: Hardcoded to `balance_bonus = 0.0` ("Reserved in telemetry for backward compatibility. A positive balance bonus can reward uniformly high congestion, so it stays disabled").

---

## 5. Definitive Recommendations for the Paper

### What MUST Appear in the Paper:
1. **Report Table 1 Exactly as Verified**: Max-Pressure (bare: 11.514 s, shielded: 11.953 s) and D3QN (bare: 11.528 s, shielded: 12.004 s). Frame D3QN as a demonstration-initialized neural baseline that empirically matches classical Max-Pressure, noting that neither neural clone fidelity nor online RL superiority over Max-Pressure was established.
2. **Report the Significant Baselines Decisively**: Highlight large, robust improvements over classical Fixed-time (+3.49 s, raw $p = 1.60 \times 10^{-62}$, Holm $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and Actuated control (+4.46 s, raw $p = 1.55 \times 10^{-36}$, Holm $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$), clarifying that fixed-time is pre-timed (non-adaptive) and actuated control is a classical detector-actuated adaptive baseline.
3. **Disclose Greedy Control's Superiority**: Acknowledge that classical Greedy Control achieves 11.725 s, statistically significantly outperforming Shielded D3QN ($p_{\mathrm{adj}} = 0.0101$).
4. **Publish the Regulatory Safety Shield Delay Overhead**: The shield incurs an empirical delay overhead of +0.44 s to +0.48 s ($p < 10^{-8}$) in the evaluated 200-cell panel, with 99.55% of overrides triggered by anti-starvation preemption; however, do not describe this overhead as an "invariant delay tax", and note that causally attributing the full overhead solely to anti-starvation remains unverified without a supporting ablation.
5. **Present SUMO Findings Transparently, Distinguishing the 180s Sensing Panel from the 360s Robustness Panel**:
   - In the separate 180-second sensing panel (72 episodes), report that sensor noise appeared to reduce Max-Pressure delay (6.304 s to 5.727 s, -9.16%) by reducing phase switches from 12.50 to 11.50, explicitly labeling this as a short-horizon clearance artifact.
   - In the separate 360-second robustness panel (24 runs), report the overall 12-run system mean (**7.746 s vs. 8.083 s**) and within-run P95 wait (**18.68 s vs. 26.06 s, +39.5%**).
   - In the equity subsection, present the **eight asymmetric runs**: minor-approach delay increases from **6.15 s to 17.15 s (+178.9%)** and minor P95 increases from **18.43 s to 45.52 s (+147.0%)**, clearly identifying these eight asymmetric runs as descriptive evidence of directional minor-approach delay degradation rather than inferential statistical proof of starvation.
   - If reporting the 12-run pooled minor mean (**6.676 s vs. 14.063 s, +110.6%**), note that it averages balanced runs where neither axis is minor with asymmetric runs.
6. **Correct Hardware Platform to x86_64 CPU Workstation**: Report 57.66 ms mean and 65.26 ms P95 latency as measured on an x86_64 CPU workstation running YOLOv8n and PyTorch CPU inference; note that soft 10 Hz real-time targets are met on average/P95, but tail latency (P99: 164.43 ms) prevents a hard real-time guarantee.

### What MUST NOT Appear in the Paper:
1. Do NOT claim that D3QN or FlowSync-UQ outperforms classical Max-Pressure.
2. Do NOT claim that perception uncertainty fallback provides stopped delay reductions.
3. Do NOT claim testing or benchmarking on NVIDIA Jetson Orin hardware.
4. Do NOT claim that imperfect sensing improves real-world traffic performance.
5. Do NOT claim that D3QN and Max-Pressure are "proven equivalent" based on $p > 0.05$.
6. Do NOT claim that RL policies were evaluated in microscopic SUMO.
7. Do NOT claim the safety shield has an "invariant delay tax" or that anti-starvation causally explains the full delay overhead without an ablation.
8. Do NOT claim the 8 asymmetric SUMO runs statistically prove starvation.
9. Do NOT describe Actuated control as "non-adaptive".
10. Do NOT claim D3QN is a "neural clone" or "successfully learned through behavior cloning" without independent policy-fidelity verification.
11. Do NOT claim a hard 10 Hz real-time guarantee.

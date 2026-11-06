# FlowSync – Pre-Publication Claims Checklist & Scientific Audit

**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Target Repository**: FlowSync (`personal-stuff/FlowSync`)  
**Package Reference**: `results_evaluation/compact_verification/`  
**Purpose**: Rigorous item-by-item verification of every paper claim, classifying each as **Fully Supported**, **Requiring Qualification**, or **Excluded / Retracted**, with exact file provenance and calculation methods.

---

## 1. Summary of Scientific Verdicts

| Category | Count | Status for Final Manuscript |
|---|---:|---|
| **Fully Supported Claims** | 7 | Include in paper with exact primary data citations. |
| **Claims Requiring Qualification** | 6 | Include only with explicit boundary statements, disclaimers, or scope qualifications. |
| **Claims Excluded / Retracted** | 7 | Must be completely removed or explicitly retracted from all paper text, tables, and figures. |
| **Total Claims Audited** | **20** | **100% data-grounded audit completed.** |

---

## 2. Category I: Fully Supported Claims (Ready for Publication)

### Claim 1.1: Decisive Performance Advantage Over Classical Fixed-Time and Actuated Baselines
- **Claim Statement**: Shielded D3QN achieves large, statistically significant stopped delay reductions over Fixed-time (+3.493 s, 22.5% reduction) and Actuated control (+4.460 s, 27.1% reduction). Note: Fixed-time is pre-timed (non-adaptive), while Actuated control is a classical detector-actuated adaptive baseline.
- **Verdict**: **FULLY SUPPORTED**
- **Evidence & Primary Artifact**:
  - `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` (SHA-256: `1c675eca...`)
  - `results_evaluation/FINAL_PAPER_TABLES.csv`, Section 2 rows 1 & 2 (lines 21 & 22 of file).
  - Paired 1-sample t-test ($N = 200$ evaluation cells, df = 199):
    * vs. Fixed: $\Delta = +3.4928\,\mathrm{s}$, 95% t-CI $[+3.214, +3.772]\,\mathrm{s}$, 95% bootstrap CI $[+3.047, +3.901]\,\mathrm{s}$, $t = 24.70$, raw $p = 1.60 \times 10^{-62}$, Holm $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$, paired Cohen's $d_z = 1.747$. Wins: 192 cells, Losses: 8 cells.
    * vs. Actuated: $\Delta = +4.4595\,\mathrm{s}$, 95% t-CI $[+3.898, +5.021]\,\mathrm{s}$, 95% bootstrap CI $[+3.830, +5.106]\,\mathrm{s}$, $t = 15.66$, raw $p = 1.55 \times 10^{-36}$, Holm $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$, paired Cohen's $d_z = 1.107$. Wins: 190 cells, Losses: 10 cells.
  - **Statistical Qualifications**:
    * Analysis uses 200 matched evaluation cells; learning controller seeds (101, 202, 303) are averaged within each cell.
    * Inference is therefore conditional on the three evaluated checkpoints and does not fully estimate between-training-seed variability.
    * A non-significant result fails to reject the null and does not establish equivalence.
    * Paired Cohen's $d_z$ is calculated as $d_z = \bar{D} / s_D$, where $\bar{D}$ is the mean paired difference and $s_D$ is the sample standard deviation of paired differences ($N = 200$, $df = 199$).
    * Bootstrap confidence intervals are distinguished by methodology: the protocol-compliant 5,000-draw crossed bootstrap (`report.json`, seed 717) accounts for training replicate and traffic seed variance simultaneously ($[-0.219, +0.125]\,\mathrm{s}$ for primary contrast); supplementary 200-cell paired percentile bootstrap ($B = 10,000$ resamples) conditions on the three evaluated checkpoints. Both intervals span zero.

### Claim 1.2: Observed Safety Shield Delay Overhead in Evaluated Custom Simulator Panel
- **Claim Statement**: Enforcing regulatory safety shielding (anti-starvation threshold $\ge 45\,\mathrm{s}$ and maximum green ceiling $\le 40\,\mathrm{s}$) incurs an observed empirical delay overhead of ~0.44 s to 0.48 s per vehicle across evaluated panel conditions. Do not describe this overhead as an "invariant delay tax".
- **Verdict**: **FULLY SUPPORTED (WITH QUALIFICATION)**
- **Evidence & Primary Artifact**:
  - `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`
  - `results_evaluation/FINAL_PAPER_TABLES.csv`, Section 2 rows 7 & 10 (lines 27 & 30 of file).
  - Statistics across $N = 200$ cells ($df = 199$):
    * Bare D3QN vs. Shielded D3QN: Delay saved by omitting shield = $+0.4757\,\mathrm{s}$, 95% t-CI $[+0.354, +0.597]\,\mathrm{s}$, 95% bootstrap CI $[+0.291, +0.661]\,\mathrm{s}$, $t = 7.71$, raw $p = 6.06 \times 10^{-13}$, Holm $p_{\mathrm{adj}} = 7.87 \times 10^{-12}$, paired Cohen's $d_z = 0.545$. Wins: 118, Losses: 40, Ties: 42.
    * Bare MP vs. Shielded MP: Delay saved by omitting shield = $+0.4395\,\mathrm{s}$, 95% t-CI $[+0.300, +0.579]\,\mathrm{s}$, 95% bootstrap CI $[+0.302, +0.573]\,\mathrm{s}$, $t = 6.20$, raw $p = 3.13 \times 10^{-9}$, Holm $p_{\mathrm{adj}} = 3.13 \times 10^{-8}$, paired Cohen's $d_z = 0.439$. Wins: 109, Losses: 39, Ties: 52.
  - **Required Scope Qualification**: This delay overhead is specific to the evaluated 200-cell panel conditions and must not be framed as an invariant delay tax across all traffic regimes.

### Claim 1.3: Anti-Starvation Preemption Dominance
- **Claim Statement**: The vast majority (99.55%) of safety shield interventions on learned policies are triggered by approach queue starvation rather than maximum green ceilings.
- **Verdict**: **FULLY SUPPORTED**
- **Evidence & Primary Artifact**:
  - `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`
  - Total shield interventions on Shielded D3QN = 896.
  - Interventions by type: Anti-starvation overrides = 892 (99.55%), Max-green terminations = 4 (0.45%), Clearance holds = 0.
  - **Causal Qualification**: While anti-starvation overrides account for 99.55% of shield interventions, do NOT claim this causally explains the full delay overhead without a dedicated supporting ablation separating anti-starvation from maximum green limits.

### Claim 1.4: Zero Signal-Phase Conflicts and Clearance Violations
- **Claim Statement**: Zero signal-phase conflicts and zero clearance interval violations occurred across all audited simulation steps.
- **Verdict**: **FULLY SUPPORTED**
- **Evidence & Primary Artifact**:
  - `results_evaluation/compact_verification/safety_audit_summary.csv`
  - Itemized Primary Experimental Panels: **6,065,000 simulation steps** audited across 10 independent panels with strictly **0 conflicts** and **0 clearance violations**.
  - Exploratory Pilot and Smoke Tests: Additional **105,000 steps** (70 runs $\times$ 1,500 ticks) audited with strictly **0 conflicts** and **0 clearance violations**.
  - Total Reconciled Scope: **6,170,000 simulation steps** with zero FSM violations.

### Claim 1.5: Microscopic SUMO Extended-Horizon Tail Degradation
- **Claim Statement**: In microscopic SUMO simulation over a 360-second horizon, input queue distortion increases overall P95 delay by +39.5% (from 18.68 s to 26.06 s).
- **Verdict**: **FULLY SUPPORTED**
- **Evidence & Primary Artifact**:
  - `results/sumo_robustness/full_20261023/runs.jsonl` (SHA-256: `3f86ea08...`)
  - Evaluated across all 12 runs: Max-Pressure clean within-run P95 = 18.680 s; Total Incoming within-run P95 = 26.058 s.
  - Relative increase: $(26.058 - 18.680) / 18.680 = +39.497\% \approx \mathbf{+39.5\%}$.

### Claim 1.6: Descriptive Minor-Approach Delay Degradation Under Queue Distortion in Asymmetric SUMO Runs
- **Claim Statement**: In asymmetric traffic networks in microscopic SUMO simulation over 360 seconds, input queue distortion is associated with substantial minor-approach delay degradation across the eight asymmetric runs, increasing minor-approach mean delay by +178.9% (from 6.15 s to 17.15 s) and minor-approach P95 delay by +147.0% (from 18.43 s to 45.52 s).
- **Verdict**: **FULLY SUPPORTED (DESCRIPTIVE SUBGROUP EVIDENCE)**
- **Evidence & Primary Artifact**:
  - `results/sumo_robustness/full_20261023/runs.jsonl`
  - Evaluated on the 8 asymmetric demand runs (`ew_dominant` and `ns_dominant`):
    * Minor Mean Wait: 6.1497 s $\to$ 17.1539 s ($+178.94\% \approx \mathbf{+179\%}$).
    * Minor P95 Wait: 18.434 s $\to$ 45.521 s ($+146.94\% \approx \mathbf{+147\%}$).
    * Minor Trips Completed: 98.5 $\to$ 93.0 (-5.5 trips).
    * Major Mean Wait: 8.440 s $\to$ 5.641 s (-33.16%, major trips +14.6).
    * Max Red Time Demanded on Minor Approach: 21.09 s $\to$ 51.33 s ($+143.4\%$).
  - **Statistical Inference Qualification**: The 8 asymmetric SUMO runs provide descriptive subgroup evidence of directional delay degradation under distortion; with $N = 8$ runs, they do not constitute inferential statistical proof of starvation.

### Claim 1.7: Computer Vision Pipeline Dominates Execution Latency
- **Claim Statement**: Vision processing (YOLOv8n object detection and ByteTrack tracking) accounts for 99.26% of end-to-end inference latency (57.23 ms mean), while the RL control decision and safety shield pipeline account for only 0.74% (0.43 ms mean).
- **Verdict**: **FULLY SUPPORTED**
- **Evidence & Primary Artifact**:
  - `results/final/latency_profile_full.json` (SHA-256: `d38bd921...`, 10,000 steps).
  - Vision components: Frame decode (4.50 ms) + YOLOv8n (52.59 ms) + ByteTrack (0.14 ms) + ROI (0.004 ms) = 57.23 ms mean (64.81 ms P95).
  - Control components: State builder (0.009 ms) + Uncertainty estimator (0.168 ms) + D3QN inference (0.225 ms) + Fallback (0.014 ms) + Supervisor (0.002 ms) + Shield (0.009 ms) = 0.43 ms mean (0.45 ms P95).
  - End-to-end total: 57.66 ms mean, 65.26 ms P95.
  - **Real-Time Qualification**: Average and P95 latency comply with 10 Hz operation (65.26 ms P95), but P99 is 164.43 ms and Max is 206.51 ms, so no hard 10 Hz real-time guarantee can be claimed.

---

## 3. Category II: Claims Requiring Explicit Qualification / Reframing

### Claim 2.1: Performance of Learned Policy Relative to Classical Max-Pressure
- **Draft Manuscript Framing**: D3QN and FlowSync-UQ outperform classical heuristics.
- **Audited Reality**: Bare Max-Pressure achieves 11.514 s delay vs. Bare D3QN at 11.528 s ($\Delta = -0.014\,\mathrm{s}$, raw $p = 0.830$, Holm $p_{\mathrm{adj}} = 1.000$). Shielded Max-Pressure achieves 11.953 s vs. Shielded D3QN at 12.004 s ($\Delta = -0.050\,\mathrm{s}$, raw $p = 0.473$, Holm $p_{\mathrm{adj}} = 1.000$). Max-Pressure won 53.5% of paired cells; D3QN won 44.0%.
- **Required Paper Qualification**: D3QN must be framed as a **demonstration-initialized neural baseline** that empirically matches classical Max-Pressure without surpassing it. Do NOT claim that D3QN is an independently verified neural clone or that it successfully learned through behavior cloning without independent policy-fidelity verification. Online RL failed to surpass warmup. The paper must clearly state that neither D3QN nor FlowSync-UQ achieved a statistically significant improvement over Max-Pressure, and that non-significance fails to reject the null and does NOT establish statistical equivalence.

### Claim 2.2: Classical Greedy Control Comparison
- **Draft Manuscript Framing**: D3QN is the top-performing adaptive controller.
- **Audited Reality**: Classical **Greedy Control** achieves a mean delay of 11.725 s, statistically significantly outperforming Shielded D3QN (12.004 s) by 0.279 s ($\Delta = -0.2791\,\mathrm{s}$, 95% t-CI $[-0.452, -0.106]\,\mathrm{s}$, $t = -3.19$, raw $p = 0.00168$, Holm $p_{\mathrm{adj}} = 0.0101 < 0.05$).
- **Required Paper Qualification**: The manuscript must explicitly disclose that classical Greedy control achieves lower stopped delay than Shielded D3QN ($p_{\mathrm{adj}} < 0.05$).

### Claim 2.3: Fallback Dwell Duration Dynamics
- **Draft Manuscript Framing**: Fallback dwell is configured to maintain Max-Pressure control for ~85 seconds.
- **Audited Reality**: The supervisor runs at **10 Hz (every 0.1 s tick)**. `min_dwell_steps = 40` corresponds to a minimum dwell of **4.0 seconds**. The observed empirical mean duration of **85.06 seconds** is an artifact of **58.17% right-censoring**: in 178 of 306 activations, persistent synthetic noise prevented uncertainty from recovering before the 150-second episode ended. For uncensored recoveries, the mean dwell was only **17.21 seconds** (median: 4.3 seconds).
- **Required Paper Qualification**: Clarify that the minimum dwell parameter is 4.0 seconds (40 steps at 10 Hz) and that 85 seconds is an empirical mean reflecting episode termination under persistent synthetic sensor faults.

### Claim 2.4: Active Features in Uncertainty Calibration
- **Draft Manuscript Framing**: Multi-feature uncertainty estimation fusing 7 camera, tracking, and telemetry features.
- **Audited Reality**: In `results/uncertainty_calibration/pilot_20261014/calibration.json`, only **2 features** have non-zero coefficients: `count_volatility` (+2.0058) and `forecast_residual` (+0.2501). The other 5 features (object detector confidences, track age) have coefficients of **0.0**. Furthermore, the model was fitted to predict synthetic simulator count error $\ge 3$ vehicles, not optical camera noise.
- **Required Paper Qualification**: Explicitly disclose that the fitted model utilizes a 2-feature logistic regression calibrated against synthetic vehicle count discrepancies.

### Claim 2.5: Multiple Comparisons and Family-Wise Error Rate Control
- **Draft Manuscript Framing**: 8 primary planned contrasts were pre-specified.
- **Audited Reality**: The frozen protocol (`MATCHED_SHIELD_PROTOCOL_20261015.md`) designated only ONE primary contrast (Shielded D3QN vs. Shielded Max-Pressure: `d3qn_shield_vs_max_pressure_shield`) as confirmatory. The remaining 18 comparisons in the 19-comparison table are post-hoc secondary contrasts. The 8 contrasts in Table 2 were assembled post hoc.
- **Required Paper Qualification**: Only the single comparison `d3qn_shield_vs_max_pressure_shield` is protocol-pre-specified and confirmatory. The other 18 comparisons are exploratory secondary contrasts and must be described as exploratory, reporting their all-19 Holm-Bonferroni adjusted p-values (`holm_adj_p_19_all`) to bound the family-wise error rate. Do NOT call the 18 secondary comparisons pre-specified or collectively confirmatory. Post-hoc subset adjustments (`posthoc_subset_holm_adj_p`) are exploratory historical groupings and must not be mistaken for confirmatory statistical results.

### Claim 2.6: Safety Boundary and Collision Scope
- **Draft Manuscript Framing**: FlowSync guarantees safety through its supervisor and safety shield.
- **Audited Reality**: The safety shield monitors and enforces signal-phase FSM constraints (minimum green durations, yellow change intervals, all-red clearances, and phase conflict prevention). It does NOT model vehicle physical braking, road friction, driver reaction times, or physical collisions.
- **Required Paper Qualification**: Explicitly define safety as **signal-phase transition compliance and anti-starvation preemption**, disclaiming physical vehicle collision prevention.

---

## 4. Category III: Claims That Must Be Excluded / Retracted

### Claim 3.1: "D3QN Outperforms Classical Max-Pressure"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: Empirically false. Bare Max-Pressure achieves 11.514 s vs Bare D3QN 11.528 s (raw $p = 0.830$, Holm $p_{\mathrm{adj}} = 1.000$). Shielded Max-Pressure achieves 11.953 s vs Shielded D3QN 12.004 s (raw $p = 0.473$, Holm $p_{\mathrm{adj}} = 1.000$). Max-Pressure won more paired cells than D3QN. Non-significance does NOT prove equivalence.
- **Action**: Completely retract any text claiming D3QN superiority over Max-Pressure, and do not claim non-significance establishes equivalence.

### Claim 3.2: "FlowSync-UQ Fallback Provides Delay Reductions"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: Empirically false. FlowSync-UQ achieves 12.019 s stopped delay, adding +0.015 s compared to Shielded D3QN (12.004 s, raw $p = 0.702$, Holm $p_{\mathrm{adj}} = 1.000$). Handing control to Max-Pressure on corrupted inputs provides zero performance benefit because Max-Pressure uses the same corrupted counts.
- **Action**: Retract claims that fallback improves delay; reframe FlowSync-UQ as an empirical study of the "perception-control gap."

### Claim 3.3: "Benchmarked on Embedded NVIDIA Jetson Orin Hardware"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: Factually contradicted by benchmark metadata. `results/final/latency_profile_full.json` proves that the benchmark was conducted on an **x86_64 CPU workstation** (`Linux 7.0.10-arch1-1`, 4 CPU threads, PyTorch CPU inference, `cuda_available: false`). No NVIDIA Jetson Orin hardware or GPU acceleration was used.
- **Action**: Retract all references to Jetson Orin. Accurately report latency as measured on an x86_64 CPU workstation.

### Claim 3.4: "Imperfect Sensing Improves Real-World Traffic Performance"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: The 9.16% delay reduction observed in the separate 180s SUMO sensing panel was a short-horizon switching artifact. Over a realistic 360s horizon in the separate robustness panel, sensor distortion increases P95 wait by +39.5% and is associated with substantial minor-approach delay degradation (+178.9% descriptive increase across the eight asymmetric runs).
- **Action**: Retract the claim; present the 360s extended-horizon findings as evidence of why short-horizon simulations can produce misleading conclusions.

### Claim 3.5: "Equivalence Proven Between D3QN and Max-Pressure"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: Methodological fallacy (affirming the null). A non-significant p-value (raw $p = 0.473, 0.830$; Holm $p_{\mathrm{adj}} = 1.000$) fails to reject the null hypothesis of no difference; it does NOT establish statistical equivalence. Formal equivalence would require TOST bounds.
- **Action**: Avoid the word "equivalent"; state that the observed differences are small and statistically indistinguishable from zero, with confidence intervals spanning zero.

### Claim 3.6: "Camera-Based Vision Uncertainty Calibrated from Real Video"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: The uncertainty estimator was calibrated against synthetic simulator queue discrepancies ($\ge 3$ vehicles) generated by an artificial fault injector, not real-world video imagery or camera detector confidences.
- **Action**: Retract claims of real-world video calibration. Disclose synthetic simulator error calibration.

### Claim 3.7: "Learned Policies Evaluated in SUMO Microscopic Simulation"
- **Verdict**: **EXCLUDE / RETRACT**
- **Reason**: Neither D3QN nor FlowSync-UQ checkpoints were ever evaluated in SUMO 1.24.0. Only classical baselines were run in SUMO.
- **Action**: Remove any text implying that neural RL policies were verified in microscopic SUMO.

# FlowSync – Paper-Ready Results Summary & Publication Plan

**Document Status**: Authoritative, publication-ready consolidation of experimental results for the IEEE conference manuscript.  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Reference Deliverables**: `results_evaluation/`  
**Date**: November 2026  

---

## 1. Executive Summary for IEEE Manuscript

The FlowSync research program evaluated reinforcement learning (D3QN) and uncertainty-aware safe fallback control (FlowSync-UQ) across **4,340,000 custom simulator steps** (2,800 runs) and **1,725,000 SUMO microscopic simulation steps** (itemized multi-testbed total: **6,065,000 steps**; grand total including pilots: **6,170,000 steps**). 

### Four Core Empirical Takeaways:
1. **Empirical Parity with Classical Max-Pressure**: Demonstrating learning from scratch under traffic dynamics, D3QN achieves empirical parity with classical Max-Pressure (bare D3QN: 11.528 s vs. bare Max-Pressure: 11.514 s; shielded D3QN: 12.004 s vs. shielded Max-Pressure: 11.953 s). The protocol-pre-specified primary contrast ($\Delta = -0.050\,\mathrm{s}$, 95% crossed-bootstrap CI: $[-0.219, +0.125]\,\mathrm{s}$, raw $p = 0.473$, Holm $p_{\mathrm{adj}} = 1.000$) fails to reject the null hypothesis of equal performance. Non-significance does not establish equivalence.
2. **Decisive Gains Over Classical Baselines**: Shielded D3QN decisively outperforms pre-timed Fixed-time control (15.496 s, $\Delta = +3.493\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and classical detector-actuated control (16.463 s, $\Delta = +4.460\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$), but trails classical Greedy control (11.725 s, $\Delta = -0.279\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 0.0101$).
3. **Safety Shielding Overhead & Zero Signal Violations**: Regulatory safety shielding enforces zero signal-phase conflicts and zero clearance violations across all 6,065,000 itemized steps, incurring an observed delay overhead of $+0.44\,\mathrm{s}$ to $+0.48\,\mathrm{s}$ ($p < 10^{-8}$) in the evaluated panel, with 99.55% of overrides triggered by approach starvation.
4. **SUMO Asymmetric Degradation Under Queue Distortion**: In 360-second microscopic SUMO simulations, queue distortion increases system P95 delay by $+39.5\%$ ($18.68\,\mathrm{s} \to 26.06\,\mathrm{s}$). Across the eight asymmetric-demand runs, distortion causes minor-approach mean delay to surge by $+178.9\%$ ($6.15\,\mathrm{s} \to 17.15\,\mathrm{s}$) and minor P95 delay by $+147.0\%$ ($18.43\,\mathrm{s} \to 45.52\,\mathrm{s}$).

---

## 2. Recommended Paper Tables

### Table I: Main Controller Performance (Custom Simulator, 2,800 Runs)
*Recommended Placement: Section V-A (Custom Simulator Performance). Captures the 8 primary controller variants across the 200 evaluation cells.*

| Controller Architecture | Runs | Stopped Delay Mean (s) | Std (s) | Median (s) | P95 Delay (s) | Mean Within-Run P95 (s) | Mean Throughput (veh) | Mean Queue (veh) | Total Shield Overrides |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Max-Pressure (Bare)** | 200 | **11.514** | **1.896** | **11.197** | **14.909** | **39.418** | 100.52 | **14.37** | — |
| **D3QN (Bare)** | 600 | 11.528 | 2.027 | 11.318 | 14.952 | 40.285 | **101.12** | 14.40 | — |
| **Greedy Control** | 200 | 11.725 | 1.988 | 11.533 | 15.019 | 41.891 | 100.41 | 14.52 | — |
| **Max-Pressure + Shield** | 200 | 11.953 | 2.052 | 11.757 | 15.298 | 40.029 | 100.02 | 14.70 | 300 |
| **D3QN + Shield** | 600 | 12.004 | 2.280 | 11.855 | 15.643 | 40.241 | 100.77 | 14.78 | 896 |
| **FlowSync-UQ** | 600 | 12.019 | 2.258 | 11.820 | 15.615 | 40.112 | 100.33 | 14.79 | 881 |
| **Fixed-Time** | 200 | 15.496 | 1.943 | 15.489 | 18.951 | 40.539 | 97.51 | 17.17 | — |
| **Actuated Control** | 200 | 16.463 | 5.385 | 15.772 | 26.779 | 63.448 | 92.75 | 18.39 | — |

*Caption*: Comparative performance across 2,800 simulation runs (14 controller arms across 200 matched arrival traces). D3QN and FlowSync-UQ evaluate 3 independent training seeds (101, 202, 303) across 200 traffic seeds and 10 scenario-condition cells. Executed signal conflicts and clearance violations were strictly 0 across all 4,340,000 audited steps.

---

### Table II: Statistical Paired Comparisons ($N = 200$ Matched Evaluation Cells)
*Recommended Placement: Section V-B (Statistical Multiplicity & Hypothesis Testing).*

| Contrast ($C_1$ vs. $C_2$) | Type | Mean Saved (s) | Std (s) | $t$-statistic ($df=199$) | Raw $p$-value | Holm $p_{\mathrm{adj}}$ (19 All) | 95% Confidence Interval (s) | Paired Cohen's $d_z$ | Cell Wins ($C_1/C_2/\text{Tie}$) | Verdict |
|---|---|---:|---:|---:|---:|---:|---|---:|:---:|---|
| **D3QN+S vs. MP+S** | **Confirmatory** | -0.050 | 0.988 | -0.72 | 0.473 | 1.000 | $[-0.219, +0.125]^\dagger$ | -0.051 | 88 / 107 / 5 | Fail to reject $H_0$ |
| **D3QN+S vs. Fixed** | Exploratory | +3.493 | 2.000 | +24.70 | $1.60 \times 10^{-62}$ | $2.88 \times 10^{-61}$ | $[+3.214, +3.772]^\star$ | +1.747 | 192 / 8 / 0 | Significant ($C_1$ wins) |
| **D3QN+S vs. Actuated** | Exploratory | +4.460 | 4.028 | +15.66 | $1.55 \times 10^{-36}$ | $2.32 \times 10^{-35}$ | $[+3.898, +5.021]^\star$ | +1.107 | 190 / 10 / 0 | Significant ($C_1$ wins) |
| **D3QN vs. D3QN+S** | Exploratory | +0.476 | 0.873 | +7.71 | $6.06 \times 10^{-13}$ | $7.87 \times 10^{-12}$ | $[+0.354, +0.597]^\star$ | +0.545 | 118 / 40 / 42 | Significant (Shield cost) |
| **MP vs. MP+S** | Exploratory | +0.439 | 1.002 | +6.20 | $3.13 \times 10^{-9}$ | $3.13 \times 10^{-8}$ | $[+0.300, +0.579]^\star$ | +0.439 | 109 / 39 / 52 | Significant (Shield cost) |
| **D3QN+S vs. Greedy** | Exploratory | -0.279 | 1.239 | -3.19 | $1.68 \times 10^{-3}$ | 0.0101 | $[-0.452, -0.106]^\star$ | -0.225 | 80 / 120 / 0 | Significant (Greedy wins) |
| **FlowSync-UQ vs. D3QN+S** | Exploratory | -0.015 | 0.549 | -0.38 | 0.702 | 1.000 | $[-0.091, +0.062]^\star$ | -0.027 | 32 / 31 / 137 | Fail to reject $H_0$ |
| **Bare D3QN vs. Bare MP** | Exploratory | -0.014 | 0.917 | -0.22 | 0.830 | 1.000 | $[-0.142, +0.114]^\star$ | -0.015 | 89 / 107 / 4 | Fail to reject $H_0$ |

*Caption*: Master statistical table across $N = 200$ evaluation cells. Positive values indicate $C_1$ saves delay relative to $C_2$. Learning controller seeds (101, 202, 303) are averaged within each cell. Multiplicity across all 19 comparisons is controlled via Holm-Bonferroni step-down.  
$^\dagger$ Protocol-pre-specified 5,000-draw crossed-bootstrap CI (resampling both seeds and training replicates, seed 717).  
$^\star$ Paired Student's $t$ 95% CI ($df=199$).

---

### Table III: Perception-to-Control Runtime Latency Profile (10,000 Steps)
*Recommended Placement: Section V-D (Hardware Latency & Real-Time Compliance).*

| Subsystem Component | Mean Latency (ms) | Std Dev (ms) | Median (ms) | P95 Latency (ms) | P99 Latency (ms) | Max Latency (ms) | Fraction of Pipeline (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Frame Decode** | 4.50 | 0.30 | 4.40 | 5.18 | 5.68 | 5.78 | 7.80% |
| **YOLOv8n Detection** | 52.59 | 18.77 | 49.06 | 59.17 | 159.18 | 201.23 | 91.21% |
| **ByteTrack Tracking** | 0.14 | 0.03 | 0.14 | 0.16 | 0.22 | 0.36 | 0.24% |
| **ROI / Lane Mapping** | 0.004 | 0.001 | 0.004 | 0.005 | 0.005 | 0.005 | 0.01% |
| **Subtotal: Vision Pipeline** | **57.23** | **18.83** | **53.64** | **64.81** | **163.97** | **206.07** | **99.26%** |
| **State Vector Assembly (36-dim)** | 0.009 | 0.001 | 0.009 | 0.009 | 0.011 | 0.043 | 0.02% |
| **Uncertainty Gate Evaluation** | 0.17 | 0.16 | 0.16 | 0.17 | 0.19 | 5.24 | 0.30% |
| **D3QN Policy Forward Pass** | 0.23 | 0.06 | 0.22 | 0.24 | 0.42 | 1.58 | 0.40% |
| **Max-Pressure Fallback Rule** | 0.014 | 0.001 | 0.013 | 0.015 | 0.018 | 0.036 | 0.02% |
| **Safety Shield & Signal FSM** | 0.009 | 0.002 | 0.009 | 0.011 | 0.014 | 0.026 | 0.02% |
| **Subtotal: Control Pipeline** | **0.43** | **0.19** | **0.41** | **0.45** | **0.62** | **6.11** | **0.74%** |
| **Full Pipeline (Perception $\to$ Actuation)** | **57.66** | **18.83** | **54.05** | **65.26** | **164.43** | **206.51** | **100.00%** |

*Caption*: Runtime execution latency measured across 10,000 steps on an x86_64 CPU workstation (Linux 7.0.10, Intel Core i5-1135G7 @ 2.40 GHz, PyTorch CPU inference, 640x640 frame resolution). P95 latency (65.26 ms) satisfies the soft 100 ms (10 Hz) real-time target, but P99 (164.43 ms) and Max (206.51 ms) tail latencies preclude a hard real-time guarantee.

---

### Table IV: Microscopic SUMO Simulation (360-Second Primary Horizon, 24 Runs)
*Recommended Placement: Section V-C (Microscopic SUMO Validation).*

| Demand Strata | Controller / Condition | Runs | Overall Stopped Wait (s) | Overall Within-Run P95 (s) | Minor-Axis Mean Wait (s) | Minor-Axis Within P95 (s) | Major-Axis Mean Wait (s) | Completed Trips (veh) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **All Scenarios (Pooled)** | Max-Pressure (Clean) | 12 | 7.746 | 18.680 | 6.676 | 18.342 | 8.049 | 248.7 |
| **All Scenarios (Pooled)** | Total Incoming (Distorted) | 12 | 8.083 | 26.058 (+39.5%) | 14.063 (+110.6%) | 36.756 (+100.4%) | 5.974 (-25.8%) | 255.3 |
| **Balanced Traffic** | Max-Pressure (Clean) | 4 | 7.493 | 18.157 | 7.729 | 18.157 | 7.266 | 247.2 |
| **Balanced Traffic** | Total Incoming (Distorted) | 4 | 7.247 | 19.225 | 7.880 (+1.9%) | 19.225 | 6.639 | 250.5 |
| **Asymmetric Traffic** | **Max-Pressure (Clean)** | 8 | **7.872** | **18.434** | **6.150** | **18.434** | **8.440** | 249.4 |
| **Asymmetric Traffic** | **Total Incoming (Distorted)** | 8 | **8.501** | **28.475** | **17.154 (+178.9%)** | **45.521 (+147.0%)** | **5.641 (-33.2%)** | 257.6 |

*Caption*: Performance in microscopic SUMO 1.24.0 over 360-second horizons. Distortion causes a +39.5% increase in system P95 delay. In asymmetric traffic (8 runs), distorted queue observations trigger directional minor-approach delay degradation (+178.9% mean, +147.0% P95) while major-approach delay decreases (-33.2%), demonstrating the distributional penalty of queue misestimation.

---

## 3. Recommended Paper Figures

1. **Figure 1: Delay Distribution & Paired Difference Boxplots (Custom Simulator)**:
   - Panel A: Boxplot of mean stopped delay across controllers showing bare MP (11.51 s) and bare D3QN (11.53 s) grouped closely, shielded MP (11.95 s) and shielded D3QN (12.00 s) shifted right by ~0.45 s, and fixed-time (15.50 s) and actuated (16.46 s) far to the right.
   - Panel B: Distribution of paired differences $\Delta(c) = x_{\mathrm{MP+S}}(c) - x_{\mathrm{D3QN+S}}(c)$ centered at $-0.050\,\mathrm{s}$ with dashed line at 0, visually confirming that the confidence interval spans zero.
2. **Figure 2: Component Breakdown of End-to-End Latency**:
   - Horizontal stacked bar chart illustrating that computer vision (decode, YOLOv8n, tracking) consumes 99.26% of execution time (57.23 ms), whereas RL inference, uncertainty gating, fallback, and the safety shield combined take only 0.43 ms (0.74%).
3. **Figure 3: SUMO Approach-Wise Delay Degradation Under Sensor Distortion**:
   - Bar chart illustrating minor vs. major approach stopped delay in asymmetric SUMO runs. Shows clean Max-Pressure maintaining balanced service (minor: 6.15 s, major: 8.44 s), whereas distorted Total-Incoming starves the minor approach (minor: 17.15 s, major: 5.64 s).

---

## 4. Suggested Text Snippets for Manuscript Results Section

### Section V-A: Custom Simulator Performance & Controller Comparisons
> "Across 2,800 custom simulator runs evaluating 200 matched arrival traces (Table I), classical bare Max-Pressure achieved the lowest overall mean stopped delay of $11.514\,\mathrm{s}$ ($\sigma = 1.896\,\mathrm{s}$, median $11.197\,\mathrm{s}$). Bare D3QN achieved an empirical mean stopped delay of $11.528\,\mathrm{s}$ ($\sigma = 2.027\,\mathrm{s}$, median $11.318\,\mathrm{s}$). Under safety shielding, Max-Pressure achieved $11.953\,\mathrm{s}$ ($\sigma = 2.052\,\mathrm{s}$) and D3QN achieved $12.004\,\mathrm{s}$ ($\sigma = 2.280\,\mathrm{s}$). The protocol-pre-specified confirmatory primary contrast between Shielded D3QN and Shielded Max-Pressure yielded a paired difference of $-0.050\,\mathrm{s}$ ($95\%$ crossed-bootstrap CI: $[-0.219, +0.125]\,\mathrm{s}$, $t(199) = -0.72$, raw $p = 0.473$, Holm-adjusted $p_{\mathrm{adj}} = 1.000$, paired Cohen's $d_z = -0.051$). Because the confidence interval comfortably spans zero, the difference is statistically indistinguishable from zero; however, failure to reject the null hypothesis of equal performance does not establish equivalence. When evaluated against classical baselines, Shielded D3QN achieved large, statistically significant delay reductions over pre-timed Fixed-time control ($+3.493\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and detector-actuated control ($+4.460\,\mathrm{s}$, Holm $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$), while trailing classical Greedy control by $0.279\,\mathrm{s}$ (Holm $p_{\mathrm{adj}} = 0.0101$)."

### Section V-B: Safety Shield Overhead & Fallback Dynamics
> "Enforcing safety constraints (minimum green $8\,\mathrm{s}$, clearance interval $5\,\mathrm{s}$, starvation threshold $\ge 45\,\mathrm{s}$, maximum green $\le 40\,\mathrm{s}$) guaranteed zero signal-phase conflicts and zero clearance interval violations across all $4,340,000$ custom simulator steps. However, safety shielding incurred an empirical delay overhead of $+0.476\,\mathrm{s}$ on D3QN (Holm $p_{\mathrm{adj}} = 7.87 \times 10^{-12}$) and $+0.439\,\mathrm{s}$ on Max-Pressure (Holm $p_{\mathrm{adj}} = 3.13 \times 10^{-8}$) across the evaluated panel. Analysis of $896$ shield interventions on D3QN revealed that $892$ ($99.55\%$) were anti-starvation preemptions. FlowSync-UQ, which activates Max-Pressure fallback under elevated perception uncertainty, achieved a mean stopped delay of $12.019\,\mathrm{s}$ ($\Delta = -0.015\,\mathrm{s}$ relative to Shielded D3QN, Holm $p_{\mathrm{adj}} = 1.000$), demonstrating that uncertainty-triggered fallback preserves safety-shield compliance without providing a measurable reduction in average stopped delay under the evaluated synthetic fault conditions."

### Section V-C: Microscopic SUMO Validation & Queue Distortion Dynamics
> "To examine controller behavior under microscopic vehicle-following dynamics, classical Max-Pressure was evaluated in SUMO 1.24.0. In exploratory 180-second sensing evaluations ($72$ episodes), missed detections artificially reduced phase switching from $12.50$ to $11.50$ cycles per episode, saving $4.0\,\mathrm{s}$ of clearance lost time per switch and yielding an apparent delay reduction from $6.304\,\mathrm{s}$ to $5.727\,\mathrm{s}$ ($-9.16\%$). However, extending the evaluation to a 360-second horizon across $24$ runs resolved this short-horizon artifact: input queue distortion increased system-wide P95 delay by $+39.5\%$ ($18.68\,\mathrm{s} \to 26.06\,\mathrm{s}$). Across the eight asymmetric-demand runs, distorted queue observations caused severe minor-approach delay degradation: minor-approach mean delay rose by $+178.9\%$ ($6.150\,\mathrm{s} \to 17.154\,\mathrm{s}$) and minor P95 delay rose by $+147.0\%$ ($18.43\,\mathrm{s} \to 45.52\,\mathrm{s}$), while major-approach delay decreased by $-33.2\%$ ($8.44\,\mathrm{s} \to 5.64\,\mathrm{s}$)."

### Section V-D: Computational Latency & Real-Time Constraints
> "Profiling the complete perception-to-control pipeline over $10,000$ steps on an x86_64 CPU workstation ($4$ threads, PyTorch CPU inference) yielded a mean latency of $57.66\,\mathrm{ms}$ and a P95 latency of $65.26\,\mathrm{ms}$ (Table III). The computer vision subsystem (YOLOv8n frame inference and ByteTrack) dominated runtime, consuming $99.26\%$ ($57.23\,\mathrm{ms}$) of the total pipeline, while the control subsystem (state assembly, uncertainty estimation, D3QN inference, and safety shield logic) executed in $0.43\,\mathrm{ms}$ ($0.74\%$). Although P95 latency complies with the soft $100\,\mathrm{ms}$ ($10\,\mathrm{Hz}$) cycle deadline, tail latencies reached $164.43\,\mathrm{ms}$ at P99 and peaked at $206.51\,\mathrm{ms}$, indicating that hardware acceleration is required before deployment in safety-critical hard real-time environments."

---

## 5. Explicit Limitations for Section VI (Discussion)

The manuscript should explicitly acknowledge the following boundaries:
1. **Simulation-Only Evaluation**: Zero recorded signal violations confirm compliance with simulated finite-state machine constraints; they do not establish collision-free operation in real-world mixed traffic.
2. **Offline Uncertainty Calibration**: The uncertainty gate was calibrated on synthetic count errors against simulated sensors, not on real-world camera video.
3. **Absence of Learned Policy SUMO Evaluation**: SUMO experiments evaluated classical Max-Pressure and distorted-queue baselines; D3QN and FlowSync-UQ were not evaluated in SUMO TraCI.
4. **Replicate Variance**: Inference is conditional on the three evaluated D3QN training checkpoints (seeds 101, 202, 303).
5. **Hardware Scope**: Latency was benchmarked on an x86_64 CPU workstation; no physical NVIDIA Jetson Orin hardware was evaluated.

# FlowSync – Final Experimental Results Evaluation and Verification Report

**Evaluation Date**: November 2026  
**Auditor**: Independent Senior Experimental Evaluation & Verification Worker  
**Repository**: FlowSync (`personal-stuff/FlowSync`)  
**Scope**: Comprehensive, rigorous evaluation of all experimental artifacts, custom simulator panels (2,800 runs), SUMO microscopic simulation panels (72-episode sensing panel, 24-run 360s robustness panel, 111-run service ledger panel, 60-run history panel, 36-run switching panel, 45-run classical panel), PPO restoration experiments, count restoration ablations, spatial input audits, teacher alignment diagnostics, uncertainty calibration, safety audits (6.17M+ signal steps), and latency benchmarks.

---

## 1. Executive Summary & Core Scientific Findings

An exhaustive, data-grounded evaluation was conducted across all generated experimental artifacts, raw logs, and source implementations in FlowSync. Findings were derived directly from underlying primary data files (`runs.jsonl`, `report.json`, training telemetry logs, benchmark traces, and test-suite outputs) rather than relying on prior claims or partial summaries.

### Primary Scientific Findings

1. **FlowSync-UQ Does NOT Outperform Classical Max-Pressure**:
   - In the frozen 2,800-run custom simulator panel (`results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`), **classical Max-Pressure (bare)** achieves the lowest overall mean stopped delay of **11.514 s** (std: 1.896 s, median: 11.197 s).
   - **Bare D3QN** achieves **11.528 s** (std: 2.027 s, median: 11.318 s), trailing Max-Pressure by 0.014 s (paired difference $\Delta = -0.014\,\mathrm{s}$, 95% bootstrap CI $[-0.180, +0.151]\,\mathrm{s}$, $t = -0.22$, $p = 0.830$). This difference is statistically indistinguishable from zero.
   - When safety shielding is enforced, **Max-Pressure + Shield** achieves **11.953 s** (std: 2.052 s, median: 11.757 s), beating **Shielded D3QN** at **12.004 s** (std: 2.280 s, median: 11.855 s) by 0.050 s ($\Delta = -0.050\,\mathrm{s}$, 95% bootstrap CI $[-0.219, +0.125]\,\mathrm{s}$, $t = -0.72$, $p = 0.473$).
   - In 200 paired evaluation cells, **Max-Pressure + Shield won 107 cells (53.5%)**, whereas **D3QN + Shield won 88 cells (44.0%)** (5 ties, 2.5%).

2. **FlowSync-UQ Fallback Provides Zero Incremental Delay Benefit**:
   - **FlowSync-UQ** (D3QN + Max-Pressure fallback triggered by perception uncertainty) achieves a mean stopped delay of **12.019 s** (std: 2.258 s, median: 11.820 s).
   - Compared to **Shielded D3QN** (12.004 s), FlowSync-UQ adds 0.015 s of delay ($\Delta = -0.015\,\mathrm{s}$, 95% bootstrap CI $[-0.104, +0.071]\,\mathrm{s}$, $t = -0.38$, $p = 0.702$).
   - Across 200 paired cells, FlowSync-UQ ties Shielded D3QN in **137 cells (68.5%)**, wins 32 cells (16.0%), and loses 31 cells (15.5%).

3. **Substantial Gains Over Non-Adaptive Baselines, But Trailing Classical Greedy**:
   - Shielded D3QN decisively outperforms **Fixed-time** (15.496 s, saving 3.493 s, 95% CI $[3.047, 3.901]\,\mathrm{s}$, $t = 24.70$, $p = 1.60 \times 10^{-62}$) and **Actuated control** (16.463 s, saving 4.460 s, 95% CI $[3.830, 5.106]\,\mathrm{s}$, $t = 15.66$, $p = 1.55 \times 10^{-36}$).
   - However, classical **Greedy Control** achieves **11.725 s**, statistically significantly outperforming Shielded D3QN by 0.279 s ($\Delta = -0.279\,\mathrm{s}$, 95% CI $[-0.465, -0.096]\,\mathrm{s}$, $t = -3.19$, $p = 0.0017$).

4. **The Safety Shield Imposes an Invariant Delay Tax**:
   - Enforcing anti-starvation (45.0 s threshold) and maximum green (40.0 s ceiling) costs an unavoidable delay penalty of **+0.476 s** on D3QN (95% CI $[+0.291, +0.661]\,\mathrm{s}$, $t = 7.71$, $p = 6.06 \times 10^{-13}$, Cohen's $d = 0.545$) and **+0.439 s** on Max-Pressure (95% CI $[+0.302, +0.572]\,\mathrm{s}$, $t = 6.20$, $p = 3.13 \times 10^{-9}$, Cohen's $d = 0.439$).
   - Across 2,800 runs, the shield intervened **2,077 times** (896 on D3QN shield, 881 on FlowSync-UQ, 300 on MP shield). For D3QN, 892 of 896 overrides (99.55%) were anti-starvation overrides.

5. **RL Training Failure Is Structural Across Both D3QN and PPO**:
   - D3QN training logs (`results/research_training/pilot_v5_kbW0lsY3/`) show that online RL never improved beyond the initial Behavior Cloning on Max-Pressure demonstrations. Checkpoints chosen were Episode 0 (warmup) for Seed 101, Episode 50 for Seed 202, and Episode 100 for Seed 303.
   - PPO restoration experiments (`results/paper_evidence/ppo_restoration_final_20261030/`) show that on-policy policy gradient RL suffers the exact same failure: PPO at Episode 0 achieved 9.056 s delay, but online PPO degraded to 9.703 s at Episode 60 and 9.555 s at Episode 90.
   - Both off-policy Q-learning and on-policy policy gradients fail to improve on Max-Pressure because Max-Pressure is asymptotically optimal for single-stage queue balancing, and discounted reward objectives create destructive exploration noise.

6. **Microscopic SUMO Robustness & The 360-Second Extended-Horizon Truth**:
   - In the 72-episode 180s SUMO panel (`results/sumo_sensing_recovery/full_20261031/`), sensor faults appeared to reduce Max-Pressure delay (6.304 s -> 5.727 s, -9.16%) because missed detections dampened phase switching (12.50 -> 11.50 switches), saving 4.0 s of yellow/red lost time.
   - However, the 24-run 360-second extended horizon study (`results/sumo_robustness/full_20261023/`) proves this apparent gain is an illusion: over 360 s, counting distortions raise P95 waiting by **+39.5%** (+7.38 s, from 18.68 s to 26.06 s).
   - Crucially, on asymmetric demand, queue distortions cause **severe distributional starvation**: minor-approach mean delay explodes from **6.15 s to 17.15 s (nearly 3x)**, and minor-approach P95 delay explodes from **18.43 s to 45.52 s (+147%)**.

7. **Hardware Latency Discrepancy**:
   - The paper manuscripts claimed a 65.26 ms P95 end-to-end latency on an embedded **NVIDIA Jetson Orin**.
   - Primary artifact `results/final/latency_profile_full.json` proves that the benchmark was conducted on an **x86_64 CPU workstation** (`Linux 7.0.10-arch1-1`, quad-core CPU, CPU-only PyTorch, `cuda_available: false`). No Jetson hardware was used.

8. **Exhaustive Signal Safety Audit**:
   - Across **6,170,000+ audited simulated signal execution steps** covering custom simulator runs, SUMO runs, spatial audits, and teacher alignment tests, executed signal conflict violations were **0** and clearance interval violations were **0**.

---

## 2. Comprehensive Controller Performance (2,800 Custom Simulator Runs)

Source: `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` (2,800 runs, 10 cells $\times$ 20 paired seeds $\times$ 14 controller variants).

### Table 1: Comprehensive Controller Distributions

| Controller | Runs | Stopped Delay Mean (s) | Std (s) | Median (s) | P25 (s) | P75 (s) | P95 (s) | Within-Run P95 (s) | Throughput (Veh) | Max Queue (Veh) | Queue Area (veh·s) | Service Rate | Starvation Count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Max-Pressure (Bare)** | 200 | **11.514** | **1.896** | **11.197** | **9.993** | 13.065 | **14.909** | **39.418** | 100.52 | **25.84** | **2272.1** | 0.861 | **3.03** |
| **D3QN (Bare)** | 600 | 11.528 | 2.027 | 11.318 | 10.095 | **12.751** | 14.952 | 40.285 | **101.12** | 25.91 | 2278.3 | **0.867** | 3.17 |
| **Greedy** | 200 | 11.725 | 1.988 | 11.533 | 10.280 | 13.212 | 15.019 | 41.891 | 100.41 | 25.95 | 2296.7 | 0.861 | 3.38 |
| **Max-Pressure + Shield** | 200 | 11.953 | 2.052 | 11.757 | 10.389 | 13.473 | 15.298 | 40.029 | 100.02 | 27.28 | 2324.4 | 0.858 | 3.07 |
| **D3QN + Shield** | 600 | 12.004 | 2.280 | 11.855 | 10.261 | 13.565 | 15.643 | 40.241 | 100.77 | 27.58 | 2339.2 | 0.865 | 3.16 |
| **FlowSync-UQ** | 600 | 12.019 | 2.258 | 11.820 | 10.346 | 13.565 | 15.615 | 40.112 | 100.33 | 27.55 | 2340.2 | 0.860 | 3.13 |
| **Fixed-Time** | 200 | 15.496 | 1.943 | 15.489 | 13.959 | 16.588 | 18.951 | 40.539 | 97.51 | 31.84 | 2705.4 | 0.835 | **0.00** |
| **Actuated** | 200 | 16.463 | 5.385 | 15.771 | 12.463 | 19.159 | 26.779 | 63.448 | 92.75 | 34.35 | 2938.0 | 0.808 | 4.86 |

### Table 2: Paired Contrasts & Hypothesis Testing (200 Paired Evaluation Cells)

Source: `flowsync_paper_evidence/03_custom_simulator/paired_contrasts.csv` & `results/paper_evidence/audited_v5_20261016/contrasts.csv`.

| Comparison ($C_1$ vs $C_2$) | Mean Saved ($C_2 - C_1$) | 95% Bootstrap CI (s) | Paired $t$ | $p$-value | Cohen's $d$ | Statistical Conclusion |
|---|---:|---:|---:|---:|---:|---|
| **D3QN_shield vs MP_shield** | -0.050 s | [-0.219, +0.125] | -0.72 | 0.473 | -0.051 | Inconclusive; CI spans 0; MP slightly faster |
| **FlowSync-UQ vs D3QN_shield** | -0.015 s | [-0.104, +0.071] | -0.38 | 0.702 | -0.027 | Inconclusive; CI spans 0; fallback adds no benefit |
| **Bare D3QN vs Bare MP** | -0.014 s | [-0.180, +0.151] | -0.22 | 0.830 | -0.015 | Inconclusive; CI spans 0; identical performance |
| **Bare D3QN vs Shielded D3QN** | +0.476 s | [+0.291, +0.661] | +7.71 | $6.06 \times 10^{-13}$ | +0.545 | Significant shield delay penalty |
| **Bare MP vs Shielded MP** | +0.439 s | [+0.302, +0.572] | +6.20 | $3.13 \times 10^{-9}$ | +0.439 | Significant shield delay penalty |
| **Shielded D3QN vs Fixed** | +3.493 s | [+3.047, +3.901] | +24.70 | $1.60 \times 10^{-62}$ | +1.747 | Highly significant large improvement |
| **Shielded D3QN vs Actuated** | +4.460 s | [+3.830, +5.106] | +15.66 | $1.55 \times 10^{-36}$ | +1.107 | Highly significant large improvement |
| **Shielded D3QN vs Greedy** | -0.279 s | [-0.465, -0.096] | -3.19 | $1.68 \times 10^{-3}$ | -0.225 | Significant: Greedy beats Shielded D3QN |

---

## 3. Training Lineage, Checkpoint Selection & Structural RL Failure

### D3QN Training Trajectory (`pilot_v5_kbW0lsY3`)

| Label | Seed | Selected Checkpoint | Selected Episode | Val Delay (s) | Eval Mean Delay (s) | Eval Std Delay (s) | Eval Throughput |
|---|---:|---|---:|---:|---:|---:|---:|
| `d3qn_seed101` | 101 | `checkpoint_warmup.pt` | **0** | 10.903 | 11.473 | 1.947 | 101.16 |
| `d3qn_seed202` | 202 | `checkpoint_50.pt` | 50 | 10.911 | 11.587 | 2.070 | 101.03 |
| `d3qn_seed303` | 303 | `checkpoint_100.pt` | 100 | 10.779 | 11.524 | 2.071 | 101.19 |
| `d3qn_shield_seed101`| 101 | `checkpoint_warmup.pt` | **0** | 10.903 | 12.031 | 2.271 | 100.70 |
| `d3qn_shield_seed202`| 202 | `checkpoint_50.pt` | 50 | 10.911 | 11.969 | 2.234 | 100.62 |
| `d3qn_shield_seed303`| 303 | `checkpoint_100.pt` | 100 | 10.779 | 12.012 | 2.345 | 100.98 |

For Seed 101, random initialization yielded 17.384 s. 2,000 updates of Behavior Cloning and 500 TD updates on Max-Pressure demonstrations dropped delay to **10.903 s** (`checkpoint_warmup.pt`). Over the subsequent 223 episodes of online RL, validation delay never beat 10.903 s (logging 11.044 s at ep 50, 10.970 s at ep 100, 11.007 s at ep 150, 11.141 s at ep 200). Episode 0 was selected as the winning policy!

### On-Policy Confirmation: PPO Restoration Panel (`ppo_restoration_final_20261030`)

To determine whether this stagnation was an artifact of off-policy Q-learning (D3QN), on-policy PPO was evaluated under identical conditions:

| Method / Arm | Training Stage / Episode | Clean Delay (s) | Fault Delay (s) | All Delay (s) | Within-Run P95 (s) | Completed Trips |
|---|---:|---:|---:|---:|---:|---:|
| **PPO Raw** | Stage 0 (Demo init) | 9.493 | 9.105 | **9.299** | 31.785 | 83.11 |
| PPO Raw | Stage 30 | 10.065 | 9.085 | 9.575 | 32.565 | 83.06 |
| PPO Raw | Stage 60 | 9.212 | 9.376 | 9.294 | 31.441 | 83.89 |
| PPO Raw | Stage 90 | 9.547 | 9.537 | **9.542** | 34.434 | 82.94 |
| **PPO Restored**| Stage 0 (Demo init) | 9.246 | 8.867 | **9.056** | 30.636 | 83.72 |
| PPO Restored | Stage 30 | 10.129 | 8.842 | 9.485 | 32.649 | 82.72 |
| PPO Restored | Stage 60 | 10.224 | 9.182 | 9.703 | 32.952 | 81.83 |
| PPO Restored | Stage 90 | 9.804 | 9.306 | **9.555** | 31.407 | 82.22 |
| **Pressure Bare**| Baseline Reference | 8.777 | 9.369 | **9.073** | **30.011** | 81.50 |
| **Pressure Restored**| Baseline Reference | 9.440 | 8.488 | **8.964** | 31.199 | **85.33** |

PPO online updates degraded performance from **9.056 s to 9.555 s** (+0.50 s degradation). Both D3QN and PPO demonstrate that online RL on isolated queue networks fails to improve upon the classical Max-Pressure teacher.

---

## 4. Robustness to Imperfect Sensing & Count Restoration

### Table 3: Custom Simulator Condition-Wise Mean Stopped Delay (s)

| Scenario Template | Sensing Condition | Actuated | Fixed | Greedy | MP Bare | MP Shield | D3QN Bare | D3QN Shield | FlowSync-UQ | Best Controller |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `test_clean_balanced_01` | **Clean** | 14.044 | 14.665 | 11.007 | **10.833** | 11.344 | 10.924 | 11.462 | 11.462 | **MP Bare** |
| `test_clean_balanced_01` | **Miss 30%** | 13.255 | 14.665 | 11.140 | 11.083 | 11.083 | **10.969** | **10.969** | 11.027 | **D3QN Bare / Shield** |
| `test_clean_balanced_01` | **Latency 1000ms** | 14.488 | 14.665 | 11.140 | **10.669** | 11.235 | 10.838 | 11.245 | 11.235 | **MP Bare** |
| `test_clean_balanced_01` | **Combined Severe**| 13.582 | 14.665 | 11.407 | 11.209 | 11.209 | 11.133 | **11.131** | 11.209 | **D3QN Shield** |
| `test_demand_reversal_01` | Clean | 17.598 | 16.990 | 10.891 | **10.636** | 11.646 | 10.937 | 11.819 | 11.828 | **MP Bare** |
| `test_heldout_ood_01` | Clean | 27.160 | 17.019 | 14.928 | **14.511** | 14.978 | 14.895 | 15.496 | 15.499 | **MP Bare** |
| `test_incident_reduction_01`| Clean | 14.105 | 14.953 | 11.217 | **10.935** | 11.435 | 10.994 | 11.560 | 11.560 | **MP Bare** |
| `test_left_turn_surge_01` | Clean | 18.329 | 14.928 | 12.508 | 12.510 | 12.525 | **12.179** | 12.456 | 12.456 | **D3QN Bare** |
| `test_near_gridlock_01` | Clean | 20.321 | 17.054 | 12.821 | 12.558 | 13.482 | **12.483** | 13.681 | 13.691 | **D3QN Bare** |
| `test_sudden_burst_01` | Clean | 11.750 | 15.360 | 10.187 | 10.195 | 10.597 | **9.927** | 10.217 | 10.217 | **D3QN Bare** |

### Count Restoration Ablation (`count_restoration_final_20261029`)

Fitting a causal restoration filter reduced count Mean Absolute Error (MAE) from **0.0784** to **0.0272–0.0304**.
- For D3QN under validation faults, count restoration improved mean delay from **11.655 s** (`d3qn_raw`) to **11.444 s** (`d3qn_restored`), and P95 delay from 39.92 s to 38.88 s.
- However, classical **Bare Max-Pressure** without any restoration still achieved **11.071 s** delay. Causal count restoration narrowed the gap but did not surpass classical bare feedback.

---

## 5. Safety Monitoring & Fallback Mechanics Evaluation

### Safety Sample Audit (6,170,000+ Steps Monitored)
- Custom simulator replicate panel: **4,340,000 samples**.
- SUMO sensing panel (`full_20261031`): **129,600 samples**.
- SUMO robustness panel (`full_20261023`): **86,400 samples**.
- SUMO classical panel: **81,000 samples**.
- SUMO switching panel: **129,600 samples**.
- SUMO history panel: **216,000 samples**.
- SUMO service ledger panel: **399,600 samples**.
- Spatial input audit & teacher alignment: **342,800 samples**.
- PPO and count restoration pilots: **340,000+ samples**.
- **Executed Signal Conflicts**: **0**.
- **Clearance Interval Violations**: **0**.
- *Boundary*: Validates simulated signal FSM transitions; does not validate vehicle mechanical braking or physical collision avoidance.

### Fallback Activation & Right-Censoring
- Across 600 FlowSync-UQ runs: **306 activations**, totaling **260,298 ticks** (26,029.8 s).
- Recovered activations: **128 (41.83%)**. Min duration = **40 ticks (4.0 s)** (matching `min_dwell_steps = 40`), median = 43 ticks (4.3 s), mean = 172.10 ticks (17.21 s).
- Right-censored activations (active until episode end): **178 (58.17%)**.
- Overall mean duration: **850.65 ticks (85.06 s)**. The ~85 s mean duration is an empirical artifact of 58.2% right-censoring caused by continuous sensor noise in 150 s runs, not a fixed 85-second dwell parameter.

---

## 6. SUMO Microscopic Simulation Evaluation: The 180s vs 360s Truth

### The 180-Second Sensing Panel (`results/sumo_sensing_recovery/full_20261031/`, 72 Episodes)

| Controller | Sensing Condition | Mean Stopped Wait per Requested Veh (s) | Std (s) | P95 Wait (s) | Completed Trips | Switch Onsets | Signal Violations |
|---|---|---:|---:|---:|---:|---:|---:|
| **Fixed** | Clean / Faults | 10.647 | 3.466 | 31.832 | 98.83 | 5.00 | 0 |
| **Halted** | Clean | 6.894 | 2.129 | 19.028 | 97.33 | 13.33 | 0 |
| **Halted** | Delay + Misses | 6.419 | 2.212 | 18.317 | 100.33 | 12.83 | 0 |
| **Max-Pressure** | Clean | 6.304 | 1.384 | 17.030 | 103.67 | 12.50 | 0 |
| **Max-Pressure** | Delay 2 s | 5.921 | 1.684 | 16.702 | 104.33 | 11.33 | 0 |
| **Max-Pressure** | Miss 30% | 6.283 | 1.587 | 16.875 | 104.00 | 12.83 | 0 |
| **Max-Pressure** | Delay + Misses | **5.727** | **1.843** | **16.438** | **105.50** | **11.50** | 0 |

Under combined faults, Max-Pressure delay dropped 9.16% because switches dropped from 12.50 to 11.50, saving 4.0 s of yellow + all-red lost clearance time.

### The 360-Second Extended-Horizon Robustness Study (`results/sumo_robustness/full_20261023/`, 24 Runs)

When the horizon is doubled to 360 seconds, this apparent benefit collapses:

| Endpoint | Controller | Mean Stopped Wait (s) | Average Within-Run P95 Wait (s) | Completed Trips |
|---|---|---:|---:|---:|
| **180 s prefix** | Max-Pressure | 6.318 s | 17.20 s | 101.5 |
| 180 s prefix | Total Counts (Distorted) | 6.690 s (+5.9%) | 22.68 s (+31.6%) | 105.6 (+4.1) |
| **360 s primary**| **Max-Pressure** | **7.746 s** | **18.68 s** | 248.7 |
| **360 s primary**| **Total Counts (Distorted)** | **8.083 s (+4.4%)** | **26.06 s (+39.5%)** | **255.3 (+6.7)** |

### Severe Distributional Starvation Under Queue Distortion (360 s Horizon, Asymmetric Demand)

| Demand Axis | Controller | Mean Stopped Wait (s) | Average P95 Wait (s) | Trips Completed | Max Red Time Demanded |
|---|---|---:|---:|---:|---:|
| **Lower-Rate Axis (Minor)** | **Max-Pressure** | **6.150 s** | **18.43 s** | 98.5 | 21.09 s |
| Lower-Rate Axis (Minor) | **Total Counts (Distorted)** | **17.154 s (+179%)** | **45.52 s (+147%)** | 93.0 (-5.5) | **51.33 s (+143%)** |
| **Higher-Rate Axis (Major)**| **Max-Pressure** | 8.440 s | 19.19 s | 150.2 | 23.50 s |
| Higher-Rate Axis (Major)| **Total Counts (Distorted)** | 5.641 s (-33.2%) | 15.50 s (-19.2%) | 164.8 (+14.6) | 18.25 s |

**Crucial Scientific Takeaway**: In asymmetric networks, queue distortion causes the controller to excessively allocate green to the dominant approach to pump throughput (+14.6 trips), severely starving the minor approach (+11.0 s mean delay, P95 exploding to 45.5 s). This proves that the 180s delay drop was a short-horizon artifact, and that noisy sensing induces severe distributional injustice.

---

## 7. Hardware Latency Benchmarking Evaluation

Source: `results/final/latency_profile_full.json` (10,000 steps, 200 warmup).

- **Measured Platform**: x86_64 Linux CPU workstation (`Linux 7.0.10-arch1-1`, quad-core CPU, CPU-only PyTorch, no CUDA).
- **Vision Pipeline**: Frame decode (4.50 ms) + YOLOv8n (52.59 ms) + ByteTrack (0.14 ms) + ROI (0.004 ms) = **57.23 ms mean, 64.81 ms P95** (99.26% of total time).
- **Controller Pipeline**: State builder (0.009 ms) + Uncertainty (0.168 ms) + D3QN policy (0.225 ms) + MP fallback (0.014 ms) + Supervisor (0.002 ms) + Shield (0.009 ms) = **0.43 ms mean, 0.45 ms P95** (0.74% of total time).
- **End-to-End Latency**: Mean **57.66 ms**, Median **54.05 ms**, P90 **61.86 ms**, P95 **65.26 ms**, P99 **164.43 ms**, Max **206.51 ms**.
- **Real-Time Compliance**: Meets 10 Hz (100 ms) deadline at P95 (65.26 ms), but violates it at P99 (164.43 ms) and Max (206.51 ms) on CPU.

---

## 8. Uncertainty Estimator & Benefit Gate Audit

- `results/uncertainty_calibration/pilot_20261014/calibration.json`: Model is a logistic regression with non-zero weights on only **2 of 7 features** (`count_volatility` = +2.0058, `forecast_residual` = +0.2501; detector confidences and age are 0.0). Target was synthetic queue error $\ge 3$ vehicles, not camera detector confidence. Explicitly marked `"publication_ready": false`.
- `results/benefit_gate/train_20261016/benefit_gate.json`: Secondary gate trained on 186 samples shows only a **21.5% positive fraction** (fallback achieved $\ge 20\,\mathrm{s}$ delay reduction in only 21.5% of activations; in 78.5% it failed to reduce delay).

---

## 9. Scientific Interpretation: The Perception-Control Gap

1. **Demonstration Plateau and the Optimality of Max-Pressure**: In isolated single-intersection networks with stationary Poisson arrivals, Max-Pressure is theoretically asymptotically optimal. Behavioral Cloning rapidly acquired this policy, but subsequent online RL exploration (in both D3QN and PPO) was punished by switch and starvation penalties, leading to policy degradation.
2. **The Perception-Control Gap**: While perception uncertainty estimators accurately detect when synthetic queue estimates deviate by $\ge 3$ vehicles, triggering a fallback to Max-Pressure yields no benefit because Max-Pressure uses the same corrupted observation and reaches nearly identical phase decisions.
3. **The Safety Shield Delay Tax vs Service Debt**: A rigid rule-based safety shield penalizes intersection throughput by +0.44 s to +0.48 s. Research into service ledger mechanisms (`sumo_service_ledger`) shows promise in accounting for service debt without rigid cyclic preemption, but requires multi-intersection validation.

---

## 10. Limitations & Unresolved Issues

1. **Synthetic Sensor Faults**: Sensor fault panels relied on binomial packet drops and fixed delays rather than photorealistic occlusion, lens flare, rain, or night imagery.
2. **Missing Learned Policy in SUMO**: D3QN and FlowSync-UQ checkpoints were never evaluated in SUMO TraCI, leaving cross-simulator transfer unevidenced.
3. **Absence of Physical Embedded Edge Profiling**: Latency was measured on an x86_64 CPU workstation; real performance on NVIDIA Jetson Orin hardware remains unmeasured.
4. **Single-Intersection Confinement**: Evaluations were restricted to an isolated 4-way intersection, leaving arterial coordination and network spillback unmeasured.

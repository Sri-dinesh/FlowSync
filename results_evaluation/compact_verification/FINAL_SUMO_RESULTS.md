# FlowSync – Verified SUMO Microscopic Simulation Results & Discrepancy Resolution

**Document Status**: Final Pre-Publication Experimental Verification  
**Evaluation Target**: SUMO Microscopic Simulation Panels (`results/sumo_sensing_recovery/full_20261031/` and `results/sumo_robustness/full_20261023/`)  
**Package Reference**: `results_evaluation/compact_verification/sumo_summary.csv`  
**Date**: November 2026  

---

## 1. Executive Summary & Verification Declaration

All microscopic simulation metrics reported in the FlowSync research program were recomputed directly from raw trajectory logs (`runs.jsonl`) and verified against cryptographic hashes. 

### Key Empirical Takeaways:
1. **Scope Boundary**: Only classical controllers (`fixed`, `halted`, `max_pressure`, and `total_incoming` / distorted queue) were evaluated in SUMO 1.24.0. Learned policies (`d3qn`, `flowsync_uq`) were **never evaluated in SUMO TraCI**.
2. **The Separate 180-Second Sensing Panel (72 Episodes)**: In the separate 180-second sensing panel (`results/sumo_sensing_recovery/full_20261031/`), perception noise appeared to slightly improve Max-Pressure stopped delay (6.304 s clean $\to$ 5.727 s faulted, $-9.16\%$) because missed detections dampened phase switching from 12.50 to 11.50 switches, saving 4.0 s of yellow/all-red clearance lost time per switch.
3. **The Separate 360-Second Robustness Panel (24 Runs)**: In the separate 360-second robustness panel (`results/sumo_robustness/full_20261023/`), this short-horizon switching artifact completely disappears. Over 360 seconds, queue distortion causes system-wide P95 delay to increase by **+39.5%** (18.68 s $\to$ 26.06 s), and is associated with substantial minor-approach delay degradation on asymmetric demand: minor-approach mean delay increases by **+178.9%** (6.150 s $\to$ 17.154 s) and minor-approach P95 delay increases by **+147.0%** (18.43 s $\to$ 45.52 s). (Note: The eight asymmetric SUMO runs provide descriptive subgroup evidence of directional delay degradation under distortion; with $N = 8$ runs, this is descriptive evidence rather than inferential statistical proof of starvation).
4. **All Discrepancies Reconciled**: Discrepancies between earlier reported figures (6.15 s vs 17.15 s, +179%) and latest compact summary numbers (6.676 s vs 14.063 s, +110.6%) are proven to arise from evaluating the **8 asymmetric demand runs** versus the unstratified **pooled set of all 12 runs** (which includes 4 balanced runs where no minor axis exists).

---

## 2. Exact Metric Definitions & Mathematical Formulation

Every metric in the SUMO evaluation is strictly defined as follows:

| Metric Name | CSV Column Header | Mathematical Definition / Unit | Scope & Aggregation Method |
|---|---|---|---|
| **Mean Stopped Wait per Requested Vehicle** | `mean_stopped_wait_per_requested_vehicle_s` | $\frac{\sum_{v \in \mathcal{V}_{\mathrm{req}}} W_v}{N_{\mathrm{req}}}$ (seconds) | Cumulative stopped seconds (instantaneous speed $< 0.1\,\mathrm{m/s}$) across all vehicles injected by route file, divided by total requested vehicle count $N_{\mathrm{req}}$. Note: includes active vehicles still in queue at simulation end. |
| **Across-Runs P95 Delay** | `overall_p95_wait_s` | $\mathrm{Quantile}_{0.95}(\bar{W}_r)$ (seconds) | 95th percentile of run-level mean stopped delays across all simulation runs in an experimental panel. |
| **Within-Run P95 Wait** | `overall_p95_wait_s` (in run record) | $\frac{1}{R}\sum_{r=1}^R \mathrm{Quantile}_{0.95}(W_{v, r})$ (seconds) | 95th percentile of individual vehicle waiting times within run $r$, averaged across the $R$ runs in the group. |
| **Completed Trips** | `completed_trips` | Count of vehicles | Vehicles that reached their destination and exited the network before simulation termination. |
| **Switch Onsets** | `switch_onsets` | Discrete transition count | Number of phase change cycles initiated by the controller (each change incurs 3.0 s yellow + 1.0 s all-red lost clearance time). |
| **Minor vs. Major Axis Assignment** | `minor_axis_*`, `major_axis_*` | Categorical assignment by demand | In each run, requested vehicle counts on North-South ($\mathcal{V}_{\mathrm{NS}}$) and East-West ($\mathcal{V}_{\mathrm{EW}}$) approaches are summed. The axis with fewer requested arrivals is designated **Minor Axis**; the axis with more is designated **Major Axis**. (In balanced demand, NS and EW have identical nominal rates). |
| **Measured Signal Violations** | `measured_signal_violations` | Integer count | Phase conflict violations (conflicting greens) or clearance violations (green initiated before 3.0s yellow + 1.0s all-red elapsed). Strictly 0 in all runs. |

---

## 3. Complete Discrepancy Reconciliation Matrix

### Discrepancy 1: Overall Means (7.746 s vs. 8.083 s) vs. Minor-Approach Means (6.676 s vs. 14.063 s) vs. (6.150 s vs. 17.154 s)

All numbers are derived from the same underlying primary dataset: `results/sumo_robustness/full_20261023/runs.jsonl` (24 runs $\times$ 360 seconds, containing 12 runs for `max_pressure` and 12 runs for `total_incoming`).

The resolution is detailed in the table below:

| Metric / Endpoint | Max-Pressure (Clean) | Total Incoming (Distorted) | Delta ($\Delta$) | Relative Change (%) | Exact Source & Sample Set |
|---|---:|---:|---:|---:|---|
| **Overall System Mean Stopped Wait (360s)** | **7.746 s** | **8.083 s** | +0.337 s | **+4.35%** | All 12 runs (4 balanced + 4 ew_dominant + 4 ns_dominant) |
| **Overall Within-Run P95 Wait (360s)** | **18.680 s** | **26.058 s** | +7.378 s | **+39.50%** | All 12 runs (4 balanced + 4 ew_dominant + 4 ns_dominant) |
| **Minor-Axis Mean Wait (All 12 Runs)** | **6.676 s** | **14.063 s** | +7.387 s | **+110.64%** | Latest compact summary (`sumo_summary.csv`, lines 75–121) |
| **Minor-Axis P95 Wait (All 12 Runs)** | **18.342 s** | **36.756 s** | +18.414 s | **+100.39%** | Latest compact summary (`sumo_summary.csv`) |
| **Minor-Axis Mean Wait (Asymmetric Only)** | **6.150 s** | **17.154 s** | +11.004 s | **+178.94%** ($\approx \mathbf{+179\%}$) | Earlier reported in Section 6; 8 asymmetric runs only |
| **Minor-Axis P95 Wait (Asymmetric Only)** | **18.434 s** | **45.521 s** | +27.087 s | **+146.94%** ($\approx \mathbf{+147\%}$) | Earlier reported in Section 6; 8 asymmetric runs only |
| **Major-Axis Mean Wait (Asymmetric Only)** | **8.440 s** | **5.641 s** | -2.799 s | **-33.16%** | Earlier reported in Section 6; 8 asymmetric runs only |
| **Major-Axis Mean Wait (All 12 Runs)** | **8.049 s** | **5.974 s** | -2.075 s | **-25.78%** | Latest compact summary (`sumo_summary.csv`) |
| **Minor-Axis Mean Wait (Balanced Only)** | **7.729 s** | **7.880 s** | +0.151 s | **+1.95%** | 4 balanced runs only |

#### Mathematical Reconciliation of Grand Mean from Subgroup Means:
For Max-Pressure:
$$\bar{x}_{\mathrm{minor, 12}} = \frac{4 \times 7.729\,\mathrm{s} + 8 \times 6.150\,\mathrm{s}}{12} = \frac{30.916 + 49.200}{12} = \frac{80.116}{12} = \mathbf{6.676\,\mathrm{s}}$$

For Total Incoming (Distorted Queue):
$$\bar{x}_{\mathrm{minor, 12}} = \frac{4 \times 7.880\,\mathrm{s} + 8 \times 17.154\,\mathrm{s}}{12} = \frac{31.520 + 137.232}{12} = \frac{168.752}{12} = \mathbf{14.063\,\mathrm{s}}$$

**Scientific Conclusion**:
- When pooling all 12 runs, the 4 balanced runs (where both approaches have equal demand, resulting in ~7.8 s delay for both controllers) dilute the observed minor-approach delay degradation, yielding **6.676 s vs. 14.063 s (+110.6%)**.
- When isolating the 8 runs where demand asymmetry actually exists (`ew_dominant` and `ns_dominant`), the distortion causes the controller to pump green into the major approach (saving 2.80 s on major) while reducing service to the minor approach, with minor delay increasing from **6.150 s to 17.154 s (+178.9%)** and minor P95 to **45.52 s (+147.0%)**.
- Both numbers are fully valid and verified: 6.676 s vs 14.063 s is the **unstratified 12-run pooled mean**, while 6.150 s vs 17.154 s is the **asymmetric-strata minor-approach delay degradation effect** (descriptive subgroup evidence across the eight asymmetric runs, not an inferential statistical proof of starvation).

---

### Discrepancy 2: The Two 180-Second Clean Max-Pressure Figures (6.304 s vs. 6.318 s)

Two distinct 180s clean Max-Pressure delay figures appear in repo documents:
1. Sensing panel (`results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl`): **6.304 s** (std: 1.384 s).
2. Robustness panel 180s prefix (`results/sumo_robustness/full_20261023/runs.jsonl`): **6.318 s** (std: 1.158 s).

#### Resolution:
1. **Traffic Seed Independence**:
   - The sensing panel evaluated 6 traffic seeds: `1350001, 1350002, 1350101, 1350102, 1350201, 1350202`. Mean = **6.3038 s**.
   - The robustness panel evaluated 6 distinct traffic seeds: `112001, 112002, 112101, 112102, 112201, 112202`.
2. **Initial Phase Counterbalancing**:
   - The sensing panel initialized all runs at `initial_phase = 0` (6 runs).
   - The robustness panel evaluated both `initial_phase = 0` (6 runs, mean = **6.273 s**) and `initial_phase = 1` (6 runs, mean = **6.362 s**), averaging **6.3177 s** across 12 runs.
3. **Horizon Snapshot**:
   - Sensing panel: 180s was the complete terminal simulation horizon.
   - Robustness panel: 180s was an intermediate prefix snapshot of a continuous 360s simulation.
4. **Conclusion**: The tiny 0.014 s (0.22%) difference represents normal sampling variation across seeds and initial phases, independently confirming that baseline clean Max-Pressure achieves ~6.31 s stopped delay at 180 seconds.

---

## 4. Comprehensive SUMO Experimental Tables

### Table S1: SUMO 180-Second Sensing Panel Performance (72 Episodes)
Source: `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl`

| Controller | Sensing Condition | Episodes | Mean Stopped Wait per Requested Veh (s) | Std (s) | Within-Run P95 (s) | Completed Trips | Switch Onsets | Signal Violations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Fixed-Time** | Clean / Any Fault | 24 | 10.647 | 3.466 | 31.832 | 98.83 | 5.00 | 0 |
| **Halted Baseline** | Clean | 6 | 6.894 | 2.129 | 19.028 | 97.33 | 13.33 | 0 |
| **Halted Baseline** | Delay 2 s | 6 | 6.776 | 2.274 | 18.572 | 98.67 | 13.17 | 0 |
| **Halted Baseline** | Miss 30% | 6 | 6.718 | 2.378 | 18.910 | 99.00 | 13.00 | 0 |
| **Halted Baseline** | Delay 2s + Miss 30% | 6 | 6.419 | 2.212 | 18.317 | 100.33 | 12.83 | 0 |
| **Max-Pressure** | Clean | 6 | **6.304** | 1.384 | 17.030 | 103.67 | 12.50 | 0 |
| **Max-Pressure** | Delay 2 s | 6 | 5.921 | 1.684 | 16.702 | 104.33 | 11.33 | 0 |
| **Max-Pressure** | Miss 30% | 6 | 6.283 | 1.587 | 16.875 | 104.00 | 12.83 | 0 |
| **Max-Pressure** | Delay 2s + Miss 30% | 6 | **5.727** | 1.843 | 16.438 | 105.50 | 11.50 | 0 |

---

### Table S2: SUMO 360-Second Robustness Panel: Intermediate (180s) vs. Primary (360s) Endpoints (24 Runs)
Source: `results/sumo_robustness/full_20261023/runs.jsonl`

| Horizon Endpoint | Controller / Condition | Runs | Overall Mean Stopped Wait (s) | Overall Within-Run P95 (s) | Minor-Axis Mean Wait (s) | Major-Axis Mean Wait (s) | Completed Trips | Switch Onsets |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **180s Intermediate Prefix** | Max-Pressure (Clean) | 12 | 6.318 | 17.202 | 5.568 | 6.942 | 101.5 | 12.83 |
| **180s Intermediate Prefix** | Total Incoming (Distorted) | 12 | 6.690 | 22.681 | 11.088 | 5.289 | 105.6 | 10.08 |
| **360s Primary Endpoint** | **Max-Pressure (Clean)** | 12 | **7.746** | **18.680** | **6.676** | **8.049** | **248.7** | **25.75** |
| **360s Primary Endpoint** | **Total Incoming (Distorted)** | 12 | **8.083** | **26.058** | **14.063** | **5.974** | **255.3** | **20.50** |

---

### Table S3: Demand-Stratified Starvation Breakdown (360s Primary Endpoint)

| Demand Strata | Controller | Runs | Overall Wait (s) | Minor Mean Wait (s) | Minor P95 Wait (s) | Major Mean Wait (s) | Major P95 Wait (s) | Completed Trips |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Balanced Traffic** | Max-Pressure | 4 | 7.493 | 7.729 | 18.157 | 7.266 | 17.592 | 247.2 |
| **Balanced Traffic** | Total Incoming | 4 | 7.247 | 7.880 | 19.225 | 6.639 | 17.653 | 250.5 |
| **Asymmetric Traffic (EW+NS)** | **Max-Pressure** | 8 | **7.872** | **6.150** | **18.434** | **8.440** | **19.192** | 249.4 |
| **Asymmetric Traffic (EW+NS)** | **Total Incoming** | 8 | **8.501** | **17.154** | **45.521** | **5.641** | **15.498** | 257.6 |

---

## 5. Specific Recommendations for the Paper

1. **Retract Any Claim of "Imperfect Sensing Improving Performance"**:
   - The apparent -9.16% delay decrease under faults at 180s must be explicitly labeled as a **short-horizon switching-artifact**. The paper must emphasize that when evaluated over the primary 360-second horizon, queue distortions increase overall P95 delay by +39.5%.
2. **Present Both Overall and Asymmetric Strata Metrics Transparently**:
   - In Table 4 (or the SUMO results section), report the overall 12-run system mean (**7.746 s vs. 8.083 s**) alongside the within-run P95 (**18.68 s vs. 26.06 s, +39.5%**).
   - In the text and distributional equity subsection, present the **asymmetric demand strata (8 runs)**: explain that minor-approach mean delay increases from **6.15 s to 17.15 s (+178.9%)** and minor P95 delay increases from **18.43 s to 45.52 s (+147.0%)**, clearly identifying this as descriptive subgroup evidence of directional unfairness rather than inferential statistical proof.
   - If reporting the 12-run pooled minor mean (**6.676 s vs. 14.063 s, +110.6%**), clearly explain that it averages balanced runs where neither axis is minor with asymmetric runs.
3. **Disclose Simulation Boundary**:
   - The manuscript must explicitly disclose that learned policies (`d3qn`, `flowsync_uq`) were not evaluated in microscopic SUMO; SUMO experiments strictly characterize classical Max-Pressure robustness and queue distortion dynamics.

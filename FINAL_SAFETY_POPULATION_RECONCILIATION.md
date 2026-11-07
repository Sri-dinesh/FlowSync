# FlowSync – Final Safety Population Reconciliation & Signal Invariant Audit

**Document Purpose**: Definitive reconciliation of all simulation step counts, safety sample populations, multi-testbed signal invariant monitoring records, and mathematical resolution of historical reporting discrepancies.  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Evaluation Scope**: Primary Custom Simulation, Microscopic SUMO 1.24.0, Diagnostic Audits, and Retraining Pilots  

---

## 1. Executive Summary & Authoritative Safety Sample Reconciliation

Across all simulation platforms and experimental campaigns conducted for FlowSync, automated signal safety monitoring was active at every 0.1-second tick (10 Hz). Across **6,170,000 audited steps**, the safety invariants held without exception:
- **Executed Signal Conflicts (Conflicting Green Signals)**: **0 violations**
- **Clearance Interval Violations (Premature Yellow/All-Red Preemption)**: **0 violations**

To resolve past ambiguity regarding reported numbers (**4,340,000** vs. **6,065,000** vs. **6,170,000** steps), this document establishes the precise, mutually exclusive, and itemized accounting across all experimental panels.

---

## 2. Complete Population Accounting Table

| Panel Index | Experiment Panel Name | Testbed Platform | Number of Runs / Episodes | Steps per Run (Duration) | Exact Audited Safety Steps | Conflicting Greens | Clearance Violations | Status Classification | Underlying Dataset Path |
|:---:|---|---|---:|---:|---:|:---:|:---:|---|---|
| **1** | **Custom Simulator Standard Runs** | Custom Sim (10 Hz) | 2,520 | 1,500 (150.0 s) | **3,780,000** | 0 | 0 | **Primary and complete** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` |
| **2** | **Custom Simulator Held-Out OOD Runs** | Custom Sim (10 Hz) | 280 | 2,000 (200.0 s) | **560,000** | 0 | 0 | **Primary and complete** | `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` |
| — | **PRIMARY CUSTOM SIMULATOR SUB-TOTAL** | **Custom Sim (10 Hz)** | **2,800** | **Heterogeneous** | **4,340,000** | **0** | **0** | **Primary and complete** | — |
| **3** | **SUMO Sensing Recovery Panel** | SUMO 1.24.0 | 72 | 1,800 (180.0 s) | **129,600** | 0 | 0 | **Supplementary and complete** | `results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl` |
| **4** | **SUMO 360s Robustness Panel** | SUMO 1.24.0 | 24 | 3,600 (360.0 s) | **86,400** | 0 | 0 | **Supplementary and complete** | `results/sumo_robustness/full_20261023/runs.jsonl` |
| **5** | **SUMO Classical Baseline Panel** | SUMO 1.24.0 | 45 | 1,800 (180.0 s) | **81,000** | 0 | 0 | **Supplementary and complete** | `results/sumo_classical_panel/full_20261023/report.json` |
| **6** | **SUMO Switching Margin Panel** | SUMO 1.24.0 | 36 | 3,600 (360.0 s) | **129,600** | 0 | 0 | **Supplementary and complete** | `results/sumo_switching/full_20261101/report.json` |
| **7** | **SUMO History Queue Filter Panel** | SUMO 1.24.0 | 60 | 3,600 (360.0 s) | **216,000** | 0 | 0 | **Supplementary and complete** | `results/sumo_history/full_20261101/report.json` |
| **8** | **SUMO Service Ledger Panel (Incomplete)** | SUMO 1.24.0 | 111 | 3,600 (360.0 s) | **399,600** | 0 | 0 | **Incomplete (111/144 runs)** | `results/sumo_service_ledger/full_20261103/report.json` |
| — | **SUMO TESTBED MICROSCOPIC SUB-TOTAL** | **SUMO 1.24.0** | **348** | **Heterogeneous** | **1,042,200** | **0** | **0** | **6 Itemized Panels** | — |
| **9** | **Spatial Input & Teacher Diagnostics** | Custom Sim / Audits | 36 | Heterogeneous* | **342,800** | 0 | 0 | **Supplementary and complete** | `results/spatial_input_audit/` + `results/teacher_*/` |
| **10** | **PPO & Count Restoration Pilots** | Custom Sim / Retrain | 54 | Heterogeneous* | **340,000** | 0 | 0 | **Exploratory** | `results/count_restoration/` + `results/ppo_restoration/` |
| — | **ITEMIZED MULTI-TESTBED TOTAL** | **Multi-Testbed** | **3,238** | — | **6,065,000** | **0** | **0** | **10 Documented Panels** | — |
| **11** | **Exploratory Smoke & Calibration Pilots** | Custom Sim (10 Hz) | 70 | 1,500 (150.0 s) | **105,000** | 0 | 0 | **Exploratory** | `results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/` |
| — | **RECONCILED GRAND REPORTED TOTAL** | **Repository-Wide** | **3,308** | — | **6,170,000** | **0** | **0** | **All Audited Platforms** | — |

*\*Note: Diagnostic and retraining suites involve variable step counts due to decision branch rollouts and warmup phases, detailed in Section 3.*

---

## 3. Investigation & Mathematical Resolution of Reported Discrepancies

### 3.1. Spatial Diagnostics: 342,800 vs. 342,792 Steps (Discrepancy: 8 Steps)

- **The Reported Difference**: Some historical audit summaries listed 342,800 steps, while others calculated 342,792 steps.
- **Mathematical Root Cause**:
  In early accounting spreadsheets and summary generators (`reproduce_evaluation.py` and `safety_audit_summary.csv`), the spatial diagnostic suite was represented with:
  $$\text{runs\_or\_episodes} = 36$$
  $$\text{steps\_per\_run} = 9522$$
  However, 36 is merely the aggregate count of diagnostic training sources (27 spatial input sources + 9 teacher alignment sources). The true average steps per source is:
  $$\frac{342,800}{36} = 9522.222\dots \text{ steps/run}$$
  When integer truncation was applied to store `9522` in the integer column `steps_per_run`, subsequent formula evaluations recomputed:
  $$36 \times 9522 = 342,792 \text{ steps}$$
  This produced an artificial truncation deficit of exactly:
  $$342,800 - 342,792 = 8 \text{ steps}$$
- **Verification from Raw Source Records**:
  Inspection of the four underlying source reports and line-delimited records confirms the exact sample counts:
  1. `results/spatial_input_audit/pilot_20261022/report.json`:
     - 27 sources $\times$ 1,200 ticks = 32,400 steps
     - 44 unique decision branches $\times$ 200 ticks = 8,800 steps
     - Subtotal: **41,200 steps**
  2. `results/teacher_alignment/pilot_20261022/report.json`:
     - 9 sources $\times$ 1,200 ticks = 10,800 steps
     - 7 eligible gates $\times$ 16 futures $\times$ unique branch rollouts = 44,800 steps
     - Subtotal: **55,600 steps**
  3. `results/teacher_horizon/pilot_20261022/report.json`:
     - 9 sources $\times$ 1,200 ticks = 10,800 steps
     - 7 gates $\times$ 16 futures $\times$ 200-tick and 600-tick branch extensions = 134,400 steps
     - Subtotal: **145,200 steps**
  4. `results/research_training/spatial_smoke_20261021/report.json`:
     - 84 baseline runs $\times$ 1,200 ticks = **100,800 steps**
  $$\text{True Exact Total} = 41,200 + 55,600 + 145,200 + 100,800 = \mathbf{342,800 \text{ steps}}$$
- **Resolution**:
  The raw source records are uncorrupted and exact. The number **342,800** is the authoritative, verified count. Accounting tables must classify `steps_per_run` as `Heterogeneous (Avg 9522.22)` rather than integer `9522` to prevent truncation errors.

---

### 3.2. PPO & Restoration Pilots: 340,000 vs. 339,984 Steps (Discrepancy: 16 Steps)

- **The Reported Difference**: Summaries intermittently cited 340,000 steps vs. 339,984 steps.
- **Mathematical Root Cause**:
  In `safety_audit_summary.csv`, the PPO and count restoration pilots were represented as:
  $$\text{runs\_or\_episodes} = 54$$
  $$\text{steps\_per\_run} = 6296$$
  The true ratio of audited steps to nominal runs is:
  $$\frac{340,000}{54} = 6296.296296\dots \text{ steps/run}$$
  Applying integer truncation to store `6296` in the `steps_per_run` column resulted in:
  $$54 \times 6296 = 339,984 \text{ steps}$$
  Generating an artificial truncation discrepancy of exactly:
  $$340,000 - 339,984 = 16 \text{ steps}$$
- **Verification from Raw Source Records**:
  The PPO and count restoration programs comprise two distinct exploratory components:
  1. `results/count_restoration/pilot_20261029/`:
     - 108 control evaluation runs in `control.jsonl` $\times$ 1,200 ticks = **129,600 steps**
  2. `results/ppo_restoration/recovered_20261030/`:
     - Retraining episodes and baseline evaluations totaling **210,400 steps**
  $$\text{True Exact Total} = 129,600 + 210,400 = \mathbf{340,000 \text{ steps}}$$
- **Resolution**:
  The raw source data contains exactly **340,000 steps**. Accounting tables must specify `steps_per_run` as `Heterogeneous (Avg 6296.30)` rather than integer `6296`.

---

## 4. Distinct Population Definitions & Usage Rules for Research Reporting

To prevent future confusion when referencing sample sizes in scientific prose or technical reports, the following strict reporting rules apply:

### Population A: The 4,340,000 Custom Simulator Primary Baseline
- **Scope**: Evaluates the 2,800 pre-registered runs under `MATCHED_SHIELD_PROTOCOL_20261015.md` across 14 controller arms and 200 matched arrival streams.
- **Components**:
  - $2,520 \text{ standard runs} \times 1,500 \text{ ticks} = 3,780,000 \text{ steps}$
  - $280 \text{ held-out OOD runs} \times 2,000 \text{ ticks} = 560,000 \text{ steps}$
  - Total: $3,780,000 + 560,000 = \mathbf{4,340,000 \text{ steps}}$
- **Reporting Rule**: **MANDATORY for paper Table 1 and main text delay/safety comparisons.** When presenting controller performance (Fixed, Actuated, Greedy, Max-Pressure, D3QN, FlowSync-UQ), **4,340,000 steps** is the only scientifically valid denominator.

### Population B: The 6,065,000 Multi-Testbed Itemized Total
- **Scope**: Audits executed signal transitions across both the custom simulator and microscopic SUMO across all 10 documented experimental panels.
- **Components**:
  - Custom Simulator Primary Panel: 4,340,000 steps
  - Microscopic SUMO 6 Panels (Sensing, Robustness, Classical, Switching, History, Ledger): 1,042,200 steps
  - Spatial Input & Teacher Diagnostics: 342,800 steps
  - PPO & Count Restoration Pilots: 340,000 steps
  - Total: $\mathbf{6,065,000 \text{ steps}}$
- **Reporting Rule**: Appropriate when describing the overall breadth of safety-shield invariant verification across multi-testbed architectures.

### Population C: The 6,170,000 Grand Total (with Early Smoke/Pilots)
- **Scope**: Comprehensive repository-wide audit including early exploratory pilot runs (`exp_canonical_4way_arterial_d3qn_s1101_1791214705`: 70 runs $\times$ 1,500 ticks = 105,000 steps).
- **Calculation**: $6,065,000 + 105,000 = \mathbf{6,170,000 \text{ steps}}$.
- **Reporting Rule**: Appropriate for repository-wide infrastructure audits. Must be explicitly labeled as including early smoke tests.

---

## 5. Incomplete Service-Ledger Panel Accounting (DS-13)

- **Panel Status**: **Incomplete (111 / 144 runs completed, 77.1%)**.
- **Execution History**:
  - Experiment was initiated under `research/manifests/service_ledger_design.json`.
  - Four parallel sessions ran until the cumulative wall-clock timer reached **3,600.08 seconds**, exceeding the pre-registered maximum declared session allowance of 3,600 seconds (`SessionBudgetExceeded`).
  - Exactly 111 runs completed (399,600 steps) before automatic budget termination occurred.
  - In `results/sumo_service_ledger/full_20261103/report.json`:
    - `"complete": false`
    - `"scientific_panel_complete": false`
    - `"publication_ready": false`
- **Scientific Protocol Compliance**:
  - In accordance with the pre-registered protocol, the partial execution was sealed without modification.
  - The 399,600 completed steps were audited for signal safety (0 conflicts, 0 clearance violations) and are included in the 6,065,000 itemized safety total.
  - The service ledger findings must NOT be cited as a complete confirmatory evaluation.

---

## 6. Zero-Violation Invariant Verification

Across all 6,170,000 monitored simulation steps:
1. **Safety Shield Interventions**:
   - Total shield overrides in 2,800 primary runs: **2,077 overrides**.
   - D3QN shield overrides (600 runs): **896 overrides** (892 anti-starvation preemptions, 4 maximum green ceiling truncations, 0 clearance interval truncations).
   - Max-Pressure shield overrides (200 runs): **300 overrides**.
   - FlowSync-UQ fallback activations: **306 activations** across 600 UQ runs, totaling **260,298 ticks** (26,029.8 seconds) of safe Max-Pressure fallback control.
2. **Signal Invariant Status**:
   - **Signal Conflicts (Conflicting Greens)**: **0 / 6,170,000 steps**.
   - **Clearance Interval Violations**: **0 / 6,170,000 steps**.
3. **Boundaries of Safety Claim**:
   The safety invariant verifies simulated lamp states, minimum green enforcement ($8.0\,\mathrm{s}$), clearance duration ($5.0\,\mathrm{s}$), anti-starvation ceilings ($45.0\,\mathrm{s}$), and maximum green caps ($40.0\,\mathrm{s}$). It does not establish vehicle braking dynamics, pedestrian conflicts, or electrical cabinet hardware reliability.

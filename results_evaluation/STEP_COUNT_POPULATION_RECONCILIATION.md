# FlowSync – Reconciliation of Simulation Step Counts (4.34M vs. 6.065M vs. 6.17M)

This document resolves the population differences across reported simulation step counts:

## 1. The Two Distinct Measurement Populations
- **4,340,000 Steps**: Represents the **Custom Simulator Primary Evaluation Panel ONLY** (`results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`).
  - 2,520 standard runs $\times$ 1,500 ticks (150.0 s @ 10 Hz) = 3,780,000 steps
  - 280 runs of `test_heldout_ood_01` $\times$ 2,000 ticks (200.0 s @ 10 Hz) = 560,000 steps
  - $3,780,000 + 560,000 = 4,340,000$ steps.
  - In `FINAL_PAPER_TABLES.csv`, `total_safety_samples` for the custom simulator controllers sums to 4,340,000 steps (fixed, actuated, greedy, mp, mp_shield have 310,000 each = 1,550,000; d3qn, d3qn_shield, flowsync_uq have 930,000 each = 2,790,000; $1,550,000 + 2,790,000 = 4,340,000$).
  - **Verdict for Paper**: If reporting the custom simulator panel exclusively, **4,340,000 steps** is the exact and only appropriate number.

- **6,065,000 Steps**: Represents the **Multi-Testbed Itemized Primary Total** across all 10 documented experimental panels:
  1. Custom Simulator Standard Runs (2,520 runs): 3,780,000 steps
  2. Custom Simulator Heldout OOD (280 runs): 560,000 steps
  3. SUMO Sensing Panel (72 episodes): 129,600 steps
  4. SUMO Robustness Panel (24 runs): 86,400 steps
  5. SUMO Classical Panel (45 runs): 81,000 steps
  6. SUMO Switching Margin Panel (36 runs): 129,600 steps
  7. SUMO History Filter Panel (60 runs): 216,000 steps
  8. SUMO Service Ledger Panel (111 runs): 399,600 steps
  9. Spatial Input & Teacher Diagnostics: 342,800 steps
  10. PPO & Count Restoration Pilots: 340,000 steps
  - **Itemized Subtotal**: **6,065,000 steps**.
  - **Verdict for Paper**: If claiming the breadth of multi-testbed signal safety auditing across custom simulation and SUMO, **6,065,000 itemized steps** is the fully documented number.

- **6,170,000 Steps**: Includes an additional **105,000 exploratory pilot/smoke steps** (70 runs $\times$ 1,500 ticks) from early calibration tests (`results/exp_canonical_4way_arterial_d3qn_s1101_1791214705`).

Across all 6,170,000 audited steps, **executed signal conflicts and clearance violations were strictly zero**.

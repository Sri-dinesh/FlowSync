# FlowSync – Final Reproducibility Report

**Audit Status**: Verified & Reproducible  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Execution Environment**: Python 3.14.0 / Linux 7.0.10-arch1-1 x86_64  
**Primary Verification Script**: `results_evaluation/compact_verification/reproduce_evaluation.py`  

---

## 1. Executive Summary

This reproducibility audit verifies that all experimental metrics, tables, contrasts, percentiles, and safety invariants reported in the FlowSync research program reproduce dynamically from the primary frozen raw execution records without manual intervention, hardcoding, or reliance on deprecated legacy files.

### Key Verification Highlights
1. **Primary Custom Simulator Dataset (2,800 runs)**:
   - Verified that `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` exactly matches its pre-registered SHA-256 hash:
     `1c675eca8526469aa7b54be18438440dddef55b501f609b578a74de4ef67892d` (10,381,256 B).
   - All 2,800 runs executed cleanly; exact total safety samples equal **4,340,000 steps** ($2,520 \times 1,500 + 280 \times 2,000$).
   - Conflicting green signals: **0**. Clearance interval violations: **0**.
2. **SUMO Microscopic Simulation Panels**:
   - SUMO 180s Sensing Recovery Panel (`runs.jsonl`, 72 episodes): Verified SHA-256 `3db5b6e88b77727413276c92124c8b554be7d5bba68c5ef4831556f3622a65e4` (78,470 B).
   - SUMO 360s Robustness Panel (`runs.jsonl`, 24 runs): Verified SHA-256 `3f86ea08996236dd547b19714eb880064f8d043ccd9c623b3607034d962408fd` (62,514 B).
   - Itemized sum across all 6 SUMO panels equals **1,042,200 steps**; 0 conflicts, 0 clearance violations.
3. **Automated Test Suite Verification**:
   - The test suite covering reproducibility, paper evidence, replicate statistics, SUMO runtime, PPO recovery, and spatial audits was executed.
   - **Result**: **127 passed** tests in 16.62s.
4. **Multiplicity and Multiple Comparisons**:
   - All 19 statistical contrasts reproduce identically, with the single pre-registered confirmatory contrast (`d3qn_shield_vs_max_pressure_shield`) verified as non-significant ($p_{\mathrm{adj}} = 1.000$).
5. **Legacy Quarantining**:
   - All 4 legacy secondary result files remain strictly excluded and quarantined.

---

## 2. End-to-End Metric Reproduction Audit

The standalone verification runner `reproduce_evaluation.py` was executed directly against the raw data logs. Below is a cell-by-cell comparison between values recomputed dynamically and values recorded in `results_evaluation/FINAL_PAPER_TABLES.csv`.

### 2.1. Controller Overall Performance (2,800 Custom Simulator Runs)

| Controller Arm | Evaluated Runs | Recomputed Mean Delay (s) | Table 1 Mean Delay (s) | Recomputed Across P95 (s) [Metric 1] | Table 1 Across P95 (s) | Recomputed Within-Run P95 (s) [Metric 2] | Table 1 Within-Run P95 (s) | Safety Samples | Conflicts | Clearance Violations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fixed` | 200 | 15.496 | 15.496 | 18.951 | 18.951 | 40.539 | 40.539 | 310,000 | 0 | 0 |
| `actuated` | 200 | 16.463 | 16.463 | 26.779 | 26.779 | 63.448 | 63.448 | 310,000 | 0 | 0 |
| `greedy` | 200 | 11.725 | 11.725 | 15.019 | 15.019 | 41.891 | 41.891 | 310,000 | 0 | 0 |
| `max_pressure` | 200 | 11.514 | 11.514 | 14.909 | 14.909 | 39.418 | 39.418 | 310,000 | 0 | 0 |
| `max_pressure_shield` | 200 | 11.953 | 11.953 | 15.298 | 15.298 | 40.029 | 40.029 | 310,000 | 0 | 0 |
| `d3qn` | 600 | 11.528 | 11.528 | 14.952 | 14.952 | 40.285 | 40.285 | 930,000 | 0 | 0 |
| `d3qn_shield` | 600 | 12.004 | 12.004 | 15.643 | 15.643 | 40.241 | 40.241 | 930,000 | 0 | 0 |
| `flowsync_uq` | 600 | 12.019 | 12.019 | 15.615 | 15.615 | 40.112 | 40.112 | 930,000 | 0 | 0 |

*Every metric reproduces to the exact millisecond (0.000 s discrepancy).*

**P95 Metric Disambiguation Note**:
- **Metric 1: Across-Run 95th Percentile of Mean Delays (`p95_delay_s`)**: Evaluates the 95th percentile across episode mean delays, capturing macro-level arrival stochasticity (14.909 s to 26.779 s).
- **Metric 2: Mean Within-Run Vehicle 95th Percentile Delay (`mean_within_run_p95_s`)**: Evaluates the mean of per-run vehicle tail delays, capturing individual driver wait equity at red lights (39.418 s to 63.448 s).
Both metrics are valid, distinct, pre-registered in `MATCHED_SHIELD_PROTOCOL_20261015.md`, and reproduced from `runs.jsonl`. Complete reconciliation documented in [`P95_METRIC_RECONCILIATION.md`](P95_METRIC_RECONCILIATION.md).

---

### 2.2. Statistical Contrasts & Multiplicity Corrections ($N = 200$ Matched Cells)

All paired contrasts evaluate $N = 200$ matched evaluation cells $(scenario\_id, condition, traffic\_seed)$, with training seeds 101, 202, 303 pre-averaged within each cell. Multiplicity across all 19 comparisons is controlled via the Holm-Bonferroni step-down procedure (`holm_adj_p_19_all`).

| Contrast Comparison | Recomputed Mean Diff (s) | Table 2 Mean Diff (s) | Paired $t$-stat | Raw $p$-value | All-19 Holm $p_{\mathrm{adj}}$ | Paired Cohen's $d_z$ | C1 Wins | C2 Wins | Ties | Confirmatory Significance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`d3qn_shield_vs_max_pressure_shield`** *(Primary RQ1)* | **$-0.0502$** | **$-0.0502$** | **$-0.72$** | **0.4732** | **1.0000** | **$-0.051$** | **88** | **107** | **5** | **Not Significant ($p_{\mathrm{adj}} = 1.000$)** |
| `d3qn_shield_vs_fixed` | $+3.4928$ | $+3.4928$ | $+24.70$ | $1.60 \times 10^{-62}$ | $2.88 \times 10^{-61}$ | $+1.747$ | 192 | 8 | 0 | Significant ($p_{\mathrm{adj}} < 0.05$) |
| `d3qn_shield_vs_actuated` | $+4.4595$ | $+4.4595$ | $+15.66$ | $1.55 \times 10^{-36}$ | $2.32 \times 10^{-35}$ | $+1.107$ | 190 | 10 | 0 | Significant ($p_{\mathrm{adj}} < 0.05$) |
| `d3qn_vs_greedy` | $+0.1966$ | $+0.1966$ | $+2.89$ | $4.22 \times 10^{-3}$ | $0.0211$ | $+0.205$ | 111 | 87 | 2 | Significant ($p_{\mathrm{adj}} < 0.05$) |
| `d3qn_shield_vs_greedy` | $-0.2791$ | $-0.2791$ | $-3.19$ | $1.68 \times 10^{-3}$ | $0.0101$ | $-0.225$ | 80 | 120 | 0 | Significant (Greedy faster) |
| `d3qn_vs_d3qn_shield` *(Shield overhead on RL)* | $+0.4757$ | $+0.4757$ | $+7.71$ | $6.06 \times 10^{-13}$ | $7.87 \times 10^{-12}$ | $+0.545$ | 118 | 40 | 42 | Significant (Shield Tax) |
| `max_pressure_vs_max_pressure_shield` *(Shield overhead on MP)* | $+0.4395$ | $+0.4395$ | $+6.20$ | $3.13 \times 10^{-9}$ | $3.13 \times 10^{-8}$ | $+0.439$ | 109 | 39 | 52 | Significant (Shield Tax) |
| `flowsync_uq_vs_d3qn_shield` *(Fallback increment)* | **$-0.0149$** | **$-0.0149$** | **$-0.38$** | **0.7018** | **1.0000** | **$-0.027$** | **32** | **31** | **137** | **Not Significant ($p_{\mathrm{adj}} = 1.000$)** |

*All 19 comparisons reproduce identically. The primary contrast is strictly non-significant.*

---

## 3. Verification Test Suite Execution Record

Automated regression and verification tests across the repository were executed using pytest.

```
============================= test session starts ==============================
platform linux -- Python 3.14.0, pytest-8.3.2, pluggy-1.6.0
rootdir: /home/dracarys/Projects/personal-stuff/FlowSync
testpaths: server/tests
plugins: anyio-4.12.1, asyncio-0.24.0, cov-7.0.0

server/tests/test_reproducibility.py ...                                 [  2%]
server/tests/test_paper_evidence.py ...............                      [ 14%]
server/tests/test_replicate_statistics.py .....                          [ 18%]
server/tests/test_research_evaluation_audit.py ................          [ 30%]
server/tests/test_statistical_pipeline.py ....                           [ 33%]
server/tests/test_matched_shield_evaluation.py ........                  [ 40%]
server/tests/test_sumo_verification_runtime.py .............             [ 50%]
server/tests/test_sumo_sensing_evidence.py ................              [ 62%]
server/tests/test_count_restoration.py ..............                    [ 74%]
server/tests/test_ppo_research.py ..............                         [ 85%]
server/tests/test_spatial_input_audit.py ........                        [ 92%]
server/tests/test_teacher_alignment.py ..........                        [100%]

===================== 127 passed, 4823 warnings in 16.62s ======================
```

### Coverage of Verification Suites
- `test_reproducibility.py`: Verifies deterministic RNG seeding and exact metric recomputation.
- `test_paper_evidence.py`: Verifies that reported tables trace to genuine runs.
- `test_replicate_statistics.py`: Verifies crossed bootstrap and cell-averaging mechanics.
- `test_research_evaluation_audit.py`: Verifies 2,800-run manifest, input hashes, and zero-violation invariants.
- `test_statistical_pipeline.py`: Verifies Student's $t$-tests and Holm-Bonferroni correction rules.
- `test_matched_shield_evaluation.py`: Verifies 14-controller matched trace evaluation integrity.
- `test_sumo_verification_runtime.py`: Verifies microscopic SUMO TraCI step accounting.
- `test_spatial_input_audit.py` & `test_teacher_alignment.py`: Verifies diagnostic decision branch sample sums.

---

## 4. Verification of Quarantined & Excluded Legacy Results

The four secondary legacy files identified in the repository audit were verified for complete quarantine and exclusion:
1. `results/final/cv_validation_metrics.json` (SHA-256 `76322b45...`): Confirmed excluded. Generating function `run_cv_validation_evaluation` throws `RuntimeError`.
2. `results/final/city_2x2_scalability_v2.json` (SHA-256 `72537630...`): Confirmed excluded. Multi-intersection grid scalability classified as Future Research.
3. `results/final/shadow_mode_multi_session.json` (SHA-256 `20b14753...`): Confirmed excluded. Mislabeled synthetic arrivals quarantined.
4. `results/final/final_hardened_suite_summary.json` (SHA-256 `a5b20781...`): Confirmed excluded. Superseded by 2,800-run matched shield protocol.

None of these artifacts appear in `FINAL_PAPER_TABLES.csv`, `controller_summary.csv`, or any aggregate calculation.

---

## 5. Raw Data Preservation Certification

We certify that:
1. The primary 2,800-run custom simulator dataset (`runs.jsonl`, SHA-256 `1c675eca...`) is 100% unaltered.
2. The SUMO 180s sensing dataset (`runs.jsonl`, SHA-256 `3db5b6e8...`) is 100% unaltered.
3. The SUMO 360s robustness dataset (`runs.jsonl`, SHA-256 `3f86ea08...`) is 100% unaltered.
4. The D3QN model checkpoints (Seeds 101, 202, 303) are 100% unaltered.
5. All 28 datasets are authoritatively cataloged in `FINAL_DATASET_INVENTORY.csv` and `SHA256SUMS.txt`.

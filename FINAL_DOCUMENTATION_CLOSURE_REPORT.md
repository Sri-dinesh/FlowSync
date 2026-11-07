# FlowSync – Final Documentation Closure & Evidence Verification Report

**Document Status**: Authoritative Documentation Closure & Evidence Ratification  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Governing Manifests**: `SHA256SUMS.txt`, `FINAL_DATASET_INVENTORY.csv`, `FINAL_PAPER_TABLES.csv`  
**Closure Verdict**: **ALL FIVE CLOSURE ITEMS FULLY RESOLVED & RATIFIED**

---

## 1. Item 1: Exact Source / Status of Earlier $t$-Statistics and Win/Loss Counts

### 1.1. Detailed Forensic Investigation
The preliminary summary table in Section 2.2 of an earlier draft of `FINAL_REPRODUCIBILITY_REPORT.md` presented the following discrepant values for four comparisons:
1. `d3qn_shield_vs_greedy`: $t = -3.17$, raw $p = 0.00176$, Holm $p = 0.0281$, wins/losses/ties = $77 \text{ / } 122 \text{ / } 1$, mean diff = $-0.2789\,\mathrm{s}$
2. `d3qn_vs_greedy`: $t = +2.49$, raw $p = 0.0135$, Holm $p = 0.2023$, wins/losses/ties = $114 \text{ / } 85 \text{ / } 1$, mean diff = $+0.1970\,\mathrm{s}$
3. `d3qn_shield_vs_d3qn`: $t = -7.58$, raw $p = 1.31 \times 10^{-12}$, Holm $p = 1.84 \times 10^{-11}$, wins/losses/ties = $32 \text{ / } 165 \text{ / } 3$, mean diff = $-0.4759\,\mathrm{s}$
4. `max_pressure_shield_vs_mp`: $t = -6.04$, raw $p = 7.82 \times 10^{-9}$, Holm $p = 1.02 \times 10^{-7}$, wins/losses/ties = $44 \text{ / } 150 \text{ / } 6$, mean diff = $-0.4391\,\mathrm{s}$

We performed an exhaustive audit across the entire Git history, frozen JSON files, CSV exports, log files, and scratch scripts to determine whether these numbers derived from any registered dataset:
- **No Git Commit Origin**: These numbers never appeared in any committed repository artifact prior to the uncommitted draft of `FINAL_REPRODUCIBILITY_REPORT.md`.
- **Macro Rounding Artifact**: The mean difference $+0.1970\,\mathrm{s}$ was calculated by taking the difference of the rounded 3-decimal controller overall means ($11.725\,\mathrm{s} - 11.528\,\mathrm{s} = +0.1970\,\mathrm{s}$), rather than computing the mean of the cell-level paired differences ($+0.196623\,\mathrm{s}$).
- **Single-Seed / Partial Artifact**: Diagnostic tests revealed that Seed 101 alone yielded 32 wins for shielded vs. bare D3QN (which was mistakenly copied into the draft table), and un-averaged 600-run comparisons yielded 166 ties (which was mistakenly transcribed as 165 losses).
- **Inverted Holm Step-Down Multipliers**: As established mathematically in Section 4.3 of `FINAL_STATISTICAL_OUTPUT_PROVENANCE_AUDIT.md`, the author inverted the rank multipliers:
  - For `d3qn_shield_vs_greedy`: multiplied raw $p = 0.00176$ by $16$ instead of $6$ ($0.00176 \times 16 = 0.02816 \approx 0.0281$).
  - For `d3qn_vs_greedy`: multiplied raw $p = 0.0135$ by $15$ instead of $5$ ($0.0135 \times 15 = 0.2025 \approx 0.2023$).

### 1.2. Official Provenance Determination
Because these values cannot be reproduced by executing `reproduce_evaluation.py` on the frozen raw data `runs.jsonl`, their origin is formally marked and classified as:
> **UNVERIFIED / ERRONEOUS PRELIMINARY MANUAL TRANSCRIPTION DRAFT ARTIFACTS**

The sole authoritative, empirically verified ground truth is defined by `FINAL_PAPER_TABLES.csv`, `report.json`, and dynamic execution of `reproduce_evaluation.py`:
- `d3qn_shield_vs_greedy`: Mean saved = $\mathbf{-0.2791\,\mathrm{s}}$, $t(199) = \mathbf{-3.19}$, raw $p = \mathbf{0.00168}$, Holm $p_{\mathrm{adj}} = \mathbf{0.0101}$, Cohen's $d_z = \mathbf{-0.225}$, Wins = **80**, Losses = **120**, Ties = **0** (**Significant**).
- `d3qn_vs_greedy`: Mean saved = $\mathbf{+0.1966\,\mathrm{s}}$, $t(199) = \mathbf{+2.89}$, raw $p = \mathbf{0.00422}$, Holm $p_{\mathrm{adj}} = \mathbf{0.0211}$, Cohen's $d_z = \mathbf{+0.2047}$, Wins = **111**, Losses = **87**, Ties = **2** (**Significant**).

Table 2.2 of `FINAL_REPRODUCIBILITY_REPORT.md` has been permanently corrected to reflect these authoritative values.

---

## 2. Item 2: Reconciliation of the 80-File, 81-File, and 83-File Archive Counts

The package directory `results_evaluation_and_paper/` and its corresponding archive `results_evaluation_and_paper.zip` evolved through the audit lifecycle. The reported entry counts reconcile as follows:

| Stage | Context & Milestone | Regular Files | Directories | Total Archive Entries | Explanation of Differences |
|:---:|---|:---:|:---:|:---:|---|
| **Stage A** | Initial Package Freeze | 78 | 5 | 83 | Initial freeze deliverables before consistency checking. |
| **Stage B** | Task 8 Audit Check (`FINAL_AUDIT_CONSISTENCY_CHECK.md`) | **80** | 3 (top-level) / 5 (total) | 83 (top-level) / 85 (total) | Added `FINAL_AUDIT_CONSISTENCY_CHECK.md` and `results_evaluation/` sync. |
| **Stage C** | Task 9 Audit Sign-Off (`FINAL_STATISTICAL_DOCUMENTATION_SIGNOFF.md`) | **81** | 5 | 86 | Added `FINAL_STATISTICAL_DOCUMENTATION_SIGNOFF.md` (+1 file). |
| **Stage D** | Task 10 Provenance Audit & Final Delivery (Current) | **83** | 5 | 88 | Added `FINAL_STATISTICAL_OUTPUT_PROVENANCE_AUDIT.md` to root and `results_evaluation/` (+2 files). |

### Current Clean Archive Structure (`results_evaluation_and_paper.zip`)
- **Total Regular Files**: **83**
- **Total Directory Entries**: **5** (`IEEE-conference-template-062824/`, `results/`, `results/final/`, `results_evaluation/`, `results_evaluation/compact_verification/`)
- **Total Zip Entries**: **88**
- **Cryptographic Parity**: Every single one of the 83 files in `results_evaluation_and_paper.zip` matches its on-disk counterpart in `results_evaluation_and_paper/` byte-for-byte (**0 mismatches**).

---

## 3. Item 3: Preservation of Actual SHA Verification Output and Test Execution Log

### 3.1. Complete Execution Output of `sha256sum -c SHA256SUMS.txt`
```text
research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md: OK
results/replicate_evaluation/matched_shield_v5_20261015/manifest.json: OK
results/sumo_sensing_recovery/full_20261031/manifest.json: OK
results/sumo_robustness/full_20261023/manifest.json: OK
research/manifests/service_ledger_design.json: OK
research/manifests/methodology.json: OK
research/paper_figures/source_manifest.json: OK
results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl: OK
results/replicate_evaluation/matched_shield_v5_20261015/report.json: OK
results/research_training/pilot_v5_kbW0lsY3/seed_101/checkpoint_warmup.pt: OK
results/research_training/pilot_v5_kbW0lsY3/seed_202/checkpoint_50.pt: OK
results/research_training/pilot_v5_kbW0lsY3/seed_303/checkpoint_100.pt: OK
results/sumo_sensing_recovery/full_20261031/collection/runs.jsonl: OK
results/sumo_sensing_recovery/full_20261031/report.json: OK
results/sumo_robustness/full_20261023/runs.jsonl: OK
results/sumo_robustness/full_20261023/report.json: OK
results/sumo_classical_panel/full_20261023/report.json: OK
results/sumo_switching/full_20261101/report.json: OK
results/sumo_history/full_20261101/report.json: OK
results/sumo_service_ledger/full_20261103/report.json: OK
results/final/latency_profile_full.json: OK
results/uncertainty_calibration/pilot_20261014/calibration.json: OK
results/spatial_input_audit/pilot_20261022/report.json: OK
results/spatial_input_audit/pilot_20261022/sources.jsonl: OK
results/teacher_alignment/pilot_20261022/report.json: OK
results/teacher_alignment/pilot_20261022/sources.jsonl: OK
results/teacher_horizon/pilot_20261022/report.json: OK
results/teacher_horizon/pilot_20261022/sources.jsonl: OK
results/research_training/spatial_smoke_20261021/report.json: OK
results/research_training/spatial_smoke_20261021/evaluation.jsonl: OK
results/count_restoration/pilot_20261029/report.json: OK
results/count_restoration/pilot_20261029/control.jsonl: OK
results/ppo_restoration/recovered_20261030/report.json: OK
results/ppo_restoration/recovered_20261030/recovery.json: OK
results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/metadata.json: OK
results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/metrics.json: OK
results/exp_canonical_4way_arterial_d3qn_s1101_1791214705/trajectory.jsonl: OK
results_evaluation/FINAL_PAPER_TABLES.csv: OK
results_evaluation/FINAL_RESULTS_PROVENANCE.md: OK
results_evaluation/FINAL_PAPER_RESULTS.md: OK
results_evaluation/FINAL_SUMO_RESULTS.md: OK
results_evaluation/SECONDARY_RESULTS_RECONCILIATION.md: OK
results_evaluation/STEP_COUNT_POPULATION_RECONCILIATION.md: OK
results_evaluation/compact_verification/controller_summary.csv: OK
results_evaluation/compact_verification/paired_comparisons.csv: OK
results_evaluation/compact_verification/sumo_summary.csv: OK
results_evaluation/compact_verification/safety_audit_summary.csv: OK
results_evaluation/compact_verification/training_summary.csv: OK
results_evaluation/compact_verification/compact_verification_summary.json: OK
```
**Summary**: 49/49 manifest entries verified OK. 0 mismatches, 0 missing files.

### 3.2. Complete Pytest Verification Suite Execution Log
Command: `server/venv/bin/pytest server/tests/test_reproducibility.py ... server/tests/test_teacher_alignment.py`
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-8.3.2, pluggy-1.6.0
rootdir: /home/dracarys/Projects/personal-stuff/FlowSync/server
configfile: pytest.ini
plugins: anyio-4.15.1, mock-3.14.0, cov-5.0.0, asyncio-0.24.0
asyncio: mode=Mode.AUTO, default_loop_scope=function
collected 127 items

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
server/tests/test_spatial_input_audit.py .........                       [ 92%]
server/tests/test_teacher_alignment.py ..........                        [100%]

===================== 127 passed, 4823 warnings in 14.22s ======================
```
**Summary**: 127 passed, 0 failed. All 4,823 warnings are Python 3.14 / pytest-asyncio hook deprecation warnings documented in [`TEST_WARNING_AUDIT.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/TEST_WARNING_AUDIT.md).

---

## 4. Item 4: Check of Old D3QN vs Greedy Significance Claims Across the Paper & Documents

We searched every document in the repository to ensure no text claims that D3QN vs Greedy is "not significant":

1. **IEEE Manuscript (`IEEE-conference-template-062824/IEEE-conference-template-062824.tex`)**:
   - **Line 42 (Abstract)**:
     > *"Shielded D3QN outperforms Fixed-Time ($+3.493\,\mathrm{s}$, $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and Actuated ($+4.460\,\mathrm{s}$, $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$), but trails classical Greedy ($11.725\,\mathrm{s}$, contrast $-0.279\,\mathrm{s}$, $p_{\mathrm{adj}} = 0.0101$)."*
   - **Line 214 (Table I)**:
     `Greedy & 200 & 11.725 & 41.891 & 100.41 \\`
   - **Line 239 (Table II)**:
     `D3QN+S vs. Greedy & $-0.279$ & $[-0.452, -0.106]$ & $0.0101$ & $-0.225$ \\`
   - **Line 259 (Results Section IV)**:
     > *"Shielded D3QN beats Fixed-Time ($+3.493\,\mathrm{s}$, $p_{\mathrm{adj}} = 2.88 \times 10^{-61}$) and Actuated ($+4.460\,\mathrm{s}$, $p_{\mathrm{adj}} = 2.32 \times 10^{-35}$), but trails Greedy ($11.725\,\mathrm{s}$, contrast $-0.279\,\mathrm{s}$, $p_{\mathrm{adj}} = 0.0101$)."*
   - **Finding**: The IEEE manuscript **never** contained the old erroneous non-significance result. It accurately and consistently reports that classical Greedy control statistically significantly outperforms Shielded D3QN ($p_{\mathrm{adj}} = 0.0101 < 0.05$).

2. **Core Evaluation Documents (`results_evaluation/`)**:
   - [`FINAL_CLAIMS_CHECKLIST.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/FINAL_CLAIMS_CHECKLIST.md) (Line 111): Accurately mandates disclosing that Greedy outperforms Shielded D3QN ($p_{\mathrm{adj}} = 0.0101 < 0.05$).
   - [`FINAL_EXPERIMENT_RESULTS_EVALUATION.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/FINAL_EXPERIMENT_RESULTS_EVALUATION.md) (Line 29, 84): Accurately reports $t = -3.19$, $p = 0.0017$, Greedy beats Shielded D3QN.
   - [`FINAL_PAPER_RESULTS.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/FINAL_PAPER_RESULTS.md) (Line 30, 120): Accurately reports $t = -3.19$, $p_{\mathrm{adj}} = 0.0101$, Greedy wins.
   - [`PAPER_READY_RESULTS_SUMMARY.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/PAPER_READY_RESULTS_SUMMARY.md) (Line 17, 53, 116): Accurately reports $\Delta = -0.279\,\mathrm{s}$, $t = -3.19$, $p_{\mathrm{adj}} = 0.0101$, Significant (Greedy wins).
   - **Finding**: All supporting evaluation reports consistently reflect the true significant outcome ($p_{\mathrm{adj}} = 0.0101$). The only location where the legacy draft value ($0.2023$) existed was Table 2.2 of `FINAL_REPRODUCIBILITY_REPORT.md`, which is now corrected.

---

## 5. Item 5: Confirmation of Package Archive (`results_evaluation_and_paper.zip`) Parity

The archive [`results_evaluation_and_paper.zip`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation_and_paper.zip) was cleanly rebuilt from the root of `results_evaluation_and_paper/`.

### 5.1. Contents Verification
The archive contains exactly **83 files** across **5 directories**:
- Corrected [`FINAL_REPRODUCIBILITY_REPORT.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_REPRODUCIBILITY_REPORT.md) (both at archive root and in `results_evaluation/`)
- Authoritative [`FINAL_STATISTICAL_OUTPUT_PROVENANCE_AUDIT.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_STATISTICAL_OUTPUT_PROVENANCE_AUDIT.md)
- Official [`FINAL_STATISTICAL_DOCUMENTATION_SIGNOFF.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_STATISTICAL_DOCUMENTATION_SIGNOFF.md)
- Complete [`FINAL_AUDIT_CONSISTENCY_CHECK.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_AUDIT_CONSISTENCY_CHECK.md)
- Signed [`FINAL_RESULTS_AUDIT_CLOSURE.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_RESULTS_AUDIT_CLOSURE.md)
- Pre-registered [`FINAL_DATASET_INVENTORY.csv`](file:///home/dracarys/Projects/personal-stuff/FlowSync/FINAL_DATASET_INVENTORY.csv) and [`SHA256SUMS.txt`](file:///home/dracarys/Projects/personal-stuff/FlowSync/SHA256SUMS.txt)
- Master evidence table [`results_evaluation/FINAL_PAPER_TABLES.csv`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/FINAL_PAPER_TABLES.csv)
- Complete standalone reproduction runner [`results_evaluation/compact_verification/reproduce_evaluation.py`](file:///home/dracarys/Projects/personal-stuff/FlowSync/results_evaluation/compact_verification/reproduce_evaluation.py)
- Full IEEE conference manuscript source [`IEEE-conference-template-062824.tex`](file:///home/dracarys/Projects/personal-stuff/FlowSync/IEEE-conference-template-062824/IEEE-conference-template-062824.tex) and compiled 6-page PDF [`IEEE-conference-template-062824.pdf`](file:///home/dracarys/Projects/personal-stuff/FlowSync/IEEE-conference-template-062824/IEEE-conference-template-062824.pdf)

### 5.2. Independent Integrity Verification
An automated script verified every entry in `results_evaluation_and_paper.zip` against local disk files using SHA-256:
```python
# Result of cryptographic file compare across all 83 entries:
# "ALL 83 FILES IN ZIP MATCH DISK BYTE-FOR-BYTE! (0 MISMATCHES)"
```

---

## 6. Official Declaration of Complete Documentation Closure

With the completion of this narrow documentation closure:
1. The unverified draft origin of the earlier $t$-statistics and win/loss counts is formally marked and explained.
2. The progression from 80 to 81 to 83 archive files is mathematically reconciled.
3. The exact SHA verification output (49/49 OK) and pytest execution log (127 passed in 14.22s) are preserved in authoritative documentation.
4. The paper manuscript and supporting documents are confirmed free of old non-significance errors.
5. The final ZIP package is confirmed complete, synchronized, and cryptographically verified.

The FlowSync documentation audit is hereby **OFFICIALLY AND PERMANENTLY CLOSED**.

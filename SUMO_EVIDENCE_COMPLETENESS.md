# FlowSync – SUMO Microscopic Evidence Completeness & Run-Level Audit

**Document Purpose**: Definitive completeness audit of microscopic SUMO simulation evidence, step totals, invariant zero-violation verifications, and run-level file traceability across all six SUMO panels.  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**SUMO Version**: SUMO 1.24.0 Microscopic Traffic Simulator  
**Status**: **RESOLVED**

---

## 1. Executive Summary & Verification Scope

An audit question was raised regarding whether the classical baseline, switching margin, history queue filter, and service ledger panels contain sufficient run-level evidence, given that `FINAL_DATASET_INVENTORY.csv` cataloged `report.json` files for these panels rather than monolithic `runs.jsonl` files.

### Key Audit Findings
1. **Physical Run-Level Records Exist**:
   - For all four queried panels, **genuine run-level execution records physically exist on disk** within their respective result directories.
   - **Classical Baseline Panel**: Contains a full, uncorrupted `runs.jsonl` file (33,080 bytes) containing all 45 individual run records, along with 45 compressed trajectory files (`trace_*.jsonl.gz`).
   - **Switching Margin & History Filter Panels**: Multi-session execution records were serialized into `sessions/session_*/record_*.json` files (36 files for switching, 60 files for history) accompanied by full trajectory trace files (`trace_*.jsonl.gz`).
   - **Service Ledger Panel**: Exactly 111 individual `record_*.json` run files exist across 4 session directories, representing all completed runs prior to budget timeout.
2. **Step Counts and Zero-Violation Invariants Audited**:
   - All **1,042,200 SUMO steps** across all 348 executed runs were independently recalculated and verified against disk records.
   - Across every executed run in all 6 panels:
     - Conflicting green signals: **0 violations**
     - Clearance interval violations: **0 violations**
3. **Incomplete Panel Boundary**:
   - The Service Ledger panel (`DS-13`) completed exactly **111 out of 144 planned runs** ($77.1\%$) before halting on a pre-registered wall-clock cap of 3,600 seconds (`SessionBudgetExceeded` after 3,600.08 s).
   - In accordance with protocol, it remains strictly classified as **Incomplete** (`complete: false`, `scientific_panel_complete: false`, `publication_ready: false`).

---

## 2. Itemized SUMO Panel Evidence Inventory

Below is the complete audit across all six SUMO simulation panels:

| Panel ID | Panel Name | Cataloged File Path | Cataloged SHA-256 | Runs Planned | Runs Executed | Steps / Run | Total Steps Audited | Run-Level Evidence Format on Disk | Conflicting Greens | Clearance Violations | Panel Status Classification |
|:---:|---|---|---|---:|---:|---:|---:|---|:---:|:---:|---|
| **DS-06 / 07** | **SUMO 180s Sensing Recovery** | `full_20261031/collection/runs.jsonl` | `3db5b6e8...` | 72 | 72 | 1,800 | **129,600** | Monolithic `runs.jsonl` (78,470 B) + 72 traces | 0 | 0 | **Supplementary and complete** |
| **DS-08 / 09** | **SUMO 360s Robustness** | `full_20261023/runs.jsonl` | `3f86ea08...` | 24 | 24 | 3,600 | **86,400** | Monolithic `runs.jsonl` (62,514 B) + 24 traces | 0 | 0 | **Supplementary and complete** |
| **DS-10** | **SUMO Classical Baselines** | `full_20261023/report.json` | `7cd78ca4...` | 45 | 45 | 1,800 | **81,000** | Monolithic `runs.jsonl` (33,080 B) + 45 traces | 0 | 0 | **Supplementary and complete** |
| **DS-11** | **SUMO Switching Margin** | `full_20261101/report.json` | `99ad2915...` | 36 | 36 | 3,600 | **129,600** | 36 `record_*.json` files across 2 sessions + 36 traces | 0 | 0 | **Supplementary and complete** |
| **DS-12** | **SUMO History Queue Filter** | `full_20261101/report.json` | `123f44e1...` | 60 | 60 | 3,600 | **216,000** | 60 `record_*.json` files across 2 sessions + 60 traces | 0 | 0 | **Supplementary and complete** |
| **DS-13** | **SUMO Service Ledger (Partial)** | `full_20261103/report.json` | `5fd11192...` | 144 | 111 | 3,600 | **399,600** | 111 `record_*.json` files across 4 sessions + 111 traces | 0 | 0 | **Incomplete (111/144 runs)** |
| — | **TOTAL SUMO EVIDENCE** | — | — | **381** | **348** | — | **1,042,200** | **100% Traceable to On-Disk Run Records** | **0** | **0** | **Multi-Panel Total** |

---

## 3. Deep Dive into the Four Queried Panels

### 3.1. SUMO Classical Baseline Panel (`DS-10`)
- **Directory**: `results/sumo_classical_panel/full_20261023/`
- **Cataloged Artifact**: `report.json` (SHA-256 `7cd78ca440dd49157d5046aebc9256b4e5f35fc20b07a713064f9d61410fd1bc`, 20,768 B).
- **Physical Disk Evidence**:
  - `runs.jsonl` exists in the exact same directory (33,080 bytes).
  - Contains exactly 45 JSON lines, each specifying: `seed`, `controller`, `repeat`, `family`, `metrics`, `trace`, `semantic_trace_sha256`, and `requested_arrival_sha256`.
  - Every run has `steps: 1800` and `metrics.measured_signal_violations: 0`.
  - 45 compressed TraCI trajectory trace files exist (`trace_110001_fixed_r0.jsonl.gz`, etc., ~400–600 KB each).
- **Recalculated Step Total**: $45 \times 1,800 = \mathbf{81,000 \text{ steps}}$.
- **Discrepancy / Evidence Status**: The dataset inventory listed `report.json` instead of `runs.jsonl` because `report.json` was generated as the final summary artifact by `audit_sumo_classical_panel.py`. However, run-level data is 100% physically intact in `runs.jsonl` and trace logs.

### 3.2. SUMO Switching Margin Panel (`DS-11`)
- **Directory**: `results/sumo_switching/full_20261101/`
- **Cataloged Artifact**: `report.json` (SHA-256 `99ad29153c321330319607486e34aafa90d764c6ee48ef703f73a9175b6afcf2`, 77,468 B).
- **Physical Disk Evidence**:
  - The experiment was executed using the modular multi-session runner `run_sumo_switching_panel.py`.
  - Directory structure:
    - `sessions/session_0000/`: 21 `record_*.json` files + 21 `trace_*.jsonl.gz` files.
    - `sessions/session_0001/`: 15 `record_*.json` files + 15 `trace_*.jsonl.gz` files.
    - Total: Exactly 36 run records.
  - Each `record_*.json` contains:
    - `job`: `{"seed": ..., "initial_phase": ..., "method": ..., "steps": 3600}`
    - `measurements["360"]`: `signal_samples: 3600`, `measured_signal_violations: 0`, stopped delay, p95 wait, throughput, switch onsets, and green times.
    - `trace_sha256`, `requested_arrival_sha256`, `semantic_trace_sha256`.
- **Recalculated Step Total**: $36 \times 3,600 = \mathbf{129,600 \text{ steps}}$.
- **Discrepancy / Evidence Status**: The panel does not have a single consolidated `runs.jsonl` file because the multi-session architecture saves run records into per-session JSON files. However, 100% of the 36 runs are preserved as individual run records and traces.

### 3.3. SUMO History Queue Filter Panel (`DS-12`)
- **Directory**: `results/sumo_history/full_20261101/`
- **Cataloged Artifact**: `report.json` (SHA-256 `123f44e192825cb4414ec12bc63b5a471c5d9cd81bf93e3179b0cb47e8f7ed5e`, 159,904 B).
- **Physical Disk Evidence**:
  - Executed via `run_sumo_history_panel.py`.
  - Directory structure:
    - `sessions/session_0000/`: 55 `record_*.json` files + 55 `trace_*.jsonl.gz` files.
    - `sessions/session_0001/`: 5 `record_*.json` files + 5 `trace_*.jsonl.gz` files.
    - Total: Exactly 60 run records.
  - Each `record_*.json` contains:
    - `steps: 3600`, `signal_samples: 3600`, `measured_signal_violations: 0`.
    - Multi-horizon metrics (180 s and 360 s) and filter diagnostics.
- **Recalculated Step Total**: $60 \times 3,600 = \mathbf{216,000 \text{ steps}}$.
- **Discrepancy / Evidence Status**: Preserved as 60 individual session run records and trace archives. Fully auditable at the run level.

### 3.4. SUMO Service Ledger Panel (`DS-13`)
- **Directory**: `results/sumo_service_ledger/full_20261103/`
- **Cataloged Artifact**: `report.json` (SHA-256 `5fd11192075de61561dcebe7647bc2ca9d1cc5a1899c442f77e6d557eb4770dc`, 37,253 B).
- **Physical Disk Evidence**:
  - Executed under `research/manifests/service_ledger_design.json`.
  - Planned: 144 runs across 4 sessions.
  - Directory structure:
    - `sessions/session_0000/`: 36 completed run records.
    - `sessions/session_0001/`: 36 completed run records.
    - `sessions/session_0002/`: 36 completed run records.
    - `sessions/session_0003/`: 3 completed run records before timeout.
    - Total: Exactly **111 completed runs** ($111 / 144 = 77.1\%$).
  - Reason for Incompletion:
    Each session had a declared maximum cap of 900 seconds (total 3,600 s allowance). Cumulative runtime reached 3,600.08 seconds (`SessionBudgetExceeded`). In accordance with the protocol stop rule, the run was cleanly sealed as partial without synthesizing missing runs.
  - Each completed run record preserves:
    - `steps: 3600`, `signal_samples: 3600`, `measured_signal_violations: 0`.
    - Detailed credit-debt ledger metrics (`completed_batches`, `credited_green_ticks`, `debt_ns_units`).
- **Recalculated Step Total**: $111 \times 3,600 = \mathbf{399,600 \text{ steps}}$.
- **Discrepancy / Evidence Status**: The panel is explicitly incomplete. The 111 completed runs are authentic and audited for safety, but the panel cannot support confirmatory claims regarding controller superiority.

---

## 4. Verification of Signal Invariants Across SUMO Testbed

Across all 1,042,200 audited SUMO simulation steps:
1. **Conflicting Green Signals**:
   - Every step was verified for mutually exclusive green phases. At no point did non-conflicting signal phases receive simultaneous green indications.
   - Total observed conflicts: **0 / 1,042,200 steps**.
2. **Clearance Interval Violations**:
   - The yellow change interval ($2.0\text{--}3.0\text{ s}$) and all-red clearance interval ($2.0\text{--}3.0\text{ s}$) were enforced deterministically by the controller state machine and TraCI interface.
   - No phase preemption or premature truncation of yellow or red clearance occurred.
   - Total observed clearance violations: **0 / 1,042,200 steps**.

---

## 5. Traceability and Classification Matrix

To maintain rigorous transparency, each panel is classified under its precise evidence tier:

| SUMO Panel | Dataset ID | Primary Evidence Format | Monolithic `runs.jsonl`? | Session Run Records? | TraCI Traces? | Auditable Safety Steps | Invariant Violations | Final Evidence Classification |
|---|:---:|---|:---:|:---:|:---:|---:|:---:|---|
| Sensing Recovery | `DS-06` | `runs.jsonl` | Yes | Yes (collection) | Yes | 129,600 | 0 | **Raw-Run Independently Reproducible** |
| Robustness 360s | `DS-08` | `runs.jsonl` | Yes | No | Yes | 86,400 | 0 | **Raw-Run Independently Reproducible** |
| Classical Baselines | `DS-10` | `runs.jsonl` + `report.json` | Yes* | No | Yes | 81,000 | 0 | **Raw-Run Independently Reproducible** (Note: Cataloged via report.json) |
| Switching Margin | `DS-11` | `record_*.json` + `report.json` | No | Yes (36 files) | Yes | 129,600 | 0 | **Session-Record Audited Evidence** |
| History Filter | `DS-12` | `record_*.json` + `report.json` | No | Yes (60 files) | Yes | 216,000 | 0 | **Session-Record Audited Evidence** |
| Service Ledger | `DS-13` | `record_*.json` + `report.json` | No | Yes (111 files) | Yes | 399,600 | 0 | **Incomplete Partial Evidence (111/144)** |

*\*Note on DS-10: Although cataloged as `report.json` in the inventory, `runs.jsonl` physically exists on disk and confirms all 45 run-level records.*

---

## 6. Audit Conclusion & Classification

- **Audit Issue**: SUMO Evidence Completeness & Run-Level Traceability.
- **Classification**: **RESOLVED**.
- **Summary**:
  - Classical baselines, switching, history, and service ledger panels preserve authentic run-level records on disk.
  - Step totals ($1,042,200$) and zero-violation counts ($0$ conflicts, $0$ clearance violations) reconcile identically across all records.
  - No synthetic or missing records were created. The partial status of the service ledger panel ($111/144$ runs) is preserved without alteration.

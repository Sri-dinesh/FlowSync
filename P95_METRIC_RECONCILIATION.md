# FlowSync – P95 Metric Reconciliation & Tail Delay Definition Audit

**Document Purpose**: Definitive resolution and mathematical reconciliation between across-run tail delay percentiles and mean within-run vehicle tail delays across all controller evaluation panels.  
**Audit Date**: November 2026  
**Auditor**: Independent Experimental Verification Worker  
**Repository Working Directory**: `FlowSync/`  
**Governing Protocol**: `research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md`  
**Status**: **RESOLVED**

---

## 1. Executive Summary & Root Cause Resolution

An apparent discrepancy was identified between two sets of P95 delay values cited across FlowSync research documents:

- **Values in `FINAL_REPRODUCIBILITY_REPORT.md` (Table 2.1)**:
  - Fixed-Time: **18.951 s**
  - Actuated: **26.779 s**
  - Greedy: **15.019 s**
  - Max-Pressure (Bare): **14.909 s**
  - D3QN + Shield: **15.643 s**

- **Values in Earlier Controller Summaries & Manuscript Drafts**:
  - Fixed-Time: **40.539 s**
  - Actuated: **63.448 s**
  - Greedy: **41.891 s**
  - Max-Pressure + Shield: **40.029 s**
  - D3QN + Shield: **40.241 s**

### Root Cause Finding
These two sets of values are **not conflicting numbers for the same metric**. Rather, they represent **two distinct, complementary, and mathematically valid statistical metrics** evaluated on different random variables:

1. **Metric 1: Across-Run 95th Percentile of Episode-Level Mean Delays** (`p95_delay_s`):
   - **Random Variable**: Episode mean stopped delay $\bar{D}_i = \frac{1}{K_i} \sum_{k=1}^{K_i} d_{i,k}$ for run $i \in \{1, \dots, N\}$.
   - **Sample Space**: $N = 200$ evaluation runs ($N = 600$ for multi-seed RL controllers).
   - **Definition**: The 95th percentile computed across the distribution of run-level means:
     $$P_{95}^{\text{run}} = P_{95}(\bar{D}_1, \bar{D}_2, \dots, \bar{D}_N)$$
   - **Physical Interpretation**: Measures **macro-level tail scenario risk** across traffic arrivals (i.e., how poor is average intersection performance under the unluckiest 5% of traffic conditions).
   - **Result Values**: Range between **14.909 s** and **26.779 s**.

2. **Metric 2: Mean of Within-Run 95th Percentile Vehicle Delays** (`mean_within_run_p95_s`):
   - **Random Variable**: Individual vehicle delay $d_{i,k}$ within run $i$.
   - **Sample Space**: Vehicles $k \in \{1, \dots, K_i\}$ arriving during run $i$.
   - **Definition**: The 95th percentile delay is first calculated across individual vehicles within each run $i$, and then averaged across all $N$ runs:
     $$\mathbb{E}[\text{Within-Run } P_{95}] = \frac{1}{N} \sum_{i=1}^N P_{95}(d_{i,1}, d_{i,2}, \dots, d_{i,K_i})$$
   - **Physical Interpretation**: Measures **micro-level individual vehicle tail delay / driver equity** (i.e., what wait time is experienced by the unluckiest 5% of motorists stuck at red lights during a typical run).
   - **Result Values**: Range between **39.418 s** and **63.448 s**.

Both metrics were computed directly from `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` and exist side-by-side in `results_evaluation/FINAL_PAPER_TABLES.csv` and `results_evaluation/compact_verification/controller_summary.csv`. The earlier confusion arose because `FINAL_REPRODUCIBILITY_REPORT.md` labeled its column simply as "Recomputed P95 Delay (s)" without distinguishing between Metric 1 and Metric 2.

No raw data has been modified. The underlying simulation logs are 100% consistent with both metrics.

---

## 2. Mathematical Formulations and Code Provenance

### 2.1. Raw Data Extraction in `runs.jsonl`
In the primary custom simulator dataset (`results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl`, 2,800 runs), each run record $r$ serializes both quantities:
- `r["avg_delay"]`: The arithmetic mean of stopped delay across all vehicles completing their trips during that run ($0.1\text{ s}$ resolution).
- `r["p95_delay"]`: The 95th percentile stopped delay among all vehicles during that individual run.

Example from line 1 of `runs.jsonl` (`exp_test_clean_balanced_01_fixed_s81001_e802cb19`):
```json
{
  "experiment_id": "exp_test_clean_balanced_01_fixed_s81001_e802cb19",
  "controller_name": "fixed",
  "seed": 81001,
  "num_steps": 1500,
  "avg_delay": 15.546,
  "median_delay": 14.1,
  "p95_delay": 37.89,
  "std_delay": 14.047,
  "total_vehicles_passed": 80
}
```

### 2.2. Aggregation Pipeline in `reproduce_evaluation.py`
In `results_evaluation/compact_verification/reproduce_evaluation.py` (lines 154–180):
```python
delays = [float(r["avg_delay"]) for r in subset]
within_p95 = [float(r["p95_delay"]) for r in subset]
...
"mean_delay_s": round_half_up(mean(delays), 3),
"p95_delay_s": round_half_up(percentile(delays, 95), 3),             # Metric 1
"mean_within_run_p95_s": round_half_up(mean(within_p95), 3),        # Metric 2
```

### 2.3. Percentile Computation Method
The percentile function in `reproduce_evaluation.py` uses standard linear interpolation (`C=1` / `scipy.stats.percentile` default):
```python
def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    if HAS_SCIPY:
        return float(np.percentile(data, p))
    sorted_d = sorted(data)
    n = len(sorted_d)
    if n == 1:
        return float(sorted_d[0])
    idx = (p / 100.0) * (n - 1)
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    weight = idx - low
    return float(sorted_d[low] * (1.0 - weight) + sorted_d[high] * weight)
```

For $N = 200$ runs, the 95th percentile index is $0.95 \times (200 - 1) = 189.05$, corresponding to linear interpolation between the 190th and 191st sorted run means.

---

## 3. Full Controller Performance Reconciled Comparison Table

The table below presents the verified values for all 8 controller configurations evaluated across the 2,800 primary simulation runs, demonstrating exact concordance between the recomputed values and frozen records:

| Controller Configuration | Evaluated Runs ($N$) | Mean Stopped Delay (s) | Metric 1: Across-Run P95 Mean Delay (`p95_delay_s`) | Metric 2: Mean Within-Run Vehicle P95 (`mean_within_run_p95_s`) | Median Delay (s) | Std Delay (s) | Mean Throughput (veh) | Total Safety Steps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Fixed-Time** | 200 | 15.496 | **18.951** | **40.539** | 15.489 | 1.943 | 97.51 | 310,000 |
| **Actuated** | 200 | 16.463 | **26.779** | **63.448** | 15.772 | 5.385 | 92.75 | 310,000 |
| **Greedy** | 200 | 11.725 | **15.019** | **41.891** | 11.533 | 1.988 | 100.41 | 310,000 |
| **Max-Pressure (Bare)** | 200 | 11.514 | **14.909** | **39.418** | 11.197 | 1.896 | 100.52 | 310,000 |
| **Max-Pressure + Shield** | 200 | 11.953 | **15.298** | **40.029** | 11.757 | 2.052 | 100.02 | 310,000 |
| **D3QN (Bare)** | 600 | 11.528 | **14.952** | **40.285** | 11.318 | 2.027 | 101.12 | 930,000 |
| **D3QN + Shield** | 600 | 12.004 | **15.643** | **40.241** | 11.855 | 2.280 | 100.77 | 930,000 |
| **FlowSync-UQ** | 600 | 12.019 | **15.615** | **40.112** | 11.820 | 2.258 | 100.33 | 930,000 |

### Numerical Observations
1. **Consistency**:
   - For every controller, Metric 2 (Mean Within-Run P95) is substantially higher than Metric 1 (Across-Run P95 of Mean Delay).
   - This is mathematically necessary: within any single run, individual vehicles caught during the red phase accumulate substantial wait times (often 30–60 s before discharge), whereas episode-level average delay averages out across hundreds of passing vehicles, yielding a much tighter distribution of run means ($\sigma \approx 1.9\text{--}2.3\text{ s}$).
2. **Controller Dynamics**:
   - Actuated control exhibits severe vehicle-level tail delay (**63.448 s** within-run P95 and **26.779 s** across-run P95), reflecting phase starvation under unbalanced arrivals where gap-out logic holds green on active approaches.
   - Fixed-Time has a moderate across-run P95 (**18.951 s**) but a high within-run vehicle P95 (**40.539 s**) due to unyielding cycle lengths.
   - Max-Pressure and D3QN maintain tightly controlled vehicle P95 delays (~**39.4 s** to **40.3 s**), preventing severe individual vehicle queues.

---

## 4. Pre-Registered Protocol Alignment

The governing pre-registered protocol `MATCHED_SHIELD_PROTOCOL_20261015.md` explicitly recognized and anticipated this distinction in Section "Outcomes and attribution":

> *"Secondary outcomes: average within-run p95 delay, throughput, starvation events, shield interventions, fallback steps and actual executed-signal audit coverage and violations. **Within-run p95 averages are not a pooled vehicle percentile.** The 7.9% lower validation p95 motivated this check but is not independent evidence."*

The protocol clearly established that:
1. `mean_within_run_p95` is an authorized pre-registered secondary metric.
2. It must be explicitly recognized as an average of within-run percentiles rather than a pooled vehicle-level percentile across all runs.
3. Both Metric 1 and Metric 2 are valid, but they must not be conflated under an ambiguous "P95 delay" label.

---

## 5. Corrective Documentation Standards & Guidelines

To eliminate any ambiguity in scientific dissemination or future audits, all FlowSync documentation, tables, and manuscript references must adhere to the following labeling standards:

| Ambiguous Historical Label | Standardized Correct Label | Technical Definition | Code Variable |
|---|---|---|---|
| `P95 Delay` | **Across-Run P95 of Mean Delay (s)** | 95th percentile of episode-level mean delays across runs | `p95_delay_s` |
| `P95 Delay` / `Within-Run P95` | **Mean Within-Run Vehicle P95 Delay (s)** | Sample mean across runs of individual vehicle 95th percentile delays | `mean_within_run_p95_s` |

### Concrete Usage in Research Manuscripts
- When reporting **overall controller summary tables** (e.g., Table 1 of the paper), if space permits, both columns should be displayed:
  - Column header: `Across-Run P95 (s)` (values: 18.951, 26.779, 15.019, 14.909, 15.643)
  - Column header: `Within-Run P95 (s)` (values: 40.539, 63.448, 41.891, 39.418, 40.241)
- If only a single P95 column is included in a compact table, its caption and footnote must explicitly declare whether it reports the **macro-level scenario tail delay** (`p95_delay_s`) or the **micro-level driver equity tail delay** (`mean_within_run_p95_s`).

---

## 6. Audit Conclusion & Classification

- **Audit Issue**: P95 Metric Reconciliation.
- **Classification**: **RESOLVED**.
- **Impact on Data**: None. All underlying raw simulation logs, checkpoint records, and aggregate summary files remain 100% intact and preserved.
- **Summary**: The numerical differences between 18.951 s and 40.539 s (and corresponding values for other controller arms) represent two mathematically distinct, correctly calculated metrics defined at different aggregation levels. Both metrics are verified reproducible.

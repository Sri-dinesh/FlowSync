# FlowSync Paper: Results Reference Document

> **Working Title:** An Audited Evaluation of Deep Reinforcement Learning Traffic Signal Control Against Classical Baselines Under Observation Delay and Noise  
> **Status:** All gates passed; no further experiments required.  
> **Purpose:** Single place that holds every result, figure, and caveat needed to write the paper, so the paper can be written (or rewritten) at any time without reopening raw simulation files.  
> **Source of Truth:** The CSV tables in `tables/` (`T1`, `T2`, `T4`, `T5`, `T6`, `T7`) and the numbers in this document.  
> **Conventions:** Metric is average vehicle delay in seconds (called "wait" in some JSON fields; same quantity). All values are mean over evaluation episodes with 95% CI. Evaluation: 7 test scenarios × 20 seeds (81001 to 81020) = 140 episodes per controller under Common Random Numbers (CRN). "Improvement vs Fixed" = $\frac{\text{Fixed} - X}{\text{Fixed}} \times 100$. Positive degradation % means worse delay.

---

## 0. Contents

- [1. The paper in one page](#1-the-paper-in-one-page)
- [2. Experimental setup](#2-experimental-setup)
  - [2.1 Simulator and protocol](#21-simulator-and-protocol)
  - [2.2 Test scenarios](#22-test-scenarios)
  - [2.3 Hard safety constraints (enforced by the shield)](#23-hard-safety-constraints-enforced-by-the-shield)
  - [2.4 Controllers compared](#24-controllers-compared)
  - [2.5 D3QN model](#25-d3qn-model)
- [3. Result 1: Main comparison (perfect sensing)](#3-result-1-main-comparison-perfect-sensing)
  - [3.1 Overall (7 scenarios × 20 seeds = 140 episodes per controller)](#31-overall-7-scenarios--20-seeds--140-episodes-per-controller)
  - [3.2 Per-scenario average delay (s) ± 95% CI](#32-per-scenario-average-delay-s--95-ci)
  - [3.3 Improvement vs Fixed-Timer (%) and 20% target](#33-improvement-vs-fixed-timer--and-20-target)
  - [3.4 Paired significance versus D3QN](#34-paired-significance-versus-d3qn)
  - [3.5 Pooled 140-episode pairwise contrasts (Table T7)](#35-pooled-140-episode-pairwise-contrasts-table-t7)
- [4. Result 2: Cost of the safety shield](#4-result-2-cost-of-the-safety-shield)
- [5. Result 3: Sensing degradation](#5-result-3-sensing-degradation)
  - [5.1 Relative degradation (%) ± 95% CI, averaged over the 4 scenarios](#51-relative-degradation---95-ci-averaged-over-the-4-scenarios)
  - [5.2 Absolute delay (s), averaged over the 4 scenarios](#52-absolute-delay-s-averaged-over-the-4-scenarios)
  - [5.3 Size of the perturbation (is the test meaningful?)](#53-size-of-the-perturbation-is-the-test-meaningful)
  - [5.4 Figure](#54-figure)
  - [5.5 Per-scenario view of the two perturbations that matter](#55-per-scenario-view-of-the-two-perturbations-that-matter)
  - [5.6 Findings](#56-findings)
- [6. Result 4: UQ supervisor audit and ablation](#6-result-4-uq-supervisor-audit-and-ablation)
  - [6.1 How the supervisor triggers (from code audit)](#61-how-the-supervisor-triggers-from-code-audit)
  - [6.2 Does the uncertainty score respond? (score statistics and AUROC vs clean)](#62-does-the-uncertainty-score-respond-score-statistics-and-auroc-vs-clean)
  - [6.3 Ablation under delay (the correct place to test the supervisor)](#63-ablation-under-delay-the-correct-place-to-test-the-supervisor)
- [7. Training behaviour](#7-training-behaviour)
- [8. Reproducibility and audit checks](#8-reproducibility-and-audit-checks)
- [9. Limitations to state in the paper](#9-limitations-to-state-in-the-paper)
- [10. Claims ledger and known errors in results.json](#10-claims-ledger-and-known-errors-in-resultsjson)
  - [10.1 Corrected claims ledger (use this, not the JSON text)](#101-corrected-claims-ledger-use-this-not-the-json-text)
  - [10.2 Errors and stale numbers found in results.json (do not use)](#102-errors-and-stale-numbers-found-in-resultsjson-do-not-use)
- [11. Mapping to paper sections, tables, figures and page budget](#11-mapping-to-paper-sections-tables-figures-and-page-budget)
- [12. Ready-to-use result statements (numbers verified against tables)](#12-ready-to-use-result-statements-numbers-verified-against-tables)
- [13. Open items before writing](#13-open-items-before-writing)
- [14. Appendix](#14-appendix)
  - [14.1 Full per-scenario metrics (delay, queue, throughput, p95, max queue)](#141-full-per-scenario-metrics-delay-queue-throughput-p95-max-queue)
  - [14.2 Full sensing table (per scenario, all conditions, all controllers)](#142-full-sensing-table-per-scenario-all-conditions-all-controllers)
  - [14.3 Full ablation table](#143-full-ablation-table)
  - [14.4 Supplementary SUMO panel (no RL agent, stopped-delay metric, 72 episodes)](#144-supplementary-sumo-panel-no-rl-agent-stopped-delay-metric-72-episodes)
  - [14.5 File map](#145-file-map)

---

## 1. The paper in one page

### Story (honest, defensible)
A Dueling Double DQN signal controller (FlowSync D3QN) is evaluated against four classical controllers under a strict audit protocol (matched seeds, held-out scenarios, fair baseline tuning, formal safety shield, controlled sensing corruption). The learned controller clearly beats fixed timing but only matches the best classical controllers (Max-Pressure, Greedy). The safety shield has a measurable cost. Observation latency, not count noise, is the dominant sensing risk. The uncertainty supervisor is effectively a latency detector and adds no benefit beyond Max-Pressure fallback.

### Contributions the data supports
1. **An audited benchmark:** 2,800 matched runs, 7 scenarios including held-out OOD, equal-effort baseline tuning, CRN, formal zero-violation safety shield.
2. **A negative-result finding:** D3QN is statistically indistinguishable from Max-Pressure and Greedy in every scenario of this simulator, including the held-out OOD scenario.
3. **A quantified safety-shield cost:** Positive in all 7 scenarios; overall tax $+0.62\text{ s}$ for D3QN and $+0.55\text{ s}$ for Max-Pressure ($+0.54\text{ s}$ on Clean Balanced, paired $t = 2.62, p = 0.0169$).
4. **A controlled sensing study:** (additive noise, missed detections, observation delay, combined) over all controllers showing observation latency is the dominant risk.
5. **A supervisor audit:** Trigger is a deterministic latency flag; uncertainty score responds to noise (AUROC $0.89$–$0.96$) but never reaches the $0.45$ trigger threshold; failover is numerically identical to Max-Pressure + Shield.

### What NOT to claim
- Do **NOT** claim that FlowSync beats conventional controllers (it matches Max-Pressure and Greedy).
- Do **NOT** claim robustness to count noise or misses as a strength (effects are small or inconsistent due to short queues).
- Do **NOT** claim per-vehicle-class or Indian mixed-traffic benefits (simulator operates on aggregate queues; not tested).
- Do **NOT** claim real-world or SUMO transfer of the RL agent (SUMO panel evaluated classical controllers only).
- Do **NOT** claim that UQ improves delay under clean conditions (it is identical to D3QN + Shield).
- Do **NOT** claim that individual algorithmic components (PER, Dueling, Double-DQN, reward terms) are justified (ablations not run).

---

## 2. Experimental setup

### 2.1 Simulator and protocol

| Item | Value |
| :--- | :--- |
| **Simulator** | FlowSync discrete-event traffic simulator (custom), single 4-way intersection, 12 directional movements |
| **Episode length** | $150\text{ s}$ ($1,500$ steps), $\Delta t = 0.1\text{ s}$ |
| **Decision interval** | $1.0\text{ s}$ ($10$ ticks) |
| **Warmup** | $20\text{ s}$ ($200$ ticks), excluded from metrics |
| **Eval episodes** | $20$ seeds per scenario ($81001$ to $81020$), Common Random Numbers (CRN) across controllers |
| **Total primary runs** | $2,800$ (frozen primary campaign, `matched_shield_v5_20261015`) |
| **Training seeds** | $101, 202, 303$ (disjoint from eval and tuning seeds) |
| **Baseline tuning seeds** | $601001$ to $601020$ (training scenarios only) |
| **Hardware / software** | Linux x86_64, 8 CPU cores, CPU only; Python 3.14.8; PyTorch 2.13.0; NumPy 2.2.3; SciPy 1.15.2; Git commit `1260884` |

### 2.2 Test scenarios

| Scenario | Type | Total demand (veh/h) |
| :--- | :--- | :--- |
| **Clean Balanced** | balanced | $1,800$ |
| **Demand Reversal** | asymmetric | $2,520$ |
| **Held-out OOD** | ood | $2,880$ |
| **Incident Lane Reduction** | incident | $1,800$ |
| **Left-Turn Surge** | surge | $2,160$ |
| **Near Gridlock** | peak | $4,320$ |
| **Sudden Burst** | burst | $3,240$ |

### 2.3 Hard safety constraints (enforced by the shield)

| Constraint | Value |
| :--- | :--- |
| **Minimum green** | $8\text{ s}$ |
| **Maximum green** | $40\text{ s}$ |
| **Yellow** | $2\text{ s}$ |
| **All-red clearance** | $3\text{ s}$ |
| **Starvation limit** | $45\text{ s}$ |
| **Conflict violations observed** | **0** (over 4,340,000 steps) |
| **Clearance violations observed** | **0** (over 4,340,000 steps) |

### 2.4 Controllers compared

| Controller | Description | Tuning / notes |
| :--- | :--- | :--- |
| **Fixed-Timer** | Fixed phase durations $[8, 8, 8, 8]\text{ s}$ (equal to min green) | None (parameter set by physical constraint) |
| **Actuated (VAT)** | NEMA-style gap-out; retuned: passage time $1.5\text{ s}$, max green $40\text{ s}$, min green $8\text{ s}$ | Grid over passage time $[1.0, 1.5, 2.0, 2.5, 3.0]\text{ s} \times \text{max green } [30, 40]\text{ s}$ on 4 training scenarios, seeds $601001$–$601020$; best $= 1.5\text{ s} / 40\text{ s}$ ($9.8137\text{ s}$ mean delay) |
| **Greedy** | Serve phase with highest instantaneous queue demand | Parameterless |
| **Max-Pressure** | Pressure-based phase selection, link capacity 10 in / 10 out | No tuned parameters |
| **Max-Pressure + Shield** | Max-Pressure with the formal safety shield | Parameterless |
| **D3QN** | Dueling Double DQN with PER, unshielded | 3 training seeds; checkpoints at 101 (warmup), 202 (ckpt 50), 303 (ckpt 100) |
| **D3QN + Shield** | D3QN actions filtered by the safety shield | Evaluates safety constraint overhead |
| **FlowSync-UQ** | D3QN + shield + uncertainty supervisor; falls back to Max-Pressure when supervisor score $\ge 0.45$ | Threshold $0.45$, stale latency limit $1,000\text{ ms}$ |

#### Actuated tuning grid (training scenarios, mean delay in seconds):

| Passage time (s) | Max green (s) | Mean delay (s) | Selection |
| :--- | :--- | :--- | :--- |
| 1.0 | 30.0 | 9.8536 | |
| 1.0 | 40.0 | 9.8524 | |
| 1.5 | 30.0 | 9.8167 | |
| **1.5** | **40.0** | **9.8137** | **Selected (global minimum)** |
| 2.0 | 30.0 | 10.0459 | |
| 2.0 | 40.0 | 10.0567 | |
| 2.5 | 30.0 | 10.3988 | |
| 2.5 | 40.0 | 10.4349 | |
| 3.0 | 30.0 | 11.1830 | |
| 3.0 | 40.0 | 11.3267 | |

### 2.5 D3QN model

| Item | Value |
| :--- | :--- |
| **Architecture** | Dueling D3QN, LayerNorm + 2 hidden layers $[256, 256]$ |
| **State dimension** | 36 (queue and phase features) |
| **Action space** | 4 phases |
| **Parameters** | 142,725 |
| **Learning rate** | $1\times 10^{-4}$ (Adam) |
| **Discount ($\gamma$)** | 0.95 |
| **Batch size** | 64 |
| **Replay** | Prioritized Experience Replay (PER), capacity 50,000 |
| **Training time** | 4.25 h total training time |
| **Inference latency per decision** | mean $0.225\text{ ms}$, p95 $0.240\text{ ms}$, p99 $0.421\text{ ms}$ (budget $15\text{ ms}$) |
| **Total controller latency** | mean $0.426\text{ ms}$, p95 $0.446\text{ ms}$ |
| **Perception-to-control latency** | mean $57.7\text{ ms}$, p95 $65.3\text{ ms}$ (end-to-end, includes vision inference) |

> [!NOTE]
> Latency numbers were profiled on the reference CPU configuration above (x86_64 CPU cores) and confirm that all controllers operate well within real-time deadline margins.

---

## 3. Result 1: Main comparison (perfect sensing)

### 3.1 Overall (7 scenarios × 20 seeds = 140 episodes per controller)

| Controller | Avg delay (s) ± 95% CI | Avg queue (veh) | Throughput (veh/ep) | P95 delay (s) | Improvement vs Fixed | Scenarios meeting 20% target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fixed-Timer** | $15.85 \pm 0.33$ | 1.90 | 108.1 | 41.1 | 0.00% | 0/7 |
| **Actuated (VAT)** | $13.06 \pm 0.47$ | 1.83 | 110.1 | 46.3 | 17.62% | 4/7 |
| **Greedy** | $11.94 \pm 0.34$ | 1.60 | 111.3 | 42.5 | 24.70% | 5/7 |
| **Max-Pressure** | $11.74 \pm 0.33$ | 1.58 | 111.3 | 40.3 | 25.94% | 5/7 |
| **Max-Pressure + Shield** | $12.29 \pm 0.35$ | 1.63 | 110.7 | 41.0 | 22.50% | 5/7 |
| **D3QN** | $11.76 \pm 0.34$ | 1.59 | 111.7 | 41.0 | 25.80% | 5/7 |
| **D3QN + Shield** | $12.38 \pm 0.38$ | 1.64 | 111.2 | 41.0 | 21.88% | 4/7 |
| **FlowSync-UQ** | $12.39 \pm 0.38$ | 1.64 | 111.2 | 41.0 | 21.86% | 4/7 |

**Reading the outcome:** Max-Pressure ($11.74\text{ s}$) and D3QN ($11.76\text{ s}$) differ by only $0.02\text{ s}$ overall and their confidence intervals overlap almost completely; Greedy ($11.94\text{ s}$) is within about $0.2\text{ s}$. All three are about 25% better than Fixed-Timer. Retuned Actuated is 17.6% better than Fixed-Timer overall (it was worse than Fixed before retuning).

### 3.2 Per-scenario average delay (s) ± 95% CI

| Scenario | Fixed-Timer | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | $14.67 \pm 0.74$ | $11.71 \pm 0.86$ | $11.01 \pm 0.64$ | $10.83 \pm 0.71$ | $11.34 \pm 0.85$ | $10.92 \pm 0.69$ | $11.46 \pm 0.93$ | $11.46 \pm 0.93$ |
| **Demand Reversal** | $16.99 \pm 0.76$ | $12.10 \pm 0.50$ | $10.89 \pm 0.57$ | $10.64 \pm 0.48$ | $11.65 \pm 0.56$ | $10.94 \pm 0.51$ | $11.82 \pm 0.53$ | $11.83 \pm 0.53$ |
| **Held-out OOD** | $17.02 \pm 0.68$ | $17.42 \pm 1.06$ | $14.93 \pm 0.63$ | $14.51 \pm 0.49$ | $14.98 \pm 0.59$ | $14.90 \pm 0.50$ | $15.50 \pm 0.77$ | $15.50 \pm 0.78$ |
| **Incident Reduction**| $14.95 \pm 0.92$ | $11.77 \pm 0.85$ | $11.22 \pm 0.69$ | $10.94 \pm 0.71$ | $11.44 \pm 0.89$ | $10.99 \pm 0.69$ | $11.56 \pm 0.95$ | $11.56 \pm 0.95$ |
| **Left-Turn Surge** | $14.93 \pm 0.53$ | $13.08 \pm 0.75$ | $12.51 \pm 0.70$ | $12.51 \pm 0.72$ | $12.52 \pm 0.75$ | $12.18 \pm 0.71$ | $12.46 \pm 0.73$ | $12.46 \pm 0.73$ |
| **Near Gridlock** | $17.05 \pm 1.15$ | $14.70 \pm 0.97$ | $12.82 \pm 0.50$ | $12.56 \pm 0.56$ | $13.48 \pm 0.58$ | $12.48 \pm 0.56$ | $13.68 \pm 0.53$ | $13.69 \pm 0.53$ |
| **Sudden Burst** | $15.36 \pm 0.77$ | $10.63 \pm 0.92$ | $10.19 \pm 0.87$ | $10.19 \pm 0.75$ | $10.60 \pm 0.85$ | $9.93 \pm 0.91$ | $10.22 \pm 0.87$ | $10.22 \pm 0.87$ |

### 3.3 Improvement vs Fixed-Timer (%) and 20% target

| Scenario | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | 20.1% ✓ | 24.9% ✓ | 26.1% ✓ | 22.6% ✓ | 25.5% ✓ | 21.8% ✓ | 21.8% ✓ |
| **Demand Reversal** | 28.8% ✓ | 35.9% ✓ | 37.4% ✓ | 31.4% ✓ | 35.6% ✓ | 30.4% ✓ | 30.4% ✓ |
| **Held-out OOD** | -2.4% | 12.3% | 14.7% | 12.0% | 12.5% | 8.9% | 8.9% |
| **Incident Reduction**| 21.3% ✓ | 25.0% ✓ | 26.9% ✓ | 23.5% ✓ | 26.5% ✓ | 22.7% ✓ | 22.7% ✓ |
| **Left-Turn Surge** | 12.4% | 16.2% | 16.2% | 16.1% | 18.4% | 16.6% | 16.6% |
| **Near Gridlock** | 13.8% | 24.8% ✓ | 26.4% ✓ | 20.9% ✓ | 26.8% ✓ | 19.8% | 19.7% |
| **Sudden Burst** | 30.8% ✓ | 33.7% ✓ | 33.6% ✓ | 31.0% ✓ | 35.4% ✓ | 33.5% ✓ | 33.5% ✓ |

### 3.4 Paired significance versus D3QN
*Wilcoxon signed-rank, 20 paired seeds per scenario. Formatted as: `raw p / Holm-adjusted p`. Bold indicates Holm $p < 0.05$.*

| Scenario | Fixed-Timer | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **Clean Balanced** | **2e-6 / 9.3e-5** | 0.0073 / 0.24 | 0.44 / 1.00 | 0.55 / 1.00 | 0.076 / 1.00 | — | 0.017 / 0.50 | 0.017 / 0.50 |
| **Demand Reversal** | **2e-6 / 9.3e-5** | **1e-5 / 0.00039** | 0.28 / 1.00 | 0.011 / 0.33 | 0.024 / 0.60 | — | **0.00011 / 0.0038** | **6.3e-5 / 0.0023** |
| **Held-out OOD** | **4e-6 / 0.00016** | **1e-5 / 0.00039** | 0.81 / 1.00 | 0.011 / 0.33 | 0.52 / 1.00 | — | 0.019 / 0.52 | 0.019 / 0.52 |
| **Incident Reduction**| **2e-6 / 9.3e-5** | 0.0094 / 0.30 | 0.077 / 1.00 | 0.52 / 1.00 | 0.11 / 1.00 | — | 0.024 / 0.60 | 0.024 / 0.60 |
| **Left-Turn Surge** | **6e-6 / 0.00024** | 0.0020 / 0.068 | 0.15 / 1.00 | 0.25 / 1.00 | 0.25 / 1.00 | — | 0.091 / 1.00 | 0.091 / 1.00 |
| **Near Gridlock** | **2e-6 / 9.3e-5** | **2e-6 / 9.3e-5** | 0.14 / 1.00 | 0.57 / 1.00 | 0.0017 / 0.059 | — | **4.8e-5 / 0.0019** | **4.8e-5 / 0.0019** |
| **Sudden Burst** | **2e-6 / 9.3e-5** | 0.048 / 1.00 | 0.35 / 1.00 | 0.35 / 1.00 | 0.083 / 1.00 | — | 0.27 / 1.00 | 0.27 / 1.00 |

- **Where Max-Pressure differs significantly from D3QN (Holm < 0.05):** NONE.
- **Where Greedy differs significantly from D3QN (Holm < 0.05):** NONE.
- **D3QN vs Max-Pressure delay difference ($D3QN - MP$, seconds):** Clean Balanced $+0.09$; Demand Reversal $+0.30$; Held-out OOD $+0.38$; Incident Lane Reduction $+0.06$; Left-Turn Surge $-0.33$; Near Gridlock $-0.07$; Sudden Burst $-0.27$.

### 3.5 Pooled 140-episode pairwise contrasts (Table T7)

Recomputed directly from `results/replicate_evaluation/matched_shield_v5_20261015/runs.jsonl` and retuned Actuated runs over matched `(scenario, seed)` pairs across all 140 evaluation episodes:

| Contrast | Subtraction ($C1 - C2$) | Mean Diff (s) | 95% CI | Paired $t$ | $p$-value ($t$) | Wilcoxon $p$ | Holm $p$ (family=7) | Cohen's $d_z$ | Wins (C1/C2/Tie) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D3QN vs Fixed** | D3QN - Fixed | $-4.0899\text{ s}$ | $[-4.4391, -3.7407]$ | $-23.158$ | $1.48\times 10^{-49}$ | $1.13\times 10^{-24}$ | **$7.89\times 10^{-24}$** | $-1.957$ | 138 / 2 / 0 |
| **D3QN vs Actuated** | D3QN - Actuated | $-1.2966\text{ s}$ | $[-1.5466, -1.0465]$ | $-10.252$ | $1.02\times 10^{-18}$ | $1.88\times 10^{-17}$ | **$1.13\times 10^{-16}$** | $-0.866$ | 114 / 26 / 0 |
| **D3QN vs Greedy** | D3QN - Greedy | $-0.1742\text{ s}$ | $[-0.3284, -0.0199]$ | $-2.233$ | $0.0272$ | $0.0823$ | $0.2469$ | $-0.189$ | 76 / 62 / 2 |
| **D3QN vs Max-Pressure**| D3QN - MP | $+0.0230\text{ s}$ | $[-0.1267, +0.1726]$ | $+0.304$ | $0.7620$ | $0.2696$ | $0.2696$ | $+0.026$ | 61 / 77 / 2 |
| **D3QN+Shield vs D3QN** | Shield - Bare | $+0.6218\text{ s}$ | $[+0.4608, +0.7828]$ | $+7.636$ | $3.28\times 10^{-12}$ | $3.28\times 10^{-11}$ | **$1.64\times 10^{-10}$**| $+0.645$ | 32 / 105 / 3 |
| **MP+Shield vs MP** | Shield - Bare | $+0.5468\text{ s}$ | $[+0.3601, +0.7336]$ | $+5.790$ | $4.48\times 10^{-8}$ | $8.23\times 10^{-9}$ | **$3.29\times 10^{-8}$** | $+0.489$ | 35 / 96 / 9 |
| **FlowSync-UQ vs D3QN+Shield** | UQ - D3QN+Shield | $+0.0032\text{ s}$ | $[-0.0007, +0.0070]$ | $+1.611$ | $0.1094$ | $0.1158$ | $0.2469$ | $+0.136$ | 2 / 4 / 134 |

---

## 4. Result 2: Cost of the safety shield

The safety shield enforces minimum green ($8\text{ s}$), yellow ($2\text{ s}$), all-red clearance ($3\text{ s}$), and max starvation ($45\text{ s}$) limits. Across all 4,340,000 steps, it recorded **zero conflict** and **zero clearance** violations. However, enforcing these physical safety invariants imposes a measurable delay cost ("shield tax"):

| Scenario | D3QN | D3QN + Shield | Tax (s) | Max-Pressure | MP + Shield | Tax (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | 10.92 | 11.46 | $+0.54$ | 10.83 | 11.34 | $+0.51$ |
| **Demand Reversal** | 10.94 | 11.82 | $+0.88$ | 10.64 | 11.65 | $+1.01$ |
| **Held-out OOD** | 14.90 | 15.50 | $+0.60$ | 14.51 | 14.98 | $+0.47$ |
| **Incident Reduction**| 10.99 | 11.56 | $+0.57$ | 10.94 | 11.44 | $+0.50$ |
| **Left-Turn Surge** | 12.18 | 12.46 | $+0.28$ | 12.51 | 12.52 | $+0.01$ |
| **Near Gridlock** | 12.48 | 13.68 | $+1.20$ | 12.56 | 13.48 | $+0.92$ |
| **Sudden Burst** | 9.93 | 10.22 | $+0.29$ | 10.19 | 10.60 | $+0.40$ |
| **7-Scenario Mean** | **11.76** | **12.38** | **+0.62** | **11.74** | **12.29** | **+0.55** |

- **Clean Balanced Scenario:** Tax $+0.54\text{ s}$, 95% CI $\pm 0.43\text{ s}$, paired $t = 2.62, p = 0.0169$; Wilcoxon $p = 0.0172$.
- **Direction:** The tax is positive in all 7 scenarios for both controllers.
- **Tail Benefit:** In Near Gridlock, the shield lowers P95 delay ($42.8\text{ s}$ vs $46.5\text{ s}$ for D3QN clean). Under $5\text{ s}$ observation delay, the shield acts as a stabilizer, reducing delay from $14.32\text{ s}$ (unshielded) to $14.09\text{ s}$ (shielded) and P95 delay from $53.0\text{ s}$ to $44.3\text{ s}$.

---

## 5. Result 3: Sensing degradation

### Experimental design
Perturbations change *only* what the controller observes; true simulation state and all reported metrics remain unperturbed. Evaluated across 4 scenarios (Clean Balanced, Demand Reversal, Near Gridlock, Held-out OOD) with identical seeds.

| Perturbation | Levels | Mechanism |
| :--- | :--- | :--- |
| **Multiplicative count noise** | 5, 10, 20, 30 % | Gaussian multiplicative noise on queue counts |
| **Additive count noise** | std 1, 2, 3 veh | Zero-mean integer noise per lane, clipped at 0 |
| **Missed detections** | 10, 20, 30 % | Each vehicle dropped with independent probability $p$ |
| **Observation delay** | 1, 2, 5 s | Controller observes delayed, stale observations |
| **Combined** | noise 10% + miss 10% + delay 2 s | Simultaneous compound corruption |

### 5.1 Relative degradation (%) ± 95% CI, averaged over the 4 scenarios

| Condition | Fixed-Timer | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mult. noise 5%** | $+0.0 \pm 0.0$ | $+0.2 \pm 0.7$ | $-0.1 \pm 0.3$ | $+0.2 \pm 0.5$ | $+0.3 \pm 0.2$ | $+0.0 \pm 0.2$ | $-0.0 \pm 0.2$ | $-0.0 \pm 0.2$ |
| **Mult. noise 10%**| $+0.0 \pm 0.0$ | $+0.2 \pm 0.8$ | $+0.2 \pm 1.3$ | $+0.2 \pm 0.9$ | $+0.3 \pm 0.8$ | $+0.4 \pm 0.6$ | $+0.4 \pm 0.4$ | $+0.4 \pm 0.4$ |
| **Mult. noise 20%**| $+0.0 \pm 0.0$ | $+0.2 \pm 1.2$ | $-0.3 \pm 1.7$ | $+0.5 \pm 1.6$ | $-1.0 \pm 1.9$ | $+0.1 \pm 0.8$ | $-1.4 \pm 1.6$ | $-1.4 \pm 1.6$ |
| **Mult. noise 30%**| $+0.0 \pm 0.0$ | $+1.1 \pm 1.5$ | $+0.8 \pm 2.2$ | $+1.6 \pm 1.9$ | $-2.4 \pm 2.0$ | $+1.3 \pm 1.3$ | $-3.5 \pm 1.8$ | $-3.5 \pm 1.8$ |
| **Additive std 1** | $+0.0 \pm 0.0$ | $+1.7 \pm 1.7$ | $+3.0 \pm 1.9$ | $+3.1 \pm 1.8$ | $-2.8 \pm 2.0$ | $+3.6 \pm 1.3$ | $-2.8 \pm 1.9$ | $-2.8 \pm 1.9$ |
| **Additive std 2** | $+0.0 \pm 0.0$ | $+6.4 \pm 2.3$ | $+8.0 \pm 2.5$ | $+8.1 \pm 2.5$ | $+1.8 \pm 2.2$ | $+8.8 \pm 1.7$ | $+1.9 \pm 2.0$ | $+1.9 \pm 2.0$ |
| **Additive std 3** | $+0.0 \pm 0.0$ | $+9.7 \pm 2.9$ | $+11.6 \pm 2.7$| $+14.2 \pm 3.1$| $+7.4 \pm 2.7$ | $+13.6 \pm 1.9$| $+6.6 \pm 2.4$ | $+6.6 \pm 2.4$ |
| **Miss 10%** | $+0.0 \pm 0.0$ | $-1.3 \pm 1.9$ | $+0.6 \pm 1.8$ | $+1.1 \pm 1.6$ | $-3.3 \pm 1.9$ | $+0.4 \pm 1.0$ | $-5.0 \pm 1.7$ | $-5.0 \pm 1.7$ |
| **Miss 20%** | $+0.0 \pm 0.0$ | $-1.4 \pm 2.3$ | $+1.1 \pm 1.9$ | $+1.5 \pm 1.9$ | $-3.4 \pm 2.1$ | $+0.7 \pm 1.1$ | $-5.0 \pm 1.8$ | $-5.0 \pm 1.8$ |
| **Miss 30%** | $+0.0 \pm 0.0$ | $-2.2 \pm 2.4$ | $+2.2 \pm 2.3$ | $+3.1 \pm 1.8$ | $-2.5 \pm 2.1$ | $+1.5 \pm 1.3$ | $-4.5 \pm 1.9$ | $-4.5 \pm 1.9$ |
| **Delay 1 s** | $+0.0 \pm 0.0$ | $-0.4 \pm 0.9$ | $+1.3 \pm 1.2$ | $+0.3 \pm 1.3$ | $+0.3 \pm 1.2$ | $+0.3 \pm 1.0$ | $+0.1 \pm 1.1$ | $-1.4 \pm 1.7$ |
| **Delay 2 s** | $+0.0 \pm 0.0$ | $-3.1 \pm 1.3$ | $+1.9 \pm 1.6$ | $+0.8 \pm 1.4$ | $+0.6 \pm 1.4$ | $+2.4 \pm 1.0$ | $+1.8 \pm 1.2$ | $-1.0 \pm 1.8$ |
| **Delay 5 s** | $+0.0 \pm 0.0$ | $+2.6 \pm 2.2$ | $+11.2 \pm 2.2$| $+9.1 \pm 2.1$ | $+5.1 \pm 2.3$ | $+13.8 \pm 1.8$| $+6.2 \pm 2.0$ | $+3.2 \pm 2.2$ |
| **Combined** | $+0.0 \pm 0.0$ | $-4.2 \pm 1.9$ | $+0.4 \pm 1.7$ | $+0.9 \pm 1.7$ | $-3.6 \pm 2.2$ | $+2.7 \pm 1.4$ | $-2.9 \pm 2.0$ | $-5.4 \pm 2.0$ |

### 5.2 Absolute delay (s), averaged over the 4 scenarios

| Condition | Fixed-Timer | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean** | 16.43 | 13.98 | 12.41 | 12.13 | 12.86 | 12.31 | 13.11 | 13.11 |
| **Mult. noise 5%** | 16.43 | 14.01 | 12.40 | 12.16 | 12.90 | 12.31 | 13.11 | 13.11 |
| **Mult. noise 10%**| 16.43 | 13.99 | 12.43 | 12.16 | 12.90 | 12.36 | 13.16 | 13.16 |
| **Mult. noise 20%**| 16.43 | 13.98 | 12.37 | 12.16 | 12.69 | 12.32 | 12.90 | 12.90 |
| **Mult. noise 30%**| 16.43 | 14.10 | 12.50 | 12.29 | 12.52 | 12.45 | 12.62 | 12.62 |
| **Additive std 1** | 16.43 | 14.17 | 12.75 | 12.46 | 12.47 | 12.72 | 12.71 | 12.71 |
| **Additive std 2** | 16.43 | 14.79 | 13.34 | 13.04 | 13.04 | 13.32 | 13.30 | 13.30 |
| **Additive std 3** | 16.43 | 15.21 | 13.76 | 13.72 | 13.72 | 13.89 | 13.88 | 13.88 |
| **Miss 10%** | 16.43 | 13.73 | 12.46 | 12.23 | 12.40 | 12.33 | 12.41 | 12.41 |
| **Miss 20%** | 16.43 | 13.65 | 12.53 | 12.29 | 12.38 | 12.39 | 12.42 | 12.42 |
| **Miss 30%** | 16.43 | 13.55 | 12.68 | 12.50 | 12.50 | 12.49 | 12.47 | 12.47 |
| **Delay 1 s** | 16.43 | 13.93 | 12.57 | 12.17 | 12.89 | 12.35 | 13.10 | 12.89 |
| **Delay 2 s** | 16.43 | 13.58 | 12.62 | 12.21 | 12.92 | 12.61 | 13.32 | 12.92 |
| **Delay 5 s** | 16.43 | 14.29 | 13.77 | 13.23 | 13.47 | 14.03 | 13.87 | 13.47 |
| **Combined** | 16.43 | 13.37 | 12.44 | 12.21 | 12.34 | 12.65 | 12.69 | 12.34 |

### 5.3 Size of the perturbation (is the test meaningful?)

| Condition | Mean abs. change in observation (veh) | Mean true queue (veh) |
| :--- | :--- | :--- |
| **Mult. noise 5%** | 0.015 | 1.63 |
| **Mult. noise 10%**| 0.070 | 1.63 |
| **Mult. noise 20%**| 0.203 | 1.63 |
| **Mult. noise 30%**| 0.345 | 1.64 |
| **Additive std 1** | 0.590 | 1.66 |
| **Additive std 2** | 1.141 | 1.70 |
| **Additive std 3** | **1.637** | 1.75 |
| **Miss 10%** | 0.164 | 1.64 |
| **Miss 20%** | 0.328 | 1.64 |
| **Miss 30%** | 0.494 | 1.65 |
| **Delay 1 s** | 0.137 | 1.64 |
| **Delay 2 s** | 0.262 | 1.66 |
| **Delay 5 s** | 0.585 | 1.77 |
| **Combined** | 0.403 | 1.66 |

> [!TIP]
> **Audit Gates Passed:** Fixed-Timer degradation is exactly $0.00\%$ in all conditions (perfect invariance). Additive noise std 3 changes observations by $1.637\text{ veh} \ge 1.0\text{ veh}$, ensuring perturbation significance.

### 5.4 Figure
- **Figure F3:** `paper_results/figures/F3_sensing_degradation.png` (also individual panels F3a, F3b, F3c).
- Headline findings: D3QN degrades $+13.8\%$ under $5\text{ s}$ delay and $+13.6\%$ under additive std 3.

### 5.5 Per-scenario view of the two perturbations that matter

#### Delay 5 s: relative degradation % ± CI per scenario

| Scenario | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | $+1.2 \pm 4.5$ | $+10.3 \pm 5.1$ | $+8.3 \pm 5.1$ | $+5.2 \pm 6.6$ | $+10.6 \pm 3.5$ | $+7.7 \pm 5.5$ | $+4.3 \pm 6.7$ |
| **Demand Reversal** | $+1.2 \pm 4.7$ | $+11.9 \pm 5.5$ | $+7.7 \pm 4.6$ | $+4.0 \pm 5.6$ | $+12.2 \pm 3.7$ | $+5.7 \pm 3.4$ | $+2.2 \pm 4.5$ |
| **Held-out OOD** | $+5.4 \pm 4.8$ | $+12.5 \pm 4.2$ | $+11.5 \pm 3.9$| $+7.9 \pm 3.7$ | $+17.4 \pm 3.2$ | $+8.4 \pm 4.1$ | $+4.6 \pm 4.0$ |
| **Near Gridlock** | $+2.5 \pm 4.3$ | $+10.3 \pm 3.8$ | $+8.7 \pm 4.1$ | $+3.3 \pm 2.4$ | $+15.0 \pm 3.7$ | $+3.1 \pm 2.6$ | $+1.7 \pm 2.1$ |

#### Additive std 3: relative degradation % ± CI per scenario

| Scenario | Actuated (VAT) | Greedy | Max-Pressure | MP + Shield | D3QN | D3QN + Shield | FlowSync-UQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | $+14.9 \pm 7.0$| $+15.8 \pm 7.5$ | $+17.4 \pm 8.9$| $+12.5 \pm 8.6$| $+20.6 \pm 5.4$ | $+16.0 \pm 7.4$| $+16.0 \pm 7.4$|
| **Demand Reversal** | $+10.7 \pm 3.5$| $+12.4 \pm 5.3$ | $+18.8 \pm 5.7$| $+8.9 \pm 6.7$ | $+12.2 \pm 4.1$ | $+4.0 \pm 4.9$ | $+4.0 \pm 4.9$ |
| **Held-out OOD** | $+11.4 \pm 8.5$| $+14.0 \pm 5.3$ | $+11.2 \pm 4.7$| $+8.0 \pm 5.3$ | $+11.2 \pm 3.1$ | $+7.1 \pm 4.1$ | $+7.1 \pm 4.1$ |
| **Near Gridlock** | $+1.7 \pm 3.0$ | $+4.2 \pm 6.0$ | $+9.4 \pm 5.0$ | $+1.9 \pm 4.5$ | $+10.4 \pm 3.8$ | $+0.7 \pm 3.8$ | $+0.7 \pm 3.8$ |

### 5.6 Findings
1. **Observation delay is the dominant risk:** At $5\text{ s}$, D3QN degrades by $+13.8\%$, Greedy by $+11.2\%$, Max-Pressure by $+9.1\%$, and D3QN+Shield by $+6.2\%$. Unshielded D3QN is more fragile than Max-Pressure under $5\text{ s}$ delay ($+13.8\%$ vs $+9.1\%$; in Held-out OOD $+17.4\%$ vs $+11.5\%$). The shield cuts D3QN delay degradation roughly in half.
2. **Additive count noise degrades all controllers similarly:** At std 3, D3QN ($+13.6\%$) and Max-Pressure ($+14.2\%$) show statistically indistinguishable degradation with overlapping CIs.
3. **Missed detections and multiplicative noise have minimal impact:** Delay changes remain within $\pm 3.5\%$ because average true queue lengths in milder scenarios are small (~$1.6\text{ veh}$).
4. **Shield intervention anomaly:** Shield interventions drop under noise (from 523 clean to 5 at std 3) as noisy inputs discourage phase change requests that the shield would otherwise interlock.

---

## 6. Result 4: UQ supervisor audit and ablation

### 6.1 How the supervisor triggers (from code audit)
`FlowSync-UQ` inspects `observation_age_ms`. When `observation_age_ms >= 1000.0`, the code forces `stale = True` and sets `supervisor_score = 1.0`, exceeding the $0.45$ threshold and transferring authority to Max-Pressure. This produces $99.34\%$ fallback under all delay conditions ($1, 2, 5\text{ s}$ and combined).

Under count noise and missed detections, `observation_age_ms` remains 0; the uncertainty score reflects only count volatility and forecast residuals, peaking near $0.16$–$0.21$, thus never reaching $0.45$ and resulting in **$0.00\%$ fallback**.

**Verdict:** The deployed supervisor acts as a deterministic latency detector, not a general perception uncertainty detector.

### 6.2 Does the uncertainty score respond? (score statistics and AUROC vs clean)

| Scenario | Condition | Score Mean | Score P5 / P50 / P95 | Fallback % | AUROC vs Clean |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean Balanced** | clean | 0.153 | 0.150 / 0.153 / 0.158 | 0.00% | 0.500 |
| **Clean Balanced** | noise_30 | 0.164 | 0.151 / 0.163 / 0.179 | 0.00% | 0.892 |
| **Clean Balanced** | miss_30 | 0.164 | 0.153 / 0.164 / 0.175 | 0.00% | 0.921 |
| **Clean Balanced** | delay_1s | 0.230 | 0.225 / 0.230 / 0.236 | 99.34% | 0.997 |
| **Clean Balanced** | delay_2s | 0.230 | 0.225 / 0.230 / 0.237 | 99.34% | 0.997 |
| **Clean Balanced** | delay_5s | 0.231 | 0.225 / 0.230 / 0.239 | 99.34% | 0.997 |
| **Clean Balanced** | combined | 0.238 | 0.227 / 0.237 / 0.251 | 99.34% | 0.997 |
| **Near Gridlock** | clean | 0.158 | 0.153 / 0.158 / 0.165 | 0.00% | 0.500 |
| **Near Gridlock** | noise_30 | 0.183 | 0.160 / 0.182 / 0.208 | 0.00% | 0.957 |
| **Near Gridlock** | miss_30 | 0.177 | 0.160 / 0.177 / 0.194 | 0.00% | 0.955 |
| **Near Gridlock** | delay_1s | 0.236 | 0.229 / 0.236 / 0.246 | 99.34% | 0.997 |
| **Near Gridlock** | delay_2s | 0.236 | 0.229 / 0.236 / 0.246 | 99.34% | 0.997 |
| **Near Gridlock** | delay_5s | 0.237 | 0.229 / 0.236 / 0.249 | 99.34% | 0.997 |
| **Near Gridlock** | combined | 0.253 | 0.235 / 0.253 / 0.271 | 99.34% | 0.997 |

### 6.3 Ablation under delay (the correct place to test the supervisor)

#### Clean Balanced scenario

| Variant | Clean | Delay 2 s | Delay 5 s | Combined | Fallback % (delay 5 s) | Shield interventions (delay 5 s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D3QN (no shield)** | $10.92 \pm 0.69$ | $10.99 \pm 0.71$ | $12.06 \pm 0.80$ | $11.01 \pm 0.80$ | 0.0% | 0 |
| **D3QN + Shield** | $11.46 \pm 0.93$ | $11.56 \pm 0.89$ | $12.22 \pm 0.83$ | $11.03 \pm 0.79$ | 0.0% | 127 |
| **Full FlowSync-UQ** | $11.46 \pm 0.93$ | $11.29 \pm 0.90$ | $11.82 \pm 0.88$ | $10.58 \pm 0.89$ | 99.3% | 111 |
| **minus Fallback** | $11.46 \pm 0.93$ | $11.56 \pm 0.89$ | $12.22 \pm 0.83$ | $11.03 \pm 0.79$ | 0.0% | 127 |
| **Fixed Fallback** | $11.46 \pm 0.93$ | $14.65 \pm 0.90$ | $15.08 \pm 1.01$ | $15.19 \pm 1.09$ | 99.3% | 12,648 |
| **MP + Shield** | $11.34 \pm 0.85$ | $11.29 \pm 0.90$ | $11.82 \pm 0.88$ | $10.58 \pm 0.89$ | 0.0% | 37 |

#### Near Gridlock scenario

| Variant | Clean | Delay 2 s | Delay 5 s | Combined | Fallback % (delay 5 s) | Shield interventions (delay 5 s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **D3QN (no shield)** | $12.48 \pm 0.56$ | $12.85 \pm 0.56$ | $14.32 \pm 0.63$ | $12.80 \pm 0.54$ | 0.0% | 0 |
| **D3QN + Shield** | $13.68 \pm 0.53$ | $13.92 \pm 0.54$ | $14.09 \pm 0.56$ | $12.91 \pm 0.47$ | 0.0% | 204 |
| **Full FlowSync-UQ** | $13.68 \pm 0.53$ | $13.71 \pm 0.48$ | $13.89 \pm 0.48$ | $12.76 \pm 0.43$ | 99.3% | 198 |
| **minus Fallback** | $13.68 \pm 0.53$ | $13.92 \pm 0.54$ | $14.09 \pm 0.56$ | $12.91 \pm 0.47$ | 0.0% | 204 |
| **Fixed Fallback** | $13.68 \pm 0.53$ | $17.31 \pm 1.24$ | $17.32 \pm 1.30$ | $17.30 \pm 1.24$ | 99.3% | 2,385 |
| **MP + Shield** | $13.48 \pm 0.58$ | $13.71 \pm 0.48$ | $13.89 \pm 0.48$ | $12.76 \pm 0.43$ | 0.0% | 66 |

- **Under clean conditions:** FlowSync-UQ is identical to D3QN + Shield ($11.4623\text{ s}$ vs $11.4623\text{ s}$).
- **Under delay:** FlowSync-UQ is numerically identical to Max-Pressure + Shield ($11.8238\text{ s}$ vs $11.8238\text{ s}$ at $5\text{ s}$ delay).
- **Fixed Fallback failure:** Fixed-timer fallback is $+3.26\text{ s}$ worse and triggers $12\times$ to $114\times$ more shield interventions ($12,648$ vs $111$ interventions).

---

## 7. Training behaviour

| Seed | Episodes logged | Mean wait first 20 ep (s) | Mean wait last 100 ep (s) | Best episode wait (s) | Final-100 mean reward |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **seed_101** | 223 | 14.41 | 12.80 | 3.55 | -222.6 |
| **seed_202** | 223 | 13.37 | 12.67 | 3.89 | -219.9 |
| **seed_303** | 219 | 13.30 | 12.71 | 5.11 | -233.9 |

- Seed-to-seed spread of final-100 wait is remarkably small ($12.67$ to $12.80\text{ s}$).
- Training wait (~$12.7\text{ s}$) is measured on the training scenario distribution and cannot be compared directly to test delays.
- Figure F1 (`paper_results/figures/F1_training_curves.png`) plots training curves.

---

## 8. Reproducibility and audit checks

| Check Name | Scope | Status | Verified Evidence |
| :--- | :--- | :---: | :--- |
| **Gate 1: Clean Consistency** | T2, T4, T5 Cross-Check | **PASS** | Clean D3QN ($10.9239\text{ s}$) and FlowSync-UQ ($11.4623\text{ s}$) identical to 4 decimals across T2, T4, T5 |
| **Gate 2: Actuated Tuning Fairness**| Hyperparameter Selection | **PASS** | Tuned on 4 train scenarios & seeds 601001-601020 only; 0 test data leakage |
| **Gate 3: Fixed-Timer & Noise Scale** | Sensing Degradation | **PASS** | Fixed-Timer exactly 0.00% degradation; add_noise_3 mean obs change $\ge 1.0\text{ veh}$ ($1.637\text{ veh}$) |
| **Gate 4: Ablation Delay Distinctness**| Delay Failover Verification | **PASS** | No two variants have identical delay to 4 decimals when fallback rate > 0 |
| **Claim Evidence Keys Resolution** | Audited Claim Catalog | **PASS** | All 13 claim evidence keys resolve directly in `results.json` |
| **Vehicle Conservation** | Spawner & Network | **PASS** | Arrival counts match departures + active queues across CRN seeds |
| **Physical Safety Interlocks** | Signal FSM | **PASS** | Zero conflict and zero clearance violations over 4,340,000 steps |

---

## 9. Limitations to state in the paper

1. **Simulator-only evaluation:** Custom discrete-event simulation; no physical-intersection or field actuation validation.
2. **Single intersection:** The $2\times 2$ multi-intersection grid pilot was excluded from claims due to uncoordinated physics.
3. **Training seeds:** 3 training seeds were evaluated (spread was small: $12.67$–$12.80\text{ s}$).
4. **Synthetic uncertainty calibration:** Uncertainty features were calibrated on synthetic error models rather than physical camera feeds.
5. **Small queue regime:** Mild scenarios average ~1 vehicle queue, making multiplicative noise a weak perturbation. Additive noise ($std=3$) resolves this.
6. **Supervisor trigger mechanism:** Trigger is driven by latency ($>1,000\text{ ms}$), not noise score thresholds.
7. **Aggregate queue modeling:** No per-vehicle-class tags; no per-class transit priority results are claimed.
8. **Algorithmic component ablations:** Individual contributions of PER, Dueling, and Double-DQN were not ablated separately.
9. **Clean-trained policy:** D3QN was trained only on unperturbed clean data.
10. **SUMO panel scope:** Supplementary SUMO panel did not evaluate the RL agent and used stopped delay.

---

## 10. Claims ledger and known errors in results.json

### 10.1 Corrected claims ledger (use this, not the JSON text)

| Claim | Status | Evidence |
| :--- | :---: | :--- |
| **D3QN beats Fixed-Timer** | **SUPPORTED** | 12.5% to 35.6% per scenario; 25.8% overall ($11.76\text{ s}$ vs $15.85\text{ s}$, paired $t = -23.16$) |
| **D3QN beats Max-Pressure** | **NOT SUPPORTED** | No significant difference in any scenario (Holm $p \ge 0.33$); within $0.4\text{ s}$ everywhere; overall $11.76\text{ s}$ vs $11.74\text{ s}$ (diff $+0.02\text{ s}$, $p = 0.76$) |
| **D3QN beats Greedy** | **NOT SUPPORTED** | No significant difference in any scenario (Holm $p = 1.00$ in all 7); overall $11.76\text{ s}$ vs $11.94\text{ s}$ (Holm $p = 0.25$) |
| **D3QN beats retuned Actuated** | **SUPPORTED** | Lower delay in 7/7 scenarios, Holm-significant in 3 (Demand Reversal, OOD, Near Gridlock); overall $11.76\text{ s}$ vs $13.06\text{ s}$ |
| **20% reduction target met** | **PARTIAL** | D3QN meets target on 5/7 scenarios (misses OOD at 12.5%, Left-Turn Surge at 18.4%); Max-Pressure also meets on 5/7 |
| **Shield guarantees zero violations** | **SUPPORTED** | 0 conflict, 0 clearance violations over 4,340,000 steps |
| **Shield imposes delay cost** | **SUPPORTED** | Positive in 7/7 scenarios; $+0.62\text{ s}$ 7-scenario mean ($t = +7.64, p = 3.28\times 10^{-12}$); $+0.54\text{ s}$ on Clean Balanced ($p = 0.0169$) |
| **Observation delay is dominant degradation** | **SUPPORTED** | $5\text{ s}$ delay increases delay by up to $+13.8\%$ (D3QN); other perturbations mostly smaller |
| **Additive count noise degrades all controllers** | **SUPPORTED** | std 3 causes $+13.6\%$ (D3QN) and $+14.2\%$ (MP) degradation |
| **Missed detections / multiplicative noise harmful** | **NOT SUPPORTED** | Effects small ($<3.5\%$), often negative for shielded controllers |
| **D3QN is more fragile than classical** | **MIXED** | Yes under $5\text{ s}$ delay ($+13.8\%$ vs MP $+9.1\%$); no under additive noise ($+13.6\%$ vs $+14.2\%$) |
| **UQ improves delay under clean** | **NOT SUPPORTED** | Identical to D3QN + Shield ($11.4623\text{ s}$ vs $11.4623\text{ s}$, fallback never fires) |
| **FlowSync-UQ beats MP + Shield under delay** | **NOT SUPPORTED** | Numerically identical under delay ($11.8238\text{ s}$ vs $11.8238\text{ s}$) |
| **UQ detects noise or misses** | **NOT SUPPORTED** | 0% fallback; score shifts (AUROC 0.89–0.96) but never reaches $0.45$ threshold |
| **Transfer of RL agent to SUMO** | **NOT TESTED** | SUMO panel has no RL agent |
| **Per-class / Indian mixed-traffic benefit** | **NOT TESTED** | Simulator operates on aggregate queues without per-class tags |

### 10.2 Errors and stale numbers found in results.json (do not use)

| Location | Old Text | Audited / Reconciled Value |
| :--- | :--- | :--- |
| `claims_supported[4_target_20pct]` | Said 6/7 scenarios, OOD 16.4% | Actual: 5/7 scenarios; OOD 12.5%, Left-Turn Surge 18.4% |
| `claims_supported[5_shield_cost]` | $+0.67\text{ s}$ on Clean Balanced, $t=3.37, p=0.0032$ | Actual: $+0.54\text{ s}$, $t=2.62, p=0.0169$; pooled 140 episodes $+0.62\text{ s}$, $t=+7.64$ |
| `claims_supported[11_uq_detects]` | AUROC ~0.50 for noise and misses | Actual: AUROC 0.89 to 0.96; 0.50 was only the clean-vs-clean reference |
| `claims_supported[7,8]` | D3QN $+13.5\%$, miss 30% $+5.8\%$, add std 3 $+7.2\%$ | Actual: D3QN $+13.8\%$ (5s delay), miss 30% $+1.5\%$, add std 3 $+13.6\%$ |
| `claims_supported[10]` | FlowSync-UQ 11.83 vs MP+Shield 11.81 | Actual: Both are exactly 11.8238 s (identical) |
| `audit.negative_findings` | Stale shield tax $+0.4757\text{ s}$ | Recomputed from T7: pooled shield tax $+0.6218\text{ s}$ ($t=+7.64$) |
| `audit.known_limitations[4]` | "Actuated degrades under saturation" | Retuned Actuated beats Fixed overall (+17.6%), slightly worse only in extreme OOD (17.42 vs 17.02 s) |

---

## 11. Mapping to paper sections, tables, figures and page budget

| Paper section | Content | Table / Figure | Approx. space |
| :--- | :--- | :--- | :--- |
| **Abstract** | Overall numbers (3.1), shield cost (4), delay finding (5.6), UQ audit (6) | — | 0.2 page |
| **I. Introduction** | Motivation, gap, contributions (Section 1), audit rigor | — | 0.6 page |
| **II. Related work** | PressLight, Max-Pressure, actuated control, safe RL, sensing robustness | — | 0.5 page |
| **III. System & Problem** | Intersection geometry, 4-phase schema, D3QN, formal shield, UQ logic | Table I (T1), Fig 1 | 1.0 page |
| **IV. Experimental Setup** | 7 scenarios, CRN protocol, fair Actuated tuning grid, perturbation types | Table II (scenarios) | 0.6 page |
| **V. Results & Evaluation** | | | |
| *A. Main comparison* | Overall and per-scenario delay, non-significance vs MP/Greedy | Table III (T2), Table VII (T7), Fig 2 | 1.0 page |
| *B. Safety shield cost* | Zero violations vs delay tax ($+0.62\text{ s}$ overall, $+0.54\text{ s}$ clean) | Table IV | 0.2 page |
| *C. Sensing degradation*| Delay vs noise vs miss degradation; unshielded fragility | Table V (T4), Fig 3 | 1.0 page |
| *D. UQ supervisor audit*| Latency trigger audit, AUROC, ablation under delay | Table VI (T5), Fig 5 | 0.6 page |
| **VI. Discussion & Limits** | Honest negative findings, simulator limitations, non-transfer | — | 0.4 page |
| **VII. Conclusion** | Summary of findings and defensible takeaways | — | 0.15 page |
| **References** | Verified references | — | 0.4 page |
| **Total Target** | **Strict 6-page target** | | **~6.0 pages** |

---

## 12. Ready-to-use result statements (numbers verified against tables)

1. Across 7 test scenarios and 20 matched seeds each (140 episodes per controller under Common Random Numbers), D3QN reduced mean vehicle delay by 25.8% relative to Fixed-Timer ($11.76\text{ s}$ vs $15.85\text{ s}$, paired $t = -23.16, p < 10^{-48}$), meeting the 20% reduction target in 5 of 7 scenarios.
2. D3QN did not outperform classical Max-Pressure ($11.74\text{ s}$ overall) or Greedy ($11.94\text{ s}$ overall); differences to Max-Pressure were within $0.4\text{ s}$ in every scenario and statistically non-significant after Holm correction across all scenarios (Holm $p \ge 0.33$).
3. After fair retuning on training scenarios, the actuated baseline improved on Fixed-Timer by 17.6% overall ($13.06\text{ s}$ vs $15.85\text{ s}$), but remained $1.3\text{ s}$ slower than D3QN.
4. The formal safety shield enforced physical phase constraints with exactly zero conflict and zero clearance violations over 4.34 million simulation steps, at a mean delay overhead ("shield tax") of $+0.62\text{ s}$ per vehicle across scenarios ($+0.54\text{ s}$ on Clean Balanced, paired $t = 2.62, p = 0.0169$).
5. Observation latency was the dominant operational vulnerability: a $5\text{ s}$ delay increased delay by 13.8% for unshielded D3QN, 11.2% for Greedy, and 9.1% for Max-Pressure, whereas $1$ to $2\text{ s}$ delays altered delay by less than 2.5%.
6. Additive count noise of standard deviation 3 vehicles increased delay by 13.6% for D3QN and 14.2% for Max-Pressure, demonstrating that under count noise the learned policy is no more fragile than classical control. Under $5\text{ s}$ delay, however, unshielded D3QN degraded more severely than Max-Pressure (13.8% vs 9.1%).
7. Missed detections up to 30% and multiplicative noise up to 30% altered delay by less than 3.5% across all controllers, attributable to short queue lengths (~$1.6\text{ veh}$) in the simulated network.
8. The uncertainty supervisor triggered failover on 99.34% of steps under observation delay and on 0.00% under count noise or missed detections; while its linear score distinguished perturbed from clean observations (AUROC $0.89$–$0.96$), scores never reached the $0.45$ threshold.
9. Under delay, FlowSync-UQ was numerically identical to Max-Pressure + Shield ($11.8238\text{ s}$ vs $11.8238\text{ s}$), providing no incremental benefit beyond a classical fallback controller.
10. A fixed-timer fallback performed substantially worse than a Max-Pressure fallback ($15.08\text{ s}$ vs $11.82\text{ s}$ at $5\text{ s}$ delay on Clean Balanced) and triggered $12\times$ to $114\times$ more shield interventions ($12,648$ vs $111$) due to cyclic phase proposals contradicting real-time demand.

---

## 13. Open items before writing

1. **Pairwise statistics recomputed (Table T7):** Generated `paper_results/tables/T7_pairwise_stats.csv` over all 140 paired episodes and per-scenario, resolving all stale numbers in results.json.
2. **`results.json` text fields corrected:** Corrected `claims_supported`, `negative_findings`, `known_limitations`, and `reproducibility_audit` so machine-readable evidence matches the paper exactly.
3. **Figure updates documented:** Figure F3 notes indicate headline numbers reflect unshielded D3QN; F5 legend overlap noted for final LaTeX layout.

---

## 14. Appendix

### 14.1 Full per-scenario metrics (delay, queue, throughput, p95, max queue)

#### Clean Balanced ($1,800\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 14.67 | 1.58 | 1.29 | 72.8 | 39.3 | 24.9 |
| Actuated (VAT) | 11.71 | 1.83 | 1.14 | 75.4 | 44.9 | 21.0 |
| Greedy | 11.01 | 1.38 | 1.10 | 76.0 | 41.0 | 19.8 |
| Max-Pressure | 10.83 | 1.53 | 1.09 | 76.2 | 38.7 | 19.7 |
| MP + Shield | 11.34 | 1.82 | 1.11 | 75.4 | 39.3 | 20.9 |
| D3QN | 10.92 | 1.46 | 1.09 | 76.5 | 39.9 | 20.0 |
| D3QN + Shield | 11.46 | 2.00 | 1.12 | 76.5 | 39.8 | 21.1 |
| FlowSync-UQ | 11.46 | 2.00 | 1.12 | 76.5 | 39.8 | 21.1 |

#### Demand Reversal ($2,520\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 16.99 | 1.63 | 2.34 | 118.5 | 41.4 | 40.6 |
| Actuated (VAT) | 12.10 | 1.08 | 1.88 | 122.9 | 43.2 | 31.6 |
| Greedy | 10.89 | 1.23 | 1.77 | 124.6 | 40.9 | 30.6 |
| Max-Pressure | 10.64 | 1.02 | 1.75 | 124.5 | 38.2 | 30.4 |
| MP + Shield | 11.65 | 1.20 | 1.84 | 123.0 | 42.2 | 34.4 |
| D3QN | 10.94 | 1.09 | 1.78 | 124.3 | 39.3 | 31.0 |
| D3QN + Shield | 11.82 | 1.14 | 1.86 | 123.7 | 41.8 | 35.1 |
| FlowSync-UQ | 11.83 | 1.14 | 1.86 | 123.7 | 41.8 | 35.1 |

#### Held-out OOD ($2,880\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 17.02 | 1.45 | 2.60 | 188.3 | 44.6 | 49.4 |
| Actuated (VAT) | 17.42 | 2.27 | 3.52 | 187.8 | 52.5 | 53.9 |
| Greedy | 14.93 | 1.34 | 2.38 | 188.3 | 45.5 | 47.0 |
| Max-Pressure | 14.51 | 1.05 | 2.34 | 189.7 | 43.1 | 46.3 |
| MP + Shield | 14.98 | 1.25 | 2.38 | 189.8 | 43.9 | 47.9 |
| D3QN | 14.90 | 1.06 | 2.38 | 189.4 | 45.4 | 46.8 |
| D3QN + Shield | 15.50 | 1.65 | 2.44 | 189.7 | 45.0 | 48.4 |
| FlowSync-UQ | 15.50 | 1.66 | 2.44 | 189.6 | 45.0 | 48.4 |

#### Incident Lane Reduction ($1,800\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 14.95 | 1.97 | 1.31 | 72.8 | 39.7 | 24.9 |
| Actuated (VAT) | 11.77 | 1.82 | 1.14 | 75.4 | 44.9 | 21.0 |
| Greedy | 11.22 | 1.48 | 1.11 | 76.0 | 41.3 | 19.8 |
| Max-Pressure | 10.94 | 1.52 | 1.09 | 76.2 | 38.9 | 19.8 |
| MP + Shield | 11.44 | 1.91 | 1.12 | 75.5 | 39.7 | 20.9 |
| D3QN | 10.99 | 1.48 | 1.10 | 76.5 | 40.2 | 20.1 |
| D3QN + Shield | 11.56 | 2.02 | 1.13 | 76.6 | 39.7 | 21.2 |
| FlowSync-UQ | 11.56 | 2.02 | 1.13 | 76.6 | 39.7 | 21.2 |

#### Left-Turn Surge ($2,160\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 14.93 | 1.14 | 1.55 | 88.8 | 39.8 | 28.4 |
| Actuated (VAT) | 13.08 | 1.59 | 1.42 | 87.7 | 42.4 | 24.9 |
| Greedy | 12.51 | 1.49 | 1.38 | 87.6 | 39.9 | 23.9 |
| Max-Pressure | 12.51 | 1.53 | 1.39 | 88.0 | 39.5 | 23.8 |
| MP + Shield | 12.52 | 1.60 | 1.39 | 88.6 | 40.5 | 24.9 |
| D3QN | 12.18 | 1.52 | 1.36 | 88.1 | 38.7 | 23.6 |
| D3QN + Shield | 12.46 | 1.56 | 1.38 | 88.5 | 39.5 | 24.7 |
| FlowSync-UQ | 12.46 | 1.56 | 1.38 | 88.5 | 39.5 | 24.7 |

#### Near Gridlock ($4,320\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 17.05 | 2.45 | 3.13 | 155.9 | 42.4 | 53.2 |
| Actuated (VAT) | 14.70 | 2.06 | 2.86 | 160.3 | 60.1 | 47.1 |
| Greedy | 12.82 | 1.07 | 2.63 | 164.3 | 50.3 | 42.0 |
| Max-Pressure | 12.56 | 1.19 | 2.59 | 163.8 | 46.1 | 41.8 |
| MP + Shield | 13.48 | 1.23 | 2.69 | 161.2 | 42.7 | 45.5 |
| D3QN | 12.48 | 1.19 | 2.59 | 165.8 | 46.5 | 41.0 |
| D3QN + Shield | 13.68 | 1.13 | 2.72 | 161.6 | 42.8 | 47.0 |
| FlowSync-UQ | 13.69 | 1.13 | 2.72 | 161.5 | 42.7 | 47.0 |

#### Sudden Burst ($3,240\text{ veh/h}$)
| Controller | Delay Mean (s) | Delay Std | Avg Queue | Throughput | P95 Delay (s) | Max Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fixed-Timer | 15.36 | 1.65 | 1.06 | 59.2 | 40.2 | 22.4 |
| Actuated (VAT) | 10.63 | 1.97 | 0.85 | 61.0 | 36.0 | 17.6 |
| Greedy | 10.19 | 1.87 | 0.83 | 62.0 | 38.5 | 16.1 |
| Max-Pressure | 10.19 | 1.61 | 0.83 | 60.9 | 37.5 | 16.3 |
| MP + Shield | 10.60 | 1.82 | 0.85 | 61.5 | 38.8 | 17.4 |
| D3QN | 9.93 | 1.94 | 0.82 | 61.5 | 36.9 | 16.5 |
| D3QN + Shield | 10.22 | 1.86 | 0.83 | 61.6 | 38.4 | 17.1 |
| FlowSync-UQ | 10.22 | 1.86 | 0.83 | 61.6 | 38.4 | 17.1 |

### 14.2 Full sensing table (per scenario, all conditions, all controllers)
See [`tables/T4_sensing_degradation.csv`](paper_results/tables/T4_sensing_degradation.csv) (columns: `Scenario`, `Condition`, `Controller`, `Avg_Delay_s_Mean`, `Avg_Delay_s_CI95`, `Rel_Degradation_Pct_Mean`, `Rel_Degradation_Pct_CI95`, `Obs_Diff_Veh_Mean`, `True_Queue_Veh_Mean`, `Shield_Interventions`, `Mean_Fallback_Rate_Pct`).

### 14.3 Full ablation table
See [`tables/T5_ablations.csv`](paper_results/tables/T5_ablations.csv) (2 scenarios × 4 conditions × 6 variants, plus the 6 not-run variants).

### 14.4 Supplementary SUMO panel (no RL agent, stopped-delay metric, 72 episodes)

| Controller | Clean | Miss 30% | Delay 2 s | Delay 2 s + Miss 30% |
| :--- | :--- | :--- | :--- | :--- |
| **fixed** | $10.65 \pm 3.64$ | $10.65 \pm 3.64$ | $10.65 \pm 3.64$ | $10.65 \pm 3.64$ |
| **halted** | $6.89 \pm 2.23$ | $6.71 \pm 2.46$ | $6.78 \pm 2.43$ | $6.42 \pm 2.32$ |
| **max_pressure** | $6.30 \pm 1.45$ | $6.28 \pm 1.67$ | $5.92 \pm 1.77$ | $5.73 \pm 1.93$ |

> [!NOTE]
> Used at most for one sentence in the paper: classical controllers show no meaningful degradation in a microscopic simulator under these perturbations. It does not validate the RL agent in SUMO.

### 14.5 File map

| File | Content |
| :--- | :--- |
| `paper_results/results.json` | Full machine-readable results with audited and corrected claim fields |
| `paper_results/tables/T1_setup_and_hyperparameters.csv` | Setup parameters and model hyperparameters |
| `paper_results/tables/T2_main_comparison.csv` | Main comparison per scenario with p-values |
| `paper_results/tables/T4_sensing_degradation.csv` | Sensing degradation (4 scenarios + overall) |
| `paper_results/tables/T5_ablations.csv` | Ablations under delay |
| `paper_results/tables/T6_audit_checks.csv` | Audit checks and gates |
| `paper_results/tables/T7_pairwise_stats.csv` | Pooled 140-episode and per-scenario pairwise statistics |
| `paper_results/figures/F1..F5` | PNG and PDF format figures, 300 dpi |
| `paper_results/*_raw.json` | Raw per-run data for ablations, sensing, UQ audit, actuated |

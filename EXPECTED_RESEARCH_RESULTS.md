# FlowSync-UQ: Expected Research Results

This document defines the target research results that FlowSync-UQ aims to achieve
and report in the IEEE research paper. All numerical values are **expected targets**,
not achieved outcomes. Targets are grounded in the system's architecture, evaluation
protocol, and the traffic-control research literature.

---

## 1. Research Objectives

FlowSync-UQ investigates whether a **Dueling Double Deep Q-Network (D3QN)** traffic
signal controller, augmented with calibrated perception-uncertainty estimation and a
hysteretic Max-Pressure fallback supervisor, can operate safely and competitively under
realistic vision-sensor corruption at a single signalised intersection.

The research does **not** aim to prove that DRL universally outperforms classical
controllers. It aims to produce an honest, reproducible empirical audit of
uncertainty-aware safe fallback control under delivered sensor faults.

### Core Research Questions

| ID   | Research Question |
|------|-------------------|
| RQ1  | Does shielded D3QN achieve competitive mean stopped delay compared with shielded Max-Pressure under matched experimental conditions? |
| RQ2  | What is the measurable delay cost imposed by the safety shield, and is the anti-starvation protection justified? |
| RQ3  | Does the two-tier physical signal state machine guarantee zero clearance violations across all audited signal samples? |
| RQ4  | Does the full end-to-end perception-to-actuation pipeline execute within a 100 ms (10 Hz) soft real-time deadline on commodity hardware? |
| RQ5  | Does the calibrated uncertainty estimator reliably detect perception degradation and trigger fallback without inducing control chattering? |
| RQ6  | How does Max-Pressure perform under synthetic vision-sensor faults in an independent SUMO simulation? |

---

## 2. Primary Numerical Targets — Custom Simulator

### 2.1 Experimental Scale

| Parameter | Target |
|-----------|--------|
| Total simulation runs | ≥ 2,500 |
| Controller variants evaluated | ≥ 7 (Fixed, Actuated, Greedy, Max-Pressure, D3QN bare, D3QN + Shield, FlowSync-UQ) |
| Independent D3QN training replicates | ≥ 3 (distinct random seeds) |
| Paired traffic evaluation seeds | ≥ 20 (Common Random Numbers across all controllers) |
| Clean traffic scenario templates | ≥ 5 (balanced, near-gridlock, left-turn surge, sudden burst, demand reversal, incident reduction, held-out OOD) |
| Sensor fault conditions | ≥ 3 (missed detections, observation latency, combined severe) |
| Total audited signal samples | ≥ 4,000,000 |

### 2.2 Controller Performance — Mean Stopped Delay

All values are mean stopped waiting time per vehicle (seconds) aggregated across
all evaluation cells and traffic seeds. The experimental unit is one traffic-seed
cell, with D3QN replicates averaged per seed to maintain paired-sample consistency.

| Controller | Target Mean Delay (s) | Interpretation |
|------------|----------------------|----------------|
| Fixed-Time | 14–17 | Passive baseline with no demand adaptation |
| Vehicle-Actuated | 14–19 | Gap-based reactive controller; vulnerable to starvation under asymmetric demand |
| Greedy (max queue) | 10–13 | Instantaneous queue-maximising heuristic |
| Max-Pressure (bare) | 10–13 | Theoretical queue-stability guarantee (Varaiya 2013) |
| D3QN (bare) | 10–13 | Competitive with Max-Pressure; not expected to be conclusively superior |
| Max-Pressure + Shield | 11–14 | Slight delay increase from anti-starvation and max-green enforcement |
| D3QN + Shield | 11–14 | Competitive with shielded Max-Pressure under matched conditions |
| FlowSync-UQ | 11–14 | D3QN + Shield + uncertainty fallback; no large incremental delay change expected |

**Key target:** The D3QN policy should achieve mean delay within ±1.0 s of Max-Pressure
across the full evaluation matrix, demonstrating competitive performance rather than
necessarily strict superiority.

### 2.3 Paired Statistical Comparisons

These are the expected contrasts using paired two-sided Student's t-tests with
N ≥ 200 evaluation cells (scenario × condition × seed combinations with replicates
averaged per seed) and 95% confidence intervals.

| Comparison | Expected Contrast (s) | Expected 95% CI Width | Interpretation |
|------------|----------------------|----------------------|----------------|
| D3QN + Shield vs. MP + Shield | ±0.5 (near zero) | ≤ 0.40 s half-width | Competitive; CI likely spans zero |
| D3QN bare vs. MP bare | ±0.5 (near zero) | ≤ 0.35 s half-width | No conclusive superiority of either |
| FlowSync-UQ vs. D3QN + Shield | ±0.2 (near zero) | ≤ 0.15 s half-width | Fallback adds no measurable delay benefit or penalty |
| D3QN + Shield vs. D3QN bare | +0.3 to +0.6 | Excluding zero (significant) | Shield imposes measurable delay cost |
| MP + Shield vs. MP bare | +0.3 to +0.6 | Excluding zero (significant) | Shield cost observable on both controllers |
| D3QN bare vs. Fixed-Time | −3.0 to −5.0 | Excluding zero (significant) | Both D3QN and MP substantially outperform Fixed |
| D3QN bare vs. Actuated | −3.0 to −6.0 | Excluding zero (significant) | Both D3QN and MP substantially outperform Actuated |

**Statistical method targets:**
- All comparisons use paired t-tests with Common Random Numbers.
- Report Holm-Bonferroni adjusted p-values across all comparisons.
- Report paired Cohen's d_z effect sizes.
- Distinguish the single pre-specified primary comparison (D3QN + Shield vs. MP + Shield)
  from post-hoc exploratory comparisons.
- Do not claim equivalence based on non-significant p-values.

### 2.4 Within-Run Tail Delay

| Metric | Target Range |
|--------|-------------|
| Within-run P95 stopped delay — Max-Pressure | 35–45 s |
| Within-run P95 stopped delay — D3QN + Shield | 35–45 s |
| Within-run P95 stopped delay — Fixed-Time | 35–45 s |
| Within-run P95 stopped delay — Actuated | 50–70 s |

**Note:** Within-run P95 is the average of per-episode 95th-percentile delay, not a
pooled vehicle percentile.

### 2.5 Throughput

| Controller | Target Vehicles Served per Episode |
|------------|-----------------------------------|
| Fixed-Time | 90–100 |
| Actuated | 85–95 |
| Greedy / Max-Pressure | 98–105 |
| D3QN + Shield | 98–105 |
| FlowSync-UQ | 98–105 |

---

## 3. Safety and Signal Integrity Targets

### 3.1 Physical Signal State Machine

| Metric | Target |
|--------|--------|
| Signal-phase conflict violations | **Exactly 0** across all audited samples |
| Clearance interval violations | **Exactly 0** across all audited samples |
| Total audited signal tick samples | ≥ 4,000,000 (custom) + ≥ 100,000 (SUMO) |
| Minimum green enforcement | 8.0 s enforced in every episode |
| Yellow clearance duration | 2.0 s (custom sim) / 3.0 s (SUMO) — never preempted |
| All-red clearance duration | 3.0 s (custom sim) / 1.0 s (SUMO) — never preempted |

**Note:** Zero signal-conflict violations confirm deterministic enforcement of simulated
cabinet clearance rules. This does not claim collision-free real-world vehicle safety.

### 3.2 Safety Shield Behaviour

| Metric | Target |
|--------|--------|
| Shield override rate (D3QN) | 0.1% – 2.0% of decision steps |
| Dominant override reason | Anti-starvation (≥ 95% of overrides) |
| Max-green ceiling overrides | Rare (< 5% of total overrides) |
| Shield override rate (Max-Pressure) | ≤ 0.5% of decision steps |

**Key target:** Shield overrides should be dominated by anti-starvation interventions,
confirming that the D3QN policy occasionally neglects low-demand phases and that the
shield prevents extreme tail waiting.

### 3.3 Phase Starvation Prevention

| Metric | Target |
|--------|--------|
| Maximum unserved phase waiting (any phase, any episode) | ≤ 55 s with shield, potentially > 60 s without shield |
| Starvation events (phases exceeding 45 s threshold) without shield | > 0 in high-demand scenarios |
| Starvation events with shield active | Significantly reduced compared to unshielded |

---

## 4. Uncertainty Estimation and Fallback Targets

### 4.1 Calibrated Uncertainty Model

| Parameter | Target |
|-----------|--------|
| Candidate uncertainty features | 7 (detector confidence, tail confidence, count volatility, forecast residual, observation age, frame drop, track instability) |
| Active fitted features after calibration | 2–3 (count volatility and forecast residual expected to dominate) |
| Calibration method | Logistic regression on synthetic count-error labels |
| Calibration target | Aggregate absolute count error ≥ 3 vehicles across 12 movements |
| Enter threshold (τ_high) | 0.50 – 0.70 (fitted, not hand-tuned) |
| Recover threshold (τ_low) | 0.30 – 0.45 (fitted, not hand-tuned) |
| Threshold gap (hysteresis band) | τ_high − τ_low ≥ 0.15 |

### 4.2 Fallback Supervisor Behaviour

| Metric | Target |
|--------|--------|
| Control frequency | 10 Hz (one decision per 0.1 s tick) |
| Minimum dwell in fallback | 40 ticks (4.0 s) |
| Recovery persistence window | 10 consecutive low-uncertainty ticks (1.0 s) |
| Chattering events (rapid authority oscillation) | **0** (hysteresis eliminates limit cycles) |
| Fallback activations under clean sensing | **0** or near-zero |
| Fallback activations under sensor faults | > 0, proportional to fault severity |
| Right-censored activations (still active at episode end) | Expected under persistent sensor faults; report as right-censored, not as ordinary durations |

### 4.3 Fallback Timing Analysis

| Metric | Target |
|--------|--------|
| Mean recovered fallback duration | 10–25 s (among activations that recover before episode end) |
| Right-censored fraction under persistent faults | 40%–70% (faults sustained through episode) |
| Mean observed duration (all activations, censored + uncensored) | Report with explicit right-censoring disclosure; do not present as uncensored mean |

**Key target:** The fallback supervisor should activate reliably under sensor faults
and not activate under clean sensing. The system should demonstrate that the hysteretic
design prevents chattering without requiring manual threshold tuning.

---

## 5. Computational Efficiency Targets

### 5.1 End-to-End Latency (Commodity x86_64 CPU)

| Pipeline Stage | Target Mean (ms) | Target P95 (ms) | Target Max (ms) |
|----------------|------------------|------------------|------------------|
| Frame decode | 3–6 | 4–7 | < 10 |
| YOLOv8n object detection (CPU) | 40–65 | 50–75 | < 250 |
| ByteTrack multi-object tracking | < 0.5 | < 0.5 | < 1.0 |
| ROI mapping | < 0.1 | < 0.1 | < 0.1 |
| **Perception subtotal** | **45–70** | **55–80** | **< 250** |
| State builder | < 0.1 | < 0.1 | < 0.5 |
| Uncertainty engine | < 0.5 | < 0.5 | < 10 |
| D3QN inference | < 0.5 | < 0.5 | < 5 |
| Max-Pressure fallback | < 0.1 | < 0.1 | < 0.5 |
| Supervisor state machine | < 0.05 | < 0.05 | < 0.1 |
| SafetyShield + FSM | < 0.1 | < 0.1 | < 0.5 |
| **Controller subtotal** | **< 1.0** | **< 1.0** | **< 15** |
| **Total end-to-end** | **< 70** | **< 85** | **< 250** |

### 5.2 Real-Time Compliance

| Criterion | Target |
|-----------|--------|
| Soft 10 Hz deadline (100 ms) — P95 compliance | ≥ 95% of ticks complete within 100 ms |
| P99 latency | < 200 ms |
| Controller-only latency (excluding perception) | < 1.0 ms mean |
| Hard real-time guarantee | **Not claimed** — tail spikes from CPU inference prevent certification |

### 5.3 Model Efficiency

| Parameter | Target |
|-----------|--------|
| D3QN policy network parameters | < 200,000 |
| Network architecture | Shared 256→256 backbone + dueling V(s)/A(s,a) streams |
| Training wall-clock time | ≤ 15 minutes per seed on commodity CPU |
| Training episodes | 200–500 online episodes after demonstration pre-training |
| Demonstration pre-training | 200 episodes of Max-Pressure behaviour cloning + 2,000 BC gradient updates + 500 TD warmup updates |

---

## 6. Robustness Under Sensor Faults — Custom Simulator

### 6.1 Fault Conditions

| Condition | Parameters | Purpose |
|-----------|-----------|---------|
| Clean | No faults | Baseline reference |
| Missed detections (30%) | Bernoulli miss rate = 0.30 | Moderate occlusion |
| Observation latency (1,000 ms) | 10-tick video delivery delay | Severe stale observations |
| Combined severe | miss = 0.20, latency = 200 ms, false positives λ = 0.15, jitter σ = 0.03 | Realistic multi-fault scenario |

### 6.2 Expected Robustness Targets

| Metric | Target |
|--------|--------|
| D3QN delay degradation under combined faults | < 15% increase relative to clean |
| Max-Pressure delay degradation under combined faults | < 10% increase relative to clean |
| Controller ranking stability across fault conditions | Max-Pressure and D3QN maintain comparable performance; neither consistently dominates under faults |
| Uncertainty score elevation under faults vs. clean | Measurable increase (≥ 0.10 average score difference) confirming fault detection |

---

## 7. Independent SUMO Validation Targets

### 7.1 Experimental Scale

| Parameter | Target |
|-----------|--------|
| SUMO version | ≥ 1.20 |
| Controllers evaluated | ≥ 3 (Fixed, Halted-count/Actuated, Max-Pressure) |
| Sensing conditions | ≥ 4 (Clean, Delay, Miss, Combined) |
| Traffic seed families | ≥ 3 demand profiles × ≥ 2 seeds each |
| Episode duration | 180 s (1,800 steps at 10 Hz) |
| Total episodes | ≥ 60 |
| Total SUMO signal samples | ≥ 100,000 |

### 7.2 Expected SUMO Results

| Metric | Target |
|--------|--------|
| Max-Pressure mean wait (clean) | 5–8 s |
| Fixed-Time mean wait (clean) | 9–13 s |
| Max-Pressure robustness under combined faults | Aggregate wait change within ±15% of clean |
| Phase switching frequency reduction under faults | 5%–15% reduction due to observation damping |
| Signal-phase violations in SUMO | **Exactly 0** |
| Clearance violations in SUMO | **Exactly 0** |

### 7.3 Robustness Panel (Extended Duration)

| Parameter | Target |
|-----------|--------|
| Extended simulation duration | 360 s (3,600 steps) |
| Controllers | ≥ 2 (Max-Pressure + alternative) |
| Seeds | ≥ 6 |
| Purpose | Verify that performance trends hold over longer horizons |

---

## 8. Qualitative Research Outcomes

### 8.1 Technical Contributions

| Contribution | Expected Outcome |
|--------------|-----------------|
| Uncertainty-aware fallback architecture | Demonstrate a complete, implementable pipeline from camera perception through calibrated uncertainty scoring to hysteretic authority transfer, with the fallback controller activating under sensor faults and remaining dormant under clean sensing |
| Two-tier safety hierarchy | Demonstrate decoupled policy-level operational bounds (anti-starvation, max-green ceiling) and downstream physical signal invariants (minimum green, yellow, all-red clearance), with zero logged violations across millions of signal samples |
| Calibrated perception uncertainty | Demonstrate that logistic regression on synthetic count errors produces a calibrated uncertainty score using only 2–3 active features, with fitted (not hand-tuned) switching thresholds |
| Honest empirical audit methodology | Demonstrate a reproducible evaluation framework using Common Random Numbers, paired statistical comparisons, multiple training replicates, and transparent checkpoint disclosure |

### 8.2 Expected Novelty

1. **Perception-uncertainty-driven fallback for traffic signals.** Prior DRL-ATSC work
   assumes perfect or partially missing observations. FlowSync-UQ explicitly models
   continuous, intermediate sensor degradation and triggers deterministic classical
   fallback when uncertainty exceeds a calibrated threshold.

2. **Decoupled two-tier safety architecture.** Existing safe-RL traffic controllers
   (SafeLight, StageLight) enforce action-level constraints within the policy. FlowSync-UQ
   separates policy-level guards (starvation, max-green) from an independent physical
   FSM that cannot be overridden by any software layer.

3. **Reproducible negative-result methodology.** The evaluation framework is designed to
   report honestly when DRL does not outperform classical Max-Pressure, demonstrating
   a level of empirical rigour uncommon in DRL-ATSC publications.

### 8.3 Expected Limitations (to be disclosed)

| Limitation | Description |
|------------|-------------|
| Single intersection | All primary experiments evaluate an isolated 4-way intersection without arterial coordination |
| Synthetic sensor faults | Faults are generated programmatically; real camera degradation involves additional physical factors (weather, glare, occlusion geometry) |
| Short training budget | Training is limited to ≤ 15 minutes per seed on CPU; ε-greedy exploration may not converge fully |
| No hardware cabinet integration | The system has not been integrated with NEMA TS-2 or ATC signal controller hardware |
| Checkpoint heterogeneity | Different training seeds may select checkpoints at different episode numbers; disclose selection procedure transparently |
| Right-censored fallback durations | Persistent sensor faults cause right-censored fallback activations; do not report as ordinary mean durations |
| No hard real-time guarantee | CPU inference tail spikes prevent certification of hard real-time deadlines |

---

## 9. Evaluation Criteria and Validation Standards

### 9.1 Statistical Standards

| Criterion | Standard |
|-----------|----------|
| Primary statistical test | Paired two-sided Student's t-test with CRN-matched evaluation cells |
| Multiple comparison correction | Holm-Bonferroni across all reported comparisons |
| Confidence level | 95% (α = 0.05) |
| Effect size reporting | Paired Cohen's d_z for every comparison |
| Pre-registration | Distinguish pre-specified primary comparison from exploratory contrasts |
| Sample size justification | ≥ 20 paired evaluation seeds × ≥ 5 scenario templates × ≥ 3 fault conditions |
| Reproducibility | Fixed random seeds, Common Random Numbers, checkpoint SHA-256 hashes, frozen evaluation manifests |

### 9.2 Claims That Must Be Supported

| Claim Category | Evidence Required |
|----------------|-------------------|
| Delay reduction vs. baseline | Paired contrast with CI excluding zero; effect size ≥ 0.2 |
| Competitive performance | Paired contrast with CI spanning zero; state explicitly as inconclusive |
| Safety guarantee | Zero violations across ≥ 4,000,000 signal samples with source-code audit of FSM |
| Real-time compliance | Latency profiling with ≥ 1,000 timing samples; P95 < 100 ms |
| Uncertainty detection | Demonstrable score elevation under fault vs. clean conditions |
| Fallback activation | Non-zero activations under faults; zero activations under clean |

### 9.3 Claims That Must Not Be Made

| Prohibited Claim | Reason |
|------------------|--------|
| DRL outperforms Max-Pressure | Unless paired contrast CI excludes zero in favour of DRL |
| Non-significant p-value proves equivalence | Non-significance does not establish equivalence |
| Zero signal violations implies collision-free driving | Signal audit covers simulated cabinet rules, not physical vehicle safety |
| System is ready for real-world deployment | No field testing, no cabinet integration, no weather/lighting validation |
| Hard 10 Hz real-time guarantee | Tail latency spikes prevent this claim |
| Imperfect sensing improves traffic performance | Observed reductions under faults may result from damped switching, not sensing improvement |

---

## 10. Paper-Ready Deliverables

### 10.1 Required Tables

| Table | Content |
|-------|---------|
| Controller performance summary | Mean delay, within-run P95, throughput, run count per controller |
| Paired statistical contrasts | Contrast (s), 95% CI, Holm-adjusted p-value, Cohen's d_z per comparison |
| SUMO evaluation results | Controller × condition × seed with mean wait, P95, trips, switches |
| End-to-end latency breakdown | Per-pipeline-stage mean, P50, P95, P99, max latency |
| Training configuration | Learning rate, discount, buffer, batch size, target update, exploration, demonstrations |

### 10.2 Required Figures

| Figure | Content |
|--------|---------|
| System architecture | Camera → state builder → D3QN / uncertainty → supervisor → shield → FSM |
| Supervisor state machine | Hysteretic Schmitt-trigger diagram with thresholds, dwell, and recovery |
| Paired effect plot | Bootstrap confidence intervals for all major contrasts |
| Robustness sweep | Controller delay across clean and fault conditions |
| Latency breakdown | Stacked or grouped bar chart of pipeline stage latencies |

### 10.3 IEEE Formatting Targets

| Criterion | Target |
|-----------|--------|
| Page count | ≤ 6 pages including references |
| Document class | IEEEtran conference |
| Layout | Two-column |
| References | ≥ 25 entries covering classical traffic control, DRL-ATSC, safe RL, perception uncertainty, and benchmarking suites |
| AI disclosure | Required in Acknowledgment section |

---

## 11. Summary of Expected Contribution

FlowSync-UQ targets an **empirical audit contribution** to the DRL-ATSC literature.
The expected contribution is a rigorously evaluated, reproducible, uncertainty-aware
traffic signal control framework that:

1. Matches (but does not necessarily surpass) classical Max-Pressure performance
   under clean and corrupted sensing.
2. Demonstrates a calibrated perception-uncertainty estimator that reliably
   distinguishes clean from degraded sensing.
3. Enforces deterministic signal-safety invariants with zero logged violations
   across millions of audited samples.
4. Operates within soft real-time constraints on commodity hardware.
5. Reports negative and inconclusive findings transparently, contributing to
   methodological standards in DRL traffic-control research.

The primary significance is the **methodology and safety architecture**, not a claim
of delay superiority over classical controllers.

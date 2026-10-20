# Headless evaluation audit — 2026-10-14

## Outcome

The original headless runner constructed **randomly initialized DQN/D3QN networks**,
not the trained checkpoint. Its results cannot establish how the trained policy
performs. Several independent experiment bugs also invalidated incident, sensing,
ablation and safety interpretations. The corrected pipeline now evaluates an
explicit checkpoint and records the evidence needed to inspect these behaviors.

This is an implementation repair, **not a claim that FlowSync-UQ now beats every
baseline, is publication-ready, or is safe to connect to public signals**. No
policy was retrained during this audit. No thresholds were optimized against the
held-out test results.

## Confirmed faults and repairs

| Area | Fault | Repair |
| --- | --- | --- |
| Policy loading | Headless constructors received no checkpoint; seeding followed initialization. | Required D3QN checkpoint, seed before construction, strict loading, inference mode, full file SHA-256 and checkpoint metadata per run. Untrained evaluation rejected by default. |
| Plain DQN | A random network was treated as an evaluated model. | Omit DQN unless a separately trained, architecture-compatible `--dqn-checkpoint` is supplied. |
| Decision timing | Policy queried every 0.1 seconds despite 2-second training decisions. | Hold learned decisions for the trained decision interval; retain phase eligibility and the physical FSM. |
| Scenarios | Incident events and burst direction filters were ignored; turn distributions used only one approach. | Execute time-bounded downstream capacity changes, direction-specific arrival multipliers and per-approach turns. Reject unsupported topology/configurations. Hash the executed configuration. |
| Observation boundary | Noise affected queue features but masks, pressure, forecasts and classical controllers could see clean simulator data. | Rebuild adaptive-controller context from delivered sensor packets; share the synthetic count sensor across adaptive methods. Fixed remains sensor-independent by design. |
| Fault injection | A miss probability attenuated whole queues rather than sampling missed vehicles; stale/drop information did not reach the supervisor. | Binomial per-vehicle omissions, packet-level latency/drop handling, corrupted outgoing/arrival counts and logged realized corruption. |
| Uncertainty | Queue values were compared with a forecast of arrival rates in different units. | Queue-to-queue EWMA residual; observable frame age reaches supervision. Defaults remain heuristic, not calibrated confidence estimates. |
| Ablations | Environment watchdogs silently supplied safeguards; phase starvation indexing was wrong; no-fallback relied on an unreachable threshold. | Separate experimental watchdog authority from the shared physical FSM, correct phase timers, explicit fallback disabling, actual authority/intervention counters. |
| Timing | Fixed/Actuated tracked wall ticks rather than actual green time; shield could override minimum green. | Use actual signal state and enforce minimum green before shield-directed changes. |
| Safety evidence | Executed conflict fields were blank. | Independently sample simulated lamps and clearance transitions after each tick; record conflicts, clearance violations and sample coverage. |
| Reproducibility | Trajectories requested by the runner were not preserved as inspectable bundles. | Save per-run metrics, metadata, events and optional traces; check identical arrival traces and checkpoint provenance; refuse bundle overwrite. |

`research/experiments/runtime.py` implements the scenario and observed-state
boundary. `server/tests/test_research_evaluation_audit.py` exercises these repairs,
including intentionally injected signal faults and explicit ablation activation.

## Preserved baseline and checkpoint

Original results remain untouched in `results/headless/final_20_seed/` and
`results/headless.zip`. Archive SHA-256:

```text
a99c775dccea0a9cc44877423f10038eb12439011d8ff67c8cf0a958b6c203bf
```

Diagnostic evaluation used the existing 1,000-episode checkpoint:

```text
server/models/76734963-e987-4024-aaa0-d21c048194c5/checkpoint_1000.pt
SHA-256: 4784798d2bc2daf53804f433ae366ba74b5132b82e53291993d073cfe8ff1ea1
```

All D3QN/UQ/ablation variants share that checkpoint. Its metadata identifies the
v6 observation encoding and v4 reward. This does **not** independently establish
its training data, training seed or separation from the evaluation scenarios.

## Diagnostic results, not paper results

Relevant regression suite: **62 passed**. A 90-run diagnostic matrix completed
without execution failures. Additional targeted fallback and trajectory checks
also completed. Arrival traces matched across controllers/noise for paired
scenario-seed combinations, and learned runs carried the exact checkpoint hash.

The following are **two traffic-seed means** from
`results/headless/full_20261014T085754Z/summary_by_scenario.csv` (delay in seconds,
lower is better). This is far too small for a superiority/generalization claim.

| Clean scenario | Fixed | Max-Pressure | Loaded D3QN | FlowSync-UQ |
| --- | ---: | ---: | ---: | ---: |
| Balanced | 14.864 | 10.367 | 9.371 | 10.574 |
| Near gridlock | 15.323 | 11.614 | 12.194 | 13.473 |
| Left-turn surge | 13.814 | 12.244 | 12.264 | 13.309 |
| Sudden burst | 14.602 | 10.339 | 12.604 | 11.764 |
| Held-out OOD | 17.022 | 14.387 | 21.067 | 15.298 |
| Demand reversal | 14.107 | 9.515 | 10.690 | 11.980 |
| Incident reduction | 15.746 | 10.629 | 9.451 | 10.659 |

The loaded policy is materially different from the original random-network
evaluation. Incidents now affect execution. However, UQ still loses to
Max-Pressure in several cases and can worsen a strong D3QN decision.

Under 30% misses on balanced demand, D3QN and UQ both averaged **11.911 s**:
fallback and shield were inactive for those runs. Equality is now explainable
from traces, but it does not demonstrate an uncertainty benefit.

Under one-second camera latency, the targeted ablation check
`results/headless/full_20261014T090016Z/` produced:

| Variant | Mean delay (s) | Fallback steps per 1,500-step run |
| --- | ---: | ---: |
| Full UQ | 10.875 | 1,490 |
| Blind D3QN | 9.221 | 0 |
| Without shield | 10.625 | 1,490 |
| Without fallback | 10.681 | 0 |
| Fixed fallback | 15.093 | 1,490 |

This verifies different authority paths; it does **not** establish that fallback
improves delay. Mild fault ablations can legitimately match when neither feature
activates. The legacy "minus UQ" and "minus fallback" settings are redundant when
both simply disable fallback; do not count them as independent contributions.

The final trace-enabled smoke run is
`results/headless/smoke_20261014T090238Z/` (10/10 runs completed). Its
`audit_checks.json` confirms matching arrivals, loaded checkpoint provenance and
1,500 signal-audit samples per run. It reproduces the balanced Fixed/D3QN/UQ and
30%-miss means above. Earlier diagnostic batches are development snapshots;
their configuration files retain source hashes. Regenerate final evidence from
one frozen revision after validation, rather than pooling development snapshots.

Measured conflict and clearance violations were zero in these diagnostic runs.
Those are **simulated signal-state checks only**, not proof of zero collisions,
pedestrian safety, correct real wiring or hardware certification.

## Run the corrected evaluation

From the repository root, start with a small inspectable run:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/run_headless_evaluation.py \
  --suite smoke --seeds 2 \
  --checkpoint server/models/76734963-e987-4024-aaa0-d21c048194c5/checkpoint_1000.pt \
  --record-trajectories
```

A limited all-scenario/latency diagnostic matrix:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/run_headless_evaluation.py \
  --suite full --seeds 2 --bootstrap 100 \
  --controllers fixed,max_pressure,d3qn,flowsync_uq \
  --conditions clean,miss_30,latency_1000ms \
  --checkpoint server/models/76734963-e987-4024-aaa0-d21c048194c5/checkpoint_1000.pt
```

Use `--help` for filters and explicit output directories. Leave the default new
timestamped output directory to preserve previous runs. `--resume` requires an
identical recorded configuration and source snapshot. Supply `--dqn-checkpoint`
only for an independently trained plain-DQN network, not this D3QN file.

Inspect `audit_checks.json`, `raw_runs.csv`, `configuration.json` and bundle
events/trajectories before interpreting aggregate tables. A successful process
exit alone is not validation. The report deliberately retains
`publication_ready: false`.

## Remaining work and deployment boundary

1. **Validate before retraining.** The existing checkpoint is usable now; no
   retraining is required to fix the old loading error. Freeze a validation/test
   split and establish checkpoint training provenance before further selection.
2. **Make UQ measurable.** Calibrate against observable camera quality, frame age
   and detection/tracking errors on validation data. Intermittent missed counts
   currently do not reliably trigger fallback. Do not leak the simulator's true
   miss probability into a fabricated camera confidence signal or lower
   thresholds merely to win held-out cases.
3. **Align learning and evaluation.** Training still defaults to environment
   watchdogs; research disables those extra overrides to isolate ablations while
   preserving the physical FSM. Align intended deployed supervision and the
   observed-input boundary during robustness training. Compare clean versus
   noisy training, and repeat across independently trained policy seeds as well
   as traffic seeds. More episodes alone are not a remedy.
4. **Validate the simulator and sensors.** The incident implementation is a
   discharge-headway surrogate, not a calibrated road-capacity model. Synthetic
   queue/count faults are not validated CCTV detections. Simplified motion,
   permissive right turns, missing pedestrian behavior and uncalibrated demand
   limit real-world conclusions. Validate these assumptions with independent
   traffic/camera data and an appropriately calibrated traffic simulator.
5. **Establish application parity.** The research WebSocket/UI path has a separate
   construction/telemetry/FSM path. It was not validated or repaired end-to-end in
   this headless audit. Do not assume website and headless results are equivalent.
6. **Freeze and rerun evidence.** After the above checks, rerun the full suite with
   at least the planned 20 traffic seeds, independent training replicates, strong
   classical baselines and paired uncertainty estimates. Keep unfavorable cases.
7. **Treat deployment as separate validation.** Begin with recorded-camera replay
   and non-actuating shadow recommendations. Live signal control remains out of
   scope until traffic-engineering review, intersection-specific conflict and
   clearance validation, hardware-in-the-loop testing, independent fail-safe
   behavior and the relevant operator approvals are established.

The historical performance/calibration/hardware/parity claims elsewhere in this
repository are not validated by this audit. Do not cite them as measured findings.

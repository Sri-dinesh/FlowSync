# Benefit-gate development protocol — 2026-10-16

Frozen before collecting this experiment's training labels or validation results.
Simulation-only development; no new final-test evaluation or RL weight updates.

## Fixed design

- Reuse all three selected v5 pilot checkpoints (training seeds 101, 202, 303),
  with their existing selection hashes and unchanged uncertainty calibration
  `results/uncertainty_calibration/pilot_20261014/calibration.json`.
- Collect from all six **train** templates, traffic seeds 91001–91006, clean
  and existing `validation_mixed` fault profiles. The profile's name does not
  determine the scenario split. This makes 216 source rollouts.
- Take at most the first two eligible fallback-entry events per source run,
  excluding hard-stale triggers. Compare paired 200-tick (20-second) forks:
  retain original fallback versus disable fallback for the fork, with shield
  and physical clearance constraints retained in both.
- Positive target: strictly lower accumulated waiting vehicle-seconds, no
  increased endpoint maximum upstream accumulated wait, and no measured
  signal violations. Require complete paired safety samples and arrivals.
- Eight observable features, as enumerated in `benefit_gate.py`; simulator
  truth is used for offline labels only. Standardized logistic regression,
  fixed L2 coefficient 0.1, fixed entry threshold 0.5; no parameter sweep.
  Stop without fitting if either outcome has fewer than ten examples.
- Gate only uncertainty-triggered entry; retain minimum fallback dwell and
  recovery, existing shield, and unconditional hard-stale failover. A veto
  is latched until the original low-uncertainty recovery window elapses.
- Validate all three policies on all three validation templates, traffic
  seeds 21001–21005, both existing fault profiles. Three matched variants:
  shield-only D3QN, original full UQ, gated full UQ (270 runs).
  Report mean delay, average within-run p95, throughput, signal-audit coverage,
  fallback activations, gate evaluations/vetoes, paired arrival hashes and
  gate/checkpoint/calibration provenance. No best-seed reporting.
- Freeze the fitted gate before validation. Do not tune it using validation
  outcomes or previously evaluated final-test traffic seeds.

## Interpretation and limitations

Repeated events and shared traffic seeds are correlated. Training labels are
short-horizon, first-event samples under the original supervisor, not estimates
of long-run gated policy value. Runtime veto duration differs from the fixed
20-second fork. The fairness condition is a **prediction target**, not a hard
runtime guarantee. Report if the gate simply reproduces shield-only control.

A negative result is retained. Improved validation is not publication readiness,
final-test superiority, real-camera calibration or evidence of road safety.
The prior final-test results and original default controller remain unchanged.

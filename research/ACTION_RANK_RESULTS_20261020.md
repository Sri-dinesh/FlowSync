# All-action label feasibility result

Artifacts: `results/action_rank_labels/feasibility_20261020`.
[Pre-execution protocol](ACTION_RANK_PROTOCOL_20261020.md).
All 18 source runs completed in 31.31 seconds. No model was fitted or promoted.

## Collected evidence

- 45 eligible decision points, 135 counterfactual branches, each 40 seconds.
- 17 decisions have a hindsight alternative saving more than one vehicle-second
  of incremental delay over the parent's first action, with parent continuation.
- 13 decisions retain such an alternative after requiring no throughput loss,
  endpoint upstream maximum wait no more than one second worse, and no measured
  signal violation.
- Qualified alternatives occur for parents 101/202/303 at 4/5/4 decision points;
  low/moderate/burst scenarios at 4/6/3; clean/mixed sensing at 5/8.
- Complete signal-audit coverage: 21,600 source samples and 54,000 branch samples;
  zero measured conflict/clearance violations. This is not road-safety evidence.

The raw records contain all valid actions, not only favorable alternatives, and
only post-fault observable policy inputs for possible future model features.
Simulator truth and future arrivals are used to score labels, not exposed to
the policy. The shield, clearance FSM and original macro-action hold are kept.

## Integrity

Input/checkpoint/source/scenario hashes and the source archive were checked;
the saved report recomputes from raw rows. All 18 source trajectories were
independently replayed through the ordinary engine, without branches, to verify
identical reported delay, generated arrivals and signal-audit results. Thus
branch collection did not alter the behavior being studied.

The branch regression suite passed 21 tests, including source-trajectory
preservation under clean/noisy sensing, full valid-action coverage, paired
arrivals, incomplete-cell rejection and keeping unconstrained hindsight gains
separate from qualified labels. `git diff --check` passed.

## What this does and does not justify

This establishes that some training situations admit a better short-horizon
action under the stated constraints. It does **not** establish that a learned
selector can recognize those situations from sensor features, that any gains
persist over a complete run, or that the learned controller beats Max-Pressure.
Forty-five correlated decision points with one traffic seed are too small for
a generalization or statistical-superiority claim. Do not sum alternative
branch savings into a simulated full-run improvement. Endpoint waiting is not
a full fairness guarantee; 40-second labels omit later consequences.

The next substantive candidate is an action-ranking correction trained from
paired outcome differences, with observed-only inputs and unchanged physical
guards. Before a larger training run: expand training-only label coverage using
prespecified seeds, reserve whole trajectories, and test whether a small
regularized model predicts beneficial actions on excluded trajectories. Then
freeze it and compare complete validation rollouts against the unchanged parent,
Max-Pressure with the same shield, and the other strong baselines. Reused
development probes and the frozen final-test panel must not select its settings.

This candidate is not yet implemented, trained or validated. Existing parent
models remain in use; the overall research-performance objective remains open.

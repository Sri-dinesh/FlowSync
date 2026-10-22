# All-action branch-label feasibility diagnostic

Purpose: move from Q prediction-error diagnostics to training labels tied to
actual simulated traffic outcomes. This collects data only; no new controller
or traffic-improvement claim follows from hindsight branch selection.

Use the same frozen v5 parents 101/202/303. Three unmodified training templates:
low balanced, moderate balanced and platoon burst; traffic seed 94001; clean and
the existing mixed fault profile. Eighteen source trajectories, 1,200 ticks each.
No validation/test trajectories or checkpoint selection. Freeze source/scenario/
parent hashes and this protocol before collection. Keep older artifacts intact.

Run each parent with its standard shield and fallback disabled. At the first
three eligible decision gates at or after tick 200, separated by at least 200
ticks, fork ALL valid proposed actions with the same shield and macro-action
hold semantics. Require at least two valid actions and 400 remaining ticks.
Score each branch over 400 ticks (40 seconds), then discard it. All branches
resume the same frozen parent policy after the changed first macro-action.
They must share generated arrivals; source trajectories must not be changed by
forking. Record raw observed 36-dimensional policy input, masks, Q values,
proposed/executed actions, delay integral, throughput, endpoint upstream maximum
wait, reward components, and executed-signal audit coverage for every branch.

Report unconstrained hindsight minimum-delay opportunities AND a stricter
subset: delay saved greater than one vehicle-second, no throughput decrease,
endpoint maximum-wait increase at most one second, and no measured signal
violation. Count per parent/scenario/fault. Endpoint maximum wait is not a full
fairness guarantee. Never sum alternative branch gains into a full-run gain.
These labels use simulator truth and a realized future only during training
data generation; deployable policies must use observed input only. The minimum
over branches is an oracle diagnostic, NOT an evaluated learned controller.

Maximum 240-second cooperative execution budget. Save partial runs with explicit
incomplete status on timeout. Do not overwrite outputs, train weights, change
production controllers, promote models, or rerun the frozen final test. This
small dataset establishes only whether useful labels exist; learning and fresh
validation remain required even if many hindsight opportunities are found.

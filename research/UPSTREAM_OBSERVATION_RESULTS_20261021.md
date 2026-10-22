# Upstream-demand observation audit

Protocol: [UPSTREAM_OBSERVATION_PROTOCOL_20261021.md](UPSTREAM_OBSERVATION_PROTOCOL_20261021.md).
Runner: `research/audit_upstream_observation.py`.
Initial artifact: `results/upstream_observation_audit/fit_20261021`.
Descriptive pressure extension: `results/upstream_observation_audit/pressure_20261021`.

## Confirmed semantics and implemented boundary

`Intersection.get_movement_queues()` counts every non-passed vehicle in its
origin movement, including vehicles already beyond the stop line. At the
simulator's free speed a vehicle takes about 4.8 seconds to travel from the
stop line (0.42) to the scene exit (1.0). During this period it can still add
to incoming demand and pressure even though another green cannot serve it.
This is not an accurate upstream-demand count. It may also act like an
implicit green-extension heuristic; removing it is not necessarily beneficial.

Added `Intersection.get_upstream_movement_counts()` with explicit stop-line
inclusion, passed-vehicle exclusion and optional backlog inclusion. The legacy
getter and all production/training defaults remain unchanged. Existing v7
checkpoints must not silently receive a different count definition. The audit
uses the new getter only to construct a read-only shadow packet.

Both packets include the same backlog to isolate the spatial boundary.
That backlog assumption is not validated against real camera visibility.
The shadow's pressure, mask and continuous-demand timers are rebuilt by the
same observation adapter, with unchanged lamp feedback and downstream counts.

## Results on unchanged source trajectories

All three parents × six training templates, traffic seed 96301, completed:
18 sources, 21,600 ticks and 314 policy gates. Every original gate's inputs,
Q values, proposal, executed action and shield reason reproduce exactly.
Full arrival hashes, mean delays and signal measurements also reproduce.

- Counts include already-discharged vehicles in 15,511/21,600 ticks (71.81%).
- There are 43,881 excess vehicle-ticks and 6,104 phantom-demand phase-ticks.
- At 65/314 policy gates (20.70%), at least one phase has historical demand
  but no upstream vehicles. **No action mask differs at those gates.**
- No proposed or executed noncurrent switch targets an upstream-empty phase.
  The current phase can legitimately remain selectable with no demand.
- Observed starvation status differs in only ten phase-ticks, all in parent 303.

The initial empty-phase-switch hypothesis is therefore **not supported** by
this panel. No causal explanation for the whole performance deficit follows.

The subsequent descriptive extension compares both Max-Pressure teacher
proposals at the same unchanged source gates. They differ at **80/314 gates
(25.48%)**: all 80 are original-count holds versus upstream-only switches.
Differences by parent are 29/110, 25/100 and 26/104. Neither teacher controls
the audited trajectory. These are proposal differences, not traffic gains.
In particular, extra switching may incur clearance losses.

## Verification and next work

92 targeted tests pass, including six new boundary, mask/timer, nonmutation,
empty-switch and teacher-choice tests. Input/output/source hashes verify;
independent aggregation reproduces all source totals and 628 teacher choices.
The initial artifact is preserved separately from the later extension.
Both record 21,600 signal samples with zero measured violations on the SAME
replayed trajectories; do not pool them as independent safety evidence.

No probe, calibration, validation or final-test outcomes were read. No model
was trained or promoted, and no superior traffic performance is demonstrated.

The next justified implementation is a **versioned spatial observation
experiment**, separating vehicles awaiting service from those already
discharged. It must preserve old checkpoints, apply corruption/delay to all
new camera-surrogate channels (no perfect-truth shortcut under sensing faults),
and compare matched control/augmented learning with identical initial weights,
update budgets, shields and traffic seeds. Baselines must have access to the
same measured information. Keep the current definition as the historical
control, rather than silently rewriting old results. The subsequently specified
v9 plan uses a training-only mechanics smoke followed by a small, matched
user-run learning screen; expanded training requires that screen to pass.

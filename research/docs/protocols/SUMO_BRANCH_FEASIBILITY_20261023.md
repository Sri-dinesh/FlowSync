# SUMO branch feasibility — mechanics only, frozen before collection

This tests whether a small independent simulator can support the paper's
arrival-future diagnostic. It is not that diagnostic's full outcome panel,
FlowSync checkpoint evaluation, a controller contest or confirmatory evidence.
No model training, old final-test access or policy promotion is permitted.

## Fixed setup

Use isolated Python 3.11 with eclipse-sumo/traci/sumolib 1.24.0. Generate one
four-arm intersection with 200 m, single-lane incoming/outgoing edges and only
straight movements. Use deterministic Krauss driving (sigma/speedDev zero,
speedFactor one), 0.1 s steps,
13.89 m/s free speed, no lane changes/rerouting and teleportation disabled.
Physical timing is 8 s minimum green, 3 s yellow and 1 s all-red. Opposite
straight movements share one green; conflicting axes never share permission.
This simplified setup does not validate real traffic or camera perception.

Use source seed 108001 and independent future keys 108101/108102. Per approach,
generate Bernoulli arrivals at 0.20 vehicles/s. Keep uninserted arrivals in an
explicit external FIFO, included in stopped-wait accounting and snapshot
reconstruction. Do not silently drop delayed departures on SUMO state reload.
Record requested and inserted arrival events separately.

Use deterministic incoming halted-count control, hold on ties, with decisions
every 2 s. This is a simple continuation controller, not Advanced-MP and not a
ported FlowSync policy. Select the first eligible decision at/after 60 s with
green age >=8 s, without inspecting branch outcomes. Save SUMO state at 17
digits with RNG enabled plus Python FSM/backlog state. At the gate, hold or
request the opposite phase for one decision; resume the same continuation.
Freeze the original future and two additional 20 s arrival schedules before
collecting branches, pair each schedule across actions, and preserve source
history. Use a new output directory.

## Checks required before any scientific panel

1. Original continuation replays the unbranched source continuation, including
   vehicle IDs/positions/speeds, requested/inserted arrivals, lamps, pending
   backlog, cumulative stopped waiting and completed vehicle counts. Compare
   floats at the explicitly recorded 1e-6 trace precision; do not call this
   byte-identical internal SUMO state.
2. Reload/repeat each same-action/same-future trajectory and match traces.
3. Match starting-state digests for every branch and requested arrival hashes
   within each action pair. Insertion times may differ after intervention.
4. Audit physical signal transitions at every tick: zero conflicting greens,
   minimum green respected and yellow/all-red durations satisfied. Reject
   collisions/teleports and unresolved SUMO pending departures.
5. Save raw per-tick traces, schedules, network/configuration, package versions,
   source/protocol/input/output hashes and complete failure information.

All checks must pass. The smoke is never a performance continuation screen;
do not use its favorable or unfavorable branch gains to choose the later
scientific panel, arrival rates, gates or horizons. No sign-flip frequency or
learned-controller generalization is estimated here. A scientific protocol
needs to be frozen separately before new source/future seeds are inspected.
The feasibility runner has a 120-second cooperative execution cap, apart from
installation; reject partial completion. Stop engineering after one working
day if matched reconstruction cannot be demonstrated.

Official boundary references:
[state save/load](https://sumo.dlr.de/docs/Simulation/SaveAndLoad.html),
[TraCI traffic lights](https://sumo.dlr.de/docs/TraCI/Change_Traffic_Lights_State.html).
SUMO documents incomplete model-state persistence and omitted not-yet-departed
vehicles; snapshot/replay correctness must be measured in the chosen setup.

## Mechanics revision after failed snapshot reconstruction

The first three feasibility attempts are preserved separately. Snapshot reload
matched the visible initial state but did not reproduce the original source
continuation. Disabling default speed-factor variation removed one divergence,
but a later junction-state divergence remained with deterministic driving.
The exact unsaved internal cause is not isolated. No branch-performance panel
was collected or screened, and no favorable outcomes were selected.

The revised mechanism reconstructs each branch by restarting SUMO with the same
inputs/RNG seed and replaying every source tick. It must match the complete
source trace before changing future arrivals. Snapshot files remain recorded
for diagnosis but are not used to establish valid branches. The gate rule,
arrival rate/keys, actions, horizon, physical rules and trace precision remain
fixed. Repeated history samples overlap and are not independent safety evidence.
This is a feasibility correction, not a retrospective scientific-screen change.

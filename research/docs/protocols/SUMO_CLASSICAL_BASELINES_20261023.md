# Executed SUMO classical baselines — fixed development comparison

Project implementation/evaluation only. No manuscript writing, DQN training,
checkpoint promotion or re-use of the closed action/future panel as a fresh
confirmation sample. Freeze this design before collecting the full outcomes.

## Controllers and common boundary

Execute three controllers from an empty intersection for whole episodes:

- `halted`: choose the axis with more incoming halted vehicles; hold on ties.
- `fixed`: alternate NS/EW with 30 s of actual green per phase. Yellow/all-red
  time is separate. This is a declared untuned symmetric schedule, not Webster
  optimization or a field signal plan.
- `max_pressure`: for each straight movement take the positive part of its
  incoming count minus the destination outgoing count, then sum by axis. Equal
  normalization capacities cancel in action selection. Preserve the current
  phase on ties or zero pressure. Check proposal equivalence against the
  existing repository controller; this is not Advanced-MP/Advanced-XLight.

All controllers use two-second decisions and the same physical FSM: 8 s
minimum green, 3 s yellow, 1 s all-red. They cannot alter pending clearance.
Use the same straight-only four-arm topology, SUMO/traci/sumolib 1.24.0,
deterministic driving and 0.1 s steps as the earlier mechanics implementation.
Keep that executed implementation and all previous results unchanged.

Build a common clean count packet from the previous step's saved six-decimal
vehicle snapshot: four incoming, four outgoing and four halted incoming counts
(speed <0.1 m/s), in NS/EW approach order N,S,E,W. Ignore internal edges in
counts. Initial packet is empty. Record the packet, pre-action FSM and proposal
at every decision; no future requests, seed/family identifier, external backlog
or outcome is a controller feature. Fixed ignores counts by design. This
declared snapshot adapter is the new comparison boundary; do not assert exact
equivalence to the old raw edge-API halted-count path at rounding boundaries.

Reuse the common physical/vehicle-step implementation with the selected
controller's proposal supplied at EVERY decision, not only the first branch
action. Schedules are generated/frozen before runs and paired across policies.
Insertion delays may depend on the controller; preserve external entry FIFO
and include its waiting in metrics. No additional shield or sensor faults are
introduced in this comparison.

## Fixed cases, horizons and budget

| Family | Per-approach NS/EW rates (vehicles/s) | Traffic seeds |
| --- | --- | --- |
| Balanced | 0.20 / 0.20 | 110001–110005 |
| NS dominant | 0.30 / 0.10 | 110101–110105 |
| EW dominant | 0.10 / 0.30 | 110201–110205 |

Fifteen cases × three controllers = **45 runs**, each **180 seconds / 1,800
ticks** from the same empty state and initial NS green. All requested arrivals
are Bernoulli draws at the fixed rates, shared across controllers. No warmup
discard, drain extension or best-horizon selection. These are new arrival
realizations in known demand families/topology, not an independent final test.
The full collection has a **900-second cooperative cap**. Preserve partial
outputs and mark incomplete on any stop/failure; do not score a truncated batch
as complete or choose only completed favorable cells.

Mechanics smoke uses one balanced seed **110901**, **80 s / 800 ticks**, all
three policies and two identical repetitions each. It checks full Fixed
cycles, repeated traces, actual policy execution, paired requests and the
verifier. It is not the full comparison, a tuning set or performance screen.
Smoke cap: 180 seconds. Do not tune the fixed duration/controller definitions
after inspecting its rankings. The user runs the full bounded job.

## Metrics and checks

Primary contrast: equal-case mean stopped waiting per REQUESTED vehicle,
Max-Pressure versus halted control. Waiting is the 0.1 s integral of all
stopped active vehicles plus external entry backlog, including unfinished
vehicles. Secondary metrics: linear-interpolated p95 accumulated waiting over
all requested vehicles, maximum accumulated waiting, completed trips, active
inventory and entry backlog. Record additional paired Fixed contrasts and
every case/family. Completed trips exit the SUMO network; this is not the old
custom-simulator passed-vehicle measure or trip travel time.

No significance, population intervals, learning benefit or policy promotion
follows from this development comparison. A complete comparison is not an
improvement screen; report unfavorable rankings and tail/throughput trade-offs.

Audit each executed lamp sequence independently and reject collisions,
teleports, SUMO-side pending departures or inconsistent inventory. Raw verification
must reconstruct every delivered packet/proposal and FSM transition from the
trace, every requested schedule and external FIFO, per-vehicle stopped waiting,
final inventory and all paired summaries. Store gzip traces, decision records,
frozen schedules/manifest, archived sources/protocol, output hashes and failure
status in a new directory. Verification reruns no traffic. Do not overwrite
the completed older panels, defaults, checkpoints or source archives.

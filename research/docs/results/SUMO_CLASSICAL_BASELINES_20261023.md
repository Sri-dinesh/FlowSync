# Executed SUMO baselines: complete and verified

This is project implementation and evaluation work. The user stopped manuscript
writing. No paper files, learned checkpoints, application defaults or old SUMO
protocols/results were changed for this task.

## Completed full development comparison

The user completed `results/sumo_classical_panel/full_20261023`: **45 runs**,
fifteen paired cases, 180 seconds per run and **81,000 executed signal samples**.
Collection took **467.89 seconds / 7.80 minutes**, inside the frozen 900-second
cap. The saved-data verifier was run again after receiving the result and
passes; it reconstructs packets, proposals, FSM, schedules, FIFO, inventory,
waiting and summaries without rerunning a traffic trajectory. All sampled
lamps/transitions have zero measured conflict/clearance violations.

| Controller | Mean waiting per requested vehicle (s) | Average within-run p95 wait (s) | Mean completed trips | Mean final entry backlog | Mean switch onsets |
| --- | ---: | ---: | ---: | ---: | ---: |
| Halted | 6.784512 | 17.974667 | 95.133333 | 4.000000 | 13.333333 |
| Fixed | 10.238577 | 32.036000 | 98.666667 | 3.333333 | 5.000000 |
| Max-Pressure | 5.935522 | 16.457000 | 101.400000 | 3.066667 | 12.600000 |

Max-Pressure's equal-case mean waiting is **0.848991 s / 12.5137% lower than
halted control** and **4.303056 s / 42.0279% lower than Fixed**. Percentages
compare aggregate controller means, not an average of per-case percentages.
Its average within-run p95 falls by 1.517667 s versus halted and 15.579000 s
versus Fixed; completed trips increase by 6.266667 and 2.733333 per run.

The primary improvement is not confined to one family:

| Family (five paired cases) | Halted mean wait (s) | Fixed mean wait (s) | Pressure mean wait (s) | Pressure saved vs halted (s) |
| --- | ---: | ---: | ---: | ---: |
| Balanced | 5.964279 | 9.135122 | 5.475876 | 0.488404 |
| NS dominant | 7.705367 | 11.166705 | 6.373423 | 1.331944 |
| EW dominant | 6.683891 | 10.413905 | 5.957267 | 0.726624 |

Retain the unfavorable cases. Versus halted, pressure improves mean waiting
in 14/15 cases and p95 in 12/15; completed trips improve in twelve, tie in two
and fall in one. Twelve cases improve mean waiting without p95/trip loss.
The three trade-off cases are:

| Seed | Mean wait saved (s) | p95 saved (s) | Completed trips gained |
| --- | ---: | ---: | ---: |
| 110005 | +0.665217 | -0.300000 | -2 |
| 110203 | +1.312418 | -0.460000 | +14 |
| 110205 | -0.092754 | -1.320000 | 0 |

Versus Fixed, pressure reduces mean and p95 waiting in all fifteen cases but
completes fewer trips in four (110001, 110004, 110102 and 110105). On the NS
dominant family it completes 0.6 fewer trips per run on average than Fixed.
Thus lower mean waiting is not a claim of universal metric dominance.

This is a completed **classical development comparison** in the declared
straight-only SUMO intersection and already inspected demand families. It
supports pressure as the stronger executed reference here. It evaluates no
FlowSync learned policy, adds no averaging/uncertainty benefit and supplies no
new-controller novelty or independent final confirmation. The earlier
six-state hindsight benefit over halted control cannot substitute for an
improvement over this stronger reference. No model is promoted.

**This collection is closed; do not rerun its launcher.** The original source
archive, protocol, schedules and every favorable/unfavorable case are preserved.

## Purpose and implemented boundary

The [saved-branch diagnosis](../audits/SUMO_ACTION_MECHANISM_20261023.md) found
that the existing halted-count continuation switched away from fifteen moving
NS vehicles at the only gate with a selected hindsight benefit. A pressure
proposal held there, but proposal agreement at six inspected gates is not a
whole-episode controller evaluation. This comparison establishes executed
classical references before another correction or learning experiment.

The [frozen development protocol](../protocols/SUMO_CLASSICAL_BASELINES_20261023.md)
now has a runner, pure observed-count policies, a shared episode adapter,
per-vehicle waiting/inventory reconstruction and a standalone raw-data verifier.
All three policies execute throughout an episode:

- Halted control chooses the axis with more halted incoming vehicles.
- Fixed alternates 30 seconds of actual green per phase, excluding clearance.
- Max-Pressure uses incoming vehicle counts and destination outgoing counts,
  with positive movement pressures and current-phase tie handling.

The adaptive policies read the same previous-step clean count packet. Fixed
ignores its counts. All share two-second decisions, an eight-second minimum
green, three-second yellow, one-second all-red and the same physical vehicle
step. Every decision's packet, pre-action context and proposal is recorded;
controller features exclude future schedules, family/seed labels and external
entry backlog. The snapshot adapter is declared explicitly rather than assumed
identical to the older raw edge-API halt adapter at rounding boundaries.

Waiting includes stopped active vehicles and external entry queues. Mean and
p95 accumulated waiting use **all requested vehicles**, including unfinished
ones. Completed trips mean network exits; do not combine this measure with
the custom simulator's stop-line passed-vehicle metric.
Controller/family summaries give equal weight to each case; their p95 and
maximum fields average within-run values rather than pooling vehicles or
reporting the single worst wait across the panel. Every run's values remain
in `runs.jsonl`.

## Completed mechanics verification

Artifact: `results/sumo_classical_panel/smoke_20261023`.
SUMO/traci/sumolib 1.24.0 ran six 80-second episodes: one separate balanced
seed, three controllers and two identical repetitions each. Collection took
18.82 seconds, inside its 180-second cap. Every run received the same 58
requested arrivals and recorded 40 policy decisions.

Each controller's repeated full semantic trace matches exactly. Fixed begins
yellow at 30 and 64 seconds, EW green at 34 seconds and NS green again at 68
seconds, confirming that clearance does not consume its 30-second green.
Halted and pressure executions also differ, confirming that the selected
policy remains active beyond the initial proposal. All **4,800 executed signal
samples** have zero measured conflict/clearance violations. Repeats are not
independent traffic samples or real-world safety evidence.

The raw-data verifier passes using both the existing Python 3.14 environment
and the fresh Python 3.11 environment. It checks complete controller/case/repeat
coverage, source/archive/output hashes, frozen requested schedules, reconstructed
packets/proposals and FSM, entry FIFO, vehicle conservation, per-vehicle waiting,
paired summaries and repeat equality. It reruns **zero** traffic trajectories;
collision/teleport/pending-departure rejection occurs during collection.

The targeted SUMO regression suite passes **59 tests**, including 32 new tests.
Coverage includes proposal equivalence with the existing Max-Pressure controller
on 200 generated packet/phase combinations, actual-green timing, moving demand
and destination pairing, continuous proposal delivery, unfinished/backlog wait,
tampered records even after their hashes are updated, omitted evidence, duplicate
cells and false smoke-to-full relabelling. One existing dependency deprecation
warning remains. This is not a full frontend/backend suite run.

The smoke is a mechanics check, **not the full development comparison**. Its
rankings do not select rates, horizons, Fixed durations or controller settings.
The smoke alone establishes no controller superiority, final-test result or
model promotion.

## Completed collection and read-only inspection

The completed job ran **45 episodes**: fifteen paired traffic cases across balanced,
NS-dominant and EW-dominant demand, three controllers, 180 seconds per episode.
Seeds 110001–110005, 110101–110105 and 110201–110205 were new arrival realizations
when frozen, in known demand families/topology; their results are now consumed
development data. The completed future-arrival panel is also closed. Neither
launcher is a next-step command.

To inspect saved data without running SUMO:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  -m research.audits.verify_sumo_classical_panel \
  results/sumo_classical_panel/full_20261023
```

The [saved-data diagnosis](../audits/SUMO_CLASSICAL_DIAGNOSIS_20261023.md) is also
complete at `results/sumo_classical_analysis/audit_20261023`. It records every
paired case, waiting attribution, same-state proposal comparison and first
trajectory split, with archived analysis sources and input/output hashes.
Its new helper tests bring the targeted SUMO suite to **70 passing tests**;
the full repository/frontend suite was not run.

Interpret `complete` and `comparison_complete` as coverage flags, not favorable
performance decisions. The next justified component test is an executed
total-incoming-count policy against the existing references, under the same
physical/sensing rules, to isolate removing outgoing-count subtraction. Its
protocol, implementation and full comparison have now
[completed separately](SUMO_COUNT_ABLATION_20261023.md): mean/p95 waiting worsen
versus pressure, while completed trips increase. Same-state shadow agreement
alone did not supply that traffic result.
No long learning batch or checkpoint promotion is justified by these results.

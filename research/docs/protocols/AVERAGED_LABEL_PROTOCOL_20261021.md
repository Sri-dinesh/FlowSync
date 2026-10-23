# Averaged action labels: frozen choices, fresh future streams

This protocol is fixed before evaluating any new future outcomes. The earlier
arrival-sensitivity panel is development evidence, not a final test. This is
a label-quality experiment, not a trained policy or full traffic benchmark.

Input: complete `arrival_label_stability/panel_20261021T063020Z`, with three
parents, six training scenarios, clean sensing, source traffic seed 95001 and
three recorded gates per source. Keep all 18 sources and 54 gates; do not
select gates based on their apparent benefits or variability.

Freeze three choices at every gate, before collecting new outcomes:

1. `parent`: unchanged parent proposal.
2. `single`: choose from original single-future branch gains.
3. `mean8`: choose from mean paired gains across the eight already recorded
   future streams (replicate IDs 0 through 7); exclude original single-future
   outcomes from this mean.

For both corrective choices use the existing criteria unchanged: predicted
delay saving >1 vehicle-second, throughput gain >=0 and endpoint-wait saving
>=-1 second; greatest delay saving wins, ties by lower action index. If no
candidate qualifies, retain the parent. Save all choices and means with a
hash before the first new simulation. The new outcomes cannot change choices.

Evaluate each frozen choice on eight independent new arrival streams, IDs
8 through 15 under the existing deterministic seed derivation. Preserve the
same current full state, backlog, sensor buffers, phase and policy hold
schedule. Pair arrivals exactly across all valid actions in each new stream;
keep the physical FSM, shield and subsequent parent continuation unchanged.
Reproduce the original full source and single-future branch labels exactly.
Never use spawner.set_seed at a gate because it resets existing demand.

A one-source mechanics smoke uses IDs 100 through 107, NOT 8 through 15,
so it cannot consume full-panel evaluation futures. Its scores cannot pass
the continuation screen. Compare original and new seed sets explicitly to
guard against accidental overlap. No further thresholds or arms are tuned.

Report all arms over all 54 gates, including retained-parent choices. First
average gain over each source's 3 gates x 8 futures, then average the 18 source
means equally. Targets: delay saving in vehicle-seconds, throughput gain in
vehicles, endpoint max-wait saving in seconds (positive is better). Record
changed proposals, changes to first executed action, qualified/harmful cases,
harmful fraction among changed-proposal cases, and parent-level means. Report
per-source and per-future rows, not only aggregates. Parent gains are zero.

The bounded engineering continuation screen requires all of:

- all 18 sources complete, not a smoke;
- mean8 aggregate delay saving >0 relative to parent, and greater than single;
- mean8 aggregate throughput and endpoint-wait gains >=0;
- mean8 has no higher harmful fraction among changed cases than single
  (if single never changes, require zero mean8 harmful cases);
- mean8 delay gain >=0 for every parent, with an actual first-action change
  and at least one qualified beneficial case for each parent.

These are development gates, not significance tests or guarantees. Single
source traffic seed, clean sensing, only eight evaluation futures and 40-second
branches limit interpretation. Even a pass only motivates a separate model
fitting experiment on broader training states, followed by fresh full-episode
validation. It cannot authorize checkpoint promotion or a superiority claim.

Preserve input/model/source/output hashes and frozen choices. Default execution
budget is 1800 seconds; stop cooperatively, save completed sources and mark an
incomplete panel explicitly. No calibration/probe/validation/final-test access,
no optimizer updates, no production controller changes, no model upload.

# Fixed-state action labels under independent future arrivals

Freeze this protocol before running the diagnostic. This is training-only
label analysis, not policy fitting, selection or a performance evaluation.

Panel: the three recorded parents (101, 202, 303), all six training templates,
clean sensing, existing fitting traffic seed 95001. Replay the three
outcome-blind gates already recorded for each of these 18 source trajectories.
No calibration/probe/validation/final-test outcomes are read. Scope is one
source traffic seed and clean sensing, not the whole training distribution.

At each gate, reproduce all original 400-step action branches exactly.
Then sample eight new future-arrival random streams. Derive each seed from
SHA256 of [protocol namespace, parent, scenario, source seed, gate, replicate].
For each replicate and valid action, fork the exact same gate state. Replace
only the copied Poisson spawner's RNG using numpy.default_rng. Do NOT call
set_seed: it resets clock, pending arrivals and counters. Keep all existing
vehicles, backlog, signal state, known demand schedule, observation buffers,
perception RNG, policy macro-action schedule and future parent policy intact.
Actions within a replicate receive the same future-arrival seed. Audit their
arrival hashes for exact pairing. The future random stream is an offline
experimental intervention, never a controller input.

Preserve the macro-action intervention, shield and physical signal FSM.
All subsequent actions follow the unchanged parent. Compare delay,
throughput and endpoint wait relative to the parent action under the SAME
future. Check signal audit coverage and conflicts on every branch.

Save every original and resampled branch outcome. Verify source replay,
original labels, input/checkpoint/scenario hashes and archived code.
Stop cooperatively at 300 seconds by default, retain completed sources,
and explicitly mark an incomplete panel; a budget stop is not success.
A one-source smoke verifies mechanics but cannot be substituted for the panel.

Report descriptive quantities over the complete panel:

- per-alternative eight-future mean and sample standard deviation of gains;
- alternatives whose delay gain takes both values >1 and <-1 vehicle-second;
- fraction of futures meeting the existing qualified-benefit constraints
  (delay gain >1, throughput >=0, endpoint wait saving >=-1);
- original hindsight-selected qualified action, using greatest delay gain
  and lower-action tie-break; its benefit/harm counts under new futures;
- per-gate constrained hindsight choices on each future and on mean gains,
  including parent/abstention. Mean-gain choice is descriptive, not a policy.

Original labels are not pooled into the eight-future estimates. Gates/actions
within a source are correlated, so do not treat them as independent statistical
evidence. Eight realizations cannot prove a guarantee or isolate every cause
of poor predictive performance. No threshold tuning, new model, controller
promotion or claim of improved full-run delay follows from this diagnostic.

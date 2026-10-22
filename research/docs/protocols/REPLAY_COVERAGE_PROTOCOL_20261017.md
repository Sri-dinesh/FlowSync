# Replay-coverage diagnostic — pre-execution specification

Follow-up to `results/fixed_replay/update_pressure_20261017`, using all three
parents (101/202/303) and the recorded `update_pressure_5qyi9cmv` training inputs.
This is development diagnosis of stationary-label transfer, not traffic evaluation.

Compare two fixed-label fitting arms:

- `narrow`: reuse the original eight fit episodes, target labels and exact
  200-by-128 uniform sampling schedule. Reproduce the prior fixed-label curve.
- `broader`: append demonstration records at zero-based indices 6–11 and online
  episodes 2/17/32/47/62/77. Collect these 12 additional training episodes with
  the unchanged parent (epsilon zero) or Max-Pressure teacher, respectively,
  shield on, fallback off, original recorded traffic/fault/scenario settings.
  Freeze labels using the same initial parent. This gives 20 fit episodes.

Keep the original four probe episodes, their tensors, initial labels and initial
actions byte-for-byte unchanged. Reject duplicate collection seeds and any
overlap with original fit/probe cases. All additional cases must be train.
Use deterministic collection, preserve all source/input/dataset hashes. Collect
all additional data before any fitting. Save tensors and schedules, not learned
checkpoints. Reject output reuse.

Both arms use 200 updates, batch size 128, Adam 0.0001, margin weight 0.5,
unit importance weights, and the production fixed-label adapter. Original
demonstration flags remain; no PER. Use RNG seed 77000 + parent seed for both
schedules, but sample from each arm's own fit dataset uniformly with replacement.
Indices/data are necessarily different; this tests increased sample coverage
and reduced reuse per sample together, not one isolated optimizer mechanism.
The number of demonstration/online episodes scales equally, but the realized
transition-level mixture may differ and must be reported.

At steps 0/25/50/100/200, measure both arms on the exact original fit and probe
sets and on the expanded fit set. Primary diagnostic: episode-independent
step-200 probe MAE against unchanged initial labels, across all three parents.
Report every seed and all intermediate steps, not the best update. Do not call
initial labels ground-truth returns or prediction errors traffic-delay seconds.

Only call this hypothesis promising for a subsequent validation experiment if
broader data reduce mean probe MAE by at least 5% relative to both narrow fitting
and the unchanged parent, no seed regresses against either, and mean probe
joint frozen objective does not worsen against either. These are engineering
gates on reused development probes, not significance or publication criteria.
No automatic rollout, larger training batch, model promotion or final-test use.

Maximum diagnostic execution 240 seconds, cooperative checks. Preserve partial
output on timeout, never claim complete. Input verification is read-only.

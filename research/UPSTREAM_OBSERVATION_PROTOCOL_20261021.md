# Read-only upstream-demand semantic audit

Question: the historical movement count includes all non-passed vehicles,
including vehicles beyond the stop line. How often does that disagree with
upstream demand at policy decisions, and does it actually produce proposals
or executed switches toward phases with no upstream vehicles?

Replay exactly the 18 fitting sources with traffic seed 96301 from the pinned
`averaged_label_model/pilot_20261021T095353Z/fit.jsonl`: all three frozen parents,
all six training templates, 1,200 ticks, clean sensing. No selection on outcomes.
No probe, calibration, validation or final-test access. No model training.

Run the original D3QN + shield unchanged. In parallel, build a shadow sensor
packet whose twelve counts include only non-passed vehicles at/before the
stop line, plus the SAME pending backlog as the original count. Keep current
lamps, delivered arrivals and downstream counts unchanged. Rebuild pressure,
demand mask and continuous-demand timers through the same ObservedState
adapter. The shadow packet must never choose source actions. Backlog inclusion
is a simulator assumption, not a demonstrated camera capability.

Record all ticks' incidence of excess counted demand, phantom phase demand
(historical positive but upstream zero), and differences in observed
starvation status. At each parent decision gate preserve original/shadow
counts, masks, timers, proposals and executed actions. Separately count
noncurrent proposals and executions aimed at an upstream-empty phase; holding
the current empty phase is NOT an empty-phase switch. Also retain all source
arrival hashes, mean delays and actual signal conflict/clearance samples.

Every original gate's inputs, proposals and executions must exactly reproduce
the pinned source, as must complete arrival hashes and average delay. Fail
the audit on any replay mismatch. Preserve source snapshot, protocol, input
hashes, per-source summaries and decision events. Do not infer a controller
performance gain from this read-only counterfactual observation audit.

A confirmed boundary mismatch justifies a versioned observation experiment
with all controllers seeing the same corrected sensor definition. It does
not justify silently feeding changed semantics into old v7 checkpoints,
changing the historical baseline or presenting prior results as corrected.

## Descriptive extension after the first replay audit

The first audit found no action-mask differences or switches toward empty
upstream phases. Consequently, also record both Max-Pressure teacher proposals
at each unchanged parent gate, using the exact original downstream counts and
separate original/upstream incoming counts. Neither teacher controls traffic.
Count proposal differences and their hold-versus-switch direction. This
extension was specified after inspecting the first diagnostic, is not an
independent test, and does not measure which proposal is better. Save a new
artifact directory; preserve the initial audit unchanged.

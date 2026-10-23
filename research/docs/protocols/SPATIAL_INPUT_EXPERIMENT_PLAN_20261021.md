# Spatial-input experiment: implementation and mechanics stage

Status: not a validated controller improvement. No long training batch is
authorized by this plan alone. The preceding read-only audit found that the
historical count confounds upstream demand with already-discharged vehicles;
it did not show that upstream-only switching reduces delay.

## Fixed observation contract

Use opt-in v9, 48 inputs: the SAME 36 v7 inputs, followed by twelve delivered
upstream movement counts in canonical order, encoded tanh(count/15). Include
vehicles at or before stop line, exclude passed/discharged vehicles, and keep
the same pending-backlog assumption as historical counts. At saturation bound
upstream by the count reconstructed from the legacy packet. This remains a
synthetic sensor, not a demonstrated field-of-view or camera validation.

Treatment: `v9_48dim_spatial`. Matched control: `v9_48dim_zero_spatial`.
Control uses the identical sensor path, fault schedule and 48-input network,
but zeros the last twelve delivered features. Preserve the old demand masks,
shield, reward, arrivals, physical FSM and Max-Pressure demonstration policy
to isolate additional spatial information from changed control rules.

Expand a v7 parent by copying all weights and zero-initializing the twelve
extra first-layer columns. Both arms must reproduce the original policy
before learning; parent files are immutable. V9 encoding fails if the delivered
spatial packet is missing or malformed, including for the zero-feature control.
There is no silent dimension padding or perfect-truth fallback.

## Fault contract

Preserve every historical aggregate fault draw. Given the same aggregate
survivor count, allocate detected upstream vehicles hypergeometrically between
upstream and already-discharged populations using a separate per-tick RNG.
This is conditional independent vehicle thinning, not an extra clean channel.
Burst occlusion zeros both counts; false positives and positive jitter are
assigned upstream with probability 0.5 (explicit synthetic assumption).
Negative jitter removes detections uniformly. Use the SAME lane swap for both
counts. Delay/drop selects the entire packet, including spatial counts, from
the same source frame. Repeated frames never refresh spatial measurements.
Delivered upstream counts cannot exceed delivered aggregate counts.

Train collection and research evaluation share this adapter. Record v9 schema,
sensor model and checkpoint version. Historical v6/v7/v8 inputs and random
streams must remain exactly unchanged on the same trajectories.

## Fair comparison and first checks

Keep both historical Max-Pressure and an explicit upstream-count Max-Pressure
baseline. The latter reads ONLY delivered spatial telemetry, never the simulator.
When comparing learned policies with shields, baseline safety constraints must
be matched too; a bare baseline alone cannot establish a matched comparison.
No existing baseline results are rewritten by adding the new method.

First: unit tests for all fault types, complete missing detections, stale/latent
packets, malformed/missing telemetry, zero-expansion, initial policy equality,
new-column gradients, train/inference parity and legacy behavior.

Then a bounded mechanics smoke on training data only, parent 101, seed 97301:
24 demonstrations, one online episode, four optimizer updates, target interval
25, learning rate 1e-4, demonstration margin 0.5, shield on/fallback off.
Use 1,200-tick training scenarios. Both arms receive identical scenario/traffic/
fault schedules and initial weights. No imitation or TD warmup. Retain both
models, all source rows and provenance. Evaluate original and both arm weights
on training seed 97302 with clean and validation_mixed *fault profiles*, but
training scenarios only; those are mechanics observations, not validation
selection. Do not promote or choose a winner from one update episode.

A full pilot still needs a frozen multi-parent comparison, equal optimizer
budgets, held-out development seeds, unchanged continuation criteria and
equally informed strong baselines. UQ/fallback benefit remains a separate
requirement; v9 alone does not resolve it. Old observed final-test results may
not be reused as fresh confirmatory evidence.

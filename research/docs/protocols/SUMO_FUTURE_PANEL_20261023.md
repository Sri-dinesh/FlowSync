# Independent SUMO future-arrival panel — frozen design

This is a new development replication of one qualitative question: how stable
is a hold/switch action advantage when the observed starting state is fixed but
future arrivals change? It is not a FlowSync-policy transfer test, state-of-art
benchmark, calibrated camera study or independent final test of the original
D3QN. No learning or parameter search is included.

## Before outcomes

Use SUMO/traci/sumolib 1.24.0 and the straight-only, four-arm, 200 m single-lane
network and deterministic driving/physical rules tested by the
[mechanics protocol](SUMO_BRANCH_FEASIBILITY_20261023.md). Snapshot restoration
failed feasibility; reconstruct each branch by fully replaying its source.
Require full source-trace equality at six decimal digits before branching.

Freeze six source configurations, one gate per source:

| Demand family | Per-approach NS/EW rates (vehicles/s) | Source seeds |
| --- | --- | --- |
| Balanced | 0.20 / 0.20 | 109001, 109002 |
| NS dominant | 0.30 / 0.10 | 109101, 109102 |
| EW dominant | 0.10 / 0.30 | 109201, 109202 |

At each source use the first eligible two-second decision at/after 60 s with
green age >=8 s, no later than 120 s. No outcome-based gate selection or source
exclusion. Continue with incoming halted-count control, hold on ties, 8 s minimum
green, 3 s yellow, 1 s all-red. Only straight phases NS/EW are available. This
continuation is not Advanced-MP or the original learned policy. Sensing is clean
and local; future arrivals are not controller inputs.

At the gate evaluate both absolute phase requests, then resume the same
continuation at the next two-second decision. Horizon is fixed at **40 s**.
Future keys are derived by SHA-256 from mode, source seed and role/index.
Freeze all source prefixes/gates and all future schedules before any branch.
Use one `single` selection future, eight `fit` selection futures (0–7), and
eight disjoint `check` futures (8–15), paired across actions. All future
arrival Bernoulli draws retain the source family's approach rates. Keep
entry-blocked demand in an explicit external FIFO, shared at branch onset.

Full size: six gates × seventeen futures × two actions = **204 branches**.
Cap total collection at 1,800 wall seconds. Incomplete collection cannot be
called complete. No automatic training continuation or threshold changes.

## Outcomes and frozen selection

Primary descriptive outcome: per-gate fraction of the eight check futures
where the alternative has saved delay >+1 vehicle-second and <-1 vehicle-second,
and the number of gates with both signs. Report all six sources, by demand
family and source seed. No significance or population prevalence from six gates.

Delay is the integral of stopped vehicles (speed <0.1 m/s) plus entry backlog,
in vehicle-seconds. Throughput is completed trips exiting the modeled network,
not FlowSync's intersection-passed count. Endpoint maximum accumulated waiting
includes vehicles still active/pending and their pre-gate history. Never pool
these values with the custom-simulator panels.
Round reported wait integrals/gains to six decimal places before threshold
comparisons. Verification permits at most 1e-9 floating accumulation roundoff
across Python versions, with strict counts/structure and six-decimal traces.

The baseline action is the continuation controller's pre-outcome proposal.
The `single` selector changes it only if its selection future gives >1
vehicle-second delay saving, nonnegative throughput gain and endpoint maximum
wait saving >=-1 s. The `mean8` selector applies those same constraints to mean
gains on the eight fit futures. Otherwise retain baseline. Freeze choices
before any check-future outcome; collect selection outcomes for ALL sources
before collecting any check outcomes. Score baseline/single/mean8 on check
futures with equal source weighting. Report changes, harmful/qualified cases,
delay, throughput and endpoint wait. No fitted predictor or new controller is
claimed; both selectors use simulator hindsight.

Record proposed-action versus actual execution. At every branch tick audit
physical signal sequence, minimum green, yellow and all-red. Reject collisions,
teleports, unexplained pending departures, changed histories/future schedules,
duplicate/missing cells and incomplete signal coverage. Requested arrivals are
paired; intervention-dependent insertion delays are retained as outcomes.
Preserve raw traces, outcomes, schedules, choices, source/protocol/package hashes
and failed/partial attempts. Write a new output directory.

The complete result is informative whether it shows stable or unstable labels,
and whether averaging helps or hurts. There is no performance-pass threshold
and no paper-readiness flag. Broader novelty, model validation and traffic
realism remain separate requirements.

## Mechanics smoke and execution

Smoke uses one balanced source seed 109901, two selection/check futures per
role, twenty-second branches and a 180 s cap. It cannot complete the full panel
or be counted as replication evidence. Its mode-specific future keys are
disjoint from the full panel. The user runs the full command after the smoke
and regression checks; see the dated results/setup note.

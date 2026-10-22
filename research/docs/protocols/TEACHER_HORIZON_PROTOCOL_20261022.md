# Teacher disagreement: horizon sensitivity diagnostic

Frozen after the 20-second teacher-alignment prerequisite failed. That failure
is retained; this diagnostic CANNOT pass or revise its continuation screen.
Hypothesis: the observed early-switch cost may recover over a complete signal
cycle. A negative 20-second branch outcome alone does not answer that question.

Use exactly the same seven frozen teacher-disagreement gates, all three policy
replicates and all 16 recorded future arrival keys from
`results/teacher_alignment/pilot_20261022`. Proposals remain frozen. No new
states, alternative timing thresholds, teachers or learned weights. Extend
each distinct proposal branch to 600 ticks (60 seconds), recording prefixes at
200 and 600. Require the 200-tick outputs to reproduce EVERY prior outcome
exactly (including reward components, switches, arrivals and endpoint wait).
Source trajectories must again reproduce exactly. Keep the SAME matched
sensor, additional shield, continuation policy and physical signal FSM.

The primary new endpoint is 600 ticks, with no best-horizon selection. Record
all per-gate/per-future delay, throughput, endpoint wait and switches at both
endpoints. Interpret a reversal only if aggregate delay saving becomes positive
without aggregate throughput or endpoint-wait loss, and every policy replicate
has nonnegative mean delay saving. These are exploratory mechanism checks,
not a new teacher-promotion screen or independent confirmation. Both future
sets have been inspected at 200 ticks; their extended outcomes are correlated
with those earlier measurements. Call them previously used future streams,
not fresh testing. No optimization, proposal selection or threshold fitting.

Bound: nine 1,200-tick source replays, seven gates, <=336 distinct branches
(three proposal maximum, 16 futures), 600 ticks per branch, one CPU Torch thread,
180-second cooperative cap. Partial outputs cannot establish a complete result.
Hash input files and frozen proposals, archive source/protocol before collection,
and preserve raw prefix records. Zero measured lamp/clearance violations and
complete sample coverage are execution checks, not real-world safety claims.

No long training, model promotion or changed defaults follow. A positive result
would require a separately frozen development test with new arrival streams
before any learning hypothesis is revived. A negative result closes this
immediate-switch teacher direction at both tested horizons.

# Conditional follow-up: upstream teacher alignment

Status: completed and FAILED; see [recorded results](TEACHER_ALIGNMENT_RESULTS_20261022.md).
The frozen pre-collection revision is preserved in the output source archive.
Do not launch the conditional learning pilot. This plan
does not revise the failed spatial pilot's screen.

Evidence: the [input-use audit](SPATIAL_INPUT_AUDIT_RESULTS_20261022.md) finds
active spatial Q effects but zero final natural/zero proposal changes. The
spatial policy follows the historical teacher at all 14 teacher-disagreement
gates on its own sampled trajectories. Existing scheduled branches contain
no teacher-disagreement gate, so they cannot judge the upstream alternative.
Demonstration agreement suggests a hypothesis, not a proven causal bottleneck.

## Prerequisite before any learning change

Use ONLY the nine recorded online training configurations already frozen in
`results/spatial_input_audit/pilot_20261022/manifest.json`, under each retained
spatial episode-90 checkpoint, matched spatial sensing/shield/physical FSM.
Replay the source unchanged and require its recorded gates, Q values, metrics
and arrival hash to reproduce. Use the first two gates per source where the
historical and upstream teachers differ, >=2 actions are valid and >=200 ticks
remain. Do not select by outcome. Preserve sources with zero eligible gates;
at most 18 gates across all training replicates. Do not replace sparse parents
with more cases from seed 101.

At each selected state freeze policy, historical-teacher and upstream-teacher
proposals before outcome collection. Fork existing observed history, sensor
fault state, shield and held-action schedule. Replace only FUTURE arrival RNG,
using the existing independently tested future-fork mechanism; no modification
to source history or pending traffic. Use eight new future keys, with the SAME
future stream for every proposal at that gate. Freeze a distinct eight-key
set for an excluded-future check before reading either set's outcomes. The
frozen partitions are indices 400–407 (first) and 408–415 (excluded), in the
new SHA-256 namespace `spatial-teacher-v1`, keyed by policy training seed,
scenario ID, source traffic seed, tick and future index. All actual 64-bit
keys and all proposals are written to `frozen_proposals.json` and hashed
before the first branch; source/configuration is archived before collection.
No choice or threshold is fitted using either future set.

Change one held macro-action then resume the SAME natural spatial policy in
all branches for 200 ticks (20 s). Deduplicate equal proposals. Never zero or
replace the physical transition rules. Report incremental stopped delay in
vehicle-seconds, throughput, endpoint maximum accumulated wait and executed
signal samples for every gate/future. Distinguish first and excluded future
sets; no threshold or proposal selection may use the excluded set.

Bound: <=18 source/gates, <=864 distinct short branches (three proposals,
16 futures), one CPU Torch thread and 180 s cooperative cap. Incomplete
collection cannot pass. This is a diagnostic command to be implemented and
tested, not a long job or training authorization.

Continuation toward a teacher-alignment LEARNING PILOT requires, on the fixed
upstream proposal in the excluded-future set: positive aggregate delay saving
against BOTH policy and historical proposal, no aggregate throughput or
endpoint-wait loss against either, at least six of eight futures jointly
non-harmful per eligible gate (delay not increased, throughput not decreased,
endpoint wait not increased), at least one strict delay benefit in each such
gate, an eligible beneficial gate from EACH training replicate, complete
paired branches and zero measured signal violations. Retain all gates and
failures. These are engineering screens, not confidence bounds. Failure stops
this hypothesis; no gate dropping, teacher mixing or threshold relaxation.

## Only after a passing prerequisite

Freeze a separate bounded learning protocol before training. Candidate and
control both retain v9 spatial inputs, the same three original parents,
additional shield/physical FSM, v5 reward, update count and cadence. Change
ONLY the demonstration teacher from historical to upstream Max-Pressure;
retain original parents and the old zero-spatial arm as descriptive references.
Both teacher types must read the same delivered spatial packet. Preserve all
three replicates, all checkpoint curves and input/arrival provenance.

Use a fixed episode-90 endpoint and at most the earlier 90-episode/360-update
budget; no extra warmup, changed margin weight or best-checkpoint substitution
in the same comparison. Require >=2% mean-delay gain against BOTH matched
historical-teacher control and unchanged parents, no seed >1% worse than
either, no aggregate within-run p95/throughput loss, complete runs and zero
measured signal violations. Fresh DEVELOPMENT traffic seeds, exact configs,
budgets and all provenance rules must be finalized in that future protocol.
No final-test use or automatic model promotion. A positive prerequisite is
still local simulator hindsight, not proof that a learned controller can
predict the advantage or achieve a full-run gain.

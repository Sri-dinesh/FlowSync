# Update-pressure pilot: verified outcome

Input: `results/research_training/update_pressure_5qyi9cmv`.
The saved `comparison.json` reproduces exactly using the audited comparator.
The [pre-execution protocol](../protocols/UPDATE_PRESSURE_PROTOCOL_20261016.md) remains
unchanged. This is development validation, not an independent final test.

## Decision

Do not promote either arm or launch expanded evaluation. Reducing update
pressure mitigated the control arm's regression, but did not improve the mean
delay of the original parents. The predefined continuation screen failed.
Do not substitute each seed's selected best for the episode-90 primary endpoint.

| Episode-90 comparison | Mean delay (s) | Mean within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: |
| Original parents | 10.841389 | 37.035417 | 89.472222 |
| Control: 32 updates/episode | 11.109278 | 40.400417 | 89.861111 |
| Low: 4 updates/episode | 10.852250 | 38.879861 | 90.027778 |

Low updates reduce delay by 0.257028 s (2.3136%) versus control, but increase it
by 0.010861 s (0.1002%) versus the parents. Parent-relative p95 also increases
by 1.844444 s. These are descriptive estimates, not significance/equivalence
claims. The small mean difference does not establish equivalence to parents.

| Training seed | Parent delay | Control delay | Low-update delay |
| --- | ---: | ---: | ---: |
| 101 | 11.035750 | 11.222750 | 11.150167 |
| 202 | 10.810917 | 10.969417 | 10.790667 |
| 303 | 10.677500 | 11.135667 | 10.615917 |

All three seeds improve relative to control. Relative to parents, seed 101
regresses just over the predefined 1% tolerance; seeds 202/303 improve slightly.
Failed gates: 2% aggregate delay improvement versus parents, no seed regression
over 1% versus parents, and no aggregate p95 regression versus parents.

For completeness, low-update mean delays at episodes 30/60/90 are
10.843222/10.871472/10.852250 s; none beats the 10.841389 s parent mean. No
alternative common checkpoint supplies a hidden aggregate improvement.

## Integrity and execution

All six workers completed 90 episodes and 24 demonstrations. Control workers
completed 2,880 updates each (277–285 s); low-update workers completed 360 each
(234–237 s). No worker stopped on its time budget.

Verified archived source hashes, parent/checkpoint provenance, unchanged initial
weights, matched demonstration records and exogenous training inputs, paired
validation arrivals, finite weights/loss diagnostics, and intended update counts.
All 360 validation rows have full signal-audit coverage: 432,000 samples and zero
measured conflict/clearance violations. This does not establish road safety.

Selections are retained for transparency, not used to replace the primary:
control seeds 101/202 select episode 30, seed 303 selects initial; low-update
seeds 101/202/303 select episodes 30/90/60 respectively.

## Learning diagnostics and next decision

Across each arm's three seeds, first-ten versus last-ten episode logs show:

| Arm | Weighted TD loss | Unweighted minibatch TD loss | Mean absolute TD error |
| --- | --- | --- | --- |
| Control | 3.539 → 0.760 | 10.917 → 16.186 | 11.406 → 16.677 |
| Low updates | 4.989 → 1.641 | 13.483 → 17.402 | 13.976 → 17.898 |

These are last-minibatch diagnostics on changing replay samples and moving
targets, not fixed-data error curves. They do not prove optimizer divergence.
Both arms retain the earlier weighted-loss interpretation problem; the new
logging makes that visible. Lower update count alone is not the demonstrated
remedy for beating the parents or Max-Pressure.

Keep the parent policies and stop repeated larger-episode runs of this setup.
The next diagnostic should use a fixed training-only replay dataset and fixed
evaluation states to separate changing data/targets from fitting behavior before
another online training batch is proposed. Specify that diagnostic and its
checks before execution; no such diagnostic has run as part of this review.
No final-test evaluation, model promotion, default-controller change or new
training was performed while verifying this batch.

## Implementation and mechanics verification

Before the full pilot, 111 targeted regression tests passed. After adding a
truncated-endpoint case, all 13 focused update-pressure tests passed; these
overlap the broader suite and must not be added together. Shell syntax and
`git diff --check` passed. The comparator refactor exactly reproduced the saved
temporal comparison without changing its negative outcome or saved artifacts.
Tests cover target-copy positions, per-arm update budgets, worker failure
propagation, paths with spaces, mismatched inputs, invalid diagnostics,
incomplete safety coverage, and rejection of truncated or failed pilots.

The separate one-episode smoke is recorded in
`results/research_training/update_pressure_smoke_nnr27n4e`. Both arms used
parent seed 101, 24 demonstrations, validation seed 21001 and a 180-second
worker budget. Control completed in 64.8 seconds with 32 optimizer updates;
low-updates completed in 58.0 seconds with four updates. These are mechanics
checks, not the episode-90 continuation comparison above.

| Smoke checkpoint | Mean validation delay (s) |
| --- | ---: |
| Initial, both arms | 12.489 |
| Control after one episode | 12.574 |
| Low updates after one episode | 12.600 |

Both retained their initial checkpoint. Checks confirmed unchanged parents,
initial/warmup weights equal to parents, paired demonstrations and training
inputs, finite weights/diagnostics, checkpoint hashes, frozen source archive
and validation arrival pairing. All 36 smoke validation rollouts had complete
signal coverage: 43,200 samples and zero measured conflict/clearance violations.
Neither smoke checkpoint improved delay; no model was promoted and no final-test
panel was used. These measurements establish execution compatibility, not
performance benefit or real-world safety.

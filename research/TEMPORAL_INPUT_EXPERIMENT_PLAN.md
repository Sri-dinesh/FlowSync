# Next bounded hypothesis: causal movement history and frame age

Status: **full pilot completed; continuation screen failed**. The three-seed
temporal arm did not improve over control; do not promote or expand this recipe.
See [results and the subsequent diagnosis](TRAINING_DRIFT_RESULTS_20261016.md).
The recipe below is retained for reproducibility, not a recommendation to rerun.

## Why this is different from more episodes

The current v7 encoder adds outgoing counts and phase-service timers to the
shared state, but not explicit frame age or a movement-level count history.
There is already aggregate arrival forecasting; do not claim the policy has
no temporal information at all. Fault injection supplies observation age in
context telemetry, but that value is not appended by the v7 policy encoder.
The hypothesis is that exposing limited causal history and age can disambiguate
similar instantaneous counts under delayed/missed observations. This does not
explain or guarantee closing the clean-traffic gap to Max-Pressure.

State representation already matters in prior traffic-control research, e.g.
[Advanced-MP/Advanced-XLight](https://proceedings.mlr.press/v162/zhang22ah.html).
The proposed history extension is not claimed as a novel technique by itself.

## Implemented observation contract

The separately versioned, opt-in research observation has 64 features:
36 unchanged v7 values; 12 delivered movement counts from one second earlier;
12 from three seconds earlier; one normalized delivered-frame age; two history
availability flags; one age-availability flag. Keep the existing count encoding.
Age is clipped at five seconds and divided by five. Unknown age is flagged
unknown, not declared fresh. Clean simulated packets explicitly have known age
zero. Record every feature's normalization and version in the checkpoint.

History is built from delivered post-fault packets on every 0.1-second tick,
not only decision steps. It must never use clean future counts, ground-truth
vehicle waits or latent arrival rates. Missing history is zero-padded with a
false availability flag; reset at every episode. Repeated stale packets remain
repeated observations with increasing age, not newly measured fresh counts.
Keep masks and mandatory signal timing unchanged.

Share the same history builder between demonstrations, online training and
evaluation. Add tests for episode reset, causal indexing, repeated frames,
availability flags, identical train/inference encodings and checkpoint version
rejection. Existing 28/36-dimensional checkpoint behavior must remain unchanged.

## Frozen matched pilot recipe

Two arms, all three parent training seeds:

- Control: a 64-input network receiving current v7 features and 28 zeros.
- Treatment: identical architecture receiving the 64 features above.

Expand each selected parent's first layer by zero-initializing the new input
columns and copying all original weights. Verify that both arms reproduce the
parent policy initially. New columns may learn during online training. All
other hyperparameters, demonstrations, randomization, update limits and
shield settings remain paired. Fallback stays disabled to isolate the change.
The zero-padded control avoids attributing extra network parameters to history.

The launcher freezes exact code/protocol/scenario/parent hashes before spawning
workers. Parents are the same three shield-selected v5 checkpoints; original
checkpoint files are not overwritten. Training seeds: 101, 202, 303. Fixed
validation seeds: 21001, 21002; all three existing validation templates; existing
clean and `validation_mixed` profiles. These are development seeds, not a new
independent test. All updates use training-only data.

Both arms use 90 online episodes, 24 demonstration episodes, zero imitation/TD
warmup updates, learning rate 1e-4, target synchronization every 200 updates,
constant demonstration margin weight 0.5, domain randomization, 1,200 ticks per
training episode and shield on/fallback off. Each **completed episode performs
exactly 32 optimizer updates after collection**; validation every 30 episodes.
The fixed update schedule applies to both arms and is an explicit departure
from the legacy per-transition schedule. It prevents unequal decision counts
from changing the optimizer budget. A replay pool smaller than batch size 128
is an error, not permission to silently skip scheduled updates.

Three workers run in each of two sequential waves (control, temporal), with a
360-second cooperative cap per worker covering collection, updates and validation.
Allow about 12 minutes plus atomic validation/checkpoint overhead; the cap can
stop runs before all 90 episodes. The comparator uses the latest common completed
online checkpoint across **all six runs**, not each arm's best and not an
unequal wall-time endpoint. It reports the full common checkpoint curve and
all three paired seeds. No common online checkpoint means comparison unavailable,
not a successful performance experiment. Long training remains user-run.

```bash
bash research/run_temporal_pilot.sh
```

Inspect the printed folder's `comparison.json`, summaries and logs. Check
`comparison_available` first; then `primary.continue_to_expanded_validation`.
A zero failed-process flag alone establishes neither completed training nor
improvement. No automatic website/Supabase promotion occurs.

For a first screen, require at least 2% aggregate mean-delay improvement over
the matched control, no training replicate with more than 1% mean regression,
no aggregate within-run p95 or throughput regression, and no signal-audit
failure. These are proposed engineering continuation criteria, not statistical
proof or safety guarantees. Failure stops expansion; do not tune the criteria
after seeing results. Passing only justifies a larger fresh-seed validation
against matched-shield Max-Pressure, not promotion or final-test superiority.

The old frozen final test remains a historical result. Any new final evaluation
must follow a frozen model and protocol, with no subsequent tuning on its data.

## Verification completed before the full pilot

221 targeted regression tests passed, including causal lag/reset/stale-frame
handling, version rejection, zero-initialized weight expansion, exact temporal
training/inference input parity, matched update budgets, checkpoint comparison,
launcher failure propagation and the existing controller/simulation suites.
Shell syntax and whitespace checks pass. Legacy 28/36-dimensional policies and
the physical FSM are unchanged; v8 requires the research history builder and is
not implicitly supported by the website sensor path.

A real two-arm mechanics smoke completed in
`results/research_training/temporal_smoke_v2_20261016/{control,temporal}` using
seed 93011, one online episode, four optimizer updates and one validation seed
(21001). Each collected 298 transitions from 24 demonstrations. Initial and
warmup validation panels matched exactly. All recorded training losses were
finite. The temporal extension's maximum absolute input weight became 0.0004011;
the control extension remained exactly zero. Each arm completed in about
55–56 seconds. The 36 validation simulations contain 43,200 signal-audit
samples with zero measured conflicts/clearance violations.

The four-update smoke did **not** improve validation: initial mean delay was
12.4887 s for both arms, versus 12.5737 s control and 12.7602 s temporal after
the episode. Both retained their initial checkpoint. These very short mechanics
checks are not evidence of superiority, and no smoke checkpoint is promoted.
An earlier four-demonstration smoke lacked a full replay batch and correctly
failed; its partial artifacts are preserved in `temporal_smoke_20261016`.

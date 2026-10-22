# Policy decision audit and next short learning test

## What the diagnostic established

The [frozen diagnostic](../protocols/POLICY_DECISION_PROTOCOL_20261016.md) completed all
36 training-only source rollouts, using all three selected v5 policies. It
observed 518 genuine semi-MDP decision gates, 39 proposal disagreements with
Max-Pressure, and 37 effective disagreements after the same shield. Thus the
policies already agree with the teacher on about 92.5% of sampled proposals.

Thirty-four disagreements had eligible paired 20-second comparisons. Replacing
one RL macro-action with the teacher action reduced incremental delay in 19
and increased it in 15; the teacher's mean saved delay was **-1.821
vehicle-seconds** across these events. The teacher reduced endpoint maximum
upstream wait in ten, increased it in six, and tied in 18. Neither controller
dominates these sampled choices. Reward and delay short-horizon rankings opposed
each other in only two comparisons; this does not establish a major reward bug.

The paired alternatives retain the teacher proposal for the same action-hold
interval, then resume the same frozen RL continuation. They do not compare an
entire Max-Pressure rollout to an RL rollout, and are not unbiased long-horizon
Q targets. First-event sampling, repeated states and one traffic seed limit
generalization. No significance or final-test performance claim follows.

All exact planned cells, checkpoint and archived source hashes, paired branch
arrivals and complete branch safety coverage verified. Source rollouts contain
43,200 signal-audit samples; branches contain 13,600. No measured conflict or
clearance violations. Tests verify source-trajectory preservation and correct
alternative action-hold state. Simulator truth scores outcomes only; it is not
fed to a controller.

Artifacts: `results/policy_decision_audit/train_20261016/`.

## Targeted hypothesis: release the imitation margin

The current demo loss penalizes other actions overtaking the stored teacher
action, with a fixed margin and fixed weight throughout training. That is an
intentional training constraint, **not a newly proven implementation defect**.
The diagnostic shows why assuming the teacher is always preferable is unjustified.
It does not prove that the constraint caused the observed final-test deficit.

The research trainer now supports optional `--demo-loss-final-weight` and
`--demo-loss-decay-episodes`. This linearly releases the margin during online
training only. It retains demonstration transitions for TD replay, leaves
warmup unchanged, and records the applied weight in episode logs/checkpoints.
Omitting these flags preserves the old constant-weight behavior.

A [paired pilot](../protocols/MARGIN_RELEASE_PROTOCOL_20261016.md) compares constant 0.5 with
release to zero over 60 online episodes, starting from each of the same three
parent checkpoints. This is continuation of existing models, not training from
scratch or selecting the best seed. It runs two three-process waves capped at
300 seconds per process, nominally about ten minutes plus atomic-step overhead.
The full pilot has **not** been launched by the assistant; the user previously
chose to run longer batches personally.

```bash
bash research/run_margin_release_pilot.sh
```

The printed batch folder includes `comparison.json`. The comparison audits
individual runs, source/parent provenance, matching non-schedule arguments and
cross-arm arrivals. It compares only the common completed validation candidate
grid for each pair. It refuses to declare an available comparison if no common
online validation completed. Process success alone is not completion of all
planned training or evidence of improved performance.

## Smoke verification, not a performance result

A real two-episode mechanics test completed in 86.26 seconds, with 12
demonstration episodes and 359 replay transitions at warmup. It used parent
seed 101, training seed 93001, and validation seed 21001. Applied margin weights
were 0.25 and 0.0; all 48 online TD updates had finite recorded losses. At the
final sampled batch, 85.156% of examples still came from demonstrations, while
the weighted margin loss was exactly zero. Four candidate validations passed
the existing artifact-integrity audit.

Mean validation delay changed from 12.4887 to 12.2593 s, but average within-run
p95 increased from 39.9367 to 40.3000 s. This single-seed, two-episode smoke test
has no matched constant-weight arm and **must not be cited as evidence that
margin release improves performance**. It is not compared to the five-seed
validation averages from previous reports. The full pilot uses shorter episodes,
two validation seeds, and skips repeated initial classical baselines to reduce
runtime; these cost reductions are identical in both arms and were fixed before
that pilot, not selected from its performance.

Smoke artifacts: `results/research_training/margin_release_smoke_20261016/`.
No website model, default, prior result, checkpoint or Supabase object was
replaced. Research superiority and real-world readiness remain unestablished.

Verification: 175 targeted regression tests passed across the learning,
simulation, audit and controller suites; shell syntax and whitespace checks pass.

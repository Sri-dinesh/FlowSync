# Short paired teacher-margin release pilot

This is a hypothesis test, not a proven correction or a guaranteed improvement.
The training-only policy audit found RL/teacher agreement at 479/518 proposal
gates. Among 34 paired effective disagreements, the teacher reduced short-horizon
delay in 19 and increased it in 15. Fixed imitation should not be assumed to
help every state. Only 2/34 short-horizon reward rankings opposed delay rankings;
this does not justify wholesale reward replacement or prove long-run Q error.

## Fixed design

Reuse each of the three selected v5 checkpoints as its own parent. Run paired
arms with identical seeds/configuration: constant demonstration margin weight
0.5 versus a linear online-only release from 0.5 at episode zero to zero at
episode 60. Keep demonstrations in TD replay. Keep physical timing, shield,
v5 reward, masks, target updates, network architecture and observations unchanged.
Fallback stays disabled in both arms. Website defaults stay unchanged.

Each arm: 120 online episodes; 24 demonstration episodes to refill replay;
zero imitation/pretraining updates (reuse the trained parent); learning rate
0.0001; target update 200; domain randomization; 1200 ticks per training episode;
validation every 30 episodes on the three validation templates, clean/mixed
faults, seeds 21001/21002. Checkpoints are selected by the existing validation
mean-delay rule, retaining the incumbent on ties. Warmup weights equal the parent.
Existing parent fine-tuning epsilon schedule is identical in both arms: starts
at 0.25 and reaches 0.05 by 80% of the planned episodes.

Both arms skip redundant classical-controller runs at initial validation;
initial, warmup and scheduled **policy** validations remain mandatory. This
pilot tests the margin schedule against its matched control, not superiority
over classical controllers. Its shorter episodes/two validation seeds reduce
screening cost; both arms use the same settings. The 86-second, two-episode
mechanics smoke test motivated the smaller workload before this full pilot,
not a search over validation performance.

Run three processes per wave, constant then release, capped at 300 seconds per
process, including validation. Nominal wall budget is about ten minutes plus
atomic-step/saving overhead. Each worker can stop at its cooperative limit;
failure flag zero does not prove completed training or completed validation.
If capped runs have different validation coverage, compare only common completed
candidate checkpoints per pair before claiming a schedule benefit; retain all
original selections and outcomes. Report every training seed, not the best one.

This is a short *continuation experiment*, not six independent from-scratch
models. Reused development validation is not final-test or real-world evidence.
Do not run another large final suite unless the paired result supports further
investigation. A negative result is preserved, not used to lower baselines.

Run from the repository root:

```bash
bash research/run_margin_release_pilot.sh
```

The launcher validates parent selection/checkpoint hashes before any workers
start. The batch retains a source/protocol snapshot and per-worker logs; the
trainer records the applied weight per episode and in checkpoints. Nothing is
uploaded, promoted, or overwritten.

The launcher also writes `comparison.json`: a read-only artifact audit and
paired comparison restricted to common completed validation candidates. A
missing common online candidate returns an unavailable comparison, not a win.
Inspect both the process flag and comparison status.

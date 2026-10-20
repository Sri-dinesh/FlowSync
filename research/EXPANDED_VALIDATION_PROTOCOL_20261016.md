# Frozen expanded validation after the margin-release pilot

Written before execution. This is additional **development validation**, not a
new final test, a claim of unseen scenario families, or a parameter search.

## Candidates and comparisons

Freeze the three constant-arm selections from `margin_release_6usc2j0j`:
seed 101 episode 120, seeds 202 and 303 initial checkpoints. Compare each with
its original selected v5 parent. The latter two retain identical policy weights;
report those null changes rather than dropping seeds. The candidate family is
the constant arm, not a hand-picked mixture of winning arms. This experiment
does not estimate the causal effect of margin release; episode 120 was outside
that earlier matched candidate grid.

Classical references: Fixed, Actuated, Greedy, Max-Pressure and Max-Pressure with
the same unchanged shield. All consume the same sensor-fault assumptions and
physical signal FSM. All learning policies use the shield, with uncertainty
fallback disabled. Do not call them the full FlowSync-UQ method.

All three existing validation templates, existing clean/mixed fault profiles,
traffic seeds **24001–24005** (not present in existing experiment manifests at
freeze). Five seeds are a quick screening set, not sufficient independent
evidence of universal superiority. Each policy pair contributes 60 simulations;
the baseline panel contributes 150: **330 total**. Run separate processes to
avoid shared global RNG interference. No optimization, changing candidates,
threshold tuning or website promotion occurs during this evaluation.

## Reporting and integrity

Check exact planned cells, checkpoint/scenario/source hashes, source archives,
matching arrivals across every panel, finite metrics and full signal-audit
coverage. Preserve all outputs in a new directory. Primary comparisons: the
candidate family against its parents and matched-shield Max-Pressure. Report
each parent seed and the aggregate, mean delay, mean within-run p95, throughput,
interventions and measured signal violations. Classical no-shield comparisons
are secondary; do not silently remove the shield to manufacture a win.

Use descriptive crossed training-replicate/traffic-seed bootstrap intervals,
with conditions fixed and no significance claims from a handful of seeds.
Two unchanged parent/candidate pairs are genuine unchanged outcomes, not new
independent successful learning runs. Preserve negative results. No follow-up
training or full final-test batch is justified solely by selecting a favorable
metric from this development screen.

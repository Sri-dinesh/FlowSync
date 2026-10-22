# Matched spatial-input learning pilot

Prespecified before inspecting the spatial mechanics-smoke traffic outcomes.
Run only after mechanics/tests verify the v9 input and fault contract in
`SPATIAL_INPUT_EXPERIMENT_PLAN_20261021.md`. This is the first multi-parent
learning screen of these inputs, not an independent confirmation or an
assumption that corrected geometry improves traffic.

Two arms: control (`v9_48dim_zero_spatial`) and spatial (`v9_48dim_spatial`),
three existing frozen parents 101/202/303 from pilot_v5_kbW0lsY3 selections.
Zero-expand the twelve new input columns; initial weights/outputs must match.
Both collect the full spatial sensor packet; only the control's extra network
inputs are zero. Historical checkpoints and masks/shields/reward are unchanged.

Both arms: 90 online episodes, 24 demonstration episodes, zero imitation/TD
warmup, exactly four optimizer updates after every complete online episode,
target sync every 25 updates, learning rate 1e-4, margin weight 0.5 constant,
1,200 simulation ticks/episode, domain randomization, shield on/fallback off.
Identical training seeds produce paired exogenous traffic/scenario/fault
schedules. Different decisions/replay contents after learning are expected.
No policy-specific reward or teacher changes.

Evaluate initial/warmup/30/60/90 checkpoints on all three validation templates,
seeds 21001/21002, clean and existing validation_mixed profiles. These repeatedly
used DEVELOPMENT cells are not fresh validation or final-test evidence.
Skip redundant initial classical evaluations; the first screen compares the
new representation to its matched learner AND each unchanged parent. A pass
only permits fresh development evaluation with matched-shield Max-Pressure,
upstream-only Max-Pressure and other baselines receiving the same sensor data.

Primary: episode 90 across all six runs, 360 optimizer updates each. A shorter
common checkpoint is descriptive and cannot pass. Report the full common
checkpoint curve and all seeds, not selected best checkpoints. Require all
six workers to finish, all demonstration episodes and all validation cells,
paired arrivals, matching source/scenario/checkpoint provenance, finite
learning diagnostics and complete signal samples.

Continuation requires at least 2% aggregate mean-delay improvement against
BOTH matched control and unchanged parents, no parent replicate regressing
more than 1% against either, no aggregate within-run p95 or throughput loss
against either, and zero measured signal violations for every completed
candidate. These engineering criteria are unchanged in spirit from the
earlier low-update pilot; they are not statistical significance or safety proof.
Failure stops expansion, with no threshold relaxation or best-seed substitution.

Two sequential waves, three workers each, 600-second cooperative cap per
worker. Budget stops preserve partial data and cannot pass the primary screen.
Allow roughly 20 minutes plus in-flight validation/save overhead; actual
completion can be faster or budget-limited. Long training is user-run.
Freeze code, protocol, train/validation YAMLs and parent hashes before launch.
No automatic model promotion, Supabase upload or final-test access.

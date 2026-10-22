# Spatial input-use and action-choice diagnosis

Protocol: [frozen bounded diagnosis](SPATIAL_INPUT_AUDIT_PROTOCOL_20261022.md).
Artifact: `results/spatial_input_audit/pilot_20261022`.
Parent experiment: [failed spatial pilot](../results/SPATIAL_INPUT_RESULTS_20261021.md).

## Outcome

The new inputs reach the network and change Q values, but **zeroing them changes
none of the episode-90 policy's proposals on 320 inspected gates**. This includes
108 gates on spatial-policy trajectories, 110 on control trajectories and 102
on teacher demonstration trajectories. This is a bounded diagnostic finding,
not a universal statement that spatial traffic information is useless.

The implementation completed all 27 planned training-configuration rollouts,
36 prescheduled branch gates and 44 distinct action branches in 31.15 seconds.
Every source has 1,200 audited ticks; each branch has 200. The 41,200 signal
samples have zero measured conflict/clearance violations. All nine selected
demonstrations reproduce original logged reward, delay and shield counts.
Online sources use final deterministic policies on recorded randomized training
configurations; they do not reproduce the original exploratory action sequences.

The original failed spatial comparison reproduces exactly. All originally
archived Python sources still match the spatial pilot's hashes. The new input,
output and source-archive hashes verify. Separate verification reproduces all
5,120 network scores, the weight analysis, teacher proposals and report from
raw records. It does not independently rerun every source/branch trajectory.

Current targeted verification passes 53 tests across the new input-audit,
spatial-policy, spatial-pilot and upstream-observation suites. This includes
source-trajectory preservation under clean/faulty sensing, exact demo replay,
branch hold/deduplication and rejection of fabricated saved Q values even if
their artifact hashes and summary are updated. `git diff --check` passes.
Existing dependency deprecation warnings remain; the full repository/frontend
suite was not run.

## Input sensitivity and choices

All initial added columns are zero, and every control checkpoint's added
columns remain zero. Spatial episode-90 column L2 norms are 0.489672, 0.349071
and 0.419477 for seeds 101/202/303; maximum absolute weights are 0.027395,
0.022301 and 0.028500. Weights are finite and changed from initialization.
Control probes and initial spatial probes have exactly zero extra-input effect.

| State distribution | Gates | Gates with nonzero spatial inputs | Mean maximum absolute Q change | Mean range of valid-action Q changes | Mean valid-action margin | Episode-90 proposal changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Control-policy trajectories | 110 | 107 | 0.861657 | 0.098035 | 2.224985 | 0 |
| Spatial-policy trajectories | 108 | 106 | 0.863911 | 0.099808 | 2.170554 | 0 |
| Teacher trajectories | 102 | 100 | 0.623707 | 0.098285 | 2.269435 | 0 |

These are natural-versus-zero-input comparisons using the SAME spatial
checkpoint, delivered base features and mask. Q units are learned discounted
returns, not traffic delay. The much smaller range across valid actions shows
that most input-induced Q movement is shared across actions; action rankings
are less sensitive. Comparing means is descriptive, not a bound at each gate.
No final proposal changes exist for the shield to suppress. At episode 30,
there are 3/110, 2/108 and 1/102 proposal changes on these same state panels,
respectively, and all survive the shield. These overlapping shadow panels are
not six independent traffic improvements. Episode 60 changes none.

| Training replicate, spatial-policy states | Gates | Natural/zero changes at episode 90 | Initial/final proposal differences | Final control/spatial proposal differences |
| --- | ---: | ---: | ---: | ---: |
| 101 | 42 | 0 | 5 | 1 |
| 202 | 35 | 0 | 1 | 2 |
| 303 | 31 | 0 | 6 | 7 |

Online training does change decisions. Differences between arm checkpoints
include changes to their shared weights and replay, so they cannot be attributed
solely to use of the extra inputs at inference. Zero-input probes do not undo
the inputs' possible effect on training gradients or targets.

## Short paired outcomes

At the 18 scheduled branch gates on each policy's trajectories, zeroing spatial
inputs changes no action, so the corresponding branches match exactly.
Historical and upstream Max-Pressure propose the same actions at ALL these
scheduled branch gates; their outcomes are duplicates, not independent evidence.

| Acting policy | Scheduled gates | Teacher changes proposal/execution | Delay benefits / harms among changed cases | Mean delay saved over changed cases (vehicle-seconds) | Total throughput gain over all scheduled gates | Mean endpoint maximum-wait reduction over all gates (s) |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Control | 18 | 4 / 4 | 2 / 2 | 11.075 | 5 | -1.361 |
| Spatial | 18 | 4 / 4 | 3 / 1 | 12.725 | 4 | -0.311 |

These change one held macro-action, preserve the next decision time and then
resume the same acting RL policy, with matched sensing, additional shield and
physical FSM. Delay saved is incremental stopped waiting over 20 seconds,
in vehicle-seconds; it is not a full-run controller delay advantage. Endpoint
wait worsens in aggregate despite average delay savings. Outcomes use one
shared future per gate and retain known arrival sensitivity.

Across ALL sampled gates, the teachers disagree at 14 control, 14 spatial and
13 teacher-state gates. The final spatial checkpoint chooses historical
Max-Pressure's proposal in every one of these 41 inspected cases, and never
the upstream proposal. These overlapping state distributions are not 41
independent experiments. None of these teacher-disagreement gates was among
the preselected branch gates. Therefore the local outcomes above do not test
the specific change from historical to upstream teacher semantics.

## Demonstrations and optimizer snapshots

On teacher trajectories the spatial checkpoint agrees with historical teacher
proposals at 95/102 initial gates and 101/102 episode-90 gates. Hinge margin
violations fall from 17 to 9. Agreement with the upstream teacher rises from
82/102 to 88/102. This is consistent with learning the historical teacher's
choices; it is not a causal demonstration-loss ablation.

| Spatial training seed | Sampled demo fraction, first/last 15 | Raw TD loss, first/last 15 | Importance-weighted TD loss, first/last 15 | Weighted demo margin loss, first/last 15 |
| --- | --- | --- | --- | --- |
| 101 | 0.7339 / 0.1958 | 8.5233 / 11.8077 | 2.7814 / 1.2467 | 0.0544 / 0.0043 |
| 202 | 0.7432 / 0.1927 | 13.8247 / 19.4926 | 4.8606 / 1.6846 | 0.0183 / 0.0035 |
| 303 | 0.7318 / 0.1797 | 18.7636 / 18.4920 | 6.4470 / 1.8314 | 0.0205 / 0.0024 |

All six runs' recorded optimizer fields are finite. Pre-clipping gradient
norms are nonzero; spatial first/last-15 means are 10.0578/3.6933,
15.4639/6.5042 and 14.2116/7.4914. Mean Q values become more negative. Neither
this shift nor falling weighted loss proves a defect or control improvement.
Each episode records only its LAST update's diagnostics, not all four updates.
The control-arm telemetry and every original row remain preserved. These
snapshots cannot establish that imitation caused spatial inactivity.

## Decision and next hypothesis

No delivery, initialization or inference-input mismatch was reproduced. The
new columns are learned and numerically active, but contribute little to
relative action values in this panel. The failed pilot is not explained by a
disconnected input or by shielding every spatially changed proposal. No
reproducible optimizer defect has been established, so no learning correction
or longer batch is justified by this audit alone.

One follow-up hypothesis is **teacher semantics alignment**: teaching choices
based on upstream rather than discharged-inclusive demand might teach the
network spatially distinct actions. Current evidence establishes a choice
disagreement and persistent historical-teacher agreement; it does not establish
that the upstream choices are better. The next prerequisite is a bounded,
separate-future action diagnostic specifically at those disagreement states,
as specified in [the conditional plan](../protocols/SPATIAL_TEACHER_ALIGNMENT_PLAN_20261022.md).
That prerequisite and its separate horizon diagnostic subsequently completed
and [failed](../results/TEACHER_ALIGNMENT_RESULTS_20261022.md). No teacher replacement or
training command is justified by these results.

For writing, this supports a simulation-only negative ablation: additional
geometric inputs can alter Q magnitudes without materially changing final
decisions. Do not turn it into a claim about general representation adequacy,
uncertainty benefit, real cameras, safety certification or paper novelty.

## Reproduction and verification

The complete diagnostic is already preserved; it need not be rerun. Verify
without simulation, using a new output filename:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  research/verify_spatial_input_audit.py \
  results/spatial_input_audit/pilot_20261022 \
  --output /tmp/spatial_input_verification.json
```

The frozen collection entry point is `research/audit_spatial_inputs.py`; its
three-minute cooperative cap is fixed. Source archives preserve the executed
implementation. No checkpoint edits, optimizer updates, final-test rollouts,
Supabase uploads, default-policy changes, commits or pushes were performed.

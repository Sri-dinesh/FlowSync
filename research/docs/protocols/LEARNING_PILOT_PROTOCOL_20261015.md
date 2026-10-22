# Short v5 learning pilot — user-run

Prepared before execution. The user subsequently ran it at
`results/research_training/pilot_v5_kbW0lsY3`; no duplicate batch was launched.
The user has chosen to execute training personally.

Three independent fresh seeds (101/202/303), each capped at 600 seconds including
initial validation, demonstrations, pretraining and online learning. This is a
cooperative limit, so the last validation simulation and checkpoint saving may
overrun slightly. This is not a completed 900-episode matched experiment.

Retain `--episodes 900` specifically to preserve the prior exploration decay
schedule; shortening that argument would also change epsilon at every training
episode. Use the same 200 demo episodes, 2,000 imitation updates, 500 TD warmup
updates, learning rate 0.0001, target update 200, v7 observations, train-only
domain randomization, 3,000-tick episodes and demo loss weight 0.5. Shield remains
enabled during collection and selection; fallback remains disabled.

Validate every 50 episodes on the same three validation templates and seeds
21001–21005 under clean/mixed faults. This increases diagnostic resolution;
do not attribute a lower selected score solely to learning when the candidate
grid differs from previous experiments. Inspect common checkpoints, all three
seed trajectories, and the selected model's full metric set. No final tests.

The active research runtime now uses v5 single-switch reward and discards
incomplete final macro-actions. Check both versions/semantics in the manifest,
actual stop reason, completed episode counts, finite losses/Q values, sampled
demonstration fraction, weighted TD/demo losses, reward component totals and
dropped-transition ticks. Compare validation delay and tail delay against
warmup and the existing matched controls; reward totals are not comparable to
v4 totals. A time-limit stop is expected, not an execution failure. If no full
validation completes, there is no selected candidate to assess.

Preserve all outcomes. The pilot can justify further investigation; it cannot
establish generalization, superiority, real-world safety or publication readiness.

## Read-only output checks

After the batch finishes, pass all three individual seed directories to
`server/venv/bin/python research/audits/audit_training_results.py`. This prints JSON;
it does not mutate artifacts or launch simulations. It checks recorded validation
cell coverage, finite traffic metrics, checkpoint file hashes, paired arrival
hashes, recomputed selection scores, summary consistency and the first minimum
among completed candidates. Completed runs must contain every scheduled validation.
Budget-stopped runs may contain an incomplete, unselected validation candidate.
Missing summaries are reported as unavailable, not proof that a process failed.

This is an artifact-consistency check, not proof of execution provenance,
checkpoint tensor finiteness, source reproducibility or independent performance.
The report includes every completed candidate, not just a winning seed. Continue
to inspect training diagnostics and the original manifest separately.

## Completed pilot findings

All three runs reached the intended 600-second budget during online training,
after completing all demonstrations and warmup updates. They completed
223/223/219 online episodes. All 18 candidate evaluations passed artifact checks;
all 665 logged episode records contained finite numeric values. Selected online
and target network tensors were finite, v5 reward/replay metadata matched, and
all recorded source hashes matched the worktree at inspection time.

| Seed | Selected checkpoint | Mean validation delay | Average within-run p95 |
| --- | --- | ---: | ---: |
| 101 | warmup | 10.903133 s | 37.459667 s |
| 202 | episode 50 | 10.910600 s | 36.755833 s |
| 303 | episode 100 | 10.779000 s | 36.705167 s |

Across the selected models, mean delay is 10.864244 s versus Max-Pressure's
10.844967 s (0.18% worse); average within-run p95 is 36.973556 s versus
40.123833 s (7.85% lower). Throughput is 84.488889 versus 84 vehicles per run.
These are validation-selected outcomes, not independent superiority evidence.
Do not describe average p95 as a pooled vehicle percentile or report only seed 303.

Best mean-delay gains over each seed's warmup are 0, 0.0965 and 0.1177 seconds.
All runs retained substantial exploration at cutoff (epsilon about 0.34).
Demo samples still represent about 44.5% of the final logged sampled batch;
there is no indication that the demonstrations disappeared from replay.
Negative Q magnitudes and higher TD errors alone do not establish divergence.
The candidate grid and execution budget differ from the old 900-episode batch;
the fixes have not established a consistent mean-delay improvement.

The next separately frozen check is [the matched-shield protocol](MATCHED_SHIELD_PROTOCOL_20261015.md),
including shielded Max-Pressure to distinguish policy and shield contributions.
Do not tune using its fresh-seed results.

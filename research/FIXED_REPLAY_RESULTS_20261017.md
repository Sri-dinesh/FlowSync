# Fixed-replay diagnostic: outcome

Artifacts: `results/fixed_replay/update_pressure_20261017`.
[Pre-execution protocol](FIXED_REPLAY_PROTOCOL_20261017.md).
Completed in 85.84 seconds: all three parents, three arms, 200 updates per arm,
45 full-dataset measurement points. No learned checkpoints were saved/promoted.

## What this established

The production optimizer can fit fixed labels on these samples. It does not
transfer that fit reliably to the reserved training episodes: fixed-label error
increases on the probe partition for all three parents. This is a concrete
fitting-versus-transfer gap, not evidence of a broken optimizer or proof that
the original full training corpus is too small.

All values below are prediction-error units, **not seconds of traffic delay**.
Means give each parent equal weight; all arms start from the same parent metrics.

| Full fixed dataset metric | Initial | Fixed labels, update 200 | Moving selector, update 200 | Moving target, update 200 |
| --- | ---: | ---: | ---: | ---: |
| Fit error against initial labels (MAE) | 11.020 | 1.313 | 1.325 | 26.991 |
| Probe error against initial labels (MAE) | 10.745 | 12.648 | 12.818 | 26.484 |
| Fit live Bellman error (MAE) | 11.020 | 1.419 | 1.135 | 5.815 |
| Probe live Bellman error (MAE) | 10.745 | 12.776 | 12.945 | 15.382 |
| Probe live-target change from initial labels (MAE) | 0 | 0.225 | 0.245 | 27.259 |

The fixed-label joint fitting objective (Huber plus demonstration margin)
decreases from 10.613 to 1.008; on probe data it increases from 10.354 to 12.584.
Thus the fit/probe result is not explained only by ignoring the margin term.

| Parent seed | Fit/probe transitions | Initial probe label MAE | Final fixed-label probe MAE |
| --- | ---: | ---: | ---: |
| 101 | 100 / 62 | 3.920 | 4.149 |
| 202 | 80 / 54 | 11.479 | 13.081 |
| 303 | 85 / 36 | 16.835 | 20.714 |

Changing next-action selection while holding the target network produced
relatively small target movement here. Copying the target every 25 updates
produced much larger movement, even without changing the dataset or sampling
schedule. **Movement alone is not proof of bad targets or divergence**: initial
labels are parent predictions, not known correct returns, and changed Bellman
targets may legitimately move toward different values. Live fit TD error still
decreases in that arm. No traffic rollout of a fitted diagnostic network was
performed, so no efficiency or safety gain/loss is inferred from action changes.

## Scope and integrity

- Regenerated 36 training episodes using frozen parents/teacher, shield on;
  these are not the original online replay buffers. No final-test collection.
- Each seed uses eight fit episodes and four probe episodes, split before
  fitting. Probe episodes are excluded from optimizer batches. They are
  purposively reserved, already-seen-domain training cases, not independent
  validation or a representative random sample of real traffic.
- All three arms use identical uniform-with-replacement batches (200 × 128),
  unit importance weights and unchanged demonstration flags/margin. PER is
  deliberately bypassed; conclusions do not isolate its contribution.
- Frozen input/source/dataset hashes, source archive, per-seed index schedules,
  original target labels, transition counts and raw-report recomputation all
  verified. Parent checkpoint files remain unchanged.
- The fixed-label adapter's optimizer update matches explicit supervised
  regression exactly in its unit test. Target/mask/terminal semantics,
  non-mutating metrics, case split rejection and report pairing are covered.
  **66 targeted regression tests passed**; `git diff --check` passed.

## Next bounded decision

Keep existing parent policies; do not launch another long training batch or
freeze production targets based on this diagnostic. More optimizer updates
alone are not supported by these findings.

The next useful controlled diagnostic is replay coverage: add prespecified
training cases while keeping the original probe episodes excluded, fixed labels,
initial parents, optimizer and update budget unchanged. This tests whether a
broader fitting set improves transfer on the same development probe panel.
It is not yet implemented/run and would not establish traffic superiority even
if successful. Separately, any proposal to change target refresh needs evidence
against rollout returns, not distance from initial Q predictions alone.

No production reward, agent update, controller default, website model or frozen
paper-test result was changed in this diagnostic. The research-superiority and
real-world-readiness objectives remain unachieved.

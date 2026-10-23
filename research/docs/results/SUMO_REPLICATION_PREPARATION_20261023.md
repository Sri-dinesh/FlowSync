# Independent SUMO replication preparation — historical setup

**Completed update:** The user ran and verified the full panel. Read the
[completed results](SUMO_FUTURE_PANEL_RESULTS_20261023.md): 204 branches, four
of six gates with both delay-gain signs, and identical single/mean-eight
choices benefiting one source. The old launch instructions below are retained
as provenance, not a request to repeat the completed experiment.

The empirical-paper writing deadline is October 31. This work prepares a
bounded independent check of future-arrival action stability while preserving
the original custom-simulator evaluation. It is not a new trained controller,
a performance win or completed scientific replication.

## Completed mechanics

Installed eclipse-sumo, traci and sumolib **1.24.0** in an isolated Python
3.11.15 environment at `/tmp/flowsync-sumo-20261023`. Existing application and
research environments/checkpoints were not modified. The optional dependency
file is [requirements-sumo.txt](../../requirements-sumo.txt).

Snapshot-based feasibility attempts `results/sumo_feasibility/smoke_20261023`,
`smoke_20261023_r2` and `smoke_20261023_r3` remain preserved as failures. Matching
visible snapshot state did not ensure continuation equality. Default speed
variation explained one mismatch, but deterministic-driving snapshot reload
still diverged later at a junction; the exact unsaved cause is not isolated.
This is consistent with SUMO's documented state-persistence limitations, not
a new general claim about all SUMO configurations.

`results/sumo_feasibility/replay_20261023` instead reconstructs each branch by
fully replaying the source history. Eighteen repeated rollouts across nine
action/future combinations pass at six-decimal trace precision, including the
original source continuation. It records 16,340 signal samples with zero
measured timing/conflict violations, including overlapping histories, in
98.06 seconds. These are mechanics samples, not independent safety trials.

The separate scientific runner smoke is
`results/sumo_future_panel/smoke_20261023`: one distinct source, five future
pairs and ten twenty-second branches, completed in 51.77 seconds. Its raw
verifier reconstructs source/arrival partitions, requested action pairing,
signal rules, stopped-wait integrals, endpoint waiting, fixed choices and
report summaries. It verifies 640 source ticks and 2,000 branch ticks without
rerunning SUMO. No full source/future configuration was simulated during
that mechanics stage; the full panel subsequently completed separately.

The smoke cannot pass the full scientific panel. Its two check futures and
retained baseline choices are not used to choose rates, gates, horizons or
thresholds. Six-decimal gain rounding and 1e-9 verification tolerance prevent
Python-version floating accumulation differences from becoming apparent
action-threshold changes. Counts/partitions remain strict.

## Fixed scientific panel

[Protocol](../protocols/SUMO_FUTURE_PANEL_20261023.md): six distinct sources,
three fixed demand families, seventeen futures per source and two actions,
giving **204 forty-second branches**. One future supplies a single-future
hindsight choice; eight supply the mean-eight choice; eight separate futures
check both choices. All source gates/schedules are frozen before branches,
and all selector choices before check outcomes. No D3QN weights are used.

Collection has a **30-minute cap**. The smoke suggests approximately 20–30
minutes on this machine, but completion is not guaranteed. Partial/failing
data remain preserved and cannot be called a completed replication. The result
is reported regardless of whether it shows stable labels, unstable labels,
beneficial averaging or harmful averaging. There is no favorable-result gate
or automatic training/promotion.

## User-run commands

From the repository root, the already installed isolated environment is ready:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/flowsync-sumo-20261023/bin/python \
  -m research.pilots.run_sumo_future_panel \
  --output results/sumo_future_panel/full_20261023
```

After successful completion, verify the saved raw traces without new traffic:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  -m research.audits.verify_sumo_future_panel \
  results/sumo_future_panel/full_20261023
```

The output directory must be new. Do not overwrite or delete partial evidence.
If the temporary environment is absent on a later machine/session, create a
fresh isolated Python 3.11 environment and install `research/requirements-sumo.txt`;
do not install these packages over the frozen research environment.

## Paper work completed in parallel

The [unified manuscript](../papers/PAPER_DRAFT_EMPIRICAL_20261023.md) has an
artifact-backed numerical ledger and two new PNG/PDF/SVG diagnostic figures
under `results/paper_evidence/empirical_audit_20261023_v2/`. The auditor verifies
eight panels, archived sources, raw summaries, saved spatial network scores,
six model refits and excluded-probe predictions. It starts no traffic rollout.
The final ledger contains 97 recomputed quantities, including wrapper-specific
fallback activity and shield counts. Twenty targeted helper/regression tests
pass in the fresh Python 3.11 environment, with one existing dependency warning.
Repository/link and diff checks pass. The full frontend/backend suite was not
rerun for these additions; no remote CI result is claimed.
This does not automatically certify every prose claim, novelty or simulator
accuracy. The [primary-source comparison](../papers/EMPIRICAL_RELATED_WORK_20261023.md)
and [draft BibTeX](../papers/empirical_references.bib) separate existing work
from the candidate empirical distinction.

Next: collect/verify the bounded independent panel, report its outcome without
selection, then finish the manuscript's methods/figures/limitations. No renewed
training campaign or rewriting of old frozen tables is justified here.

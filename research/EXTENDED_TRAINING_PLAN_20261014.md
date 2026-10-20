# Additional validation-driven training budget

> Updated 2026-10-15 IST: the user subsequently launched and completed this batch
> at `results/research_training/domain_rCXu3gDe`. All three runs completed 900
> episodes in approximately 28–29 minutes each. This supersedes the earlier
> "prepared, not started" status. The original time window below is historical;
> see [the evidence handoff](RESEARCH_STATUS.md) for results and limitations.

User authorized up to four additional hours, simulation-only. Budget starts
2026-10-14 15:17:12 UTC; stop additional training by 19:17:12 UTC. Preserve time
for verification and reporting. No claim that this budget guarantees success.

The preceding frozen 2,000-run evaluation and 210-run, 600-second sensitivity
check are completed and preserved. They did not establish superiority over
Max-Pressure. They are now previously inspected evidence, not a reusable source
of final checkpoint/threshold selection.

Next experiment addresses training-code observations, not tuning test scores:

- Existing training templates share a narrow turn mix; randomize train-only
  approach weights, turn distributions and demand, with rare capacity incidents.
- Use 300-second training episodes rather than only 120-second templates.
- Keep the audited v7 observed input and physical FSM; no simulator truth enters
  the policy. Truth supplies rewards and calibration labels only.
- Strengthen demonstration regularization from 0.1 to 0.5, retaining the standard
  TD objective. This is a learning-stability experiment, not a novelty claim.
- Fresh training seeds 101/202/303, up to 900 episodes each, 200 demonstration
  episodes, 2,000 imitation updates, 500 TD warmup updates, learning rate 1e-4,
  target update every 200 optimizer updates.
- Validation seeds 21001–21005 on all three validation templates, both clean and
  fixed mixed faults. Minimum mean validation delay selects checkpoints; include
  warm-start candidates and report if subsequent RL does not improve them.
- Per-run soft time limit 10,200 seconds, below the overall budget. Do not start
  another large batch merely because a selected test result is unfavorable.
  The limit now covers initialization, demonstrations, imitation, TD warmup,
  online training and validation. Checks are cooperative: an in-flight validation
  simulation or optimizer step, plus checkpoint saving, can exceed the deadline.
  Partial validation has no selection score; the last fully validated incumbent
  is retained. If initial validation never completes, there is no selected model.
  An interrupted checkpoint and stage/counters are retained in the run summary.
- Record each executed randomized scenario, seed, fault, Q diagnostics and all
  candidates; never overwrite earlier runs or pick only the favorable training
  seed for reporting.

Further decisions use validation data only. A subsequent confirmatory evaluation
requires fresh frozen traffic seeds (61001 onward), and must disclose that the
existing scenario families have already been inspected. New scenario generation
and matched-recipe ablations, if undertaken, must be specified before inspecting
their evaluation outcomes.

Scientific targets: reproducible improvement over strong classical baselines,
honest uncertainty intervals, and documented failure conditions. Universal
outperformance and publication acceptance cannot be guaranteed by configuration
changes or training time.

# FlowSync RL Audit and Recovery Guide

Date: 2026-09-28

## Bottom line

The 1,000–1,800 episode checkpoints were not failing because the network was too small or because more episodes were needed. The training tuples, reward, demand calibration, checkpoint selection, and evaluation harness were inconsistent. More training repeated corrupted supervision.

The corrected pipeline produced a useful smoke result after demonstration pretraining, but FlowSync is still a research simulator. It is not ready to actuate a public signal.

The first corrected 100-episode run (training seed 11) was evaluated on five held-out balanced-demand seeds. Its validation-selected checkpoint reduced queue-area by 14.6% versus fixed and 2.5% versus greedy, with mean delay 10.25 s versus 13.25 s and 10.63 s respectively. See `server/benchmarks/rl_v6_smoke_seed11.json`. This is a pipeline validation, not a general performance claim.

## Actual architecture

1. `PoissonSpawner` generates total junction demand and distributes it across 12 movements.
2. `Intersection` advances 0.1-second vehicle physics and mandatory green/yellow/all-red signal states.
3. `TrafficEnv` builds the 28-D observation and aggregates micro-ticks into variable-duration control decisions.
4. `DQNAgent` uses masked dueling Double DQN, PER, and DQfD demonstration margin loss.
5. `Trainer` applies curriculum demand, performs one update per decision, evaluates held-out seeds, and saves `checkpoint_0.pt` as the validation winner.
6. `DeterministicEvaluator` compares AI, fixed, greedy, and VAT on paired offered demand.
7. The WebSocket layer drives the UI. The camera pipeline detects/tracks traffic, but a field deployment still needs calibrated approach/movement inference and a certified hardware safety layer.

## Confirmed root causes

| Severity | Defect | Consequence |
| --- | --- | --- |
| Critical | An episode was 500 ticks = 50 s; a fixed four-phase cycle is about 52 s. | The agent rarely observed a complete cycle or long-term consequences. |
| Critical | A replay tuple stored a one-tick outcome every 10 ticks and called it semi-MDP. | The selected action was not causally paired with the reward/next decision state. |
| Critical | `executed_action` was the request, even when minimum green rejected it. | Q-learning updated the wrong action. |
| Critical | Reward used change in wait attached only to vehicles still present. | Removing an old vehicle manufactured a positive reward from disappearing historical wait. |
| Critical | `lambda` was applied once per approach. | Configured demand was 4× higher than documented and often above intersection capacity. |
| Critical | Full lanes silently dropped new vehicles. | Poor policies reduced their own measured demand and could look artificially better. |
| Critical | `reset(seed=...)` never seeded the spawner. | The deterministic/CRN evaluator compared different arrival traces. |
| Critical | The evaluator requested 120/300 s but stopped at the 50 s environment limit. | Reported benchmark durations were false. |
| High | Current-state action masks were reused as next-state masks; production used different masks and watchdog thresholds. | Bellman targets and deployed action choice disagreed. |
| High | Greedy replay seeding had no imitation objective. | Unseen actions remained overestimated; random exploration immediately discarded the teacher benefit. |
| High | “Best” meant lowest stochastic training-episode delay and was usually not saved immediately. | Model selection overfit noise; latest was auto-loaded instead of held-out best. |
| High | Resume swallowed checkpoint-load failure, used an empty replay buffer, and resumed near epsilon 0.05. | A missing checkpoint could silently train random weights under a misleading episode number. |
| High | Real-world state builder emitted 20 features while the DQN expected 28. | Inference silently padded forecast features with zeros. |
| High | EWMA constants labeled 5/10/20 seconds were actually about 0.5/1/2 seconds at 10 Hz. | “Forecast” features were noisy recent-arrival filters. |
| Medium | Delay metrics only examined vehicles still queued. | A controller could change the measured population by serving selected vehicles. |
| Medium | Starvation was tracked by compass direction, not controllable phase. | A left phase could reset a through-movement timer without serving it. |
| Medium | City queue normalization differed from single-intersection training. | Shared-policy city inference saw an out-of-distribution state scale. |

## Implemented corrections

- Five-minute episodes (`3000 × 0.1 s`).
- Decision-level transitions: a hold spans 2 s; a switch includes clearance and new minimum green.
- Variable-duration bootstrap discount: `gamma ** (duration / decision_dt)`.
- Incremental incurred-delay reward, small pressure-level cost, throughput credit, and one-time switch cost.
- Separate current and next action masks in replay/Double-DQN targets.
- DQfD large-margin loss plus 500 pretraining updates on greedy demonstrations.
- Total-rate lambda semantics and upstream demand backlog instead of deletion.
- Seed propagation to the spawner and true requested-duration evaluation.
- Completed + active + upstream wait in delay metrics; offered arrivals and service rate in benchmark output.
- Phase-level starvation and consistent 28-D state construction.
- Held-out five-seed checkpoint selection by queue-area.
- Resume failures are fatal; resumed training rebuilds replay demonstrations and reopens exploration.
- Fresh training actually resets weights, optimizer, replay, and counters.

## Reproducible training

Use the pinned Python 3.11 environment. From `server/`:

```bash
../.venv/bin/python scripts/train_rl_offline.py \
  --episodes 1000 \
  --seed 20260928 \
  --output models/offline_rl_v6
```

Important artifacts:

- `checkpoint_best.pt` / `checkpoint_0.pt`: identical copies of the lowest held-out queue-area winner; `checkpoint_0.pt` is the server-loadable alias.
- `checkpoint_<episode>.pt`: validation milestones.
- `training_history.json`: reward, loss, demand, delay, throughput, Q diagnostics, and validations.
- `summary.json`: winning episode and run metadata.

Do not compare the new model with old dashboard aggregates. State, reward, demand, and metric semantics changed; generate a new benchmark population.

## Acceptance protocol

A candidate is promotable only if all conditions hold:

1. At least 10 held-out seeds per demand/profile; report paired confidence intervals, not one run.
2. Demand levels include undersaturated, near-capacity, and oversaturated cases.
3. Profiles include balanced, NS/EW asymmetric, heavy-left, burst/platoon, detector noise, and incident/blockage cases.
4. Primary metric is queue-area or total delay. Also report p50/p95 delay, throughput, offered arrivals, service rate, max queue/backlog, phase changes, starvation, and watchdog overrides.
5. AI must beat fixed and greedy on aggregate without losing badly on any safety-critical slice. Compare against VAT as the minimum realistic field baseline.
6. Run at least five independent training seeds. Report mean and spread across training seeds as well as traffic seeds.
7. Freeze the checkpoint hash before final evaluation. Never select on test seeds.
8. Run 24+ simulated hours of soak/stress tests with zero conflicting greens and zero unbounded starvation.

## Sim-to-real work still required

Before a closed-course pilot, add or validate:

- camera calibration, lane/movement polygons, occlusion testing, night/rain/glare cases, and detector drift alarms;
- approach-specific arrival forecasts (the current eight forecast features summarize junction-wide demand);
- downstream occupancy from actual downstream cameras/sensors; single-intersection outgoing pressure is otherwise only a weak proxy;
- domain randomization for count noise, missed detections, latency, frame loss, turning uncertainty, saturation flow, and driver behavior;
- a shadow-mode phase where the policy recommends but cannot actuate;
- controller-in-the-loop testing with NEMA/ATC timing, pedestrian phases, emergency preemption, coordination plans, and communication failure;
- an independent, deterministic safety supervisor that owns min-green, yellow, all-red, conflict matrix, max-green, and fallback timing;
- manual override, health monitoring, rollback, audit logs, and road-authority approval.

The safe rollout sequence is simulation → replay/digital twin → shadow mode → closed course → supervised limited pilot. Public-road control is not the next step after a good simulation benchmark.

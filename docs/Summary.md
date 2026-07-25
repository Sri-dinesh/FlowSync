# FlowSync — Comprehensive Project Summary

> **AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning**

---

## 1. Project Overview

### What Is FlowSync?

FlowSync is a full-stack, real-time traffic simulation system that demonstrates how **Dueling Double DQN with Prioritized Experience Replay (PER)** can optimize traffic signal control at both **single 4-way intersections** and **2×2 multi-intersection city grids**. It serves as a **proof-of-concept Digital Twin** for smart-city infrastructure modernization, replacing traditional fixed-timer traffic signals with an autonomous, learning AI agent — plus **Manual (MNL) control mode** for human-in-the-loop operation, and a new **Greedy mode** for rule-based benchmarking. The system is designed as a research platform to study **pressure-based reward functions**, **starvation-aware constraint handling**, **multi-intersection coordination**, and **real-time RL inference** in traffic domains.

**Mission:** Show that Reinforcement Learning can significantly outperform static traffic systems, reducing urban congestion, wait times, and vehicle emissions.

**Core Research Contributions:**
- **Dueling Double DQN** with separate value (V) and advantage (A) streams for better state-value estimation under high-density traffic
- **Prioritized Experience Replay** with SumTree data structure, priority annealing (α=0.6), and importance-sampling bias correction (β: 0.4→1.0)
- **Max-Pressure Formulation** (PressLight/MPLight-style): pressure computed per **movement** (12 total movements mapped to destination directions) with phase-level aggregation via `_get_phase_pressure()` — Phase 0 (NS straight), Phase 1 (EW straight), Phase 2 (NS left), Phase 3 (EW left)
- **20-dimensional pressure-based observation space** encoding 12 lane-level movement queues, phase one-hot, signal context, and starvation metrics
- **Multi-component pressure reward** combining pressure differential (PressLight-style), throughput bonus, switch penalty (evaluated against **previous** phase's pressure, not current), starvation penalty (-2.0 per starved direction), max-green violation penalty (-1.0), and balance bonus (computed over **phase-level** pressures) — all with hard constraint enforcement
- **Two-agent decoupling**: separate inference agent (live simulation) and training agent (background training) with periodic weight synchronization
- **Starvation-aware signal control**: per-direction wait timers trigger automatic phase overrides at 45s threshold, independent of RL policy; **starvation bleed fix**: timers also reset for directions in the pending/next phase
- **Destination-aware outgoing counts**: `get_outgoing_counts()` maps each lane to its actual destination direction (e.g., south_straight→north, west_left→north) for accurate pressure calculation
- **Multi-Intersection City Grid**: 2×2 grid of 4 coordinated intersections with vehicle routing between intersections, shared-policy AI control, and automated benchmark comparison (Fixed vs Greedy vs AI)
- **Greedy Rule-Based Controller**: deterministic highest-queue phase selector for baseline comparison against learned policies
- **Async Environment Stepping**: offloaded to thread pool via `asyncio.to_thread()` to prevent event-loop blocking during training

**Problem It Solves:**
- Traditional fixed-timer traffic signals waste time by ignoring real-time demand
- Urban congestion costs billions annually in lost productivity and fuel
- Municipalities lack low-risk tools to evaluate AI traffic control before real-world deployment
- FlowSync provides a sandbox to train, test, and compare AI vs. traditional vs. manual control
- Research platform for studying pressure-based RL, PER, and constraint-aware traffic signal control

### Target Audience

- **Researchers & Students** studying Reinforcement Learning (RL) applications in intelligent transportation
- **Smart-city engineers** evaluating AI-based traffic control
- **Hackathon judges & technical interviewers** evaluating full-stack AI demos
- **Developers** interested in full-stack AI + 3D visualization architectures

### Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Frontend** | Next.js | 16.2.6 (App Router) | React framework |
| | React | 19.2.4 | UI library |
| | TypeScript | 5.x | Type safety |
| | Three.js / React Three Fiber | 0.184.0 / 9.6.1 | 3D rendering engine |
| | Tailwind CSS | 4.x | Utility-first CSS |
| | shadcn/ui | 4.8.0 | UI component library (Vercel theme) |
| | Zustand | 5.0.13 | Client-side global state |
| | TanStack React Query | 5.100.14 | Server-state / data fetching |
| | Recharts | 3.8.0 | Training metric charts |
| | Framer Motion | 12.40.0 | Animations |
| | Radix UI | 1.4.3 | Accessible UI primitives |
| | Prisma | 6.19.3 | ORM (server-side reads) |
| | pnpm | — | Package manager |
| **Backend** | Python | 3.11.9 | Runtime |
| | FastAPI | 0.115.0 | Web framework |
| | Uvicorn | 0.30.0 | ASGI server |
| | PyTorch | 2.3.1 (CPU) | Deep learning / neural networks |
| | Gymnasium | 0.29.1 | RL environment interface |
| | NumPy | 1.26.4 | Numerical computation |
| | Pydantic v2 | 2.10.6 | Data validation |
| | Supabase Python client | 2.4.6 | Database + storage |
| | websockets | 12.0 | WebSocket support |
| | ujson | 5.10.0 | Fast JSON serialization |
| **Database** | Supabase PostgreSQL | — | Primary data store |
| **Storage** | Supabase Storage | — | Model checkpoint bucket (`model-checkpoints`) |
| **Infra** | Docker | — | Backend containerization |
| | Render | — | Backend hosting |
| | Vercel | — | Frontend hosting |

### Current Status

**Active Development / MVP — Research Platform.** The project is fully functional with a landing page, **two simulation dashboards** (single-intersection `/simulation` and multi-intersection `/city`), live training, manual control, **Dueling Double DQN with PER**, **starvation-aware constraint handling**, **pressure-based observations**, multi-intersection vehicle routing, automated benchmark comparison, and data persistence. Designed as a **research tool** for studying pressure-based RL in traffic signal control.

**Recent Major Milestone (July 2026):** Implemented 2×2 multi-intersection city grid with shared-policy AI, greedy rule-based baseline, automated comparison benchmark, and new `/city` route with dedicated 3D visualization.

---

## 1.1 Current Project Status — Detailed Breakdown

### What Is Working (✅ Verified Functional)

| Area | Status | Details |
|---|---|---|
| **Frontend Build** | ✅ Working | `pnpm dev` compiles, Next.js 16 App Router loads, TypeScript strict mode passes |
| **Backend Server** | ✅ Working | `uvicorn app.main:app --reload` starts on :8000, lifespan initializes 2 envs + 2 agents + Trainer + CityNetwork |
| **WebSocket Simulation** | ✅ Working | `/ws/simulation` connects, 10 Hz frames broadcast, 3D scene renders vehicles, AI mode computes reward via `training_env.compute_reward()` |
| **WebSocket City** | ✅ Working | `/ws/city` connects, 10 Hz frames for 2×2 grid, 4 intersections + road vehicles, Fixed/Greedy/AI modes, comparison benchmark |
| **WebSocket Training** | ✅ Working | `/ws/training` connects, per-episode metrics stream, checkpoint notifications, `is_training` flag on last episode |
| **Fixed-Timer Control** | ✅ Working | 4-phase cycle with smart queue-based switching, yellow (2s) → red (3s) → green (min 4s, default 8s), early switch if current phase empty, **hard 40s green cap** |
| **AI (Dueling Double DQN) Control** | ✅ Working | Dueling architecture (V + A streams), PER buffer (SumTree, α=0.6, β annealing), 20-dim pressure obs, `select_action(ε=0)` for inference |
| **Manual (MNL) Control** | ✅ Working | 4 phase buttons, holds green indefinitely, phase changes go through yellow→red→green clearance |
| **Greedy Baseline (City)** | ✅ Working | Rule-based max-queue phase selector per intersection, respects min-green guard, shared across 4 intersections |
| **Yield-on-Left Logic** | ✅ Working | Left-turners at stop line during phases 0/1 yield to oncoming straight/right traffic |
| **Max-Pressure Reward Formulation** | ✅ Working | Per-movement pressure with destination mapping (12 movements, each mapped to downstream direction); `_get_phase_pressure()` aggregates to phase level; switch penalty evaluates **previous phase** pressure |
| **Starvation Bleed Fix** | ✅ Working | `starvation_timer` resets for BOTH current green AND pending phase directions — no false accumulation during yellow-red transitions |
| **Destination-Aware Outgoing Counts** | ✅ Working | `get_outgoing_counts()` uses proper dest mapping (south_straight→north, west_left→north, etc.) for accurate pressure calculation |
| **Starvation Overrides** | ✅ Working | Per-direction `starvation_timer` (45s threshold), triggers `set_phase()` to serve starved direction, -2.0 penalty in reward |
| **Max Green Enforcement** | ✅ Working | Hard 40s cap on any green phase, forces `_get_best_alternative_phase()` (highest pressure via `_get_phase_pressure()`) |
| **Right-Turn Always-Allowed** | ✅ Working | Right turns excluded from pressure calculation, bypass signal checks entirely, `is_right_turn` property on Vehicle |
| **Two-Agent Decoupling** | ✅ Working | `sim_agent` (inference) + `training_agent` (training) are independent `DQNAgent` instances; weights synced at checkpoints |
| **3-Lane Roads + Visuals** | ✅ Working | 40×6 roads, stop bars at ±3.1, zebra crossings, lane offsets (0.5/1.5/2.5), direction labels |
| **Traffic Light Arrows + CCTV** | ✅ Working | ← for left phases, ↑→ for through/right; CCTV camera with blinking status LED on each pole |
| **Vehicle Paths** | ✅ Working | CurvePath (LineCurve3 + QuadraticBezierCurve3) with piecewise arclength mapping |
| **Vehicle Interpolation** | ✅ Working | Smooth 60 fps between 10 Hz WS updates, wheel rotation, emergency siren lights |
| **Day/Night 3D Toggle** | ✅ Working | State-driven lighting: emissive sun (intensity 8) + bright ambient (day) vs moody directional (night) |
| **MeshPhysicalMaterial Environment** | ✅ Working | Ground plane, skyscrapers with clearcoat 1.0 + metalness 0.9 + neon corner stripes emissive 3.5 |
| **City Grid Environment** | ✅ Working | 2×2 grid (A/B/C/D), connecting roads, 8 external entry points, inter-intersection vehicle routing, world-space coordinates |
| **Side-by-Side Layout** | ✅ Working | Canvas left (flex-1), controls sidebar right (420px, scrollable) |
| **Live Training Dashboard** | ✅ Working | Reward/Wait/Epsilon/Loss sparklines, trend arrows, phase description, ETA, ep/min |
| **Model Checkpointing** | ✅ Working | Every 50 eps: saves to Supabase Storage + local disk, metadata upsert to `rl_models` |
| **Model Loading** | ✅ Working | Dropdown fetches `/training/models`, loads state dict into both sim_agent + training_agent |
| **Emergency Preemption** | ✅ Working | 4 directional buttons, spawns ambulance, forces priority phase, clears on exit |
| **Performance Comparison** | ✅ Working | Compare tab aggregates Fixed/AI/Manual wait time + throughput, improvement %, 3-bar chart (#475569/#38bdf8/#f59e0b) |
| **City Comparison Benchmark** | ✅ Working | Automated 3-mode (Fixed/Greedy/AI) sequential run with 30s per mode, live progress, results chart with improvement % |
| **Episode History** | ✅ Working | Paginated table (10/page), auto-refresh 10s during training, best episode highlighted |
| **Real-Time Metrics** | ✅ Working | MetricsPanel (2×2 animated cards), LiveSnapshot (draggable framer-motion overlay), QValuePanel (AI reasoning) |
| **Supabase Persistence** | ✅ Working | Simulations, Episodes, TrafficLogs, SignalStates, PerformanceMetrics, RLModels |
| **Keep-Alive Ping** | ✅ Working | Frontend pings `/api/keep-alive` → FastAPI `/health` on mount |
| **Docker Backend** | ✅ Working | `docker-compose up` builds CPU-only PyTorch image, runs on :8000 |
| **Tests** | ✅ Passing | `pytest` runs 27 tests (api, rl, simulation) with mocked Supabase |

### Partially Working / Known Quirks (⚠️)

| Area | Status | Details |
|---|---|---|
| **Queue Length Accuracy** | ⚠️ Minor | `get_queue_lengths()` counts `state != "passed"` — vehicles at stop line with `can_move=false` are counted, but those actively in intersection are not |
| **All-Red Clearance** | ⚠️ Tunable | Fixed at 3.0s (`red_duration`); may be too short for heavy traffic — vehicles can still be in intersection when cross-traffic gets green |
| **Manual Mode Phase Display** | ⚠️ Minor | Traffic light shows correct color but doesn't visually distinguish "manual hold" vs normal green |
| **PER Beta Annealing Granularity** | ⚠️ Minor | Beta is annealed linearly over total episodes; on early-stop, beta may not reach 1.0 |
| **Switch Penalty Edge Case** | ⚠️ Minor | Switch penalty checks `prev_phase` pressure > 0.3 — only penalizes if combined pressure of both left-turn lanes in the abandoned phase exceeds threshold; single-lane pressure just below 0.3 may allow premature switching without penalty |
| **WS Reconnection Storm** | ⚠️ Rare | Exponential backoff (max 5) works, but rapid reconnects can occur if backend restarts mid-session |
| **Prisma Migrations** | ⚠️ Manual | No CI migration step — `prisma db push` required after schema changes |
| **Hardcoded Render URL** | ⚠️ Config | `flowsync-gelt.onrender.com` removed from `utils.ts`/`next.config.ts` but may persist in docs |
| **City Vehicle Routing Latency** | ⚠️ Minor | Vehicles waiting at full destination lane queue are held at road end; visual "bunching" at city boundaries during high throughput |
| **Greedy Policy Myopia** | ⚠️ Design | Greedy mode maximizes local queue per intersection; no coordination for green-wave or downstream pressure |

### Not Implemented / Missing (❌)

| Area | Status | Details |
|---|---|---|
| **Authentication/Authorization** | ❌ None | No user accounts, no WS auth, no API keys — single-user demo only |
| **Rate Limiting** | ❌ None | No protection on REST or WS endpoints |
| **CI/CD Pipeline** | ❌ None | No GitHub Actions, no automated test/lint/deploy |
| **GPU Training** | ❌ Blocked | Render free tier CPU-only; no CUDA in Dockerfile |
| **GraphQL / Webhooks** | ❌ Not planned | REST + WS covers all current needs |
| **Data Retention Policy** | ❌ None | Data persists indefinitely on Supabase free tier |
| **Automated Security Scanning** | ❌ None | No Dependabot, Snyk, or SAST in CI |
| **WebSocket Message Schema Validation** | ❌ None | Commands validated by if-else chains only |
| **Multi-Agent Coordination** | ❌ Not started | Each intersection uses shared single-intersection policy; no explicit communication or joint reward |
| **Pedestrian / Cyclist Models** | ❌ Not planned | Vehicle-only simulation |
| **Weather / Incident Simulation** | ❌ Not planned | Static traffic demand only |

### Deployment Status

| Environment | Status | URL | Notes |
|---|---|---|---|
| **Frontend (Vercel)** | ✅ Deployed | `https://flowsyncc.vercel.app` | Auto-deploys on push to `main` |
| **Backend (Render)** | ✅ Deployed | `https://flowsync-gelt.onrender.com` | Auto-deploys on push to `main` (Docker); spins down after 15min idle |
| **Database (Supabase)** | ✅ Active | Project: `flowsync` | Free tier (500 MB DB, 1 GB Storage); `model-checkpoints` bucket exists |

### Test Coverage

| Suite | Tests | Coverage |
|---|---|---|
| `tests/api/test_main.py` | 2 | Root + health endpoints |
| `tests/api/test_simulation.py` | 5 | Start/stop/reset/set_mode/status |
| `tests/api/test_training.py` | 4 | Start/stop/status/models |
| `tests/rl/test_replay_buffer.py` | 2 | Push + sample |
| `tests/rl/test_dqn_agent.py` | 4 | Init, random/greedy action, train_step |
| `tests/simulation/test_vehicle.py` | 4 | Init, move, wait, pass |
| `tests/simulation/test_traffic_signal.py` | 6 | Phase transitions, yellow/red/green, green permission |
| **Total** | **27** | Core logic paths; no integration/E2E tests |

### Recent Commits Impact (Last 30)

| Commit | Date | Impact |
|---|---|---|
| `7b73d8b` | 2026-07-21 | **Project Documentation**: Added `docs/Project-Objectives.md` with comprehensive project objectives and research goals |
| `79df942` | 2026-07-21 | **City Grid Visuals**: Smooth lateral lane transitions, fixed visual teleportation during lane changes, improved vehicle interpolation on road segments |
| `e9cd8e7` | 2026-07-21 | **Backend-Frontend Routing Sync**: Synced road vehicle offsets, pass routing intent (`prev_turn`/`next_turn`) to frontend for correct lane visualization |
| `7d4a34a` | 2026-07-21 | **City Vehicle Lifecycle**: Fixed vehicle routing and injection in multi-intersection grid; correct spawning at 8 entry points, proper inter-intersection transfers |
| `15f9e4d` | 2026-07-21 | **City Route & Navigation**: Added `/city` page route, updated global header navigation with City Grid Experiment link |
| `f643a1b` | 2026-07-21 | **City 3D Components**: Built CityCanvas, CityGrid, CityRoads, CityVehicle, CityControls, CityMetricsPanel, CityComparisonPanel with full visual fidelity |
| `71fb774` | 2026-07-21 | **City Types & State**: Added `types/city.ts`, `useCitySocket.ts` hook, updated Zustand store for city simulation state |
| `b3fe488` | 2026-07-21 | **City WebSocket Controller**: `/ws/city` handler with Fixed/Greedy/AI modes, automated comparison benchmark (Fixed→Greedy→AI, 30s each), shared-policy DQN inference |
| `562d85d` | 2026-07-21 | **City Network Models**: `CityNetwork` (2×2 grid, 4 Intersections, ROAD_CONNECTIONS, RoadVehicle routing), `CitySpawner` (8 external entry points, Poisson spawn), schemas, frame builder |
| `74c6415` | 2026-07-19 | **Greedy Mode + Q-Value Tracking**: Added greedy rule-based controller (max-queue phase selector) for `/simulation` and `/city`; `QValuePanel` shows per-phase Q-values, confidence %, explore/exploit badge |
| `f93788c` | 2026-07-19 | **UI Polish**: Training warmup indicator, resolved TypeScript/ESLint warnings |
| `22768d4` | 2026-07-19 | **RL Hyperparam Tuning**: `MIN_REPLAY_SIZE` 2000→500 (faster warmup), `EPSILON_DECAY` 0.998→0.994 (reaches 0.05 by ~550 eps), added training speed & buffer-ready metrics to WS |
| `5c8dd03` | 2026-07-19 | **Fixed Signal Upgrade**: Queue-based phase selection with `_pick_highest_queue_phase()`, hard 40s green cap (`MAX_GREEN_TIME`), left turns restricted to dedicated left phases (2,3) |
| `41066da` | 2026-07-19 | **RL Phase Pressure Fix**: `_compute_movement_pressures()` now takes explicit `intersection` arg; `_get_phase_pressure()` corrected (Phase 0/1 = straight only, Phase 2/3 = left only); `phase_changed` uses pre-tick action vs current phase; switch penalty iterates movement keys (`d_turn`) |
| `2f00cc1` | 2026-07-18 | **Lint & Build Fixes**: Resolved all TypeScript/ESLint warnings, clean build |
| `f3bcd9f` | 2026-07-16 | **Algorithm Fixes** (code-level deep-dive): **(a) Per-movement max-pressure formulation** — `_compute_movement_pressures()` changed from direction-level (4 entries summing straight+left) to movement-level (12 entries with `dest_map` lookup), enabling destination-aware pressure (e.g. `north_straight→south`, `north_left→east`). **(b) Switch penalty evaluated against previous phase** — `step()` now captures `prev_phase` pre-tick and passes it to `compute_reward()`; penalty checks `prev_pressures[PHASE_GREEN_LANES[prev_phase]]` instead of post-switch `curr_pressures[PHASE_GREEN_LANES[current_phase]]`. **(c) Starvation bleed fix** — `traffic_signal.tick()` now checks BOTH `green_dirs` (current) AND `pending_dirs` (pending_phase) before resetting starvation timers; prevents false accumulation when a direction has a pending green but is still in yellow→red→green transition. **(d) Destination-aware outgoing counts** — `get_outgoing_counts()` replaced naive `lane_key.split("_")[0]` with full `dest_mapping` dict (12 entries mapping each lane key to its physical destination). **(e) Phase-level balance bonus** — balance bonus `imbalance` now computed over 4 phase-level pressures (via `_get_phase_pressure()`) instead of 12 raw movement pressures. **(f) `_get_best_alternative_phase()`** — now uses `_get_phase_pressure()` instead of direction-level `PHASE_GREEN_DIRS_MAP`. **(g) New helper** `_get_phase_pressure(pressures, phase)` aggregates 12 movement pressures into 4 phase groups. |

---

## 1.2 Readiness Assessment

| Criterion | Rating | Notes |
|---|---|---|
| **Demo Ready** | ✅ **Yes** | All 3 control modes work, 3D visuals polished, training visible, comparison works |
| **Hackathon Submission** | ✅ **Yes** | Impressive full-stack AI + 3D, live training, manual override for judges to try |
| **Research/Thesis Use** | ✅ **Yes** | Dueling DQN + PER + pressure reward properly implemented, reproducible, metrics logged, checkpoints loadable |
| **Production Deployment** | ❌ **No** | No auth, no rate limits, free-tier infra, single-process, no CI/CD |
| **Multi-User SaaS** | ❌ **No** | Shared `Intersection` instance, no session isolation, no user accounts |
| **CI/CD Ready** | ❌ **No** | No GitHub Actions, manual `prisma db push`, no lint/test gates |

---

## 1.3 Immediate Next Steps (Priority Order)

1. **Multi-Agent RL** — Extend to multi-intersection coordination for "Green Wave" synchronization (research-grade)
2. **Add Prisma Migration to CI** — Write GitHub Action: `prisma migrate deploy` + `pytest` on PR
3. **WS Message Validation** — Add Pydantic/Zod schemas for all WS commands (client + server)
4. **Rate Limiting** — Add `slowapi` or similar to FastAPI; per-IP WS connection limits
5. **All-Red Duration Config** — Expose `red_duration` as env var / UI slider for tuning
6. **E2E Tests** — Add Playwright/Cypress for critical user journeys (start → train → load → compare)
7. **GPU Training** — Enable CUDA in Dockerfile for accelerated training (blocked by Render free tier)

---

## 1.4 Research Methodology

### 1.4.1 Problem Formalization (Markov Decision Process)

The traffic signal control problem is formalized as a discrete-time MDP with the following components:

**State Space (S):** 20-dimensional continuous vector normalized to [0,1]:
- 12 movement-level queue lengths (normalized by MAX_CAP=10.0): `north_straight`, `north_left`, `north_right`, `south_straight`, `south_left`, `south_right`, `east_straight`, `east_left`, `east_right`, `west_straight`, `west_left`, `west_right`
- 4 one-hot phase encoding: exactly one dimension is 1.0 for the current phase (0-3)
- 2 signal context dimensions: `time_in_phase / MAX_GREEN_TIME` (normalized, capped at 1.0), `is_transitioning` (1.0 if yellow/red, 0.0 if green)
- 1 pressure context: `min(total_movement_pressure / 20.0, 1.0)` — aggregate congestion signal
- 1 starvation context: `min(max(starvation_timer) / STARVATION_THRESHOLD, 1.0)` — worst-case direction wait

**Action Space (A):** Discrete(4) — one of four signal phases:
| Action | Phase ID | Description |
|--------|----------|-------------|
| 0 | NS_GREEN | North+South straight, left, right |
| 1 | EW_GREEN | East+West straight, left, right |
| 2 | NS_LEFT | North+South left-turn only |
| 3 | EW_LEFT | East+West left-turn only |

**Transition Function (T):** Deterministic state transitions driven by:
1. Agent's phase selection (filtered through hard constraints: max-green override, starvation override, yellow-red clearance)
2. Poisson vehicle spawn process (λ=0.8 training, λ=0.5 evaluation) — 50% straight, 25% left, 25% right
3. Vehicle physics: constant speed (DEFAULT_SPEED=0.12), stop-line enforcement, yield-on-left logic, collision avoidance (MIN_DIST=0.08), intersection reservation by direction group

**Reward Function (R):** Multi-component pressure-based reward:
`R = 1.5·Δpressure + 0.2·throughput - 0.3·switch_penalty - 2.0·|starved| - 1.0·max_green_violation + 0.2·balance_bonus`
- Primary signal: pressure reduction (PressLight-style, incoming-outgoing per movement)
- Corrective signals: starvation penalty (hard constraint), max-green penalty, switch penalty
- Shaping bonus: throughput (conservative 0.2), phase-level balance (0.2 when imbalance < 0.2)

**Discount Factor (γ):** 0.97 — moderate discount for near-term congestion relief

### 1.4.2 Algorithm Selection Rationale

| Algorithm Component | Selection | Rationale |
|---------------------|-----------|-----------|
| **Base algorithm** | Deep Q-Network (DQN) | Discrete action space (4 phases), value-based methods converge stably with experience replay |
| **Overestimation reduction** | Double DQN | Standard DQN overestimates Q-values by up to 100% in some Atari domains; Double DQN decouples action selection (online net) from evaluation (target net), reducing overestimation bias for more stable phase selection |
| **State-value separation** | Dueling DQN | In high-density traffic, many actions yield similar Q-values; separate V(s) and A(s,a) streams let the agent learn which states are congested regardless of action, improving policy evaluation under heavy traffic |
| **Sampling efficiency** | Prioritized Experience Replay (PER) | Critical events (starvation, max-green violations, emergency preemption) are rare; PER prioritizes high-TD-error transitions via SumTree (α=0.6), learning from important events up to O(log n) times more frequently |
| **Gradient stability** | Smooth L1 Loss (Huber) | Less sensitive to outliers than MSE; prevents exploding gradients from high-TD-error transitions sampled early in training |
| **Importance sampling** | PER β-annealing (0.4→1.0) | Corrects for priority bias; β starts at 0.4 for stability (allows aggressive priority sampling early), anneals linearly to 1.0 over training (fully corrected by end) |
| **Gradient clipping** | max_norm=10.0 | Prevents destabilizing gradient updates from rare high-error transitions |

**Why not other approaches:**
- **Policy gradient (PPO/A2C):** Higher variance, more sample-inefficient for this discrete-action domain; DQN variants are well-established in traffic control literature (PressLight, MPLight, FPA-DQN)
- **Model-based RL:** Requires accurate traffic flow model; simulation is already the model, making model-free more direct
- **SARSA:** On-policy; would require separate behavior policy and lose efficiency of off-policy replay buffer

### 1.4.3 Evaluation Protocol

**Training Configuration:**
- Episodes: 1,000 (default), capped at 1,000 steps per episode (100s simulated time)
- Vehicle spawn: Poisson(λ=0.8) during training, Poisson(λ=0.5) during evaluation inference
- Exploration: ε-greedy with exponential decay — ε starts at 1.0, decays by 0.998× per episode, floor at 0.05
- PER: α=0.6, β annealed from 0.4→1.0, buffer warmup of 2,000 steps before training begins
- Network updates: every 2 steps, batch size 128, target network sync every 300 steps

**Baselines:**
| Baseline | Type | Description |
|----------|------|-------------|
| Fixed-Timer | Rule-based | 4-phase cycle: GREEN 8s → YELLOW 2s → RED 3s (clearance) → next phase; smart early-switch if current queue empty, sequential fallback |
| Manual (MNL) | Human-in-loop | Operator selects phases via UI buttons; holds green indefinitely until manual override; uses same yellow→red→green clearance |

**Performance Metrics:**
| Metric | Definition | Collection |
|--------|------------|------------|
| Average Wait Time | Mean `vehicle.wait_time` across all non-passed vehicles | Computed per tick via `get_avg_wait_time()` |
| Throughput | Total vehicles with `state == "passed"` | `intersection.total_passed` accumulator |
| Max Queue Length | Max of `get_queue_lengths()` values (per direction) | Sampled every DB flush |
| Total Pressure | Sum of 12 per-movement pressure values | Computed via `_compute_movement_pressures()` |
| Starvation Events | Number of directions with timer ≥ STARVATION_THRESHOLD (45s) | `signal.get_starved_directions()` |

**Comparison Methodology:**
- Each mode (Fixed, AI, Manual) runs on the same intersection geometry with comparable spawn rates
- Performance metrics written to `performance_metrics` table on simulation stop
- Frontend Compare tab fetches aggregated metrics from `/api/metrics` with `?mode=` filter
- Improvement percentage: `(avgWait_baseline - avgWait_AI) / avgWait_baseline × 100`

### 1.4.4 Research Contributions & Findings

**Core Contributions:**
1. **Dueling Double DQN + PER for traffic control** — Combines three established RL improvements (Dueling, Double, PER) into a single architecture for 4-phase intersection control, demonstrating feasibility with CPU-only training
2. **Per-movement max-pressure formulation** — Extends PressLight's pressure concept from direction-level to movement-level (12 movements with destination mapping), enabling finer-grained congestion sensing
3. **Starvation-aware constraint handling** — Novel integration of hard starvation overrides (45s threshold) with RL reward penalties (-2.0 per starved direction), preventing the "starvation bleed" bug where pending-phase directions accumulate false wait time
4. **Two-agent decoupling** — Separate inference and training agents allow continuous simulation without training-induced latency; weight synchronization at discrete checkpoints ensures consistency
5. **Phase-level balance bonus** — Phase-level pressure aggregation (4 groups) for the balance bonus prevents single-lane spikes from incorrectly triggering equal-service rewards

**Key Findings:**
- Per-movement pressure (12-dim) provides better signal than direction-level pressure (4-dim) — the agent can distinguish straight vs turning congestion
- Switch penalty must evaluate the **abandoned** phase's pressure (pre-tick), not the **entered** phase's pressure (post-tick), to correctly penalize premature switching
- Starvation timers must account for `pending_phase` directions to avoid false accumulation during yellow→red→green transitions
- Separate inference/training agents eliminate freeze-frame issues during training updates without sacrificing policy freshness (50-episode sync interval is sufficient)

---

## 1.5 System Architecture

### 1.5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │ Three.js │  │ Zustand  │  │ TanStack │  │ Recharts Charts │ │
│  │  (R3F)   │  │  Store   │  │  Query   │  │ (Train/Compare) │ │
│  │ 3D Scene │  │ State    │  │  Cache   │  │ Metrics/History │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬────────┘ │
│       │             │             │                  │          │
│       └─────────────┼─────────────┼──────────────────┘          │
│                     │             │                             │
│              WebSocket (10Hz)     REST (/api/* → Prisma)        │
└─────────────────────┼─────────────┼─────────────────────────────┘
                      │             │
┌─────────────────────┼─────────────┼─────────────────────────────┐
│                     │             │                             │
│              /ws/simulation  /api/metrics, /api/episodes        │
│              /ws/training   /api/models, /api/simulations       │
│                     │             │                             │
│                     ▼             ▼                             │
│                    BACKEND (FastAPI / Python / PyTorch)         │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    app.state                             │   │
│  │  ┌───────────────────┐    ┌───────────────────────────┐  │   │
│  │  │ sim_intersection  │    │ training_env (TrafficEnv) │  │   │
│  │  │ (Intersection)    │    │ - separate from sim       │  │   │
│  │  │ - live simulation │    │ - used only by Trainer    │  │   │
│  │  └────────┬──────────┘    └───────────┬───────────────┘  │   │
│  │           │                            │                  │   │
│  │  ┌────────▼──────────┐    ┌───────────▼───────────────┐  │   │
│  │  │ sim_agent         │    │ training_agent            │  │   │
│  │  │ (DQNAgent)        │    │ (DQNAgent)                │  │   │
│  │  │ - inference only  │    │ - training with PER       │  │   │
│  │  │ - ε = 0 (greedy)  │    │ - ε: 1.0 → 0.05          │  │   │
│  │  │ - no replay buf   │    │ - full SumTree (100K)    │  │   │
│  │  └────────────────────┘    └───────────┬───────────────┘  │   │
│  │                                        │                  │   │
│  │                          Weight Sync (every 50 episodes)  │   │
│  │                          ◄──────────────────────────────┘ │   │
│  │                                                                │
│  │  ┌────────────────────────────────────────────────────────┐   │
│  │  │ Trainer                                                │   │
│  │  │ - orchestrates episodes                                │   │
│  │  │ - anneals PER β                                        │   │
│  │  │ - saves checkpoints                                    │   │
│  │  │ - broadcasts metrics                                   │   │
│  │  └────────────────────────────────────────────────────────┘   │
│  │                                                                │
│  │  ┌────────────┐  ┌────────────┐                               │
│  │  │ Supabase   │  │ Model      │                               │
│  │  │ Service    │  │ Service    │                               │
│  │  │ (DB writes)│  │ (checkpts) │                               │
│  │  └──────┬─────┘  └─────┬──────┘                               │
│  └─────────┼──────────────┼──────────────────────────────────────┘
│            │              │
│     supabase-py REST      │ supabase-py Storage API
└────────────┼──────────────┼────────────────────────────────────────
             │              │
             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SUPABASE PLATFORM                            │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐ │
│  │ PostgreSQL Database  │  │ Storage (model-checkpoints)      │ │
│  │ - simulations        │  │ - models/{sim_id}/checkpoint_N.pt│ │
│  │ - episodes           │  └──────────────────────────────────┘ │
│  │ - traffic_logs       │                                       │
│  │ - signal_states      │                                       │
│  │ - performance_metrics│                                       │
│  │ - rl_models          │                                       │
│  └──────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.5.2 Component Interaction Model

The system uses three independent processing pipelines:

**1. Simulation Pipeline (Real-Time, ~10 Hz):**
```
User → WebSocket (/ws/simulation) → simulation_loop()
  → Intersection.tick() [physics + vehicles + signal]
    ├── Fixed mode: no agent, automatic phase cycling
    ├── AI mode: 
    │     _build_obs_from_intersection() → 20-dim obs
    │     sim_agent.select_action(ε=0) → action
    │     training_env.compute_reward(...) → reward
    │     build_frame() → SimulationFrame JSON
    └── Manual mode: no agent, holds green indefinitely
  → manager.broadcast() → WebSocket → Frontend Three.js (60fps lerp)
  → [every 50 ticks] _SimBuffer.add() → [every 10 samples] flush to Supabase
```

**2. Training Pipeline (Background, ~100ms per episode):**
```
User → REST (/training/start) → Trainer.train()
  → Reset TrafficEnv
  → For each step (max 1000):
      training_agent.select_action(ε-greedy)
      env.step(action) [hard constraints enforced]
      PER buffer.push(state, action, reward, next_state, done)
      [every 2 steps, if buffer ≥ 2000]: PER sample → train_step
      [every 300 steps]: sync target network
  → [per episode]: save_episode(), broadcast_training_metric()
  → [every 50 episodes]: save_checkpoint(), sync sim_agent weights
```

**3. Data Pipeline (Asynchronous):**
```
Simulation metrics (sampled every 50 ticks)
  → _SimBuffer (in-memory, max 10 samples)
  → [flush trigger] asyncio.create_task(_flush_buffer)
    → supabase_service.save_traffic_logs_bulk()
    → supabase_service.save_signal_states_bulk()
  → [simulation stop] supabase_service.save_performance_metric()

Training metrics (per episode)
  → supabase_service.save_episode() (sync via asyncio.to_thread)
  
Frontend reads:
  → TanStack React Query (15s refetch) → Next.js API Route → Prisma → Supabase
```

### 1.5.3 Technology Stack & Rationale

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Python/FastAPI** | NumPy/PyTorch compatibility, async WebSocket support, rapid prototyping | GIL-bound training; CPU-only on Render free tier |
| **PyTorch CPU** | Dynamic computation graphs, extensive RL ecosystem, Kaiming init built-in | No GPU acceleration; training 10× slower than CUDA |
| **Next.js 16 App Router** | SSR for landing page, API routes for Prisma, React Server Components | Overhead for primarily client-rendered simulation |
| **Three.js / R3F** | Declarative 3D scene graph, React integration, postprocessing via EffectComposer | Performance ceiling for 100+ vehicles with bloom |
| **Zustand** | Minimal boilerplate, TypeScript-first, works with React 19 | No middleware ecosystem (compared to Redux) |
| **TanStack React Query** | Auto-refetch, caching, optimistic updates, devtools | Overkill for single-user demo |
| **Supabase** | Free PostgreSQL + file storage + REST API, no ops overhead | Vendor lock-in; no self-hosted option on free tier |
| **Two independent agents** | Zero-contention inference during training; sync at discrete checkpoints | Double memory for network weights (~2× 1.2M params) |
| **PER with SumTree** | O(log n) priority sampling, O(log n) priority update | ~24MB for 100K transitions at 20-dim state |
| **Recharts** | Lightweight, React-native charting, composable | Limited animation compared to D3; no 3D charts |

---

## 2. Core Features & Functionality

### 2.1 Real-Time 3D Intersection Visualization

**What:** A detailed 3D-rendered 4-way intersection with vehicles, traffic lights, roads, buildings, parks, and trees — all rendered via Three.js / React Three Fiber with physical materials and postprocessing effects.

**How It Works — Technical Details:**

**Rendering Pipeline:**
- Backend runs physics at ~10 Hz and streams JSON frames via WebSocket
- Frontend interpolates vehicle positions between frames for smooth 60 fps rendering via `useFrame` continuous loop
- Orthographic camera (position: [20,20,20], zoom: 45) with OrbitControls (auto-rotation disabled, maxPolarAngle: π/2-0.05, zoom range: 15-120)
- **EffectComposer** with **Bloom** (luminance threshold: 0.2 night / 0.9 day, intensity: 1.5) for emissive glow
- **ContactShadows** (opacity 0.8, scale 50, blur 1.5, resolution 512) for soft ground shadows

**Scene Composition:**
- **Ground:** `MeshPhysicalMaterial` (color #0f111a, clearcoat 0.2, metalness 0.3, roughness 0.7)
- **Roads:** 40×6 unit dual 3-lane roads with asphalt texture, double yellow centerlines (split at intersection), white stop bars (±3.1), zebra crossings, directional labels
- **4 Corner Zones:**
  - NW/SE Parks: Concrete curb + grass tiles + `LowPolyTree` (CylinderGeometry trunk + stacked BoxGeometry foliage with emissive #064e3b)
  - NE/SW City Blocks: `Skyscraper` components in `MeshPhysicalMaterial` (clearcoat 1.0, metalness 0.9, reflectivity 1.0) with neon corner stripes (emissiveIntensity 3.5)
- **Traffic Lights:** 4 cantilever poles with 3D lens spheres (SphereGeometry r=0.15) with emissive glow + arrow text overlay + point lights (intensity 2.0, distance 8) + CCTV camera units (body/visor/lens with blinking red LED)
- **Queue Labels:** `Billboard`-based holographic overlays (dark backing plate + glow border + color-coded value: cyan ≤4, yellow 5-7, red ≥8)

**Lighting System:**
| Mode | Ambient | Directional | Hemisphere | Special |
|------|---------|-------------|------------|---------|
| **Day** | intensity 1.0 | pos [20,40,20], intensity 2.0, color #fffcf2, shadow 2048² | sky #fff, ground #aaa, 0.8 | Sun sphere (r=4, pos [-25,30,-25], emissive #ffaa00, intensity 8.0) |
| **Night** | intensity 0.5 | pos [10,20,10], intensity 1.2, shadow 2048² + pos [-10,15,-10], intensity 0.6, color #6b9bd1 | sky #87ceeb, ground #2a2a3e, 0.4 | — |

**Vehicle Rendering:**
- 6 body types: sedan, suv, hatchback, sportscar, bike, ambulance (hash-selected per vehicle ID)
- Path-following via `CurvePath` (LineCurve3 for straight, QuadraticBezierCurve3 for turns) with piecewise arclength parameter mapping
- Smooth `lerp` interpolation between 10 Hz WebSocket updates
- Dynamic wheel rotation proportional to speed
- Emergency siren: alternating red/blue emissive + point lights

**User Flow:** Navigate to `/simulation` → immediately see the 3D scene → orbit/zoom with mouse → toggle Day/Night → watch vehicles spawn and move → observe queue holograms.

**Priority:** ★★★★★ (core experience)

### 2.2 Fixed-Timer Signal Control

**What:** Traditional traffic signal timing with smart queue-based phase selection and starvation-aware override logic.

**How It Works — Technical Details:**

**Phase Configuration:**
| Phase | ID | Green Directions | Allowed Turns | Default Duration |
|-------|-----|-----------------|---------------|------------------|
| NS_GREEN | 0 | North, South | straight, right | 8s |
| EW_GREEN | 1 | East, West | straight, right | 8s |
| NS_LEFT | 2 | North, South | left only | 8s |
| EW_LEFT | 3 | East, West | left only | 8s |

**Timing Sequence:** GREEN (min 4s, default 8s) → YELLOW (2s) → RED (3s clearance) → GREEN for next phase

**Smart Phase Selection Logic (Upgraded):**
1. After `min_green_duration` (4s), check if current phase has 0 vehicles AND another phase has >0 → switch early
2. At `fixed_duration` (8s) timeout OR if **hard green cap** (40s) is exceeded: select the phase with the **highest total queue count** (excluding current phase) via `_pick_highest_queue_phase()` — no longer sequential fallback
3. If all other phases have 0 vehicles: fall back to next sequential phase
4. **Minimum green guard:** `can_switch_phase` returns False if `time_in_phase < MIN_GREEN_TIME` (8s) unless in transition
5. **Hard green cap (NEW):** In `tick()`, if `color == GREEN` and `time_in_phase >= MAX_GREEN_TIME` (40s), immediately force switch to highest-queue phase — prevents starvation from operator error or logic bugs in both fixed and AI modes

**Phase Transition Safety (Yellow-Red Clearance):**
- `set_phase(target)`: immediately sets `pending_phase = target`, color → YELLOW, timer resets
- After 2s yellow: color → RED, timer resets  
- After 3s red: `current_phase = pending_phase`, color → GREEN, timer resets
- This ensures **5 seconds of clearance** (2s yellow + 3s all-red) between opposing movements

**Intersection Reservation System (All Modes):**
- Vehicles entering the intersection lock the crossing by **direction group**: phases 0,2 reserve NS group; phases 1,3 reserve EW group
- A vehicle enters the intersection only if `intersection_reserved_phase is None` OR the requesting group matches the reserved group
- The reservation releases when `vehicles_in_intersection` becomes empty (last `state == "passed"` vehicle)
- This prevents perpendicular-movement collisions without full collision detection

**Vehicle Collision Avoidance (All Modes):**
- Vehicles in the same lane maintain `MIN_DIST=0.08` spacing from the vehicle ahead
- `max_position = max(0.0, vehicle_ahead.position - MIN_DIST)`
- A vehicle can only move if the vehicle ahead has `speed > 0`, preventing tight bumper-to-bumper creep
- Stop-line enforcement: vehicles cap position at `STOP_LINE` (0.42) when the signal is red, preventing intersection entry

**Starvation Tracking (Shared with AI Mode):**
- Per-direction timers (`starvation_timer` dict): reset to 0 when direction receives green, accumulate `dt` when direction is red
- `get_starved_directions()`: returns directions with timer ≥ `STARVATION_THRESHOLD` (45s)
- In fixed mode: starvation does NOT override phase selection (only AI mode has starvation override), but the metric is still tracked for reward computation

**Yield-on-Left (All Modes):**
- Condition: `vehicle.position ≤ STOP_LINE (0.42) AND turn == "left" AND signal.current_phase in (0, 1)`
- Oncoming direction resolved via map: `{"north": "south", "south": "north", "east": "west", "west": "east"}`
- Checks oncoming straight+right lanes for vehicles with `position` in range `[0.15, 1.0)`
- If any oncoming vehicle found: `can_move = False`
- Only applied for parallel green phases (0,1) where left-turners cross oncoming traffic

**Right-Turn Always-Allowed (All Modes):**
- Right-turning vehicles (`is_right_turn = True`) bypass signal checks entirely
- Not subject to any red-light enforcement

**User Flow:** Launch simulation → toggle to "Fixed" mode → watch traditional cycle → observe yield-on-left → compare with AI mode.

**Priority:** ★★★★★ (baseline for comparison)

---

### 2.2.1 Vehicle Movement & Intersection Physics — Core Algorithms

This section documents the low-level vehicle dynamics and intersection control algorithms that form the simulation engine's foundation.

#### 2.2.1.1 Vehicle Kinematics (`server/app/simulation/vehicle.py`)

Each vehicle follows a deterministic kinematic model updated at 10 Hz (dt = 0.1s):

```
DEFAULT_SPEED = 0.12  # position units per second (normalized 0→1 over road length)
MIN_DIST = 0.08       # minimum following distance (normalized)
STOP_LINE = 0.42      # normalized position of stop line
```

**State Machine:**
```
State ∈ {waiting, moving, braking, passed}
```

**Per-Tick Update (`tick(dt, can_move)`):**
```
if can_move:
    # Accelerate toward target speed
    position += DEFAULT_SPEED * dt
    state = "moving"
else:
    # Hold at stop line or behind vehicle
    if position + DEFAULT_SPEED * dt >= STOP_LINE:
        position = STOP_LINE
    state = "waiting"

# Track wait time while not passed
if state != "passed":
    wait_time += dt

# Transition to passed when clearing intersection
if position >= 1.0:
    state = "passed"
```

#### 2.2.1.2 Car-Following & Collision Avoidance (`intersection.py`)

Vehicles maintain safe spacing using a leader-follower model:

```
for each lane:
    for i, vehicle in enumerate(lane_queue):
        if i > 0:  # has leader
            leader = lane_queue[i-1]
            if leader.position < 1.0:  # leader still in system
                max_position = max(0.0, leader.position - MIN_DIST)
                if vehicle.position + DEFAULT_SPEED * dt >= max_position:
                    vehicle.position = max_position
                    # Only move if leader is also moving
                    can_move = can_move and (leader.speed > 0)
```

**Key properties:**
- **MIN_DIST = 0.08** (8% of road length) prevents rear-end collisions
- **Speed coupling**: follower only moves if leader.speed > 0, preventing "phantom" traffic waves
- **Stop-line enforcement**: vehicles cap at `STOP_LINE = 0.42` when signal is red

#### 2.2.1.3 Intersection Reservation System (`intersection.py`)

Prevents perpendicular collisions using a **direction-group locking** mechanism:

```
# Direction groups: NS (phases 0,2) and EW (phases 1,3)
current_group = 0 if signal.current_phase in (0, 2) else 1
reserved_group = 0 if intersection_reserved_phase in (0, 2) else 1

# Vehicle attempts to enter intersection
entering = vehicle.position + DEFAULT_SPEED * dt >= STOP_LINE
if entering:
    if intersection_reserved_phase is None or current_group == reserved_group:
        vehicles_in_intersection.add(vehicle.id)
        intersection_reserved_phase = signal.current_phase
    else:
        # Perpendicular traffic still clearing
        vehicle.position = STOP_LINE
        can_move = False

# Release lock when last vehicle exits
if vehicle.state == "passed" and vehicle.id in vehicles_in_intersection:
    vehicles_in_intersection.remove(vehicle.id)
    if not vehicles_in_intersection:
        intersection_reserved_phase = None
```

**Invariants:**
- Only one direction group (NS or EW) occupies intersection at a time
- Vehicles entering set the reservation; it clears only when **all** vehicles from that group have passed
- Prevents gridlock without full collision detection

#### 2.2.1.4 Yield-on-Left Logic

Applied during phases 0 (NS_GREEN) and 1 (EW_GREEN) where left-turners cross oncoming traffic:

```
if vehicle.position <= STOP_LINE and vehicle.turn == "left" and signal.current_phase in (0, 1):
    oncoming_dir = {"north": "south", "south": "north", "east": "west", "west": "east"}[dir_name]
    for oncoming_turn in ["straight", "right"]:
        oncoming_queue = lanes.get(f"{oncoming_dir}_{oncoming_turn}", [])
        for oncoming_veh in oncoming_queue:
            if 0.15 <= oncoming_veh.position < 1.0:  # in approach or intersection
                can_move = False
                break
```

**Thresholds:**
- **Yield trigger**: left-turner at or behind stop line (position ≤ 0.42)
- **Oncoming detection range**: position ∈ [0.15, 1.0) — from approach through intersection

#### 2.2.1.5 Right-Turn Priority

Right-turning vehicles (`is_right_turn = True`) **completely bypass signal control**:

```
if vehicle.is_right_turn:
    is_green_for_movement = True  # unconditionally
else:
    is_green_for_movement = signal.is_green_for(direction, turn)
```

- Not subject to stop-line enforcement
- Not counted in pressure calculations
- Not affected by yield-on-left

---

### 2.2.2 Phase Definitions & Signal Logic

**Phase Definitions (updated — left turns separated):**
| Phase | ID | Label | Directions | Turns Allowed | Min Green | Max Green |
|-------|-----|-------|------------|---------------|-----------|-----------|
| NS_GREEN | 0 | NS Straight/Right | North, South | straight, right | 4s | 40s |
| EW_GREEN | 1 | EW Straight/Right | East, West | straight, right | 4s | 40s |
| NS_LEFT | 2 | NS Left Only | North, South | left | 8s | 40s |
| EW_LEFT | 3 | EW Left Only | East, West | left | 8s | 40s |

**Phase Transition (Yellow-Red Clearance):**
```
set_phase(target):
    pending_phase = target
    color = YELLOW
    time_in_phase = 0
    
# In tick():
if color == YELLOW and time_in_phase >= 2.0:
    color = RED
    time_in_phase = 0
if color == RED and time_in_phase >= red_duration (3.0s):
    current_phase = pending_phase
    pending_phase = None
    color = GREEN
    time_in_phase = 0
```

**Total clearance: 5s (2s yellow + 3s all-red)**

---

### 2.2.3 Smart Fixed-Timer Phase Selection (`traffic_signal.py`)

The upgraded fixed-timer uses **queue-based priority selection** instead of sequential cycling:

```
def _pick_highest_queue_phase(current_phase, lanes):
    if lanes is None:
        return (current_phase + 1) % 4
    
    best_phase = None
    best_count = -1
    
    for phase in range(4):
        if phase == current_phase:
            continue
        count = 0
        for lane_dir in PHASE_GREEN_LANES[phase]:  # e.g., ["north", "south"]
            for turn in ["straight", "left", "right"]:
                count += len(lanes.get(f"{lane_dir}_{turn}", []))
        if count > best_count:
            best_count = count
            best_phase = phase
    
    if best_phase is None or best_count == 0:
        return (current_phase + 1) % 4  # fallback sequential
    return best_phase
```

**Decision Logic (in `tick()`):**
1. **Hard max-green cap (NEW)**: If `color == GREEN and time_in_phase >= MAX_GREEN_TIME (40s)` → force switch to `_pick_highest_queue_phase()`
2. **Early switch**: If `time_in_phase >= min_green_duration (4s)` AND current queue empty AND another phase has vehicles → switch
3. **Fixed-duration rollover**: At `fixed_duration (8s)` → switch to highest-queue phase
4. **Fallback**: Sequential if all other phases empty

---

### 2.3 AI (Dueling Double DQN + PER) Signal Control

**What:** A Dueling Double Deep Q-Network agent with Prioritized Experience Replay (PER) that learns optimal signal timing through trial and error, using pressure-based observations and multi-component reward.

**How It Works — Full Technical Architecture:**

#### 2.3.1 Neural Network Architecture (Dueling DQN)
Based on Wang et al. 2016 ("Dueling Network Architectures for Deep Reinforcement Learning"), the network splits Q(s,a) into separate value and advantage streams:

```
Input (20-dim) → Linear(20,256) → LayerNorm → ReLU → Linear(256,256) → LayerNorm → ReLU
    ├──→ Value Stream:   Linear(256,128) → ReLU → Linear(128,1)        → V(s)
    └──→ Advantage Stream: Linear(256,128) → ReLU → Linear(128,4)      → A(s,a)
                Q(s,a) = V(s) + A(s,a) - mean(A(s,a))
```

- **Value stream V(s):** Estimates state-value — "how good is the current traffic state regardless of action"
- **Advantage stream A(s,a):** Estimates action advantage — "how much better is each phase compared to the average"
- **Benefits:** Better policy evaluation under high-density traffic where many actions yield similar Q-values; the value stream learns the baseline state quality while the advantage stream focuses on action differences
- **Weight initialization:** Kaiming uniform for all Linear layers (He et al. 2015)

#### 2.3.2 Observation Space (20-Dimensional)
Normalized to [0,1] range for stable neural network training:

1. **12 Movement Queues** (12 dims): Per-movement vehicle count / MAX_CAP (10.0)
   - `north_straight`, `north_left`, `north_right`
   - `south_straight`, `south_left`, `south_right`
   - `east_straight`, `east_left`, `east_right`
   - `west_straight`, `west_left`, `west_right`
2. **Phase Encoding** (4 dims): One-hot vector [0,0,0,0] — only current phase index is 1.0
3. **Signal Context** (2 dims):
   - `time_in_phase / MAX_GREEN_TIME` — normalized time spent in current phase (capped at 1.0)
   - `is_transitioning` — binary flag (1.0 if YELLOW or RED, 0.0 if GREEN)
4. **Pressure Context** (1 dim): `min(total_pressure / 20.0, 1.0)` — aggregate congestion signal
5. **Starvation Context** (1 dim): `min(max(starvation_timer) / STARVATION_THRESHOLD, 1.0)` — worst-case wait across all directions

#### 2.3.2.1 Observation Builder — Detailed Implementation

Two separate observation builders exist: one for **training** (`TrafficEnv._get_obs()`) and one for **inference** (`simulation_ws._build_obs_from_intersection()`). They must produce **identical** 20-dim vectors.

**Training Observation Builder** (`TrafficEnv._get_obs()` in `environment.py`):

```python
def _get_obs(self) -> np.ndarray:
    movement_queues = self.intersection.get_movement_queues()
    signal = self.intersection.signal
    pressures = self._compute_movement_pressures()  # Full pressure computation
    
    # 1. 12 Movement Queues (normalized by MAX_CAP = 10.0)
    movements = [
        movement_queues.get("north_straight", 0) / 10.0,
        movement_queues.get("north_left", 0) / 10.0,
        movement_queues.get("north_right", 0) / 10.0,
        movement_queues.get("south_straight", 0) / 10.0,
        movement_queues.get("south_left", 0) / 10.0,
        movement_queues.get("south_right", 0) / 10.0,
        movement_queues.get("east_straight", 0) / 10.0,
        movement_queues.get("east_left", 0) / 10.0,
        movement_queues.get("east_right", 0) / 10.0,
        movement_queues.get("west_straight", 0) / 10.0,
        movement_queues.get("west_left", 0) / 10.0,
        movement_queues.get("west_right", 0) / 10.0,
    ]
    
    # 2. Phase One-Hot (4 dims)
    phase_onehot = [0.0, 0.0, 0.0, 0.0]
    phase_onehot[signal.current_phase] = 1.0
    
    # 3. Signal Context (2 dims)
    time_norm = min(signal.time_in_phase / signal.MAX_GREEN_TIME, 1.0)
    is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0
    
    # 4. Pressure Context (1 dim) — FULL computation
    dest_map = { ... }  # 12-entry destination mapping
    outgoing = self.intersection.get_outgoing_counts()
    total_pressure = 0.0
    for movement, dest in dest_map.items():
        incoming = movement_queues.get(movement, 0) / 10.0
        out = outgoing.get(dest, 0) / 10.0
        total_pressure += max(0.0, incoming - out)
    pressure_norm = min(total_pressure / 20.0, 1.0)
    
    # 5. Starvation Context (1 dim)
    max_starv = max(signal.starvation_timer.values()) / signal.STARVATION_THRESHOLD
    max_starv_norm = min(max_starv, 1.0)
    
    obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm]
    return np.array(obs, dtype=np.float32)
```

**Inference Observation Builder** (`_build_obs_from_intersection()` in `simulation_ws.py`):

```python
def _build_obs_from_intersection(intersection) -> np.ndarray:
    movement_queues = intersection.get_movement_queues()
    signal = intersection.signal
    MAX_CAP = 10.0
    
    movements = [ ... ]  # Same 12 movements as above
    
    phase_onehot = [0.0, 0.0, 0.0, 0.0]
    phase_onehot[signal.current_phase] = 1.0
    
    time_norm = min(signal.time_in_phase / signal.MAX_GREEN_TIME, 1.0)
    is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0
    
    # CRITICAL DIFFERENCE: Simplified pressure for inference
    pressure_norm = 0.0  # Not computed in inference — avoids extra computation
    
    max_starv_norm = min(
        max(signal.starvation_timer.values()) / signal.STARVATION_THRESHOLD, 1.0
    )
    
    obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm]
    return np.array(obs, dtype=np.float32)
```

**Critical Difference:**
| Component | Training (`_get_obs`) | Inference (`_build_obs_from_intersection`) |
|-----------|----------------------|--------------------------------------------|
| Pressure | Full `dest_map` + `outgoing` | **Hardcoded to 0.0** |
| Computation | ~200 ops | ~20 ops |
| Accuracy | Exact | Approximate (pressure context = 0) |

**Why?** Inference runs at 10 Hz in the simulation loop; computing full pressure (dest_map lookup, outgoing counts) adds latency. The agent learns to operate with pressure_norm=0.0 during inference, and the reward signal during training provides sufficient pressure information through the reward components.

#### 2.3.2.2 Normalization Constants

| Component | Normalization | Range |
|-----------|--------------|-------|
| Movement queues | `count / 10.0` | [0, 1] |
| Phase one-hot | Exact 1.0 | {0, 1} |
| Time in phase | `time / 40.0` | [0, 1] |
| Pressure | `total / 20.0` | [0, 1] (theoretical max = 12 × 1.0 = 12, but capped) |
| Starvation | `max_timer / 45.0` | [0, 1] |

---

### 2.3.3 Action Space (Discrete 4)
| Action | Phase | Description |
|--------|-------|-------------|
| 0 | NS_GREEN | North + South straight, left, right (left allowed) |
| 1 | EW_GREEN | East + West straight, left, right (left allowed) |
| 2 | NS_LEFT | North + South left-turn only |
| 3 | EW_LEFT | East + West left-turn only |

Agent actions are filtered through **hard constraints** — see 2.3.5.

#### 2.3.4 Prioritized Experience Replay (PER)
Based on Schaul et al. 2016 ("Prioritized Experience Replay"):

- **Data structure:** `SumTree` binary tree (O(log n) priority sampling)
- **Capacity:** 100,000 transitions
- **Priority formula:** `p = (|TD-error| + ε)^α` where ε=1e-6, α=0.6
- **New transitions** are stored with `max_priority^α` to ensure they are sampled at least once
- **Sampling:** Stratified sampling over priority segments; batch of 128 experiences per train step
- **Importance Sampling (IS) weights:** `w = (N × P(i))^(-β)` to correct for priority bias; weights normalized by max(w)
- **Beta annealing:** β starts at 0.4 and linearly anneals to 1.0 over the course of training (Schaul et al. recommend β_start ≈ 0.4 for stability)
- **Priority updates:** After each train step, TD errors update the corresponding tree leaves; `max_priority` tracks the running maximum



---

### 2.3.4.1 SumTree Data Structure — Detailed Algorithm

The **SumTree** is a complete binary tree stored as a flat array where each parent node stores the sum of its children's priorities. This enables O(log n) priority-based sampling and O(log n) priority updates.

**Tree Structure:**
```
Tree array size = 2 * capacity - 1
Leaves start at index = capacity - 1
Data array (transitions) size = capacity

Example (capacity=8, tree size=15):
  Indices:  0       1     2     3    4    5    6    7  8  9 10 11 12 13 14
           root    L     R    LL  LR  RL  RR   leaves...
```

**Core Operations:**

```python
class SumTree:
    def __init__(self, capacity):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data = [None] * capacity
        self.write_ptr = 0
        self.n_entries = 0
    
    def _propagate(self, idx, change):
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)
    
    def _retrieve(self, idx, s):
        left = 2 * idx + 1
        right = left + 1
        if left >= len(self.tree):
            return idx
        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])
    
    @property
    def total_priority(self):
        return self.tree[0]
    
    def add(self, priority, data):
        idx = self.write_ptr + self.capacity - 1
        self.data[self.write_ptr] = data
        self.update(idx, priority)
        self.write_ptr = (self.write_ptr + 1) % self.capacity
        self.n_entries = min(self.n_entries + 1, self.capacity)
    
    def update(self, idx, priority):
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)
    
    def get(self, s):
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return idx, self.tree[idx], self.data[data_idx]
```

**Complexity Analysis:**
| Operation | Time | Notes |
|-----------|------|-------|
| `add` | O(log n) | Single path to root |
| `update` | O(log n) | Single path to root |
| `get` (sample) | O(log n) | Root to leaf traversal |
| Space | O(n) | 2n array |

---

### 2.3.4.2 PrioritizedReplayBuffer — Complete Algorithm

```python
class PrioritizedReplayBuffer:
    def __init__(self, capacity=100_000):
        self.capacity = capacity
        self.tree = SumTree(capacity)
        self.alpha = 0.6           # Priority exponent (0=uniform, 1=full prioritization)
        self.beta = 0.4            # IS weight start
        self.beta_end = 1.0        # IS weight end
        self.epsilon = 1e-6        # Prevents zero priority
        self.max_priority = 1.0
    
    def push(self, state, action, reward, next_state, done):
        """Store transition with maximum priority (guarantees sampling)."""
        transition = (
            np.array(state, dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            float(done),
        )
        priority = self.max_priority ** self.alpha
        self.tree.add(priority, transition)
    
    def sample(self, batch_size):
        """
        Stratified sampling over priority segments.
        Returns: (states, actions, rewards, next_states, dones, weights, indices)
        """
        indices = []
        priorities = []
        transitions = []
        
        segment = self.tree.total_priority / batch_size
        
        for i in range(batch_size):
            a = segment * i
            b = segment * (i + 1)
            s = np.random.uniform(a, b)
            idx, priority, transition = self.tree.get(s)
            
            if transition is None:
                s = np.random.uniform(0, self.tree.total_priority)
                idx, priority, transition = self.tree.get(s)
            
            indices.append(idx)
            priorities.append(priority)
            transitions.append(transition)
        
        # Importance Sampling weights to correct for priority bias
        sampling_probs = np.array(priorities) / self.tree.total_priority
        weights = (self.tree.n_entries * sampling_probs) ** (-self.beta)
        weights /= weights.max()  # Normalize
        
        states, actions, rewards, next_states, dones = zip(*transitions)
        
        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(np.array(actions)),
            torch.FloatTensor(np.array(rewards)),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor(np.array(dones)),
            torch.FloatTensor(weights),
            indices,
        )
    
    def update_priorities(self, indices, td_errors):
        """Update priorities after training step using new TD errors."""
        for idx, td_error in zip(indices, td_errors):
            priority = (abs(float(td_error)) + self.epsilon) ** self.alpha
            self.tree.update(idx, priority)
            self.max_priority = max(self.max_priority, priority)
    
    def anneal_beta(self, episode, total_episodes):
        """Linear annealing from 0.4 to 1.0 over training."""
        self.beta = min(
            self.beta_end,
            0.4 + (self.beta_end - 0.4) * (episode / total_episodes)
        )
    
    def __len__(self):
        return self.tree.n_entries
    
    @property
    def is_ready(self):
        return len(self) >= 2000  # MIN_REPLAY_SIZE
```

**Design Rationale:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| α = 0.6 | Priority exponent | Moderate prioritization (α=1=full, α=0=uniform) |
| β = 0.4→1.0 | IS annealing | Starts biased for learning speed, ends unbiased |
| ε = 1e-6 | Priority floor | Prevents zero priority for zero TD-error |
| New at max_priority | Priority initialization | Guarantees new transitions sampled quickly |
| Stratified sampling | Segment-based | Ensures batch covers full priority range |

---

### 2.3.4.3 PER in Training Loop — Complete Flow

```
Episode Loop (1000 episodes):
    β = 0.4 + 0.6 × (episode / 1000)          # Anneal PER β
    state = env.reset()                        # 20-dim observation
    total_reward = 0
    
    for step in 0..999:
        # 1. Action Selection (ε-greedy)
        if random() < ε:
            action = random(0..3)
        else:
            q = online_net(state)
            action = argmax(q)
        
        # 2. Pre-tick Capture (for switch penalty)
        prev_phase = signal.current_phase
        prev_pressures = _compute_movement_pressures()
        
        # 3. Hard Constraints (override agent)
        if signal.is_max_green_exceeded and action == current_phase:
            action = _get_best_alternative_phase()
        if signal.get_starved_directions():
            action = _get_phase_for_direction(starved[0])
        
        # 4. Environment Step
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        # 5. Store Transition
        buffer.push(state, action, reward, next_state, terminated)
        
        # 6. Training (if warm)
        if buffer.is_ready and step % 2 == 0:
            batch = buffer.sample(128)
            loss, td_errors = train_step(batch)    # See Double DQN below
            buffer.update_priorities(indices, |td_errors|)
        
        # 7. Target Network Sync
        if step_count % 300 == 0:
            target_net.load_state_dict(online_net.state_dict())
        
        total_reward += reward
        state = next_state
        if done: break
    
    ε = max(0.05, ε × 0.998)  # Decay
    log_metrics(total_reward, avg_wait, throughput, ε, loss)
    
    if episode % 50 == 0:
        save_checkpoint()      # Online + Target + Optimizer + Step + obs_version
        sync_sim_agent()       # training_agent → sim_agent
        broadcast_checkpoint()
```

---

### 2.3.4.4 Double DQN Train Step with PER — Full Algorithm

```python
def train_step(batch):
    states, actions, rewards, next_states, dones, weights, indices = batch
    
    # Current Q-values (online net)
    current_q_all = online_net(states)                    # [B, 4]
    current_q = current_q_all.gather(1, actions.unsqueeze(1)).squeeze(1)  # [B]
    
    with torch.no_grad():
        # Double DQN: online net SELECTS action, target net EVALUATES it
        next_actions = online_net(next_states).argmax(1)  # [B]
        next_q = target_net(next_states).gather(
            1, next_actions.unsqueeze(1)
        ).squeeze(1)  # [B]
        
        # Bellman target
        target_q = rewards + GAMMA * next_q * (1 - dones)
    
    # Per-sample TD errors (needed for PER priority update)
    td_errors = (target_q - current_q).detach().cpu().numpy()  # [B]
    per_sample_loss = loss_fn(current_q, target_q)              # [B]
    
    # Weight loss by importance sampling weights (PER bias correction)
    weighted_loss = (per_sample_loss * weights).mean()
    
    optimizer.zero_grad()
    weighted_loss.backward()
    torch.nn.utils.clip_grad_norm_(online_net.parameters(), max_norm=10.0)
    optimizer.step()
    
    step_count += 1
    
    # Update PER priorities with new TD errors
    replay_buffer.update_priorities(indices, np.abs(td_errors))
    
    return float(weighted_loss.item()), td_errors
```

**Key Components Explained:**

| Component | Formula | Purpose |
|-----------|---------|---------|
| **Double DQN Action Selection** | `next_actions = online_net(next_states).argmax(1)` | Online net chooses best action |
| **Double DQN Evaluation** | `next_q = target_net(next_states).gather(1, next_actions)` | Target net evaluates that action |
| **Bellman Target** | `target_q = r + γ × next_q × (1 - done)` | No next_q for terminal states |
| **TD Error (PER)** | `td_error = target_q - current_q` | Drives priority updates |
| **PER-Weighted Loss** | `loss = mean(weights × SmoothL1(current_q, target_q))` | Corrects sampling bias |
| **Gradient Clipping** | `clip_grad_norm(max_norm=10.0)` | Stability for high-TD-error samples |

**Why Double DQN?** Standard DQN uses `max_a Q_target(s', a)` which overestimates because the same network selects and evaluates. Double DQN decouples: online selects `argmax`, target evaluates `Q(s', argmax_online)`.

**Why SmoothL1 (Huber)?** 
```
L1 for |x| > 1: L = |x| - 0.5
L2 for |x| ≤ 1: L = 0.5 × x²
```
Quadratic near 0 (stable), linear beyond (robust to outliers from PER sampling).

---

### 2.3.5
#### 2.3.5 Reward Function — Pressure-Based
Based on PressLight (Wei et al. 2019), MPLight, and FPA-DQN (Wang et al. 2025):

`R = pressure_reward + throughput_reward + switch_penalty + starvation_penalty + max_green_penalty + balance_bonus`

| Component | Formula | Weight | Purpose |
|-----------|---------|--------|---------|
| **Pressure Reward** | `(total_prev_pressure - total_curr_pressure) × 1.5` | 1.5 | Primary signal — reduce intersection-wide congestion pressure |
| **Throughput Bonus** | `vehicles_passed × 0.2` | 0.2 | Reward clearing vehicles (conservative to avoid dominating) |
| **Switch Penalty** | `-0.3` if phase changed AND **previous** phase's green directions still have pressure > 0.3 | -0.3 | Discourage premature phase abandonment (evaluated against the phase we **left**, not the one we entered) |

**Code-level switch penalty mechanism:** `step()` captures `prev_phase = self.intersection.signal.current_phase` **before** `tick()`. This pre-tick phase is passed to `compute_reward()`. The penalty evaluates `prev_pressures` of `PHASE_GREEN_LANES.get(prev_phase, [])` — i.e., the pressure of the phase the agent just abandoned. Without this pre-tick capture, the penalty would incorrectly evaluate the phase the agent *entered* (post-tick state), which always has low pressure at the start of green.
| **Starvation Penalty** | `-2.0 × len(starved_directions)` | -2.0 | Hard penalty per direction waiting > 45s |
| **Max Green Penalty** | `-1.0` if current phase exceeds 40s | -1.0 | Prevent agent from holding green indefinitely |
| **Balance Bonus** | `+0.2` if **phase-level** pressures are nearly equal (imbalance < 0.2) AND traffic is present | 0.2 | Encourage evenly distributed service across all 4 phases |

**Pressure Calculation — Per-Movement Max-Pressure Formulation:**
`Pressure(movement) = max(0, incoming_vehicles(movement) / MAX_CAP - outgoing_vehicles(destination) / MAX_CAP)`

Where:
- **12 movements** with **destination mapping**:
  | Movement | Dest Direction | Movement | Dest Direction |
  |---|---|---|---|
  | north_straight | south | south_straight | north |
  | north_left | east | south_left | west |
  | north_right | west | south_right | east |
  | east_straight | west | west_straight | east |
  | east_left | south | west_left | north |
  | east_right | north | west_right | south |
- `incoming(movement)` = queue count for that specific movement lane
- `outgoing(destination)` = vehicles in the lane that this movement **feeds into** (vehicles with position > 0.9 or state == "passed" in the destination direction's lanes)
- `MAX_CAP = 10.0` (max vehicles per lane)

**Phase-Level Pressure Aggregation (`_get_phase_pressure()`):**
Pressure is aggregated to the phase level for `_get_best_alternative_phase()` and balance bonus:
| Phase | Movements Included |
|-------|-------------------|
| 0 (NS_GREEN) | north_straight, north_left, south_straight, south_left |
| 1 (EW_GREEN) | east_straight, east_left, west_straight, west_left |
| 2 (NS_LEFT) | north_right, south_right |
| 3 (EW_LEFT) | east_right, west_right |

**Code-level distinction:** Before the fix, `_get_best_alternative_phase()` used a `PHASE_GREEN_DIRS_MAP` at the direction-level (grouping by N/S/E/W) and summed direction-level pressures — this meant phases 0 and 2 returned identical pressures (both NS directions). Now it uses `_get_phase_pressure()` which correctly distinguishes the straight/left vs right-turn groupings. Similarly, the balance bonus now aggregates 12 movement pressures into 4 phase-level values before computing `imbalance = max(phase_pressures) - min(phase_pressures)` — preventing single-lane pressure spikes from incorrectly triggering the bonus.

This per-movement pressure formulation provides finer granularity than direction-level pressure — the agent can distinguish which specific movements within a direction are congested, and the destination-aware outgoing count prevents serving a movement whose downstream lane is already full.

#### 2.3.6 Hard Constraints (Safety Overrides)
Applied BEFORE the agent's action takes effect — these are hard guards, not learned:

| Constraint | Trigger | Action | Priority |
|------------|---------|--------|----------|
| **Max Green Override** | Current green phase exceeds MAX_GREEN_TIME (40s) | Force switch to highest-pressure alternative phase via `_get_best_alternative_phase()` | Overrides agent action |
| **Starvation Override** | Any direction waits > STARVATION_THRESHOLD (45s) | Force phase serving starved direction (`_get_phase_for_direction()`: north/south→0, east/west→1) | Overrides agent action |
| **Minimum Green** | `can_switch_phase` returns False if time_in_phase < 8s (unless transitioning) | Blocks phase change request | Signal-level guard |
| **Yellow-Red Clearance** | Any phase change triggers yellow (2s) → red (3s) → green sequence | Enforces safety clearance | Signal-level guard |
| **Intersection Reservation** | Perpendicular traffic group (NS vs EW) holds the crossing | Blocks perpendicular vehicles from entering until all current-group vehicles clear | Group-level guard |

**Constraint enforcement order in `TrafficEnv.step()`:**
1. `signal.is_max_green_exceeded AND action == current_phase` → override action via `_get_best_alternative_phase()`
2. `signal.get_starved_directions()` non-empty → find starved direction's phase, if different from current → override action
3. Pass (potentially overridden) action to `intersection.tick(action=action)`
4. Signal-level guards (min green, yellow-red clearance) enforced inside `signal.set_phase()` and `signal.tick()`

#### 2.3.7 Training Loop

```
For each episode:
  1. Anneal PER beta: β = lerp(PER_BETA_START, PER_BETA_END, episode / total_episodes)
  2. Reset environment → initial 20-dim observation
  3. For each step (max 1000):
     a. Select action via ε-greedy (ε decays 0.998× per episode, floor 0.05)
     b. Capture prev_phase AND prev_pressures pre-tick (for correct switch penalty evaluation)
     c. Hard constraints override action if max-green or starvation triggered
     d. Execute step: intersection.tick(dt=0.1, action=action)
     e. Compute pressure-based reward using pre-tick prev_phase, prev_pressures, post-tick curr_pressures
     d. Push (s, a, r, s', done) into PER buffer with max priority
     e. If buffer size ≥ MIN_REPLAY_SIZE (2000) and step % TRAIN_EVERY_N_STEPS (2) == 0:
        - Sample batch of 128 from PER with IS weights
        - Train step: Double DQN (online net selects action, target net evaluates)
        - Gradient clip: max_norm = 10.0
        - Update PER priorities with new TD errors
     f. If step_count % TARGET_UPDATE_FREQ (300) == 0: sync target network
     g. If done: break
  4. Decay epsilon
  5. Save episode metrics to Supabase + broadcast via WebSocket
  6. If episode % 50 == 0:
     a. Save checkpoint (online + target + optimizer + step_count + obs_version)
     b. SYNC sim_agent weights from training_agent
     c. Save model metadata with rolling 50-episode avg reward
     d. Broadcast "checkpoint_saved" via training WebSocket
```

#### 2.3.8 Two-Agent Architecture

```
┌─────────────────────────┐       ┌──────────────────────────┐
│   sim_agent (inference) │       │ training_agent (training)│
│   DuelingDQNNetwork     │       │ DuelingDQNNetwork        │
│   Used by: /ws/simulation│       │ Used by: Trainer         │
│   ε = 0 (greedy)        │       │ ε: 1.0 → 0.05           │
│   No replay buffer      │       │ Full PER buffer (100K)   │
└────────┬────────────────┘       └───────────┬──────────────┘
         │                                       │
         └─────────── Weight Sync ───────────────┘
               (every 50 episodes during training,
                training_agent.online_net → sim_agent.online_net)
```

**Key point:** The two agents are completely independent instances. Training gradient updates never directly affect live inference. The sim_agent only receives updated weights at explicit sync points (every 50 episodes).

#### 2.3.9 Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| STATE_DIM | 20 | Observation dimension (12 movements + 4 phase + 4 context) |
| ACTION_DIM | 4 | Discrete phase actions |
| LEARNING_RATE | 3e-4 | Adam optimizer learning rate |
| GAMMA | 0.97 | Discount factor (higher = more future-aware) |
| BATCH_SIZE | 128 | PER batch size |
| TRAIN_EVERY_N_STEPS | 2 | Train step frequency |
| REPLAY_BUFFER_SIZE | 100,000 | PER capacity |
| MIN_REPLAY_SIZE | 2,000 | Warmup steps before training |
| EPSILON_START / END | 1.0 / 0.05 | Exploration range |
| EPSILON_DECAY | 0.998 | Per-episode decay multiplier |
| MAX_STEPS_PER_EPISODE | 1,000 | Episode length |
| DEFAULT_EPISODES | 1,000 | Default training episodes |
| TARGET_UPDATE_FREQ | 300 | Target network sync interval |
| PER_ALPHA | 0.6 | Priority exponent |
| PER_BETA_START / END | 0.4 / 1.0 | Importance sampling annealing |
| MIN_GREEN_TIME | 8.0s | Minimum green hold |
| MAX_GREEN_TIME | 40.0s | Absolute green phase cap |
| STARVATION_THRESHOLD | 45.0s | Starvation trigger |
| TRAINING_LAMBDA | 0.8 | Vehicle spawn rate during training |
| EVAL_LAMBDA | 0.5 | Vehicle spawn rate during evaluation |

#### 2.3.10 Research Context & Literature References

The architecture integrates components from multiple established RL-for-traffic-control papers:
- **Dueling DQN:** Wang et al. 2016 — separate V(s) and A(s,a) for better value estimation
- **Double DQN:** van Hasselt et al. 2016 — reduces overestimation bias in Q-learning
- **PER:** Schaul et al. 2016 — prioritized sampling of high-TD-error transitions
- **Pressure-based reward:** PressLight (Wei et al. 2019), MPLight, Advanced-MPLight, FPA-DQN (Wang et al. 2025)
- **Pressure calculation:** Incoming - outgoing formulation from MPLight / PDLight
- **Constraints:** Max-green and starvation guards inspired by real-world traffic controller specifications

**User Flow:** Launch simulation → toggle "AI" mode → watch Dueling DQN decisions → see live metrics improve over training sessions → load trained checkpoint → compare vs fixed/manual.

**Priority:** ★★★★★ (core differentiator)

### 2.4 Greedy Baseline Control — **NEW**

**What:** A deterministic rule-based controller that selects the phase with the highest total queued vehicles at each decision point. Serves as an interpretable baseline between Fixed-Timer and learned AI policies.

**How It Works — Technical Details:**
- Available in both single-intersection (`/simulation`) and city grid (`/city`) modes via `"greedy"` mode string
- At each tick (when `signal.can_switch_phase` is true):
  1. Compute total queue count per phase: sum of vehicles across phase's green directions × allowed turns
  2. Phase 0/1 (straight+right): sum straight+right queues for NS/EW directions
  3. Phase 2/3 (left): sum left queues for NS/EW directions
  4. Select `best_phase = argmax(phase_counts)`
  5. If `signal.can_switch_phase` is false (min-green not met), hold current phase
- No learning, no exploration, no reward function — purely myopic queue-maximization
- Respects the same hard constraints as AI mode: min-green (8s), yellow-red clearance (5s), max-green (40s), starvation tracking

**Phase Mapping (matches updated Fixed-Timer):**
| Phase | Directions | Turns Counted |
|-------|------------|---------------|
| 0 (NS_GREEN) | north, south | straight, right |
| 1 (EW_GREEN) | east, west | straight, right |
| 2 (NS_LEFT) | north, south | left |
| 3 (EW_LEFT) | east, west | left |

**Why It Matters:**
- Provides a strong, interpretable baseline that often beats Fixed-Timer
- Exposes the value of learned coordination: Greedy is locally optimal but globally myopic (no green-wave, no downstream pressure awareness)
- In city grid, Greedy runs **independently per intersection** — same logic applied at each of 4 intersections simultaneously
- Shared-policy AI can learn coordination patterns Greedy cannot

**User Flow:** Select "Greedy" mode → watch rule-based decisions → compare with AI on Comparison Benchmark.

**Priority:** ★★★★☆ (essential baseline for research)

### 2.5 Multi-Intersection City Grid (2×2) — **NEW MAJOR FEATURE**

**What:** A 2×2 grid of 4 coordinated intersections (A, B, C, D) with inter-intersection vehicle routing, shared-policy DQN control, and automated benchmark comparison. Extends the single-intersection architecture to a network level.

```
Layout:     [A] ═══ [B]
             ║         ║
            [C] ═══ [D]

A = top-left,  B = top-right
C = bot-left,  D = bot-right
```

**Architecture — Backend (`server/app/simulation/`):**

| Component | Responsibility |
|-----------|----------------|
| `city_network.py` | `CityNetwork` class: 4 `Intersection` instances, `RoadVehicle` transfer logic, `ROAD_CONNECTIONS` (A↔B, C↔D E-W; A↔C, B↔D N-S), `EXIT_DIR_MAP` (12 movement→destination), `build_obs()` (20-dim per intersection, matches single-intersection exactly), `get_greedy_action()` (same logic as single), `tick()` (orchestrates intersection ticks → collect passed vehicles → route to roads/destination → inject into destination lanes), `get_city_metrics()` (city-wide avg wait, throughput, congestion level, per-intersection breakdown) |
| `city_spawner.py` | `CitySpawner`: 8 external entry points (N/S/E/W of each corner intersection), Poisson spawn divided across entries, 50/25/25 straight/left/right, max 12/lane, carries accumulated wait time across intersections |
| `city_schema.py` | Pydantic models for `/ws/city` frames: `CityFrame` (timestep, mode, city_metrics, intersections dict, road_vehicles), `CityIntersectionState` (signal, queues, vehicles, Q-values, world coords), `RoadVehicleState` (progress, world coords), `build_city_frame()` with world-position helpers (`INTERSECTION_WORLD_POS`, `_lane_to_world()`, `_road_vehicle_world()`) |
| `city_ws.py` | `/ws/city` handler: `CityConnectionManager`, `_city_simulation_loop()` at 10 Hz, supports Fixed/Greedy/AI modes + **automated comparison test** (`ComparisonTestState`: runs Fixed→Greedy→AI sequentially, 30s each, broadcasts phase progress, final results), command validation (`set_mode`, `set_spawn_rate`, `run_comparison`) |

**Vehicle Routing Between Intersections:**
1. Vehicle passes intersection (state → "passed") → `_route_passed_vehicles()` looks up `ROAD_CONNECTIONS[(from_iid, exit_dir)]`
2. If connects to another intersection: creates `RoadVehicle` with `from_intersection`, `to_intersection`, `entry_dir`, `next_turn` (random 50/25/25), adds to `road_vehicles` list
3. If exits city boundary: increments `total_city_throughput`
4. Road vehicles advance `progress` each tick (30 ticks = 3s travel time at 10 Hz); on arrival (`progress >= 1.0`), `_inject_vehicle()` attempts to insert into destination intersection's entry lane (respects `MAX_QUEUE=12`); if full, vehicle waits at road end

**Shared-Policy AI Control:**
- Single `sim_agent` (DQNAgent, ε=0) used for **all 4 intersections**
- At each tick: `build_obs(iid)` → `agent.select_action(obs, ε=0)` → `intersection.tick(action)` — same as single-intersection but looped over A,B,C,D
- Policy learns to coordinate implicitly through shared weights and pressure observations that include downstream congestion
- Greedy mode also runs independently per intersection using local queues

**Automated Comparison Benchmark (`run_comparison` command):**
- Resets city, enables spawner, runs Fixed → Greedy → AI sequentially (30s each by default)
- Samples city metrics every 10 ticks, computes per-mode avg wait & throughput
- Broadcasts `comparison_progress` (current mode, elapsed, phase index) and final `comparison_results` (per-mode avg_wait_time, throughput)
- Frontend `CityComparisonPanel` renders grouped bar chart with improvement % vs Fixed

**Frontend Components (`client/src/components/city/`):**
| Component | Purpose |
|-----------|---------|
| `CityCanvas` | Three.js canvas: 4 intersection nodes, road vehicles, congestion heatmap overlay, queue labels, TrafficLight reuse |
| `CityGrid` | 9 city blocks (parks + skyscrapers with neon stripes), MeshPhysicalMaterial ground |
| `CityRoads` | Continuous asphalt roads (56 units), double yellow lines, stop bars, directional labels |
| `CityVehicle` | Reuses single-intersection `CurvePath` logic + **road-vehicle linear interpolation** (world_x/z from frame) with lateral offset based on `prev_turn`/`next_turn` |
| `CityControls` | Fixed/Greedy/AI mode toggle, Start/Stop/Reset, spawn rate slider (0.05–1.5), congestion heatmap toggle, Run Comparison button |
| `CityMetricsPanel` | 2×2 global metric cards (Avg Wait, Throughput, Active, Road Vehicles) + per-intersection rows with signal dots, queue bars, phase |
| `CityComparisonPanel` | Recharts bar chart (Fixed/Greedy/AI), improvement badge, live progress during benchmark |

**Data Flow (`/ws/city` at 10 Hz):**
```
CitySpawner.spawn() → CityNetwork.tick(mode, shared_agent)
  → each Intersection.tick() → passed vehicles routed to RoadVehicle or city exit
  → RoadVehicle.tick() advances progress
  → arrived RoadVehicles injected into destination Intersection
  → build_city_frame() → broadcast CityFrame JSON
```

**User Flow:** Navigate to `/city` → select Fixed/Greedy/AI → Start → watch 4-intersection coordination → Run Comparison → view benchmark results.

**Priority:** ★★★★★ (major architectural milestone)


---

### 2.5.1 City Grid Routing & Vehicle Transfer — Core Algorithms

This section documents the core vehicle routing and inter-intersection transfer logic that enables multi-intersection simulation.

#### 2.5.1.1 Grid Topology & Road Connections (`city_network.py`)

```python
# Grid layout:
#     [A] ==== [B]
#      ||           ||
#     [C] ==== [D]

ROAD_CONNECTIONS: Dict[Tuple[str, str], Tuple[str, str]] = {
    # A's exits
    ("A", "east"):  ("B", "west"),
    ("A", "south"): ("C", "north"),
    # B's exits
    ("B", "west"):  ("A", "east"),
    ("B", "south"): ("D", "north"),
    # C's exits
    ("C", "north"): ("A", "south"),
    ("C", "east"):  ("D", "west"),
    # D's exits
    ("D", "north"): ("B", "south"),
    ("D", "west"):  ("C", "east"),
}

# External exits (vehicles leaving the city)
EXTERNAL_EXITS: Dict[Tuple[str, str], str] = {
    ("A", "north"): "north_exit", ("A", "west"):  "west_exit",
    ("B", "north"): "north_exit", ("B", "east"):  "east_exit",
    ("C", "south"): "south_exit", ("C", "west"):  "west_exit",
    ("D", "south"): "south_exit", ("D", "east"):  "east_exit",
}

# Movement => Exit Direction mapping
EXIT_DIR_MAP: Dict[str, str] = {
    "north_straight": "south", "north_left": "east",  "north_right": "west",
    "south_straight": "north", "south_left": "west",  "south_right": "east",
    "east_straight":  "west",  "east_left":  "south", "east_right":  "north",
    "west_straight":  "east",  "west_left":  "north", "west_right":  "south",
}
```

#### 2.5.1.2 Vehicle Routing Pipeline (`_route_passed_vehicles`)

```python
def _route_passed_vehicles(self, dt, passed_vehicles):
    """
    For each just-passed vehicle, determine its destination:
    - Another intersection (create RoadVehicle)
    - City boundary (increment throughput)
    """
    for iid, vehicle in passed_vehicles:
        lane_key = f"{vehicle.lane}_{vehicle.turn}"
        exit_dir = EXIT_DIR_MAP.get(lane_key)
        if exit_dir is None:
            continue
        
        connection_key = (iid, exit_dir)
        
        if connection_key in ROAD_CONNECTIONS:
            # Route to adjacent intersection
            to_inter, entry_dir = ROAD_CONNECTIONS[connection_key]
            next_turn = np.random.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25])
            
            rv = RoadVehicle(
                vehicle_id=vehicle.id,
                from_intersection=iid,
                to_intersection=to_inter,
                entry_dir=entry_dir,
                wait_time=vehicle.wait_time,  # Carry accumulated wait time
                prev_turn=vehicle.turn,
                next_turn=next_turn,
            )
            self.road_vehicles.append(rv)
        else:
            # Exits city boundary
            self.total_city_throughput += 1
```

**Key Design Decisions:**
- **Wait time carryover**: `wait_time` accumulates across intersections (critical for pressure calculation)
- **Random next turn**: 50/25/25 straight/left/right for realism
- **Max queue per lane**: `MAX_QUEUE = 12` prevents gridlock

#### 2.5.1.3 Road Vehicle Dynamics (`RoadVehicle.tick`)

```python
class RoadVehicle:
    def __init__(self, vehicle_id, from_intersection, to_intersection, 
                 entry_dir, wait_time, prev_turn, next_turn):
        self.id = vehicle_id
        self.from_intersection = from_intersection
        self.to_intersection = to_intersection
        self.entry_dir = entry_dir        # Direction entering destination intersection
        self.progress = 0.0               # 0.0 to 1.0 along road segment
        self.wait_time = wait_time
        self.ticks_traveled = 0
        self.prev_turn = prev_turn
        self.next_turn = next_turn
    
    def tick(self, dt):
        """Returns True when vehicle has reached destination intersection."""
        self.progress = min(1.0, self.progress + dt / ROAD_TRAVEL_TIME)
        self.ticks_traveled += 1
        return self.progress >= 1.0
```

**Parameters:**
- `ROAD_TRAVEL_TIME = 3.0s` = 30 ticks at 10 Hz
- Progress advances linearly from 0.0 (departure) to 1.0 (arrival)

#### 2.5.1.4 Vehicle Injection at Destination (`_inject_vehicle`)

```python
def _inject_vehicle(self, intersection, rv):
    """Insert arriving road vehicle into destination intersection's lane."""
    turn = rv.next_turn
    lane_key = f"{rv.entry_dir}_{turn}"
    lane_queue = intersection.lanes.get(lane_key, [])
    
    if len(lane_queue) < MAX_QUEUE:  # MAX_QUEUE = 12
        vehicle = Vehicle(
            id=rv.id,
            lane=rv.entry_dir,
            turn=turn,
            position=0.0,
            wait_time=rv.wait_time,   # Carry accumulated wait
            speed=DEFAULT_SPEED,
            state="waiting",
        )
        lane_queue.append(vehicle)
        intersection._spawned_this_interval += 1
        return True
    return False  # Lane full - vehicle waits at road end
```

**Queue Management:**
- **MAX_QUEUE = 12** per lane (vs 10 for single intersection)
- If lane full: vehicle **stalls at road end** (`progress = 1.0`), re-checked next tick
- **Wait time preservation**: `wait_time` accumulates across intersections - pressure calculation reflects total journey delay

#### 2.5.1.5 World Coordinate Mapping (Frontend Visualization)

```python
INTERSECTION_WORLD_POS = {
    "A": (-10.0, -10.0),   # (world_x, world_z) top-left
    "B": ( 10.0, -10.0),   # top-right
    "C": (-10.0,  10.0),   # bottom-left
    "D": ( 10.0,  10.0),   # bottom-right
}

# Road vehicle world position (linear interpolation):
def _road_vehicle_world(rv):
    ax, az = INTERSECTION_WORLD_POS[rv.from_intersection]
    bx, bz = INTERSECTION_WORLD_POS[rv.to_intersection]
    dx, dz = bx - ax, bz - az
    dist = sqrt(dx**2 + dz**2)
    nx, nz = dx / dist, dz / dist
    offset = 6.0  # 6 units from center
    start_x, start_z = ax + nx * offset, az + nz * offset
    end_x, end_z = bx - nx * offset, bz - nz * offset
    wx = start_x + (end_x - start_x) * rv.progress
    wz = start_z + (end_z - start_z) * rv.progress
    return wx, wz
```

**Intersection Lane World Position:**
```python
def _lane_to_world(iid, lane, position):
    cx, cz = INTERSECTION_WORLD_POS[iid]
    road_len = 6.0
    lateral = 1.0  # lane offset
    
    if lane == "north":
        wx, wz = cx - lateral, cz - road_len + position * road_len
    elif lane == "south":
        wx, wz = cx + lateral, cz + road_len - position * road_len
    elif lane == "east":
        wx, wz = cx + road_len - position * road_len, cz - lateral
    elif lane == "west":
        wx, wz = cx - road_len + position * road_len, cz + lateral
    return wx, wz
```

---

### 2.6 Manual (MNL) Signal Control

**What:** Human-in-the-loop control mode where the operator directly sets signal phases.

**How It Works:**
- Backend `TrafficSignal.tick()` receives `is_manual=true` flag
- In manual mode, the signal **holds the current green phase indefinitely** — no auto-cycling
- Frontend provides 4 phase buttons: NS Green (0), EW Green (1), NS Left (2), EW Left (3)
- User clicks a button → `manual_override` WebSocket command → backend calls `signal.set_phase(phase)` → goes through yellow (2s) → red (3s) → green for new phase
- **Yield-on-left logic still applies** during manual green phases
- Emergency override still forces priority phase

**User Flow:** Select "Manual" mode → 4 phase buttons appear → click to change phase → observe traffic response.

**Priority:** ★★★★☆ (educational/human-factors evaluation)

### 2.7 Live Training Dashboard

**What:** Watch the Dueling DQN + PER agent learn in real-time with streaming metrics.

**How It Works — Technical Details:**

**Data Flow:**
- Separate WebSocket (`/ws/training`) pushes per-episode metrics via `broadcast_training_metric()` at the end of each training episode
- `Trainer` sends: `episode`, `total_reward`, `avg_wait_time`, `throughput`, `epsilon`, `loss`, `is_training` (False on last episode)
- Frontend `TrainingControls` subscribes to Zustand `trainingMetrics` store (capped at 1000 entries)
- Backend also broadcasts `"checkpoint_saved"` events at every checkpoint (every 50 episodes)

**Metrics Display:**
- **Reward:** Area chart (cyan) with trend arrow + sparkline + progress bar, color-coded by value (green >0, red <0)
- **Avg Wait Time:** Area chart (orange) with rolling window
- **Epsilon:** Area chart (yellow) showing exploration decay over episodes
- **Loss:** Area chart (purple) showing PER-weighted SmoothL1 loss

**Training Chart (Analytics Tab):**
- `Recharts` `<AreaChart>` with toggleable metrics, showing last 100 episodes
- Interactive summary cards below chart with latest metric values

**Training Controls Component:**
- **Train Agent button:** Opens config modal (1–2000 episodes, default 1000)
- **During training:** Shows all 4 metric cards with animated updates, progress bar (episodes completed / total), ETA (estimated from episodes/min), and speed (episodes/min)
- **After training:** "Load Model" dropdown fetches `/training/models`, loads checkpoint into both sim_agent + training_agent

**PER Integration:**
- Beta value is annealed linearly from 0.4 to 1.0 over total episodes (visible via loss metric behavior)
- Buffer warmup: first 2000 steps are pure exploration (no training) until MIN_REPLAY_SIZE is reached

**User Flow:** Click "Train Agent" → configure episodes → watch live metrics (reward increasing, wait decreasing) → monitor epsilon decay → model auto-saves every 50 episodes → load model → run AI inference.

**Priority:** ★★★★★ (key educational feature)

### 2.8 Performance Comparison (AI vs Fixed vs Manual)

**What:** Side-by-side bar charts comparing all three single-intersection control modes with live improvement metrics.

**How It Works — Technical Details:**

**Data Pipeline:**
- Frontend fetches `/api/metrics` (Next.js API route → Prisma → Supabase `performance_metrics` table) every 15 seconds via TanStack React Query with `refetchInterval: 15000`
- Data grouped by `mode` field: filters for "fixed", "ai", and "manual"/"mnl" rows
- `avgWaitTime` and `throughput` computed as mean averages per mode group

**Rendering:**
- `Recharts` `<BarChart>` with 2 data groups: "Avg Wait (s)" and "Throughput"
- Up to 3 bar series: Fixed (#475569 slate), AI (#38bdf8 cyan), Manual (#f59e0b amber)
- Improvement percentage: `((avgWaitFixed - avgWaitAI) / avgWaitFixed) × 100`
- Positive improvement = green badge, negative = red badge with "keep training" message
- Empty state with instructional text if no data
- Loading spinner during fetch

**Database Persistence:**
- `save_performance_metric()` called when simulation stops (via stop command or WebSocket disconnect)
- Fields: simulationId, mode, avgWaitTime, throughput, maxQueueLength, totalSteps
- One row per simulation per mode

**User Flow:** Run simulations in each mode → switch to "Compare" tab → view bar chart with improvement %.

**Priority:** ★★★★☆ (proves value)

### 2.9 City Grid Comparison Benchmark — **NEW**

**What:** Automated 3-mode benchmark (Fixed → Greedy → AI) on the 2×2 city grid with live progress tracking and results visualization.

**How It Works:**
- Triggered via `run_comparison` WebSocket command on `/ws/city`
- `ComparisonTestState` orchestrates: resets city, enables spawner, runs each mode for `duration_per_mode` (default 30s)
- Every 10 ticks (1s): samples `get_city_metrics()` → records avg_wait & throughput per mode
- Broadcasts `comparison_progress` frame with current mode, elapsed, phase index
- On completion: broadcasts `comparison_results` with per-mode aggregates
- Frontend `CityComparisonPanel` renders grouped bar chart (Avg Wait / Throughput) with improvement % vs Fixed

**Rendering:**
- `Recharts` `<BarChart>` with Fixed/Greedy/AI series (#475569 / #f59e0b / #38bdf8)
- Live progress overlay during benchmark run
- Results persist only in-memory (not saved to DB) — intended for live demo sessions

**User Flow:** Navigate to `/city` → Analytics tab → Compare → click "Run Comparison" → watch 90s benchmark → view results.

**Priority:** ★★★★☆ (proves multi-intersection value)

**Rendering:**
- `Recharts` `<BarChart>` with Fixed/Greedy/AI series (#475569 / #f59e0b / #38bdf8)
- Live progress overlay during benchmark run
- Results persist only in-memory (not saved to DB) — intended for live demo sessions

**User Flow:** Navigate to `/city` → Analytics tab → Compare → click "Run Comparison" → watch 90s benchmark → view results.

**Priority:** ★★★★☆ (proves multi-intersection value)

---

### 2.9.1 Automated Comparison Benchmark — Detailed Algorithm

This section documents the complete algorithm for the automated 3-mode comparison benchmark that runs Fixed → Greedy → AI sequentially on the city grid.

#### 2.9.1.1 ComparisonTestState Machine (`city_ws.py`)

```python
class ComparisonTestState:
    def __init__(self):
        self.running = False
        self.current_mode_idx = 0
        self.modes = ["fixed", "greedy", "ai"]
        self.duration_per_mode = 30   # seconds per mode
        self.results = {}
        self.snapshots = {}
        self.started_at = 0.0
    
    def start(self):
        self.running = True
        self.current_mode_idx = 0
        self.results = {}
        self.snapshots = {}
        self.started_at = time.time()
    
    def current_mode(self):
        return self.modes[self.current_mode_idx]
    
    def elapsed(self):
        return time.time() - self.started_at
    
    def should_advance(self):
        return self.elapsed() >= self.duration_per_mode
    
    def record_snapshot(self, city_metrics):
        mode = self.current_mode()
        if mode not in self.snapshots:
            self.snapshots[mode] = []
        self.snapshots[mode].append({
            "avg_wait": city_metrics["avg_wait_time"],
            "throughput": city_metrics["total_throughput"],
        })
    
    def advance(self):
        """Move to next mode. Returns True if all modes done."""
        mode = self.current_mode()
        snaps = self.snapshots.get(mode, [])
        if snaps:
            avg_waits = [s["avg_wait"] for s in snaps]
            throughputs = [s["throughput"] for s in snaps]
            self.results[mode] = {
                "avg_wait_time": round(sum(avg_waits) / len(avg_waits), 2),
                "throughput": throughputs[-1] if throughputs else 0,
            }
        self.current_mode_idx += 1
        self.started_at = time.time()
        return self.current_mode_idx >= len(self.modes)
    
    def finish(self):
        self.running = False
        return self.results
```

#### 2.9.1.2 Benchmark Execution Loop (`_city_simulation_loop`)

```python
async def _city_simulation_loop(app):
    comparison_state = ComparisonTestState()
    
    while True:
        if not app.state.city_running:
            await asyncio.sleep(0.1)
            continue
        
        city_net = app.state.city_network
        city_spawner = app.state.city_spawner
        agent = app.state.sim_agent
        
        # Determine current mode
        if comparison_state.running:
            mode = comparison_state.current_mode()
            # Sample metrics every 10 ticks (1s)
            if city_net.timestep % 10 == 0:
                raw = city_net.get_city_metrics()
                comparison_state.record_snapshot(raw)
            # Check if mode duration elapsed
            if comparison_state.should_advance():
                done = comparison_state.advance()
                if done:
                    results = comparison_state.finish()
                    await city_manager.broadcast({
                        "frame_type": "comparison_results",
                        "results": results,
                    })
                    app.state.city_mode = "fixed"
                    city_net.reset()
                    city_spawner.set_enabled(True)
                    continue
                else:
                    # Reset for next mode
                    city_net.reset()
                    city_spawner.set_enabled(True)
                    await city_manager.broadcast({
                        "frame_type": "comparison_phase",
                        "current_mode": comparison_state.current_mode(),
                        "elapsed": 0,
                        "total": comparison_state.duration_per_mode,
                    })
        else:
            mode = getattr(app.state, "city_mode", "fixed")
        
        # Spawn & tick
        city_spawner.spawn(dt=0.1, intersections=city_net.intersections)
        city_net.tick(dt=0.1, mode=mode, shared_agent=agent if mode == "ai" else None)
        
        # Build & broadcast frame
        frame = build_city_frame(city_net, mode, shared_agent=agent if mode == "ai" else None)
        payload = frame.model_dump()
        
        if comparison_state.running:
            payload["comparison_progress"] = {
                "running": True,
                "current_mode": comparison_state.current_mode(),
                "elapsed": round(comparison_state.elapsed(), 1),
                "total": comparison_state.duration_per_mode,
                "mode_index": comparison_state.current_mode_idx,
                "total_modes": len(comparison_state.modes),
            }
        else:
            payload["comparison_progress"] = {"running": False}
        
        await city_manager.broadcast(payload)
        await asyncio.sleep(0.1)
```

#### 2.9.1.3 Metrics Aggregation

Each mode runs for **30 seconds (300 ticks at 10 Hz)**. Metrics are sampled every **10 ticks (1 second)**.

**Per-Snapshot Metrics:**
```python
{
    "avg_wait": city_metrics["avg_wait_time"],      # Mean wait across all intersections
    "throughput": city_metrics["total_throughput"], # Cumulative vehicles exited city
}
```

**Final Per-Mode Aggregation:**
```python
avg_wait_time = round(sum(avg_waits) / len(avg_waits), 2)
throughput = throughputs[-1] if throughputs else 0  # Final cumulative count
```

**Improvement Calculation (Frontend):**
```python
improvement = ((fixed_avg_wait - ai_avg_wait) / fixed_avg_wait) * 100
```

#### 2.9.1.4 Frame Types Broadcast

| Frame Type | Trigger | Payload |
|------------|---------|---------|
| `comparison_started` | `run_comparison` command | `{modes: [...], duration_per_mode: 30}` |
| `comparison_phase` | Mode transition | `{current_mode, elapsed, total}` |
| `city_simulation` (with `comparison_progress`) | Every tick (10 Hz) | Standard frame + `{running, current_mode, elapsed, total, mode_index, total_modes}` |
| `comparison_results` | Benchmark complete | `{fixed: {avg_wait, throughput}, greedy: {...}, ai: {...}}` |

---

### 2.10 Episode History

**How It Works:**
- Fetches from `/api/episodes` (Next.js API route → Prisma)
- Auto-refreshes every 10 seconds during training
- Columns: Episode #, Reward (color-coded), Wait Time, Throughput, Epsilon, Duration
- Best episode highlighted in green
- 10 per page with pagination

**User Flow:** Switch to "History" tab → browse episodes → identify best-performing episode.

**Priority:** ★★★☆☆

### 2.11 Real-Time Metrics Panel

**What:** Live stats updating during simulation.

**How It Works:**
- 2×2 card grid showing avg wait time, throughput, max queue, episode
- Animated number transitions, progress bars, SVG sparklines
- 20-point rolling history displayed per metric
- Live Snapshot panel (bottom-left overlay) shows connection status, active vehicles, etc.

**User Flow:** Watch metrics update live as simulation runs.

**Priority:** ★★★★☆

### 2.12 Model Persistence & Loading

**What:** Save and load trained model checkpoints with metadata tracking.

**How It Works — Technical Details:**

**Checkpoint Structure:**
```
{
  'online_net':  state_dict,       # DuelingDQNNetwork weights
  'target_net':  state_dict,       # Target network (sync of online)
  'optimizer':   state_dict,       # Adam optimizer state
  'step_count':  int,              # Total training steps
  'obs_version': 'v3_20dim_pressure'  # Observation schema version tracking
}
```

**Save Locations:**
1. **Supabase Storage** (`model-checkpoints` bucket): path = `models/{simulation_id}/checkpoint_{episode}.pt`
2. **Local disk** (`server/models/`): same path structure (fallback for development)

**Metadata (rl_models table):**
- Upserted at checkpoint time (every 50 episodes), keyed by `simulation_id` (reuses simulation UUID)
- Fields: id, name (formatted as `"Model {date} {time} - {episode}eps - {rating}"`), version (episode number), storagePath, avgReward (rolling 50-episode window), epsilon, totalEpisodes, isActive
- **Rating system:** `_get_rating(avg_reward)`: Excellent (>10) → Efficient (>0) → Fair (>-10) → Poor (>-30) → Failing (≤-30)

**Loading Flow (`POST /training/load`):**
1. `GET /training/models` returns all models (3-tier discovery: DB → Supabase Storage listing → local disk, deduplicated)
2. User selects model → `POST /training/load {model_id}` → `model_service.list_checkpoints()` finds latest episode
3. `model_service.load_checkpoint()`: tries Supabase Storage first, falls back to local disk
4. State dict loaded into **both** `sim_agent.online_net` AND `training_agent.online_net` (for future training continuity)
5. Target networks also synced; optimizer and step_count loaded if available
6. Legacy checkpoint compatibility (raw state_dict without metadata dict)

**Agent Weight Synchronization:**
- During active training, at each checkpoint, Trainer syncs:
  ```python
  sim_agent.online_net.load_state_dict(training_agent.online_net.state_dict())
  sim_agent.target_net.load_state_dict(training_agent.target_net.state_dict())
  ```
- This ensures live AI inference uses the latest trained policy

**User Flow:** Train agent → checkpoints auto-save every 50 eps → metadata persisted with rating → "Load Model" dropdown → select checkpoint → both agents loaded → run AI mode inference.

**Priority:** ★★★★☆

### 2.13 Emergency Vehicle Preemption

**What:** Spawn emergency vehicles that force priority green lights.

**How It Works — Technical Details:**
- 4 directional buttons in the control panel (North/South/East/West)
- `trigger_emergency_override(lane)`: spawns emergency vehicle with `is_emergency=True`, random ID `emergency-{uuid4.hex[:6]}`, straight turn, position 0.0
- **Guard:** prevents double-spawning — checks if any vehicle in the direction's three lanes has `is_emergency=True`
- **Signal Bypass Mechanism (`intersection.tick()` lines 52–69):**
  1. Detect active emergency in any lane
  2. Compute `priority_phase = 0` for north/south, `1` for east/west
  3. Directly set `signal.current_phase = priority_phase`
  4. Directly set `signal.color = SignalColor.GREEN`
  5. Reset `signal.time_in_phase = 0.0`
  6. Clear `signal._pending_phase = None`
  7. Set `action = None` — bypasses normal RL/fixed signal logic entirely
- Emergency vehicle passes through with siren lights (red/blue alternating emissive + point lights)
- When last emergency vehicle exits (`state == "passed"`), `emergency_override_lane` is cleared and normal control resumes
- Only one emergency vehicle per direction at a time

**User Flow:** Click "Emergency" button for a direction → watch emergency vehicle spawn → see signals change → ambulance clears intersection.

**Priority:** ★★★☆☆ (showcase feature)

### 2.14 Configurable Traffic Flow

**What:** Slider to adjust vehicle arrival rate.

**How It Works:**
- Poisson distribution spawner (default λ = 0.3)
- Slider range: 0.1–1.0
- 50% straight, 25% left, 25% right turn probability
- Max 10 vehicles per lane
- Spawns into one random direction per tick

**User Flow:** Drag slider → see traffic density change immediately.

**Priority:** ★★★☆☆

### 2.15 Keep-Alive Ping

**What:** Prevents backend cold-start on free-tier hosting.

**How It Works:**
- Frontend `KeepAlivePing` component pings `/api/keep-alive` on mount
- The Next.js API route forwards to FastAPI `/health`
- Replaced an earlier Vercel cron job approach

**Priority:** ★★☆☆☆ (infrastructure)

### 2.16 Dark Theme UI with Day/Night 3D Mode

**What:** Comprehensive dark mode with cyberpunk aesthetic + **NEW** Day/Night toggle for 3D scene.

**How It Works:**
- Tailwind v4 custom CSS variables for light/dark
- Semi-transparent glassmorphism panels (backdrop-blur)
- Animated borders, glow effects, floating holographic queue labels
- **3D Scene:** Day mode = bright sky, emissive sun with rays, high ambient; Night mode = dark sky, moody directional lights, bloom
- Consistent across all pages

**Priority:** ★★★☆☆

**Priority:** ★★★☆☆

---

### 2.17 Frontend 3D Vehicle Interpolation & Path Algorithms

This section documents the core algorithms for smooth 60 FPS vehicle rendering from 10 Hz WebSocket updates, including Three.js `CurvePath` construction, piecewise arclength parameterization, and temporal interpolation.

#### 2.17.1 CurvePath Construction (`Vehicle.tsx` / `CityVehicle.tsx`)

Each vehicle follows a parametric curve composed of straight segments and quadratic Bézier curves for turns:

```typescript
function buildCurve(lane: string, turn: "straight" | "left" | "right", 
                    SPAWN_DIST: number, EXIT_DIST: number): CurvePath<Vector3> {
    const path = new CurvePath<Vector3>();
    const STOP = 3.5;                    // Distance from intersection center to stop line
    const off = turn === "left" ? 0.5 :  // Lateral offset per lane
                turn === "straight" ? 1.5 : 2.5;
    
    let start, enter, exit, end, control;
    
    switch (lane) {
        case "north":  // Vehicle traveling South (+Z)
            start = new Vector3(-off, Y, -SPAWN_DIST);
            enter = new Vector3(-off, Y, -STOP);
            if (turn === "straight") {
                exit = new Vector3(-off, Y, STOP);
                end = new Vector3(-off, Y, EXIT_DIST);
                control = new Vector3(-off, Y, 0);
            } else if (turn === "right") {  // West
                exit = new Vector3(-STOP, Y, -off);
                end = new Vector3(-EXIT_DIST, Y, -off);
                control = new Vector3(-off, Y, -off);
            } else {  // left -> East
                exit = new Vector3(STOP, Y, off);
                end = new Vector3(EXIT_DIST, Y, off);
                control = new Vector3(-off, Y, off);
            }
            break;
        // ... similar for south, east, west
    }
    
    // Straight: line segment from enter to exit
    // Turn: quadratic Bézier from enter to exit via control point
    path.add(new LineCurve3(start, enter));
    if (turn === "straight") {
        path.add(new LineCurve3(enter, exit));
    } else {
        path.add(new QuadraticBezierCurve3(enter, control, exit));
    }
    path.add(new LineCurve3(exit, end));
    return path;
}
```

**Key Parameters:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `STOP` | 3.5 | Distance from center to stop line |
| Lane offsets | 0.5 / 1.5 / 2.5 | Left / Straight / Right lane lateral position |
| `Y` | 0.12 | Vehicle height above ground |

#### 2.17.2 Piecewise Arclength Parameterization

Backend provides position ∈ [0, 1] (0 = spawn, 1 = passed). Frontend maps this to CurvePath parameter:

```typescript
// Precompute total curve length and stop parameter
const t_stop = (SPAWN_DIST - STOP) / curve.getLength();

// In useFrame (runs at display refresh rate, ~60 Hz):
const elapsed = time - lastUpdateTime;
const progress = Math.min(1.0, elapsed / updateInterval);

let t = startT + (targetT - startT) * progress;  // Interpolate backend position
t = Math.min(Math.max(t, 0), 0.999);

let t_visual;
if (t <= 0.42) {  // Before stop line
    t_visual = (t / 0.42) * t_stop;
} else {           // Through intersection
    t_visual = t_stop + ((t - 0.42) / 0.58) * (1.0 - t_stop);
}
t_visual = Math.min(Math.max(t_visual, 0), 0.999);

const targetPos = curve.getPointAt(t_visual);
const tangent = curve.getPointAt(tAhead).sub(targetPos).normalize();
const targetRot = Math.atan2(tangent.x, tangent.z);
```

**Mapping Logic:**
- Backend [0, 0.42] → approach to stop line → maps to visual [0, t_stop]
- Backend [0.42, 1.0] → through intersection → maps to visual [t_stop, 1.0]
- Ensures vehicle stops exactly at visual stop line when backend position = 0.42

#### 2.17.3 Smooth Temporal Interpolation (60 FPS from 10 Hz)

```typescript
// In useFrame (runs every frame at ~60 Hz):
if (vehicle.position !== lastTargetTRef.current) {
    const actualInterval = time - lastUpdateTime.current;
    updateInterval.current = Math.min(Math.max(actualInterval, 0.05), 2.0);
    
    startTRef.current = lastVisualTRef.current;
    lastTargetTRef.current = vehicle.position;
    lastUpdateTime.current = time - delta;
}

const elapsed = time - lastUpdateTime.current;
const progress = Math.min(1.0, elapsed / updateInterval.current);

let t = startTRef.current + (vehicle.position - startTRef.current) * progress;
t = Math.min(Math.max(t, 0), 0.999);
// ... then map to t_visual as above
```

**Algorithm Details:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `min interval` | 0.05s | Prevents jitter from rapid updates |
| `max interval` | 2.0s | Handles network stalls gracefully |
| `rotation smoothing` | `dRot * min(1, delta * 15)` | Smooth heading changes |

#### 2.17.4 Road Vehicle Linear Interpolation (`CityVehicle.tsx`)

Road vehicles (between intersections) use simple linear world-space interpolation with lateral lane offset:

```typescript
// In useFrame for road vehicles:
const elapsed = time - lastUpdateTime.current;
const progress = Math.min(1.0, elapsed / updateInterval.current);

const x = startX + (targetX - startX) * progress;
const z = startZ + (targetZ - startZ) * progress;

// Heading from velocity vector
const dx = targetX - startX, dz = targetZ - startZ;
const distance = sqrt(dx*dx + dz*dz);
if (distance > 0.005) {
    targetAngle = atan2(dx, dz);
}

// Smooth rotation
if (smoothRotRef.current === null) smoothRotRef.current = targetAngle;
let dRot = targetAngle - smoothRotRef.current;
while (dRot > PI) dRot -= 2*PI;
while (dRot < -PI) dRot += 2*PI;
smoothRotRef.current += dRot * min(1, delta * 12);

// Lateral offset based on turn (smooth transition)
const offStart = turn === "left" ? 0.5 : turn === "straight" ? 1.5 : 2.5;
const offEnd = nextTurn === "left" ? 0.5 : nextTurn === "straight" ? 1.5 : 2.5;
const currentOff = offStart + (offEnd - offStart) * visualProgress;
const finalX = x + latX * currentOff;
const finalZ = z + latZ * currentOff;
```

---

### Feature Flags / Gated Functionality

None currently implemented. All features are accessible to all users.

---

## 3. System Operations & Workflows

### 3.1 Key User Journeys

#### Journey A: Observe Traffic Simulation
1. Navigate to `/simulation`
2. 3D scene renders immediately (static, no vehicles)
3. Click **Start** — vehicles begin spawning and moving
3. Watch queue lengths, wait times, and throughput on the right panel
4. Click **Stop** — simulation pauses, metrics finalized
5. Click **Reset** — intersection clears

#### Journey B: Compare Fixed vs AI vs Manual Control
1. Start simulation in **Fixed mode** → let it run → Stop
2. Toggle to **AI mode** → Start again → let it run → Stop
3. Toggle to **Manual mode** → Start → use phase buttons to control → Stop
4. Switch to **Compare tab** → side-by-side bar chart shows wait time and throughput for all modes
5. Improvement percentages displayed if data exists

#### Journey C: Train the AI Agent
1. Ensure backend is running and WebSocket connected
2. Click **Train Agent** button
3. Configure episode count in the modal (default 500)
4. Watch live metrics stream in: reward, avg wait, epsilon, loss
5. Training chart builds episode by episode
6. Every 50 episodes: checkpoint auto-saved, model metadata persisted
7. After training completes → go to **History** tab → browse episodes
8. Click **Load Model** → select checkpoint → run AI mode inference

#### Journey D: Emergency Preemption
1. Start simulation (any mode)
2. Click one of 4 **Emergency buttons** (N/S/E/W)
3. Emergency vehicle spawns with siren (red/blue lights)
4. Signal immediately switches to priority green
5. Vehicle passes through intersection
6. Normal control resumes

#### Journey E: Manual Control
1. Select **Manual** mode from the three-way toggle
2. Four phase buttons appear: NS Green, EW Green, NS Left, EW Left
3. Click a button → signal transitions through yellow (2s) → red (3s) → green for selected phase
4. Signal holds that green indefinitely until next manual override
5. Yield-on-left logic still applies during green phases

### 3.2 Background Jobs / Scheduled Operations

| Task | Trigger | Frequency | Description |
|---|---|---|---|
| **Simulation loop** | WebSocket first client connect | Continuous (~10 Hz) | Physics tick, vehicle movement, signal logic |
| **Training loop** | User starts training | Per-episode (~100ms each) | DQN training, reward calc, network updates |
| **DB sampling** | Every 50 simulation ticks | ~5s | Sample traffic_log + signal_state row for buffer |
| **DB buffer flush** | Every 10 samples (10×5s = 10 samples) | ~50s during simulation | Bulk insert buffered traffic logs + signal states to Supabase (reduces round-trips) |
| **Checkpoint save** | Every 50 episodes | During training | Save model state dict to Supabase Storage + disk |
| **Target network sync** | Every 300 steps | During training | Copy online DuelingDQNNetwork weights to target network for stable Double DQN targets |
| **Agent weight sync** | Every 50 episodes | During training | Copy training_agent online_net → sim_agent online_net for live inference |
| **PER beta annealing** | Every episode | Each step | Linearly anneal importance-sampling weight β from 0.4 → 1.0 over total episodes |
| **PER priority update** | Every train step | During training | Update SumTree leaf priorities with new |TD-error| from loss computation |
| **Keep-alive ping** | Frontend mount | Once on page load | Wake backend from cold start |

### 3.3 Data Flows

#### Real-Time Simulation Flow
```
Backend (Intersection.tick)
  │
  ├── Fixed mode: tick(action=None, is_manual=False)
  ├── AI mode: 
  │     _build_obs_from_intersection() → 20-dim obs
  │     ├── Note: sim_ws uses simplified pressure_norm=0.0 for inference
  │     │   vs training_env._get_obs() which computes full pressure_norm from _compute_movement_pressures()
  │     → sim_agent.select_action(state, ε=0) → action
  │     → training_env.compute_reward(prev_pressures, curr_pressures, ...)
  │     → tick(action=selected, is_manual=False)
  │     → build_frame() with Q-values, obs, reward, action, exploration_flag
  └── Manual mode: tick(action=None, is_manual=True)
       │
       │ [10 Hz]
       ▼
  WebSocket broadcast (SimulationFrame JSON)
       │
       ▼
  Frontend Three.js render (60 fps interpolation)
       │
       │ [every 50 ticks = ~5s]
       ▼
  DB Buffer (traffic_logs + signal_states) ──[every 10 samples = ~50s]──▶ Supabase PostgreSQL
```

#### Training Flow
```
training_agent (ε-greedy select_action)
    → Environment (step with hard constraints: max_green / starvation override)
    → PER Buffer (push with max priority)
         │
    [every 2 steps, if buffer ≥ 2000]
         ▼
    PER Sample (stratified over SumTree segments, IS weights)
    → Dueling Double DQN Train Step:
        - Online net selects best next action
        - Target net evaluates that action
        - PER-weighted SmoothL1Loss
        - Gradient clip (max_norm=10)
        - Update PER priorities using |TD-error|
         │
    [every 300 steps] → sync target_network ← online_net
         │
    [every 50 episodes]
         ▼
    Save Checkpoint → Supabase Storage (online + target + optimizer + step_count)
    Save Metadata  → rl_models table (reuse simulation_id as PK, upsert)
    SYNC sim_agent weights ← training_agent weights
    Broadcast "checkpoint_saved" → Training WebSocket
```

#### API Data Flow (Read Path)
```
User clicks tab ──▶ Next.js API Route ──▶ Prisma ──▶ Supabase PostgreSQL ──▶ JSON Response
```

### 3.4 Integration Points

| Integration | Type | Direction | Data |
|---|---|---|---|
| **Supabase PostgreSQL** | Database (REST via supabase-py) | Backend writes, Frontend reads (via Prisma) | Simulations, episodes, metrics, models, logs |
| **Supabase Storage** | File storage (REST via supabase-py) | Backend read/write | Model checkpoint `.pt` files |
| **Vercel** | Hosting | Static/Frontend deployment | Next.js app |
| **Render** | Hosting | Docker deployment | FastAPI backend |

---

## 4. API & Interface Summary

### 4.1 REST Endpoints (FastAPI)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/` | Root health check | — | `{"status": "ok", "service": "FlowSync API"}` |
| `GET` | `/health` | Health check | — | `{"status": "ok"}` |
| `POST` | `/simulation/start` | Start a new simulation | — | `{"simulation_id": "..."}` |
| `POST` | `/simulation/stop` | Stop current simulation | — | `{"status": "stopped"}` |
| `POST` | `/simulation/reset` | Reset intersection state | — | `{"status": "reset"}` |
| `PUT` | `/simulation/mode` | Toggle fixed/ai/manual mode | `{"mode": "fixed" \| "ai" \| "manual"}` | `{"mode": "..."}` |
| `GET` | `/simulation/status` | Current metrics snapshot | — | MetricsSnapshot |
| `POST` | `/training/start` | Start training | `{"num_episodes": 500, "simulation_id": "..."}` | `{"status": "started", "simulation_id": "..."}` |
| `POST` | `/training/stop` | Stop training | — | `{"status": "stopping"}` |
| `GET` | `/training/status` | Training state | — | `{"is_training": bool, "current_episode": int, "epsilon": float}` |
| `GET` | `/training/models` | List all saved models | — | `{"models": [...]}` |
| `POST` | `/training/load` | Load a model checkpoint | `{"model_id": "..."}` | `{"status": "loaded", "episode": int}` |
| `GET` | `/metrics/current` | Current metrics snapshot | — | MetricsSnapshot |

### 4.2 Next.js API Routes (Frontend → DB)

| Method | Path | Description | Query Params |
|---|---|---|---|
| `GET` | `/api/simulations` | List recent simulations | — (returns 20 most recent) |
| `GET` | `/api/models` | List RL models | — (descending by creation) |
| `GET` | `/api/metrics` | Performance metrics | `?simulationId=...` (max 100) |
| `GET` | `/api/episodes` | Training episodes | `?simulationId=...` (max 500) |
| `GET` | `/api/keep-alive` | Ping backend health | — |

### 4.3 WebSocket Endpoints

**`/ws/simulation`** — Bidirectional
- **Server → Client (10 Hz):** `SimulationFrame` JSON — `timestep`, `mode`, `signal` (current_phase, color_per_lane dict, is_transitioning), all `vehicles` (id, lane, turn, position, wait_time, speed, state, is_emergency), `queues` (per-lane QueueState with length field), `metrics` (avg_wait_time, throughput_total), `rl` (Q-values list, action, reward, epsilon, exploration_flag)
  - **Client-side flattening** (`useSimulationSocket.ts`):
    - `queue_lengths` extracted from nested `queues` dict (each QueueState → `.length`)
    - `signal_color` derived: if `signal.is_transitioning` → check per-lane colors for yellow/red; else → "green"
    - `signal_phase` = `signal.current_phase`
- **Client → Server (commands):**
  - `{"command": "start"}`
  - `{"command": "stop"}`
  - `{"command": "reset"}`
  - `{"command": "set_mode", "mode": "fixed" \| "ai" \| "manual" \| "greedy"}`
  - `{"command": "set_spawn_rate", "value": 0.1-1.0}`
  - `{"command": "emergency_override", "lane": "north"\|"south"\|"east"\|"west"}`
  - `{"command": "manual_override", "phase": 0-3}`
- **Command validation:** `COMMAND_SCHEMAS` dict defines required fields and types per command; `validate_ws_command()` rejects unknown commands and invalid types
  ```python
  COMMAND_SCHEMAS = {
      "set_mode": {"mode": str},
      "set_spawn_rate": {"value": float},
      "emergency_override": {"lane": str},
      "manual_override": {"phase": int},
  }
  ```
  Commands without schema (`start`, `stop`, `reset`) accept no parameters. Type coercions are tried at validation time, and invalid types return a descriptive error message rather than crashing the connection.

**`/ws/city`** — Bidirectional **(NEW: Multi-Intersection City Grid)**
- **Server → Client (10 Hz):** `CityFrame` JSON — `timestep`, `mode` (fixed/greedy/ai), `city_metrics` (avg_wait_time, total_throughput, active_vehicles, road_vehicles, congestion_level, worst/best_intersection), `intersections` (dict keyed by "A"/"B"/"C"/"D" with signal state, queue lengths, avg_wait, vehicles, Q-values, grid_x/grid_z), `road_vehicles` (id, from_intersection, to_intersection, progress, world_x, world_z, prev_turn, next_turn), `comparison_progress` (running, current_mode, elapsed, total, mode_index, total_modes)
  - **Comparison Benchmark:** Automated sequential Fixed→Greedy→AI run (30s each); broadcasts `comparison_phase` on mode switch and `comparison_results` (avg_wait_time, throughput per mode) on completion
- **Client → Server (commands):**
  - `{"command": "start"}`
  - `{"command": "stop"}`
  - `{"command": "reset"}`
  - `{"command": "set_mode", "mode": "fixed" \| "greedy" \| "ai"}`
  - `{"command": "set_spawn_rate", "value": 0.05-2.0}` (city-wide rate, distributed across 8 entry points)
  - `{"command": "run_comparison"}` — triggers automated 3-mode benchmark
- **Command validation:** `CITY_COMMAND_SCHEMAS` with `set_mode` and `set_spawn_rate` schemas; unknown commands rejected with descriptive error

**`/ws/training`** — Bidirectional
- **Server → Client (per episode):** `TrainingMetric` JSON — episode, reward, avg wait, throughput, epsilon, loss, is_training
- **Server → Client (checkpoint):** `{"type": "checkpoint_saved", "model_id": "...", "episode": N}`
- **Client → Server:**
  - `{"command": "start_training", "num_episodes": 500}`
  - `{"command": "stop_training"}`

### 4.4 Authentication & Authorization

**None.** The application does not implement authentication. The Supabase service key is used server-side only and is never exposed to the client. The config validates that the key is a `service_role` key (not anon/publishable) and raises clear errors for misconfigured keys.

### 4.5 Rate Limiting

**None implemented.** This is a single-user demo application. The sampling strategy for DB writes (~1 row per 5s, flushed every 50s) naturally limits database load.

### 4.6 Webhooks / Event System

**None.** All real-time communication is via WebSocket. There is no webhook or event bus.

---

## 5. Data Model & Storage

### 5.1 Database Schema (Prisma: `client/prisma/schema.prisma`)

#### Entity Relationship Diagram

```
Simulation
  ├── id            (String, PK, cuid)
  ├── createdAt     (DateTime)
  ├── updatedAt     (DateTime) — **NEW**
  ├── mode          (String: "fixed" | "ai" | "manual")
  ├── status        (String: "running" | "completed" | "stopped")
  ├── totalSteps    (Int)
  └── durationMs    (Int)
  │
  ├──< Episode (1:N)
  │     ├── id            (String, PK)
  │     ├── simulationId  (FK → Simulation)
  │     ├── episodeNumber (Int)
  │     ├── totalReward   (Float)
  │     ├── avgWaitTime   (Float)
  │     ├── throughput    (Int)
  │     ├── epsilon       (Float)
  │     ├── loss          (Float?)
  │     └── steps         (Int)
  │
  ├──< PerformanceMetric (1:N)
  │     ├── id             (String, PK)
  │     ├── simulationId   (FK → Simulation)
  │     ├── mode           (String)
  │     ├── avgWaitTime    (Float)
  │     ├── throughput     (Int)
  │     ├── maxQueueLength (Int)
  │     ├── totalSteps     (Int)
  │     └── improvementPct (Float?)
  │
  └──< TrafficLog (1:N)
        ├── id              (String, PK)
        ├── simulationId    (FK → Simulation)
        ├── timestep        (Int)
        ├── vehiclesSpawned (Int)
        ├── vehiclesPassed  (Int)
        ├── avgWaitTime     (Float)
        └── maxQueueLength  (Int)

SignalState (standalone)
  ├── id           (String, PK)
  ├── simulationId (String — FK with Cascade) — **NEW**
  ├── timestep     (Int)
  ├── phase        (Int: 0-3)
  ├── duration     (Int)
  ├── queueNorth   (Int)
  ├── queueSouth   (Int)
  ├── queueEast    (Int)
  └── queueWest    (Int)

RLModel (standalone)
  ├── id            (String, PK)
  ├── name          (String)
  ├── version       (String)
  ├── storagePath   (String — Supabase Storage path)
  ├── avgReward     (Float)
  ├── epsilon       (Float)
  ├── totalEpisodes (Int)
  ├── createdAt     (DateTime)
  └── isActive      (Boolean, default false)
  └── @@unique([name, version]) — **NEW**

```

#### Key Relationships
- **Simulation 1:N Episode** — Each simulation can have many training episodes
- **Simulation 1:N PerformanceMetric** — Each simulation creates one performance metric per mode
- **Simulation 1:N TrafficLog** — Sampled traffic data per timestep
- **Simulation 1:N SignalState** — **NEW FK with Cascade**
- **RLModel** — Standalone; model_id reuses simulation UUID; unique constraint on (name, version)

### 5.2 Database Write Strategy

- **Episodes:** Written once per episode during training (sync via `asyncio.to_thread`)
- **TrafficLogs + SignalStates:** Sampled every 50 simulation ticks (~5s), buffered, flushed every 10 samples (~50s) via bulk insert
- **PerformanceMetrics:** Written once when a simulation is stopped
- **RLModel metadata:** Upserted at checkpoint time (every 50 episodes); uses simulation UUID as primary key to avoid duplicate rows
- **Simulations:** Created on start, updated on stop

### 5.3 File Storage

| Bucket | Content | Access Pattern |
|---|---|---|
| `model-checkpoints` (Supabase Storage) | PyTorch state dict `.pt` files | Backend write on checkpoint; read on model load |
| Local disk (`server/models/`) | Same `.pt` files (fallback) | Development/offline use |

**Storage path format:** `models/{simulation_id}/checkpoint_{episode}.pt`

### 5.4 Caching Strategy

**None implemented.** The frontend TanStack Query's default caching handles some API calls. No Redis, in-memory cache, or CDN caching is configured.

### 5.5 Search Indexing

**None.** No full-text search or indexing beyond PostgreSQL default B-tree indexes on primary keys.

### 5.6 Data Retention & Privacy

- No user accounts or PII collected
- Simulation data persists indefinitely (no retention policy configured)
- Supabase project is on free tier (500 MB database, 1 GB storage)
- No data anonymization or deletion mechanisms implemented

---

## 6. Deployment & Infrastructure

### 6.1 Hosting Environment

| Component | Provider | Region | Tier |
|---|---|---|---|
| **Frontend** | Vercel | Auto (default) | Free/Hobby |
| **Backend** | Render | Auto | Free (spins down after inactivity) |
| **Database** | Supabase | Auto | Free |

**Production URLs:**
- Frontend: `https://flowsyncc.vercel.app` (or `https://flowsync.vercel.app`)
- Backend: `https://flowsync-gelt.onrender.com`

### 6.2 CI/CD Pipeline

**No automated CI/CD.** Deployment is manual:
- Frontend: Connected Vercel git repo → auto-deploys on push to main
- Backend: Connected Render git repo → auto-deploys on push to main (Docker)
- No GitHub Actions, no test runners in CI

### 6.3 Local Development

**Frontend:**
```bash
cd client && pnpm install && pnpm dev
# → http://localhost:3000
```

**Backend:**
```bash
cd server && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
```

**Docker (backend only):**
```bash
docker-compose up
# Builds from server/Dockerfile, runs on :8000
```

### 6.4 Environment Variables

**Frontend** (`client/.env.local`):
- `DATABASE_URL` — Supabase PostgreSQL direct connection
- `DIRECT_URL` — Supabase direct connection (for migrations)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_FASTAPI_HTTP_URL` — defaults to `http://localhost:8000`
- `NEXT_PUBLIC_FASTAPI_WS_URL` — defaults to `ws://localhost:8000`

**Backend** (`server/.env`):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (aliases: `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KEY`)
- `CORS_ORIGINS` — comma-separated (defaults include localhost:3000 and Vercel URLs)
- `SIGNAL_RED_DURATION` — all-red clearance seconds (default: 3.0)

### 6.5 Monitoring, Logging, Alerting

| Aspect | Implementation |
|---|---|
| **Backend logging** | Python `logging` module throughout; all DB failures logged with `logger.exception` |
| **Frontend logging** | `console.log` with styled prefixes (`[SimWS]`, `[TrainWS]`) for WebSocket events |
| **Metrics** | No external monitoring (no Sentry, DataDog, etc.) |
| **Alerting** | None |

### 6.6 Scaling Strategy

**Current state:** Single-process, single-thread, single-CPU. The async design with `asyncio.sleep(0)` prevents WebSocket starvation.

**Future scaling considerations:**
- Backend: Could use multiple workers (gunicorn + uvicorn workers) for multi-core
- Database: Supabase auto-scales with plan upgrade
- Frontend: Vercel auto-scales edge functions
- **Key bottleneck:** Training is CPU-bound (PyTorch); distributed training would require `torch.distributed` or Ray

---

## 7. Known Issues & Technical Debt

### 7.1 Current Bugs & Limitations

| Issue | Severity | Details |
|---|---|---|
| **Free-tier cold starts** | Medium | Render spins down after 15 min inactivity. First request takes ~30s. Keep-alive helps but isn't perfect. |
| **Single-process bottleneck** | Medium | Training blocks the event loop despite `asyncio.sleep(0)` — no GPU acceleration. |
| **No WebSocket auth** | Low | Any client can connect to `/ws/simulation` and `/ws/training`. Fine for demo but not production. |
| **DB buffer loss on crash** | Low | If the server crashes between flushes (~50s window), buffered traffic logs are lost. |
| **Prisma migrations in CI** | Low | DB schema must be applied manually via `prisma db push`. |
| **No input validation on spawn rate** | Low | Slider is 0.1–1.0 but WS handler does `float(value)` without clamp (now fixed in WS handler). |

### 7.2 Planned Refactors & Migrations

| Item | Status | Notes |
|---|---|---|
| **Multi-intersection support** | Planned (long-term) | Currently single 4-way intersection. Would need environment refactor. |
| **GPU training support** | Planned (medium-term) | Currently CPU-only PyTorch. CUDA support blocked by Render free tier. |
| **GraphQL API** | Not planned | REST + WebSocket covers all needs. |
| **Frontend monorepo extraction** | Not planned | pnpm workspace already clean. |

### 7.3 Security Considerations

| Concern | Status | Mitigation |
|---|---|---|
| **Supabase service key exposure** | ✅ Mitigated | Key validated as service_role, never sent to client. |
| **CORS** | ✅ Mitigated | Configurable allowlist + regex fallback. |
| **CSRF** | ✅ N/A | No cookies or auth tokens. Stateless API. |
| **WS message validation** | ⚠️ Partial | JSON parsed; commands validated by if-else chain. No schema validation on WS messages. |
| **Rate limiting** | ❌ Missing | No protection against WS message flooding. |
| **SQL injection** | ✅ Mitigated | No raw SQL — supabase-py and Prisma use parameterized queries. |
| **Dependency vulnerabilities** | ⚠️ Unknown | No automated scanning (Dependabot, Snyk). |

---

## 8. Team & Ownership

### 8.1 Maintainers

**Solo project.** No explicit ownership assignments. Based on git history and commit patterns, the project appears to be maintained by a single developer.

### 8.2 Documentation Locations

| Document | Location | Description |
|---|---|---|
| **README** | `README.md` | Project overview, features, tech stack, getting-started guide |
| **Internal Docs** | `client/DOCUMENTATION.md` | Developer-oriented: "Cycle of Intelligence" workflow, project structure map |
| **Pitch Script** | `pitch.md` | 4-role team pitch with glossary |
| **Presentation Outline** | `ppt.txt` | 8-slide technical presentation |
| **Supabase Setup Guide** | `server/SUPABASE_KEYS_SETUP.txt` | Key setup instructions |
| **API Docs (auto)** | `/docs` (FastAPI Swagger) | Automatic OpenAPI documentation |
| **This Summary** | `docs/Summary.md` | Comprehensive project analysis |
| **Issues Audit** | `ISSUES.md` | Full-stack audit findings |

### 8.3 Onboarding Notes for New Developers

1. **Start with README.md** for project overview and setup instructions
2. **Read client/DOCUMENTATION.md** for internal architecture understanding
3. **Set up Supabase** first (database + storage bucket)
4. **Run backend before frontend** — the frontend depends on WebSocket connections
5. **Use `pnpm` not `npm`** for frontend (pnpm-lock.yaml, pnpm-workspace.yaml)
6. **Python 3.11.9** is pinned — other versions may have compatibility issues
7. **Check python-dotenv** — backend loads from `server/.env` automatically
8. **CPU-only PyTorch** — don't expect GPU training on Render free tier
9. **First request is slow** (~30s cold start on Render)
10. **Tests:** Run `cd server && pytest` (pytest, pytest-asyncio, pytest-cov, httpx, pytest-mock required)

---

## 9. Future Roadmap

### 9.1 Upcoming Features (Speculative)

Based on the pitch and presentation materials:

| Feature | Timeline | Notes |
|---|---|---|
| **Multi-Agent RL** | Long-term | Coordinate multiple intersections for "Green Wave" synchronization |
| **V2X Integration** | Long-term | Communicate directly with smart vehicles for precision control |
| **Edge Deployment** | Long-term | Run AI core on local traffic controller hardware |
| **GPU Training** | Medium-term | Enable CUDA for faster training |
| **3D model enhancements** | Short-term | More vehicle types, pedestrian models, weather effects |
| **Multi-intersection view** | Long-term | City-wide traffic management |

### 9.2 Deprecation Plans

**None documented.** No deprecated features or end-of-life plans.

### 9.3 Long-Term Vision

From `ppt.txt`:
> FlowSync demonstrates that Reinforcement Learning can significantly outperform static traffic systems, reducing wait times and environmental impact. Future expansion targets multi-agent RL for city-wide coordination, V2X communication, and edge deployment on traffic controller hardware.

---

## 10. File-by-File Code Summary

### Root-Level

| File | Purpose |
|---|---|
| `README.md` | Project landing page — overview, features, tech stack, setup guide |
| `pnpm-workspace.yaml` | Declares `client/` as pnpm workspace package |
| `docker-compose.yml` | Single-service Docker Compose for FastAPI backend on port 8000 |
| `render.yaml` | Render deployment config — Python runtime, CPU-only PyTorch, uvicorn start |
| `runtime.txt` | Pins Python version to 3.11.9 |
| `.gitignore` | Ignores `.kiro/`, `.vscode/`, `.agents/`, node_modules, __pycache__, .env, *.pt, models/, venv/ |
| `pitch.md` | Team pitch script (4 roles + technical deep-dive + glossary) |
| `ppt.txt` | 8-slide presentation outline (abstract, modules, requirements, architecture/ER diagrams, algorithms, working, features, future scope) |
| `ISSUES.md` | Full-stack audit findings (17 issues across 7 layers) |
| `fixes.md` | Complete step-by-step fix plan (9 fixes, 90+ tasks) |

### Client Config Files

| File | Purpose |
|---|---|
| `package.json` | Dependencies: Next.js 16, React 19, Three.js, Tailwind v4, shadcn/ui, Zustand, TanStack Query, Recharts, Framer Motion |
| `next.config.ts` | Image optimization, env defaults (production backend URL), strict mode, compression |
| `tsconfig.json` | TypeScript config: ES2017 target, strict mode, `@/` → `./src/*` alias |
| `postcss.config.mjs` | PostCSS with `@tailwindcss/postcss` |
| `eslint.config.mjs` | ESLint v9 flat config (Next.js core-web-vitals + TS presets) |
| `components.json` | shadcn/ui config: Nova style, RSC enabled, neutral base, lucide icons |
| `prisma/schema.prisma` | Database schema with 6 models (Simulation, Episode, SignalState, TrafficLog, RLModel, PerformanceMetric) |
| `next-env.d.ts` | Auto-generated Next.js type references |

### Client Source Files

| File | Purpose |
|---|---|
| `src/app/globals.css` | Tailwind v4 with custom theme variables (light/dark), shadcn/ui integration, scrollbar styles |
| `src/app/layout.tsx` | Root layout — Geist fonts, TooltipProvider, KeepAlivePing, QueryClient Provider |
| `src/app/providers.tsx` | Client component — initializes TanStack React Query's QueryClient |
| `src/app/page.tsx` | Landing page — hero, "How it works" (Simulate-Train-Compare), feature cards, tech stack, CTA |
| `src/app/simulation/page.tsx` | **UPDATED** Main dashboard — side-by-side layout: left 3D canvas with floating `LiveSnapshot`, right sidebar (Controls card with SimulationControls + TrainingControls, Real-time Metrics, Analytics tabs: Training/Compare/History). |
| `src/app/api/simulations/route.ts` | GET — returns 20 most recent simulations via Prisma |
| `src/app/api/models/route.ts` | GET — returns all RL models (descending by creation) via Prisma |
| `src/app/api/metrics/route.ts` | GET — returns performance metrics, optional `?simulationId` filter (max 100) |
| `src/app/api/episodes/route.ts` | GET — returns episodes, optional `?simulationId` filter (max 500) |
| `src/app/api/keep-alive/route.ts` | GET — pings FastAPI `/health` to prevent backend cold start |
| `src/types/simulation.ts` | TypeScript interfaces: `SimulationMode` (includes `"manual"`), `VehicleState`, `SimulationFrame`, `TrainingMetric` |
| `src/store/simulationStore.ts` | Zustand store — connection/running/training state, current frame, training metrics (capped at 1000), action methods |
| `src/lib/utils.ts` | `cn()` class merging, `getFastApiUrls()` — environment-aware backend URL resolution (no hardcoded URLs) |
| `src/lib/prisma.ts` | Singleton PrismaClient (prevents hot-reload connection leaks) |

#### Hooks

| File | Purpose |
|---|---|
| `src/hooks/useSimulationSocket.ts` | **UPDATED** WebSocket hook for `/ws/simulation` — extracts `queue_lengths` from nested `QueueState` dict (per-lane `length` field), derives `signal_color` from `is_transitioning` flag + per-lane color values, flattens raw frame into `SimulationFrame` interface, exponential backoff retry (max 5). |
| `src/hooks/useTrainingSocket.ts` | WebSocket hook for `/ws/training` — same reconnect strategy, handles training metric streaming |
| `src/hooks/useSimulations.ts` | React Query hook — fetches `/api/simulations` |
| `src/hooks/useEpisodes.ts` | React Query hook — fetches episodes, auto-refresh every 10s |

#### Control Components

| File | Purpose |
|---|---|
| `src/components/controls/SimulationControls.tsx` | **UPDATED** Three-mode toggle (Fixed/Manual/AI) with debounce, Start/Stop/Reset buttons, vehicle arrival rate slider, emergency vehicle preemption panel (4 directional buttons + active status display), connection/running status indicator |
| `src/components/controls/TrainingControls.tsx` | Training panel with Train Agent button (config modal 1-2000 episodes), live training metrics display with animated stat cards (reward, avg wait, epsilon, loss), progress bar + ETA + episodes/min speed, Load Model dropdown (fetches from `/training/models`), model loading with success/error feedback |

#### Simulation (3D) Components

| File | Purpose |
|---|---|
| `src/components/simulation/SimulationCanvas.tsx` | **UPDATED** Three.js canvas setup — orthographic camera, Day/Night mode toggle (changes ambient/directional/hemisphere lights, sun sphere with emissiveIntensity=8 for day), `MeshPhysicalMaterial` environment, `Environment` preset ("city"), `ContactShadows`, `OrbitControls` with `autoRotate={false}`, Bloom postprocessing (luminance threshold varies by time of day), dynamic status indicator (ready/connected colors), bottom legend overlay. |
| `src/components/simulation/IntersectionScene.tsx` | **UPDATED** Main 3D scene: `resolveLightColor()` maps phase+color to left-turn signals ("left-green"/"left-yellow"); `QueueLabel` billboard holograms with dark backing plate + glow border + color-coded value (cyan ≤4, yellow 5-7, red ≥8); 4 phase-aware traffic lights; vehicles from frame. |
| `src/components/simulation/IntersectionGrid.tsx` | **MAJOR UPDATE** Ground plane: `MeshPhysicalMaterial` (color #0f111a, clearcoat 0.2, metalness 0.3, roughness 0.7). 4 corner zones: NW/SE parks with concrete curb + grass + `LowPolyTree` components (Cylinder trunk + stacked Box foliage with emissive); NE/SW city blocks with `Skyscraper` components (MeshPhysicalMaterial clearcoat 1.0, metalness 0.9, reflectivity 1.0 + neon corner stripes emissiveIntensity 3.5). |
| `src/components/simulation/Road.tsx` | **UPDATED** 3-lane roads (40 units long, 6 units wide) with: asphalt base, double yellow center lines (split at intersection), white stop bars (6 units wide), zebra crossing stripes, directional text labels (EASTBOUND, WESTBOUND, SOUTHBOUND, NORTHBOUND) |
| `src/components/simulation/TrafficLight.tsx` | **MAJOR UPDATE** Cantilever pole + bracket arm; 3D lens spheres with emissive glow + arrow text ("←" for left phases, "↑ →" for straight/right); smooth emissive lerp via `useFrame`; dynamic point light per color (intensity 2.0, distance 8); CCTV camera (body/visor/lens/LED with blinking status LED 0.4s every 1.2s); direction-specific offsets; cleanup disposal in useEffect. |
| `src/components/simulation/Vehicle.tsx` | **UPDATED** 3D vehicle system with: 6 types (sedan, suv, hatchback, sportscar, bike, ambulance), hash-based color diversity, **CurvePath-based paths** (LineCurve3 for straight, QuadraticBezierCurve3 for turns) with **piecewise arclength mapping** from backend [0,1] position to visual parameter, smooth position interpolation between WS updates, dynamic wheel rotation, emergency vehicle siren lights (alternating red/blue with point lights) |

#### Dashboard Components

| File | Purpose |
|---|---|
| `src/components/dashboard/AIStatusBadge.tsx` | Shows Training/Ready/Idle status based on training state |
| `src/components/dashboard/LiveSnapshot.tsx` | **UPDATED** Draggable floating widget (`framer-motion` drag): connection/running/mode badges (color-coded), training pulse badge, grid stats (Last Frame time, Active Vehicles, Avg Wait Time, Max Queue), "CCTV AI Scanner" card with vehicle detection count. |
| `src/components/dashboard/TrainingChart.tsx` | Recharts area chart with 4 toggleable metrics: Reward (cyan), Avg Wait (orange), Epsilon (yellow), Loss (purple), last 100 episodes, interactive summary cards |
| `src/components/dashboard/MetricsPanel.tsx` | 2×2 card grid: Avg Wait Time, Throughput, Max Queue, Episode. Animated numbers, progress bars, SVG sparklines (20-point rolling) |
| `src/components/dashboard/EpisodeHistory.tsx` | Paginated table (10/page): Episode #, Reward (color-coded), Wait Time, Throughput, Epsilon, Duration. Best episode highlighted green. Live training indicator. |
| `src/components/dashboard/ComparisonChart.tsx` | **MAJOR UPDATE** Bar chart comparing Fixed vs AI vs Manual (3 bars): Avg Wait Time and Throughput computed from `/api/metrics` (fetched every 15s), improvement percentage display (green positive, red negative), loading/empty/no-data states, Legend with mode-colored bars (#475569 Fixed, #38bdf8 AI, #f59e0b Manual). |
| `src/components/dashboard/QValuePanel.tsx` | **NEW** Per-phase Q-value bars with gradient fills, active phase highlight, confidence score (gap between top-2 Q-values as %), explore/exploit badge, ε display — visualizes agent reasoning in real-time |

#### City Grid Components — **NEW**

| File | Purpose |
|---|---|
| `src/app/city/page.tsx` | **NEW** City Grid page — lazy-loads `CityCanvas`, header with tick/mode/congestion, mode toggle (Fixed/Greedy/AI), spawn rate, congestion heatmap, Run Comparison, side panel with Controls, Metrics, Analytics tabs |
| `src/components/city/CityCanvas.tsx` | **NEW** Three.js canvas for 2×2 grid: 4 intersection nodes at world positions, congestion heatmap overlay (green/amber/red based on avg wait), road vehicles, reused TrafficLight, QueueLabel, CityVehicle components |
| `src/components/city/CityGrid.tsx` | **NEW** 9 city blocks (parks + skyscrapers with neon stripes), MeshPhysicalMaterial ground, center monument, LowPolyTree, Skyscraper components |
| `src/components/city/CityRoads.tsx` | **NEW** Continuous 56-unit asphalt roads, double yellow centerlines, stop bars at all 4 intersections, directional labels (EASTBOUND/WESTBOUND/NORTHBOUND/SOUTHBOUND) |
| `src/components/city/CityVehicle.tsx` | **NEW** Reuses single-intersection CurvePath for intersection vehicles; **road vehicles** use linear world_x/z interpolation with lateral offset based on `prev_turn`/`next_turn` |
| `src/components/city/CityControls.tsx` | **NEW** Fixed/Greedy/AI mode buttons, Start/Stop/Reset, spawn rate slider (0.05–1.5), congestion heatmap toggle, Run Comparison button |
| `src/components/city/CityMetricsPanel.tsx` | **NEW** 2×2 global metric cards (Avg Wait, Throughput, Active, Road Vehicles) with sparklines + per-intersection rows (signal dot, queue bar, phase, wait time) |
| `src/components/city/CityComparisonPanel.tsx` | **NEW** Recharts bar chart for Fixed/Greedy/AI comparison, improvement % vs Fixed, live progress overlay during benchmark run |

#### Layout Components

| File | Purpose |
|---|---|
| `src/components/layout/Header.tsx` | Top bar showing FlowSync branding, connection status badge (green/red), current mode badge |
| `src/components/layout/KeepAlivePing.tsx` | Client component that pings `/api/keep-alive` on mount to wake backend |

#### shadcn/ui Components

Standard Radix-based components: `badge.tsx`, `button.tsx`, `card.tsx`, `chart.tsx`, `scroll-area.tsx`, `select.tsx`, `separator.tsx`, `slider.tsx`, `switch.tsx`, `table.tsx`, `tabs.tsx`, `tooltip.tsx`

### Server Source Files

| File | Purpose |
|---|---|
| `server/app/__init__.py` | Empty package init |
| `server/app/main.py` | **MAJOR UPDATE** FastAPI application entry point: lifespan creates **two independent environments** — `sim_intersection` (`Intersection`) for live simulation, `training_env` (`TrafficEnv`) for Trainer; **two independent agents** — `sim_agent` (inference) and `training_agent` (training); CORS middleware with allowlist + regex; includes 3 routers; registers 2 WebSocket routes; `/` and `/health` endpoints |
| `server/app/config.py` | Pydantic Settings: loads `SUPABASE_URL`, `supabase_service_key` (with alias resolution from 4 env var names), `CORS_ORIGINS`, **`SIGNAL_RED_DURATION`**; validates service key is admin-level (decodes JWT, checks `role=service_role`) |
| `server/app/routers/simulation.py` | REST endpoints: POST `/simulation/start`, POST `/simulation/stop`, POST `/simulation/reset`, PUT `/simulation/mode`, GET `/simulation/status` (MetricsSnapshot) |
| `server/app/routers/training.py` | REST endpoints: POST `/training/start`, POST `/training/stop`, GET `/training/status`, GET `/training/models`, POST `/training/load` |
| `server/app/routers/metrics.py` | REST endpoint: GET `/metrics/current` (MetricsSnapshot) |
| `server/app/schemas/simulation_schema.py` | Pydantic models: `VehicleState`, `SignalState`, `QueueState`, `MetricsState`, `RLState`, `SimulationFrame`; **enhanced `build_frame()`** with world coordinates, per-lane signal colors, Q-values, action labels, exploration flags |
| `server/app/schemas/training_schema.py` | Pydantic models: `TrainingMetric`, `StartTrainingRequest` |
| `server/app/schemas/metrics_schema.py` | `MetricsSnapshot`: avg_wait_time, throughput, max_queue, current_phase, is_training, current_episode, epsilon |

#### Services

| File | Purpose |
|---|---|
| `server/app/services/supabase_service.py` | All DB writes: `create_simulation`, `update_simulation`, `save_episode`, `save_traffic_logs_bulk`, `save_signal_states_bulk`, `save_performance_metric`, `save_model_metadata` (upsert), `set_active_model`. All sync, called via `asyncio.to_thread`. Error logging on every failure. |
| `server/app/services/model_service.py` | Checkpoint management: `save_checkpoint` (local disk + Supabase Storage), `load_checkpoint` (Storage with local fallback), `list_checkpoints`, `list_all_models` (3-tier discovery: DB → Storage listing → local disk, deduplicated) |

#### Simulation Engine

| File | Purpose |
|---|---|
| `server/app/simulation/environment.py` | **LATEST: Max-Pressure Formulation Fix** Gymnasium `TrafficEnv`: **20-dim observation** (12 movement queues normalized by 10 + 4 one-hot phase + time_in_phase/MAX_GREEN_TIME + is_transitioning + total_pressure/20 + max_starvation/THRESHOLD), Discrete(4) action space. **Pressure-based reward** (PressLight/MPLight): pressure_change×1.5 + throughput×0.2 + switch_penalty -0.3 (evaluated against **previous** phase's pressure, not current) + starvation_penalty -2.0/starved + max_green_penalty -1.0 + balance_bonus 0.2 (computed over **phase-level** pressures). `_compute_movement_pressures()`: per-movement pressure with **destination mapping** — 12 movements each mapped to their downstream direction (e.g., north_straight→south, north_left→east). `_get_phase_pressure(phase)`: aggregates movement pressures to phase-level (Phase 0: NS straight+left, Phase 1: EW straight+left, Phase 2: NS right, Phase 3: EW right). `_get_best_alternative_phase()` uses `_get_phase_pressure()`. Hard constraints: max green override (forced switch at 40s), starvation override. Terminal at 1000 steps. |
| `server/app/simulation/intersection.py` | **LATEST: Destination-Aware Outgoing Counts Fix** Core traffic intersection: 12 lanes (4 directions × 3 turns), TrafficSignal, PoissonSpawner, timestep counter, intersection reservation system (by direction group: NS vs EW), emergency override. **`get_queue_lengths()` counts only `state != "passed"` vehicles**. **Yield-on-left logic**: left-turning vehicles at stop line during phases 0/1 must yield to oncoming straight/right traffic. **Per-lane queues** with `_spawned_this_interval` / `_passed_this_interval` counters for telemetry. **`get_movement_queues()`** returns 12-movement counts. **`get_outgoing_counts()`** — **UPDATED** with **destination mapping** (e.g., south_straight→north, west_left→north, east_right→north) instead of naive `lane_key.split("_")[0]` for accurate pressure calculation. **`get_approaching_count(direction)`** counts vehicles before stop line. |
| `server/app/simulation/vehicle.py` | Vehicle dataclass: id, lane (direction), turn, position, wait_time, speed, state, is_emergency. `is_right_turn` property. `tick(dt, can_move)` moves vehicle at DEFAULT_SPEED (0.12) if allowed, tracks wait time, transitions to "passed" at position ≥ 1.0 |
| `server/app/simulation/traffic_signal.py` | **LATEST: Starvation Bleed Fix** Traffic signal logic: 4 phases (NS_GREEN, EW_GREEN, NS_LEFT, EW_LEFT), 3 colors (GREEN, YELLOW, RED). `red_duration=3.0` all-red clearance. **Starvation tracking**: `starvation_timer` dict per-direction — **FIXED**: timers now reset for directions in BOTH the current green phase AND the **pending phase**, preventing "starvation bleed" where a direction with a pending green still accumulated wait time. `STARVATION_THRESHOLD=45s`, `get_starved_directions()`, `is_max_green_exceeded` (40s cap), `can_switch_phase` (8s min). **Manual mode**: `is_manual` holds green indefinitely. `PHASE_ALLOWED_TURNS`: left-turn phases (2,3) restricted to "left" only. Smart phase selection (highest queue after min green, early switch if current phase empty). AI phase requests go through yellow→red→green transition. `set_phase(phase)` initiates yellow→red→target transition. |
| `server/app/simulation/spawner.py` | **UPDATED** `PoissonSpawner`: configurable λ (default 0.3), spawns into one random direction per tick, 50% straight / 25% left / 25% right, max 10 vehicles per lane. Lanes now keyed by `{direction}_{turn}`. |
| `server/app/simulation/metrics.py` | `MetricsTracker`: rolling calculation of avg_wait_time, avg_throughput, avg_queue_length with running totals. (Currently unused but retained) |
| `server/app/simulation/city_network.py` | **NEW** `CityNetwork`: 2×2 grid of 4 `Intersection` instances (A/B/C/D), `RoadVehicle` inter-intersection transfer logic, `ROAD_CONNECTIONS` (A↔B, C↔D E-W; A↔C, B↔D N-S), `EXIT_DIR_MAP` (12 movement→destination), `ROAD_TRAVEL_TIME=3.0s` (30 ticks), `build_obs()` (20-dim per intersection, matches single-intersection exactly), `get_greedy_action()` (same logic as single), `tick()` orchestrates 4 intersection ticks → collects passed vehicles → routes to roads/exits → advances road vehicles → injects arrivals into destination intersections, `get_city_metrics()` (city-wide avg wait, throughput, congestion level, per-intersection breakdown) |
| `server/app/simulation/city_spawner.py` | **NEW** `CitySpawner`: 8 external entry points (N/S/E/W of each corner intersection), Poisson spawn divided across entries, 50/25/25 straight/left/right, max 12/lane, carries accumulated wait time across intersections |
| `server/app/simulation/vehicle.py` | Vehicle dataclass: id, lane (direction), turn, position, wait_time, speed, state, is_emergency. `is_right_turn` property. `tick(dt, can_move)` moves vehicle at DEFAULT_SPEED (0.12) if allowed, tracks wait time, transitions to "passed" at position ≥ 1.0 |

#### Reinforcement Learning

| File | Purpose |
|---|---|---|
| `server/app/rl/dqn_network.py` | **REWRITTEN** Dueling DQN architecture (Wang et al. 2016): shared feature backbone Linear(20,256)→LayerNorm→ReLU→Linear(256,256)→LayerNorm→ReLU; **value stream** Linear(256,128)→ReLU→Linear(128,1); **advantage stream** Linear(256,128)→ReLU→Linear(128,4). Q = V(s) + A(s,a) - mean(A). Kaiming uniform init. |
| `server/app/rl/dqn_agent.py` | **REWRITTEN** Dueling Double DQN with PER. Two agents: `sim_agent` (inference) + `training_agent` (training). `train_step()`: PER importance-sampling weighted SmoothL1Loss, Double DQN (online selects argmax, target evaluates), gradient clipping max_norm=10. `get_checkpoint_state()`: includes obs_version='v3_20dim_pressure'. Legacy checkpoint compatibility. |
| `server/app/rl/replay_buffer.py` | **REWRITTEN** Prioritized Experience Replay (Schaul et al. 2016). `SumTree` for O(log n) priority sampling. `PrioritizedReplayBuffer`: α=0.6, β-start=0.4, β-end=1.0, ε=1e-6, capacity=100,000. `push` with max priority. `sample` returns importance-sampling weights + tree indices. `update_priorities` from TD errors. `anneal_beta` over training. |
| `server/app/rl/hyperparams.py` | **MAJOR UPDATE** Dataclass: STATE_DIM=20, ACTION_DIM=4, LR=3e-4, γ=0.97, BATCH=128, TRAIN_EVERY=2, REPLAY=100000, MIN_REPLAY=2000, ε_start=1.0, ε_end=0.05, ε_decay=0.998, MAX_STEPS=1000, DEFAULT_EPISODES=1000, TARGET_UPDATE=300, CHECKPOINT_EVERY=50. **New PER params**: α=0.6, β_start=0.4, β_end=1.0, ε=1e-6. **New constraints**: MIN_GREEN_TIME=8.0, MAX_GREEN_TIME=40.0, STARVATION_THRESHOLD=45.0. **New sim params**: TRAINING_LAMBDA=0.8, EVAL_LAMBDA=0.5. Lowercase property mappings. |
| `server/app/rl/trainer.py` | **MAJOR UPDATE** Training orchestrator: **PER beta annealing** per episode. **Agent weight sync**: at every checkpoint, `sim_agent.online_net.load_state_dict(training_agent.online_net.state_dict())` for live inference syncing. `checkpoint_saved` WebSocket broadcast. Sends `is_training` flag (false on last episode) in WS metrics. Improved event loop yielding (every step during warmup, every 4 steps during training). Rolling 50-episode reward for metadata. |

#### WebSocket Handlers

| File | Purpose |
|---|---|
| `server/app/websockets/simulation_ws.py` | **MAJOR UPDATE** Simulation WebSocket: ConnectionManager for multi-client broadcast. Main loop at 10 Hz. **AI mode**: builds 20-dim observation via `_build_obs_from_intersection()`, `agent.select_action(ε=0)`, computes reward via `training_env.compute_reward()` with pressure/throughput/phase_change, `build_frame()` now passes full context (agent Q-values, obs, reward, action, exploration flag). Command validation with `COMMAND_SCHEMAS` dict. Local dev frame logging. Flushes buffer on cancel/crash. |
| `server/app/websockets/city_ws.py` | **NEW** City Grid WebSocket (`/ws/city`): `CityConnectionManager`, `_city_simulation_loop()` at 10 Hz. Supports Fixed/Greedy/AI modes + **automated comparison test** (`ComparisonTestState`: runs Fixed→Greedy→AI sequentially, 30s each, broadcasts phase progress, final results), command validation (`set_mode`, `set_spawn_rate`, `run_comparison`). Reuses `sim_agent` (shared policy) for AI mode. |
| `server/app/websockets/training_ws.py` | Training WebSocket: separate ConnectionManager. `broadcast_training_metric()` used by Trainer. Handles start_training/stop_training commands. Creates simulation record if needed. Sends current status immediately on connect. |

### Server Config Files

| File | Purpose |
|---|---|
| `server/requirements.txt` | Production dependencies (11 packages) |
| `server/requirements-dev.txt` | Test dependencies (pytest, pytest-asyncio, pytest-cov, httpx, pytest-mock) |
| `server/pytest.ini` | Pytest config: asyncio auto-mode, coverage on `app/`, term-missing report |
| `server/runtime.txt` | Python 3.11.9 version pin |
| `server/SUPABASE_KEYS_SETUP.txt` | Detailed Supabase key setup guide explaining service_role vs anon key distinction |
| `server/Dockerfile` | Multi-stage Docker build: python:3.11-slim, build deps, CPU-only PyTorch, runs uvicorn on port 8000 |

### Tests (`server/tests/`)

| File | Purpose |
|---|---|
| `conftest.py` | Pytest fixtures: `mock_supabase` (patches supabase_client), `mock_model_service` (patches save/load/list), `client` (FastAPI TestClient with lifespan), `app_state` |
| `tests/api/test_main.py` | Tests root (`/`) and `/health` endpoints |
| `tests/api/test_simulation.py` | Tests start/stop/reset/set_mode/get_status — 5 test functions |
| `tests/api/test_training.py` | Tests start/stop/status/models — 4 test functions |
| `tests/rl/test_replay_buffer.py` | Tests buffer push and sample — 2 test functions |
| `tests/rl/test_dqn_agent.py` | Tests init, random action, greedy action, train_step — 4 test functions |
| `tests/simulation/test_vehicle.py` | Tests init, movement, waiting, passed state — 4 test functions |
| `tests/simulation/test_traffic_signal.py` | Tests init, phase change, yellow→red→green transitions, fixed duration rollover, green permission — 6 test functions |

---

## Appendix: Git History Summary (55+ Commits)

The project evolved through numbered phases early on, then shifted to feature-based commits:

| Phase | Commits | Description |
|---|---|---|
| **Phase 1-3** (earliest) | `c39b678`, `58d1b7f`, `2a3a9f4` | RL agent core, server + WebSocket wiring, app shell |
| **Phase 4-6** | `86942dc`, `fd4a767`, `bb733f` | Dashboard controls, end-to-end flows, performance optimizations |
| **Phase 7-9** | `2e42fd6`, `b29b04e`, `3c77eb2` | Simulation alignment, traffic light enhancement, turn logic |
| **Deployment** | `d37e394`, `b3cee83`, `a067810`, `0e697b2` | Supabase config, deployment fixes, CORS, Prisma |
| **Training enhancements** | `c6a43d`, `4525243`, `e0c5cbd` | Real-time training dashboard, model persistence, reward optimization |
| **UI & Docs** | `302d2a2`, `b6e2668`, `20f13cb`, `7bab979` | Documentation, landing page, animations |
| **Infrastructure** | `6f94c89`, `b162c34`, `50c1e1c`, `c1a267c`, `d4b2670` | Keep-alive (added, moved to API route, workflows removed) |
| **Emergency + Multi-Vehicle** | `f042669`, `7ad81e8`, `7ca7d8c` | Emergency preemption UI, multi-vehicle intersection locks, 3D lighting fixes with CCTV cameras |
| **Fixes 1-9 (Foundation)** | `07f018b`...`a3d650c` | Env separation (2 envs in app.state), all-red clearance (3s), queue counting (non-passed only), configurable red_duration, pending phase tracking, Double DQN + LayerNorm, Huber loss, gradient clipping, 50K→100K buffer, reward redesign (queue reduction + throughput + overflow), schema v2 (world coords + Q-values + per-lane colors), DB schema v2 (SignalState FK/Cascade, RLModel unique constraint), code cleanup |
| **Manual Mode** | `df5a3a4` | Manual (MNL) mode + WebSocket `manual_override` command with yellow→red→green clearance |
| **Visual Polish I** | `926a754`, `4b390b2`, `2885db9`, `630aac6` | Sun emissive intensity (8.0), traffic light arrows (← for left, ↑→ for through/right), environment scaling, 3-lane roads with exact stop line tracking |
| **Telemetry Schema v2** | `87a4f92`, `e694309` | Simulation frame restructured to match client: nested QueueState→queue_lengths flattening, signal_color derived from is_transitioning + per-lane colors, world coordinates + Q-values in frame |
| **Dueling DQN + PER** | `ade47fe`, `134c411`, `5e74135`, `97bb6de`, `98588b4` | Full RL upgrade: Dueling network (V Stream Linear(128,1) + A Stream Linear(128,4)), SumTree PER (α=0.6, β: 0.4→1.0), 20-dim observation (12 movements + 4 phase one-hot + 4 context), LayerNorm, Kaiming init, SmoothL1Loss, gradient clipping max_norm=10 |
| **Two-Agent Decoupling** | `0efed2d` | Separate sim_agent (inference, ε=0) + training_agent (training, ε:1.0→0.05), weight sync at checkpoints, fix DB timestamp handling |
| **Starvation & Constraints** | `e6be1b7`, `d009830` | Starvation overrides (45s threshold with -2.0 reward penalty), right-turn always-allowed (excluded from pressure), pressure-based 20-dim obs, max-green enforcement (40s cap with -1.0 penalty), reward inflation fix (throughput 0.5→0.2, remove empty balance bonus), phase change detection fix (pre-tick vs post-tick) |
| **Comparison + Draggable UI** | `8d7536d`, `5e2aff3` | 3-mode comparison chart (Fixed/AI/Manual with improvement %), draggable LiveSnapshot (framer-motion drag), left-turn arrow display fix, holographic queue label UI |
| **Environment Styling II** | `2d074b3`, `d5a22ec` | MeshPhysicalMaterial upgrade (ground clearcoat 0.2/metalness 0.3, skyscraper clearcoat 1.0/metalness 0.9/reflectivity 1.0), neon corner stripes (emissiveIntensity 3.5), LowPolyTree, Day/Night sun sphere (emissiveIntensity 8.0), CCTV cameras with blinking LED, camera auto-rotation disabled |
| **Algorithm Fixes — Max-Pressure + Starvation Bleed** | `f3bcd9f` | **(a)** Pressure computed per-movement (12 entries with `dest_map`: north_straight→south, north_left→east, etc.) instead of per-direction. **(b)** Switch penalty evaluates `prev_pressures[prev_phase]` via pre-tick capture. **(c)** Starvation timers reset for **both** current `green_dirs` AND `pending_phase` directions. **(d)** `get_outgoing_counts()` uses proper destination mapping (12-entry `dest_mapping`). **(e)** Balance bonus uses phase-level aggregation (`_get_phase_pressure()`) over 4 groups. **(f)** `_get_best_alternative_phase()` uses `_get_phase_pressure()`. **(g)** New `_get_phase_pressure()` helper for phase-level grouping. |
| **City Grid — Multi-Intersection** | `562d85d`, `b3fe488`, `f643a1b`, `71fb774`, `15f9e4d`, `7d4a34a`, `e9cd8e7`, `79df942` | **NEW MAJOR FEATURE**: 2×2 grid (A/B/C/D), `CityNetwork` (4 intersections + RoadVehicle routing), `CitySpawner` (8 entry points), `CitySpawner` schemas, `/ws/city` with Fixed/Greedy/AI modes + automated comparison benchmark, `/city` page with full 3D viz, CityVehicle with road/intersection path logic, CityGrid/CityRoads/CityControls/CityMetricsPanel/CityComparisonPanel |
| **Greedy Mode + Q-Value Panel** | `74c6415` | Greedy rule-based controller (max-queue phase selector) for `/simulation` and `/city`; `QValuePanel` shows per-phase Q-values, confidence %, explore/exploit badge |
| **Hyperparam Tuning + Async Step** | `22768d4`, `5c8dd03`, `41066da` | `MIN_REPLAY_SIZE` 2000→500 (faster warmup), `EPSILON_DECAY` 0.998→0.994 (reaches 0.05 by ~550 eps), `env.step()` offloaded via `asyncio.to_thread()` to prevent event-loop blocking; fixed phase pressure mapping (straight-only for phases 0/1, left-only for 2/3), train/inference obs mismatch resolved |
| **Fixed Signal Upgrade** | `5c8dd03` | Queue-based phase selection with `_pick_highest_queue_phase()`, hard 40s green cap, left turns restricted to dedicated left phases (2,3), PHASE_ALLOWED_TURNS updated |
| **Lint/Build Fixes** | `2f00cc1`, `f8f8417`, `1657b71`, `8053133`, `7202593`, `bd7d978`, `8b4ab5c`, `17d55e3`, `f63b92f`, `5fea7a0`, `99b07e4`, `1bc8b10`, `2d4db8b`, `24b3a4b` | ESLint/TypeScript clean, chart data loss fix, training offload to worker, WS dashboard sync, reward/spawner bugs, pause removal, historical stats, LiveSnapshot compact, pause feature, project summary update |

---

*Generated: 2026-07-21 — Comprehensive project analysis of FlowSync. Architecture: Dueling Double DQN + PER + per-movement max-pressure formulation + two-agent decoupling + starvation-aware constraints + destination-aware outgoing counts + 2×2 multi-intersection city grid with shared-policy AI + greedy baseline + automated benchmark. Deep-dive includes: intersection reservation system (direction-group locking), vehicle collision avoidance (MIN_DIST=0.08), emergency override bypass mechanism (direct signal phase mutation), command validation (COMMAND_SCHEMAS with type coercion), inference vs training observation builder distinction (simplified pressure_norm=0.0 for live inference), city network routing (RoadVehicle transfer with wait-time carryover), automated 3-mode comparison benchmark (Fixed→Greedy→AI). Updated through commit `7b73d8b`.*
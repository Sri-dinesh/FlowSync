# FlowSync — Comprehensive Project Summary

> **AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning**

---

## 1. Project Overview

### What Is FlowSync?

FlowSync is a full-stack, real-time traffic simulation system that demonstrates how **Dueling Double DQN with Prioritized Experience Replay (PER)** can optimize traffic signal control at a 4-way city intersection. It serves as a **proof-of-concept Digital Twin** for smart-city infrastructure modernization, replacing traditional fixed-timer traffic signals with an autonomous, learning AI agent — plus a **Manual (MNL) control mode** for human-in-the-loop operation. The system is designed as a research platform to study **pressure-based reward functions**, **starvation-aware constraint handling**, and **real-time RL inference** in traffic domains.

**Mission:** Show that Reinforcement Learning can significantly outperform static traffic systems, reducing urban congestion, wait times, and vehicle emissions.

**Core Research Contributions:**
- **Dueling Double DQN** with separate value (V) and advantage (A) streams for better state-value estimation under high-density traffic
- **Prioritized Experience Replay** with SumTree data structure, priority annealing (α=0.6), and importance-sampling bias correction (β: 0.4→1.0)
- **20-dimensional pressure-based observation space** encoding 12 lane-level movement queues, phase one-hot, signal context, and starvation metrics
- **Multi-component pressure reward** combining pressure differential (PressLight-style), throughput bonus, switch penalty, starvation penalty (-2.0 per starved direction), max-green violation penalty (-1.0), and balance bonus — all with hard constraint enforcement
- **Two-agent decoupling**: separate inference agent (live simulation) and training agent (background training) with periodic weight synchronization
- **Starvation-aware signal control**: per-direction wait timers trigger automatic phase overrides at 45s threshold, independent of RL policy

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

**Active Development / MVP — Research Platform.** The project is fully functional with a landing page, 3D simulation dashboard, live training, manual control, **Dueling Double DQN with PER**, **starvation-aware constraint handling**, **pressure-based observations**, and data persistence. Designed as a **research tool** for studying pressure-based RL in traffic signal control.

---

## 1.1 Current Project Status — Detailed Breakdown

### What Is Working (✅ Verified Functional)

| Area | Status | Details |
|---|---|---|
| **Frontend Build** | ✅ Working | `pnpm dev` compiles, Next.js 16 App Router loads, TypeScript strict mode passes |
| **Backend Server** | ✅ Working | `uvicorn app.main:app --reload` starts on :8000, lifespan initializes 2 envs + 2 agents + Trainer |
| **WebSocket Simulation** | ✅ Working | `/ws/simulation` connects, 10 Hz frames broadcast, 3D scene renders vehicles, AI mode computes reward via `training_env.compute_reward()` |
| **WebSocket Training** | ✅ Working | `/ws/training` connects, per-episode metrics stream, checkpoint notifications, `is_training` flag on last episode |
| **Fixed-Timer Control** | ✅ Working | 4-phase cycle with smart queue-based switching, yellow (2s) → red (3s) → green (min 4s, default 8s), early switch if current phase empty |
| **AI (Dueling Double DQN) Control** | ✅ Working | Dueling architecture (V + A streams), PER buffer (SumTree, α=0.6, β annealing), 20-dim pressure obs, `select_action(ε=0)` for inference |
| **Manual (MNL) Control** | ✅ Working | 4 phase buttons, holds green indefinitely, phase changes go through yellow→red→green clearance |
| **Yield-on-Left Logic** | ✅ Working | Left-turners at stop line during phases 0/1 yield to oncoming straight/right traffic |
| **Starvation Overrides** | ✅ Working | Per-direction `starvation_timer` (45s threshold), triggers `set_phase()` to serve starved direction, -2.0 penalty in reward |
| **Max Green Enforcement** | ✅ Working | Hard 40s cap on any green phase, forces `_get_best_alternative_phase()` (highest pressure) |
| **Right-Turn Always-Allowed** | ✅ Working | Right turns excluded from pressure calculation, bypass signal checks entirely, `is_right_turn` property on Vehicle |
| **Two-Agent Decoupling** | ✅ Working | `sim_agent` (inference) + `training_agent` (training) are independent `DQNAgent` instances; weights synced at checkpoints |
| **3-Lane Roads + Visuals** | ✅ Working | 40×6 roads, stop bars at ±3.1, zebra crossings, lane offsets (0.5/1.5/2.5), direction labels |
| **Traffic Light Arrows + CCTV** | ✅ Working | ← for left phases, ↑→ for through/right; CCTV camera with blinking status LED on each pole |
| **Vehicle Paths** | ✅ Working | CurvePath (LineCurve3 + QuadraticBezierCurve3) with piecewise arclength mapping |
| **Vehicle Interpolation** | ✅ Working | Smooth 60 fps between 10 Hz WS updates, wheel rotation, emergency siren lights |
| **Day/Night 3D Toggle** | ✅ Working | State-driven lighting: emissive sun (intensity 8) + bright ambient (day) vs moody directional (night) |
| **MeshPhysicalMaterial Environment** | ✅ Working | Ground plane, skyscrapers with clearcoat 1.0 + metalness 0.9 + neon corner stripes emissive 3.5 |
| **Side-by-Side Layout** | ✅ Working | Canvas left (flex-1), controls sidebar right (420px, scrollable) |
| **Live Training Dashboard** | ✅ Working | Reward/Wait/Epsilon/Loss sparklines, trend arrows, phase description, ETA, ep/min |
| **Model Checkpointing** | ✅ Working | Every 50 eps: saves to Supabase Storage + local disk, metadata upsert to `rl_models` |
| **Model Loading** | ✅ Working | Dropdown fetches `/training/models`, loads state dict into both sim_agent + training_agent |
| **Emergency Preemption** | ✅ Working | 4 directional buttons, spawns ambulance, forces priority phase, clears on exit |
| **Performance Comparison** | ✅ Working | Compare tab aggregates Fixed/AI/Manual wait time + throughput, improvement %, 3-bar chart (#475569/#38bdf8/#f59e0b) |
| **Episode History** | ✅ Working | Paginated table (10/page), auto-refresh 10s during training, best episode highlighted |
| **Real-Time Metrics** | ✅ Working | MetricsPanel (2×2 animated cards), LiveSnapshot (draggable framer-motion overlay) |
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
| **WS Reconnection Storm** | ⚠️ Rare | Exponential backoff (max 5) works, but rapid reconnects can occur if backend restarts mid-session |
| **Prisma Migrations** | ⚠️ Manual | No CI migration step — `prisma db push` required after schema changes |
| **Hardcoded Render URL** | ⚠️ Config | `flowsync-gelt.onrender.com` removed from `utils.ts`/`next.config.ts` but may persist in docs |

### Not Implemented / Missing (❌)

| Area | Status | Details |
|---|---|---|
| **Authentication/Authorization** | ❌ None | No user accounts, no WS auth, no API keys — single-user demo only |
| **Rate Limiting** | ❌ None | No protection on REST or WS endpoints |
| **CI/CD Pipeline** | ❌ None | No GitHub Actions, no automated test/lint/deploy |
| **Multi-Intersection** | ❌ Not started | Single 4-way intersection only; env would need major refactor |
| **GPU Training** | ❌ Blocked | Render free tier CPU-only; no CUDA in Dockerfile |
| **GraphQL / Webhooks** | ❌ Not planned | REST + WS covers all current needs |
| **Data Retention Policy** | ❌ None | Data persists indefinitely on Supabase free tier |
| **Automated Security Scanning** | ❌ None | No Dependabot, Snyk, or SAST in CI |
| **WebSocket Message Schema Validation** | ❌ None | Commands validated by if-else chains only |

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

### Recent Commits Impact (Last 15)

| Commit | Date | Impact |
|---|---|---|
| `d5a22ec` | 2026-07-15 | Disable camera auto-rotation (manual orbit only) |
| `2d074b3` | 2026-07-13 | Upgrade environment: MeshPhysicalMaterial, neon skyscrapers, LowPolyTree, Day/Night sun emissive 8.0 |
| `8d7536d` | 2026-07-13 | 3-mode comparison chart, draggable LiveSnapshot framer-motion widget |
| `d009830` | 2026-07-13 | Fix reward inflation: reduce throughput bonus 0.5→0.2, remove empty-intersection balance bonus, fix phase change detection (pre-tick vs post-tick) |
| `0efed2d` | 2026-07-12 | **Two-agent decoupling**: separate sim_agent + training_agent, weight sync at checkpoints, fix DB timestamp errors |
| `ade47fe` | 2026-07-12 | **Dueling DQN + PER**: V/A streams, SumTree, importance sampling, α=0.6, β=0.4→1.0 |
| `e6be1b7` | 2026-07-12 | Starvation overrides (45s), right-turn always-allowed, pressure-based 20-dim obs, max green 40s cap |
| `5e2aff3` | 2026-07-12 | Correct traffic light direction, holographic queue labels, arrow display polish |
| `87a4f92` | 2026-07-12 | WS frame flattening: QueueState dict → queue_lengths, signal_color from per-lane colors |
| `2a3b393` | 2026-07-12 | Datetime parsing for fallback storage, consistent model naming |
| `482cbec` | 2026-07-12 | Model naming: date + time + episodes + efficiency rating |
| `a3d650c` | 2026-07-12 | Cleanup: remove hardcoded URLs, delete dead metrics.py, update pytest |
| `e694309` | 2026-07-12 | Schema v2: world coordinates, Q-values, performance metrics DB refactor |
| `134c411` | 2026-07-12 | Double DQN + LayerNorm, replay buffer 50K→100K, Huber loss, gradient clipping |
| `5e74135` | 2026-07-12 | Observation space redesign: 8-dim→20-dim, pressure-based compute_reward |

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
| NS_GREEN | 0 | North, South | straight, left, right | 8s |
| EW_GREEN | 1 | East, West | straight, left, right | 8s |
| NS_LEFT | 2 | North, South | left only | 8s |
| EW_LEFT | 3 | East, West | left only | 8s |

**Timing Sequence:** GREEN (min 4s, default 8s) → YELLOW (2s) → RED (3s clearance) → GREEN for next phase

**Smart Phase Selection Logic:**
1. After `min_green_duration` (4s), check if current phase has 0 vehicles AND another phase has >0 → switch early
2. At `fixed_duration` (8s) timeout: iterate through candidate phases in sequential order, select first phase with waiting vehicles
3. If no candidate has vehicles: fall back to next sequential phase
4. **Minimum green guard:** `can_switch_phase` returns False if `time_in_phase < MIN_GREEN_TIME` (8s) unless in transition

**Phase Transition Safety (Yellow-Red Clearance):**
- `set_phase(target)`: immediately sets `pending_phase = target`, color → YELLOW, timer resets
- After 2s yellow: color → RED, timer resets  
- After 3s red: `current_phase = pending_phase`, color → GREEN, timer resets
- This ensures **5 seconds of clearance** (2s yellow + 3s all-red) between opposing movements

**Starvation Tracking (Shared with AI Mode):**
- Per-direction timers (`starvation_timer` dict): reset to 0 when direction receives green, accumulate `dt` when direction is red
- `get_starved_directions()`: returns directions with timer ≥ `STARVATION_THRESHOLD` (45s)
- In fixed mode: starvation does NOT override phase selection (only AI mode has starvation override), but the metric is still tracked for reward computation

**Yield-on-Left (All Modes):**
- When vehicle.position ≤ STOP_LINE (0.42) AND vehicle.turn == "left" AND signal.current_phase in (0, 1):
  - Check oncoming lane (north↔south, east↔west) for straight/right vehicles with position between 0.15 and 1.0
  - If found: set `can_move = False` to yield right-of-way

**Right-Turn Always-Allowed (All Modes):**
- Right-turning vehicles (`is_right_turn = True`) bypass signal checks entirely
- Not subject to any red-light enforcement

**User Flow:** Launch simulation → toggle to "Fixed" mode → watch traditional cycle → observe yield-on-left → compare with AI mode.

**Priority:** ★★★★★ (baseline for comparison)

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

#### 2.3.3 Action Space (Discrete 4)
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

#### 2.3.5 Reward Function — Pressure-Based
Based on PressLight (Wei et al. 2019), MPLight, and FPA-DQN (Wang et al. 2025):

`R = pressure_reward + throughput_reward + switch_penalty + starvation_penalty + max_green_penalty + balance_bonus`

| Component | Formula | Weight | Purpose |
|-----------|---------|--------|---------|
| **Pressure Reward** | `(total_prev_pressure - total_curr_pressure) × 1.5` | 1.5 | Primary signal — reduce intersection-wide congestion pressure |
| **Throughput Bonus** | `vehicles_passed × 0.2` | 0.2 | Reward clearing vehicles (conservative to avoid dominating) |
| **Switch Penalty** | `-0.3` if phase changed AND green direction still has pressure > 0.3 | -0.3 | Discourage unnecessary switching that leaves pressure unserved |
| **Starvation Penalty** | `-2.0 × len(starved_directions)` | -2.0 | Hard penalty per direction waiting > 45s |
| **Max Green Penalty** | `-1.0` if current phase exceeds 40s | -1.0 | Prevent agent from holding green indefinitely |
| **Balance Bonus** | `+0.2` if pressure values are nearly equal (imbalance < 0.2) AND traffic is present | 0.2 | Encourage evenly distributed service |

**Pressure Calculation** (per direction):
`Pressure(d) = max(0, incoming_count(d) / MAX_CAP - outgoing_count(d) / MAX_CAP)`

Where:
- `incoming(d)` = vehicles in straight + left movements for direction d (right turns excluded — always allowed)
- `outgoing(d)` = vehicles in outgoing lanes (position > 0.9 or state == "passed")
- `MAX_CAP = 10.0` (max vehicles per lane)

#### 2.3.6 Hard Constraints (Safety Overrides)
Applied BEFORE the agent's action takes effect — these are hard guards, not learned:

| Constraint | Trigger | Action | Priority |
|------------|---------|--------|----------|
| **Max Green Override** | Current green phase exceeds MAX_GREEN_TIME (40s) | Force switch to highest-pressure alternative phase | Overrides agent action |
| **Starvation Override** | Any direction waits > STARVATION_THRESHOLD (45s) | Force phase that serves the starved direction | Overrides agent action |
| **Minimum Green** | `can_switch_phase` returns False if time_in_phase < 8s (unless transitioning) | Blocks phase change request | Signal-level guard |
| **Yellow-Red Clearance** | Any phase change triggers yellow (2s) → red (3s) → green sequence | Enforces safety clearance | Signal-level guard |

#### 2.3.7 Training Loop

```
For each episode:
  1. Anneal PER beta: β = lerp(PER_BETA_START, PER_BETA_END, episode / total_episodes)
  2. Reset environment → initial 20-dim observation
  3. For each step (max 1000):
     a. Select action via ε-greedy (ε decays 0.998× per episode, floor 0.05)
     b. Execute step: action goes through hard constraints → intersection.tick()
     c. Compute pressure-based reward
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

### 2.4 Manual (MNL) Signal Control — **NEW**

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

### 2.5 Live Training Dashboard

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

### 2.6 Performance Comparison (AI vs Fixed vs Manual)

**What:** Side-by-side bar charts comparing all three control modes with live improvement metrics.

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

### 2.7 Episode History

**What:** Paginated table of all training episodes with color-coded rewards.

**How It Works:**
- Fetches from `/api/episodes` (Next.js API route → Prisma)
- Auto-refreshes every 10 seconds during training
- Columns: Episode #, Reward (color-coded), Wait Time, Throughput, Epsilon, Duration
- Best episode highlighted in green
- 10 per page with pagination

**User Flow:** Switch to "History" tab → browse episodes → identify best-performing episode.

**Priority:** ★★★☆☆

### 2.8 Real-Time Metrics Panel

**What:** Live stats updating during simulation.

**How It Works:**
- 2×2 card grid showing avg wait time, throughput, max queue, episode
- Animated number transitions, progress bars, SVG sparklines
- 20-point rolling history displayed per metric
- Live Snapshot panel (bottom-left overlay) shows connection status, active vehicles, etc.

**User Flow:** Watch metrics update live as simulation runs.

**Priority:** ★★★★☆

### 2.9 Model Persistence & Loading

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

### 2.10 Emergency Vehicle Preemption

**What:** Spawn emergency vehicles that force priority green lights.

**How It Works:**
- 4 directional buttons in the control panel (North/South/East/West)
- Spawns an emergency vehicle with siren lights (red/blue alternating) and point lights
- Forces the traffic signal to the priority phase immediately (skips normal RL/fixed control)
- Only one emergency vehicle per direction at a time
- Normal control resumes after emergency clears

**User Flow:** Click "Emergency" button for a direction → watch emergency vehicle spawn → see signals change → ambulance clears intersection.

**Priority:** ★★★☆☆ (showcase feature)

### 2.11 Configurable Traffic Flow

**What:** Slider to adjust vehicle arrival rate.

**How It Works:**
- Poisson distribution spawner (default λ = 0.3)
- Slider range: 0.1–1.0
- 50% straight, 25% left, 25% right turn probability
- Max 10 vehicles per lane
- Spawns into one random direction per tick

**User Flow:** Drag slider → see traffic density change immediately.

**Priority:** ★★★☆☆

### 2.12 Keep-Alive Ping

**What:** Prevents backend cold-start on free-tier hosting.

**How It Works:**
- Frontend `KeepAlivePing` component pings `/api/keep-alive` on mount
- The Next.js API route forwards to FastAPI `/health`
- Replaced an earlier Vercel cron job approach

**Priority:** ★★☆☆☆ (infrastructure)

### 2.13 Dark Theme UI with Day/Night 3D Mode

**What:** Comprehensive dark mode with cyberpunk aesthetic + **NEW** Day/Night toggle for 3D scene.

**How It Works:**
- Tailwind v4 custom CSS variables for light/dark
- Semi-transparent glassmorphism panels (backdrop-blur)
- Animated borders, glow effects, floating holographic queue labels
- **3D Scene:** Day mode = bright sky, emissive sun with rays, high ambient; Night mode = dark sky, moody directional lights, bloom
- Consistent across all pages

**Priority:** ★★★☆☆

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
| **DB buffer flush** | Every 10 samples | ~50s during simulation | Flush buffered traffic logs + signal states to Supabase |
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
  - `{"command": "set_mode", "mode": "fixed" \| "ai" \| "manual"}`
  - `{"command": "set_spawn_rate", "value": 0.1-1.0}`
  - `{"command": "emergency_override", "lane": "north"\|"south"\|"east"\|"west"}`
  - `{"command": "manual_override", "phase": 0-3}`
- **Command validation:** `COMMAND_SCHEMAS` dict defines required fields and types per command; `validate_ws_command()` rejects unknown commands and invalid types

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
| `server/app/simulation/environment.py` | **MAJOR UPDATE** Gymnasium `TrafficEnv`: **20-dim observation** (12 movement queues normalized by 10 + 4 one-hot phase + time_in_phase/MAX_GREEN_TIME + is_transitioning + total_pressure/20 + max_starvation/THRESHOLD), Discrete(4) action space. **Pressure-based reward** (PressLight/MPLight): pressure_change×1.5 + throughput×0.2 + switch_penalty -0.3 + starvation_penalty -2.0/starved + max_green_penalty -1.0 + balance_bonus 0.2. **Hard constraints**: max green override (forced switch at 40s), starvation override (forces phase for starved direction). `_compute_movement_pressures()`: incoming/MAX_CAP - outgoing/MAX_CAP per direction. `_get_best_alternative_phase()`: picks highest-pressure non-current phase. Terminal at 1000 steps. |
| `server/app/simulation/intersection.py` | **MAJOR UPDATE** Core traffic intersection: 12 lanes (4 directions × 3 turns), TrafficSignal, PoissonSpawner, timestep counter, intersection reservation system (by direction group: NS vs EW), emergency override. **`get_queue_lengths()` counts only `state != "passed"` vehicles**. **Yield-on-left logic**: left-turning vehicles at stop line during phases 0/1 must yield to oncoming straight/right traffic. **Per-lane queues** with `_spawned_this_interval` / `_passed_this_interval` counters for telemetry. **`get_movement_queues()`** returns 12-movement counts. **`get_outgoing_counts()`** estimates outgoing lane occupancy for pressure calculation. **`get_approaching_count(direction)`** counts vehicles before stop line. |
| `server/app/simulation/vehicle.py` | Vehicle dataclass: id, lane (direction), turn, position, wait_time, speed, state, is_emergency. `is_right_turn` property. `tick(dt, can_move)` moves vehicle at DEFAULT_SPEED (0.12) if allowed, tracks wait time, transitions to "passed" at position ≥ 1.0 |
| `server/app/simulation/traffic_signal.py` | **MAJOR UPDATE** Traffic signal logic: 4 phases (NS_GREEN, EW_GREEN, NS_LEFT, EW_LEFT), 3 colors (GREEN, YELLOW, RED). `red_duration=3.0` all-red clearance. **Starvation tracking**: `starvation_timer` dict per-direction (resets on green, accumulates on red), `STARVATION_THRESHOLD=45s`, `get_starved_directions()`, `is_max_green_exceeded` (40s cap), `can_switch_phase` (8s min). **Manual mode**: `is_manual` holds green indefinitely. `PHASE_ALLOWED_TURNS`: left-turn phases (2,3) restricted to "left" only. Smart phase selection (highest queue after min green, early switch if current phase empty). AI phase requests go through yellow→red→green transition. `set_phase(phase)` initiates yellow→red→target transition. |
| `server/app/simulation/spawner.py` | **UPDATED** `PoissonSpawner`: configurable λ (default 0.3), spawns into one random direction per tick, 50% straight / 25% left / 25% right, max 10 vehicles per lane. Lanes now keyed by `{direction}_{turn}`. |
| `server/app/simulation/metrics.py` | `MetricsTracker`: rolling calculation of avg_wait_time, avg_throughput, avg_queue_length with running totals. (Currently unused but retained) |

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

## Appendix: Git History Summary (40+ Commits)

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

---

*Generated: 2026-07-15 — Comprehensive project analysis of FlowSync. Architecture: Dueling Double DQN + PER + pressure-based reward + two-agent decoupling + starvation-aware constraints. Updated through commit `d5a22ec`.*
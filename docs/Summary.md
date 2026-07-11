# FlowSync — Comprehensive Project Summary

> **AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning**

---

## 1. Project Overview

### What Is FlowSync?

FlowSync is a full-stack, real-time traffic simulation system that demonstrates how Deep Reinforcement Learning (DQN) can optimize traffic signal control at a 4-way city intersection. It serves as a **proof-of-concept Digital Twin** for smart-city infrastructure modernization, replacing traditional fixed-timer traffic signals with an autonomous, learning AI agent — plus a new **Manual (MNL) control mode** for human-in-the-loop operation.

**Mission:** Show that Reinforcement Learning can significantly outperform static traffic systems, reducing urban congestion, wait times, and vehicle emissions.

**Problem It Solves:**
- Traditional fixed-timer traffic signals waste time by ignoring real-time demand
- Urban congestion costs billions annually in lost productivity and fuel
- Municipalities lack low-risk tools to evaluate AI traffic control before real-world deployment
- FlowSync provides a sandbox to train, test, and compare AI vs. traditional vs. manual control

### Target Audience

- **Researchers & Students** studying Reinforcement Learning (RL) applications
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

**Active Development / MVP.** The project is fully functional with a landing page, 3D simulation dashboard, live training, manual control, and data persistence. Not yet deployed for production-scale use — designed as a demonstration/research tool.

---

## 1.1 Current Project Status — Detailed Breakdown

### What Is Working (✅ Verified Functional)

| Area | Status | Details |
|---|---|---|
| **Frontend Build** | ✅ Working | `pnpm dev` compiles, Next.js 16 App Router loads, TypeScript strict mode passes |
| **Backend Server** | ✅ Working | `uvicorn app.main:app --reload` starts on :8000, lifespan initializes Env/Agent/Trainer |
| **WebSocket Simulation** | ✅ Working | `/ws/simulation` connects, 10 Hz frames broadcast, 3D scene renders vehicles |
| **WebSocket Training** | ✅ Working | `/ws/training` connects, per-episode metrics stream, checkpoint notifications fire |
| **Fixed-Timer Control** | ✅ Working | 4-phase cycle with smart queue-based switching, yellow (2s) → red (1s) → green transitions |
| **AI (DQN) Control** | ✅ Working | Agent selects phases via `select_action(ε=0)`, reward computed, observation includes pending phase |
| **Manual (MNL) Control** | ✅ Working | 4 phase buttons, holds green indefinitely, phase changes go through yellow/red clearance |
| **Yield-on-Left Logic** | ✅ Working | Left-turners at stop line during phases 0/1 yield to oncoming straight/right traffic |
| **3-Lane Roads + Visuals** | ✅ Working | 40×6 roads, stop bars at ±3.1, zebra crossings, lane offsets (0.5/1.5/2.5), direction labels |
| **Traffic Light Arrows** | ✅ Working | ← for left phases, ↑→ for through/right, rendered inside lenses, larger/bolder |
| **Vehicle Paths** | ✅ Working | CurvePath (LineCurve3 + QuadraticBezierCurve3) with piecewise arclength mapping |
| **Vehicle Interpolation** | ✅ Working | Smooth 60 fps between 10 Hz WS updates, wheel rotation, emergency siren lights |
| **Day/Night 3D Toggle** | ✅ Working | State-driven lighting: emissive sun + bright ambient (day) vs moody directional (night) |
| **Side-by-Side Layout** | ✅ Working | Canvas left (flex-1), controls sidebar right (420px, scrollable) |
| **Live Training Dashboard** | ✅ Working | Reward/Wait/Epsilon/Loss sparklines, trend arrows, phase description, ETA, ep/min |
| **Model Checkpointing** | ✅ Working | Every 50 eps: saves to Supabase Storage + local disk, metadata upsert to `rl_models` |
| **Model Loading** | ✅ Working | Dropdown fetches `/training/models`, loads state dict into online + target networks |
| **Emergency Preemption** | ✅ Working | 4 directional buttons, spawns ambulance, forces priority phase, clears on exit |
| **Performance Comparison** | ✅ Working | Compare tab aggregates Fixed/AI/Manual wait time + throughput, improvement % |
| **Episode History** | ✅ Working | Paginated table (10/page), auto-refresh 10s during training, best episode highlighted |
| **Real-Time Metrics** | ✅ Working | MetricsPanel (2×2 animated cards), LiveSnapshot (bottom-left overlay) |
| **Supabase Persistence** | ✅ Working | Simulations, Episodes, TrafficLogs, SignalStates, PerformanceMetrics, RLModels |
| **Keep-Alive Ping** | ✅ Working | Frontend pings `/api/keep-alive` → FastAPI `/health` on mount |
| **Docker Backend** | ✅ Working | `docker-compose up` builds CPU-only PyTorch image, runs on :8000 |
| **Tests** | ✅ Passing | `pytest` runs 29 tests (api, rl, simulation) with mocked Supabase |

### Partially Working / Known Quirks (⚠️)

| Area | Status | Details |
|---|---|---|
| **Queue Length Accuracy** | ⚠️ Minor | `get_queue_lengths()` counts only `state=="waiting"` — vehicles at stop line with `can_move=false` are counted, but those already in intersection are not |
| **All-Red Clearance** | ⚠️ Tunable | Fixed at 1.0s (`red_duration`); may be too short for heavy traffic — vehicles can still be in intersection when cross-traffic gets green |
| **Manual Mode Phase Display** | ⚠️ Minor | Traffic light shows correct color but doesn't visually distinguish "manual hold" vs normal green |
| **Training While Sim Running** | ⚠️ Architectural | Trainer and Simulation share same `Intersection` instance — training reset clears active simulation vehicles |
| **WS Reconnection Storm** | ⚠️ Rare | Exponential backoff (max 5) works, but rapid reconnects can occur if backend restarts mid-session |
| **Prisma Migrations** | ⚠️ Manual | No CI migration step — `prisma db push` required after schema changes |
| **Hardcoded Render URL** | ⚠️ Config | `flowsync-gelt.onrender.com` in `utils.ts:29,32` and `next.config.ts:12-13` |

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
| **Input Validation on WS** | ❌ Partial | `set_spawn_rate` does `float(value)` without bounds check |
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

### Recent Commits Impact (Last 10)

| Commit | Date | Impact |
|---|---|---|
| `df5a3a4` | Latest | Manual (MNL) mode + WebSocket `manual_override` command |
| `926a754` | Latest | Sun emissive intensity increase for bloom rays |
| `4b390b2` | Latest | Traffic light arrows: larger, bolder, pitch black |
| `2885db9` | Latest | Environment elements scaled to 3-lane road width |
| `630aac6` | Latest | 3-lane visual road with exact stop line tracking |
| `07e3448` | Latest | `get_queue_lengths` counts only waiting vehicles |
| `6f95862` | Latest | Standard print for WS frame logs (replaced ujson) |
| `462b560` | Latest | Yield-on-left check + dynamic phase cycling fix |
| `121e66c` | Latest | Added Summary.md + ISSUES.md |
| `1edc45e` | Latest | Added ISSUES.md with 17 audit findings |

---

## 1.2 Readiness Assessment

| Criterion | Rating | Notes |
|---|---|---|
| **Demo Ready** | ✅ **Yes** | All 3 control modes work, 3D visuals polished, training visible, comparison works |
| **Hackathon Submission** | ✅ **Yes** | Impressive full-stack AI + 3D, live training, manual override for judges to try |
| **Research/Thesis Use** | ✅ **Yes** | DQN implementation correct, reproducible, metrics logged, checkpoints loadable |
| **Production Deployment** | ❌ **No** | No auth, no rate limits, free-tier infra, single-process, no CI/CD |
| **Multi-User SaaS** | ❌ **No** | Shared `Intersection` instance, no session isolation, no user accounts |
| **CI/CD Ready** | ❌ **No** | No GitHub Actions, manual `prisma db push`, no lint/test gates |

---

## 1.3 Immediate Next Steps (Priority Order)

1. **Fix Shared Environment Bug** — Give Trainer its own `TrafficEnv` copy so training doesn't reset active simulation
2. **Add Prisma Migration to CI** — Write GitHub Action: `prisma migrate deploy` + `pytest` on PR
3. **WS Message Validation** — Add Pydantic/Zod schemas for all WS commands (client + server)
4. **Rate Limiting** — Add `slowapi` or similar to FastAPI; per-IP WS connection limits
5. **Environment Variable Cleanup** — Remove hardcoded Render URL from `utils.ts`/`next.config.ts`
6. **All-Red Duration Config** — Expose `red_duration` as env var / UI slider for tuning
7. **E2E Tests** — Add Playwright/Cypress for critical user journeys (start → train → load → compare)

---

## 2. Core Features & Functionality

### 2.1 Real-Time 3D Intersection Visualization

**What:** A detailed 3D-rendered 4-way intersection with vehicles, traffic lights, roads, buildings, parks, and trees — all rendered via Three.js / React Three Fiber.

**How It Works:**
- Backend runs physics at ~10 Hz and streams JSON frames via WebSocket
- Frontend interpolates vehicle positions between frames for smooth 60 fps rendering
- Orthographic camera with orbit controls; auto-rotates while simulation is running
- Bloom + Vignette postprocessing for visual polish
- **Day/Night mode toggle** with dynamic lighting (sun with emissive rays at day, moody night lighting)
- Traffic light arrows rendered inside lenses (↑ → for through/right, ← for left-turn phases)

**User Flow:** Navigate to `/simulation` → immediately see the 3D scene → orbit/zoom with mouse → watch vehicles spawn and move.

**Priority:** ★★★★★ (core experience)

### 2.2 Fixed-Timer Signal Control

**What:** Traditional traffic signal timing with smart queue-based phase selection.

**How It Works:**
- 4 phases: NS Green, EW Green, NS Left, EW Left
- Default 8s green, 2s yellow, **1s all-red clearance**, minimum 4s green
- After minimum green, system can switch early if current phase has no waiting vehicles
- At timeout, selects the next phase in sequence that has vehicles waiting, or defaults to next sequential phase
- Turn restrictions enforced by phase (left-turn-only phases)

**User Flow:** Launch simulation → toggle to "Fixed" mode → watch traditional cycle.

**Priority:** ★★★★★ (baseline for comparison)

### 2.3 AI (DQN) Signal Control

**What:** A Deep Q-Network agent that learns optimal signal timing through trial and error.

**How It Works:**
- **State (8-dim):** queue lengths per direction (4), current phase, time in phase, signal color, normalized timestep
- **Action (discrete 4):** choose next signal phase
- **Reward function:** wait_penalty (−0.1 × total waiting) + throughput_bonus (+1.0 per passed vehicle) + switch_penalty (−0.5 for unnecessary changes) + overflow_penalty (−2.0 per lane with queue ≥ 8)
- **Terminal:** 500 timesteps per episode
- Epsilon-greedy exploration starts at 1.0, decays by 0.995 per episode, floor at 0.05
- **Observation includes pending phase** during yellow/red transitions for better learning

**User Flow:** Launch simulation → toggle "AI" mode → watch AI decisions → see live metrics improve over time.

**Priority:** ★★★★★ (core differentiator)

### 2.4 Manual (MNL) Signal Control — **NEW**

**What:** Human-in-the-loop control mode where the operator directly sets signal phases.

**How It Works:**
- Backend `TrafficSignal.tick()` receives `is_manual=true` flag
- In manual mode, the signal **holds the current green phase indefinitely** — no auto-cycling
- Frontend provides 4 phase buttons: NS Green (0), EW Green (1), NS Left (2), EW Left (3)
- User clicks a button → `manual_override` WebSocket command → backend calls `signal.set_phase(phase)` → goes through yellow (2s) → red (1s) → green for new phase
- **Yield-on-left logic still applies** during manual green phases
- Emergency override still forces priority phase

**User Flow:** Select "Manual" mode → 4 phase buttons appear → click to change phase → observe traffic response.

**Priority:** ★★★★☆ (educational/human-factors evaluation)

### 2.5 Live Training Dashboard

**What:** Watch the DQN agent learn in real-time with streaming metrics.

**How It Works:**
- Separate WebSocket (`/ws/training`) pushes per-episode metrics
- Metrics: episode number, total reward (with sparkline + trend arrow), avg wait time (sparkline), epsilon (color-coded phases), loss
- Animated stat cards with progress bars
- ETA, episodes/min speed display
- Training chart (Recharts area chart with toggleable metrics, last 100 episodes)
- Configurable episode count (1–2000)

**User Flow:** Click "Train Agent" → configure episodes → watch live metrics → monitor training chart → model auto-saves every 50 episodes.

**Priority:** ★★★★★ (key educational feature)

### 2.6 Performance Comparison (AI vs Fixed vs Manual)

**What:** Side-by-side bar charts comparing all three control modes.

**How It Works:**
- Aggregates all performance metrics from the database
- Shows avg wait time and throughput side-by-side
- Calculates and displays improvement percentage (green positive, red negative)
- Data persisted via `performance_metrics` table

**User Flow:** Run simulations in each mode → switch to "Compare" tab → view bar chart.

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

**What:** Save and load trained model checkpoints.

**How It Works:**
- Checkpoints saved every 50 episodes (configurable)
- Dual storage: Supabase Storage (`model-checkpoints` bucket) + local disk fallback
- Model metadata upserted into `rl_models` table (prevents duplicates per run)
- "Load Model" dropdown in Training Controls panel
- Loading a model sets its state dict into the agent's online + target networks

**User Flow:** Train agent → checkpoints auto-save → click "Load Model" → select checkpoint → run AI mode inference with loaded weights.

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
3. Click a button → signal transitions through yellow (2s) → red (1s) → green for selected phase
4. Signal holds that green indefinitely until next manual override
5. Yield-on-left logic still applies during green phases

### 3.2 Background Jobs / Scheduled Operations

| Task | Trigger | Frequency | Description |
|---|---|---|---|
| **Simulation loop** | WebSocket first client connect | Continuous (~10 Hz) | Physics tick, vehicle movement, signal logic |
| **Training loop** | User starts training | Per-episode (~100ms each) | DQN training, reward calc, network updates |
| **DB buffer flush** | Every 10 samples | ~50s during simulation | Flush buffered traffic logs + signal states to Supabase |
| **Checkpoint save** | Every 50 episodes | During training | Save model state dict to Supabase Storage + disk |
| **Target network sync** | Every 500 steps | During training | Copy online network weights to target network |
| **Keep-alive ping** | Frontend mount | Once on page load | Wake backend from cold start |

### 3.3 Data Flows

#### Real-Time Simulation Flow
```
Backend (Intersection.tick) ──[10 Hz JSON frame]──WebSocket──▶ Frontend (Three.js render)
     │                                                            │
     │ [every ~5s]                                               │ [mouse/keyboard]
     ▼                                                            ▼
  DB Buffer (traffic_logs + signal_states) ──[~50s flush]──▶ Supabase PostgreSQL
```

#### Training Flow
```
DQN Agent (select_action) → Environment (step) → Replay Buffer (push)
                                                         │
                                                    [every 4 steps]
                                                         ▼
                                                  Train Step (sample + backprop)
                                                         │
                                                    [every 50 episodes]
                                                         ▼
                                              Save Checkpoint → Supabase Storage
                                              Save Metadata  → rl_models table
                                              Broadcast via → Training WebSocket
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
- **Server → Client (10 Hz):** `SimulationFrame` JSON — timestep, mode, signal state, all vehicle positions/states, queue lengths, metrics
- **Client → Server (commands):**
  - `{"command": "start"}`
  - `{"command": "stop"}`
  - `{"command": "reset"}`
  - `{"command": "set_mode", "mode": "fixed" \| "ai" \| "manual"}`
  - `{"command": "set_spawn_rate", "value": 0.1-1.0}`
  - `{"command": "emergency_override", "lane": "north"\|"south"\|"east"\|"west"}`
  - `{"command": "manual_override", "phase": 0-3}` — **NEW**

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
  │     ├── id               (String, PK)
  │     ├── simulationId     (FK → Simulation)
  │     ├── mode             (String)
  │     ├── avgWaitTimeFixed (Float?)
  │     ├── avgWaitTimeAI    (Float?)
  │     ├── throughputFixed  (Int?)
  │     ├── throughputAI     (Int?)
  │     └── improvementPct   (Float?)
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
  ├── simulationId (String — no FK constraint)
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
```

#### Key Relationships
- **Simulation 1:N Episode** — Each simulation can have many training episodes
- **Simulation 1:N PerformanceMetric** — Each simulation creates one performance metric
- **Simulation 1:N TrafficLog** — Sampled traffic data per timestep
- **SignalState** — No formal FK; stored with simulationId for querying
- **RLModel** — Standalone; model_id reuses simulation UUID

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
| **Fixed deployment URLs** | Low | Backend URL hardcoded as `flowsync-gelt.onrender.com` in client/src/lib/utils.ts. |
| **No Prisma migrations in CI** | Low | DB schema must be applied manually via `prisma db push`. |
| **No input validation on spawn rate** | Low | Slider is 0.1–1.0 but WS handler does `float(value)` without clamp. |

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
| **Edge Deployment** | Long-term | Run the AI core on local traffic controller hardware |
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
| `ppt.txt` | 8-slide technical presentation outline |
| `ISSUES.md` | Full-stack audit findings (17 issues across 7 layers) |

### Client Config Files

| File | Purpose |
|---|---|
| `package.json` | Next.js 16.2.6 project with all frontend dependencies |
| `next.config.ts` | Image optimization, env defaults (production backend URL), compression, strict mode |
| `tsconfig.json` | TypeScript config: ES2017 target, strict mode, bundler module resolution, `@/` → `./src/*` alias |
| `postcss.config.mjs` | PostCSS config using `@tailwindcss/postcss` |
| `eslint.config.mjs` | ESLint v9 flat config using `eslint-config-next` core-web-vitals and typescript presets |
| `components.json` | shadcn/ui configuration: Radix Nova style, RSC enabled, neutral base color, lucide icons, custom path aliases |
| `prisma/schema.prisma` | Database schema with 6 models (Simulation, Episode, SignalState, TrafficLog, RLModel, PerformanceMetric) |
| `next-env.d.ts` | Auto-generated Next.js type references |

### Client Source Files

| File | Purpose |
|---|---|
| `src/app/globals.css` | Tailwind v4 with custom theme variables (light/dark), shadcn/ui integration, scrollbar custom styles |
| `src/app/layout.tsx` | Root layout with Geist fonts, TooltipProvider, KeepAlivePing component, Providers wrapper |
| `src/app/providers.tsx` | Client component that initializes TanStack React Query's QueryClient |
| `src/app/page.tsx` | Landing page with 5 sections: hero header, "How it works" (Simulate-Train-Compare), feature cards, tech stack display, CTA |
| `src/app/simulation/page.tsx` | **UPDATED** Main simulation dashboard — side-by-side layout: left 3D canvas, right sidebar (controls, metrics, analytics tabs) |
| `src/app/api/simulations/route.ts` | GET — returns 20 most recent simulations from Prisma |
| `src/app/api/models/route.ts` | GET — returns all RL models from Prisma (descending by creation) |
| `src/app/api/metrics/route.ts` | GET — returns performance metrics, optional `?simulationId` filter (max 100) |
| `src/app/api/episodes/route.ts` | GET — returns episodes, optional `?simulationId` filter (max 500) |
| `src/app/api/keep-alive/route.ts` | GET — pings FastAPI backend's `/health` endpoint to prevent cold starts |
| `src/types/simulation.ts` | **UPDATED** TypeScript interfaces: `SimulationMode` now includes `"manual"`, `VehicleState.turn` now required |
| `src/store/simulationStore.ts` | Zustand store managing connection/running/training state, current frame, training metrics (capped at 1000) |
| `src/lib/utils.ts` | `cn()` class merging, `getFastApiUrls()` — environment-aware backend URL resolution |
| `src/lib/prisma.ts` | Singleton PrismaClient instance for server-side database access |

#### Hooks

| File | Purpose |
|---|---|
| `src/hooks/useSimulationSocket.ts` | WebSocket hook for `/ws/simulation` — auto-connect, exponential backoff retry (max 5), frame logging, `sendCommand()` |
| `src/hooks/useTrainingSocket.ts` | WebSocket hook for `/ws/training` — same reconnect strategy, handles training metric streaming |
| `src/hooks/useSimulations.ts` | React Query hook fetching `/api/simulations` |
| `src/hooks/useEpisodes.ts` | React Query hook fetching episodes, auto-refreshes every 10s |

#### Control Components

| File | Purpose |
|---|---|
| `src/components/controls/SimulationControls.tsx` | **UPDATED** Three-mode toggle (Fixed/Manual/AI) with debounce, Start/Stop/Reset buttons, vehicle arrival rate slider, emergency vehicle preemption panel (4 directional buttons + active status display), connection/running status indicator |
| `src/components/controls/TrainingControls.tsx` | Training panel with Train Agent button (config modal 1-2000 episodes), live training metrics display with animated stat cards (reward, avg wait, epsilon, loss), progress bar + ETA + episodes/min speed, Load Model dropdown (fetches from `/training/models`), model loading with success/error feedback |

#### Simulation (3D) Components

| File | Purpose |
|---|---|
| `src/components/simulation/SimulationCanvas.tsx` | **UPDATED** Three.js canvas setup — orthographic camera, multi-light setup, OrbitControls with auto-rotate, Bloom + Vignette postprocessing, **Day/Night mode toggle**, status overlay, bottom legend |
| `src/components/simulation/IntersectionScene.tsx` | **UPDATED** Main 3D scene composing: IntersectionGrid, Roads (horizontal + vertical), 4 TrafficLights with `resolveLightColor` that distinguishes left-turn phases (`left-green`, `left-yellow`), floating holographic queue count labels (color-coded: cyan<5, yellow<8, red≥8), Vehicle instances mapped from frame data |
| `src/components/simulation/IntersectionGrid.tsx` | **UPDATED** Detailed 3D environment: 45×45 ground plane, 4 corner zones (NW/SE parks with trees, NE/SW city blocks with neon skyscrapers), scaled for new 40-unit roads |
| `src/components/simulation/Road.tsx` | **UPDATED** 3-lane roads (40 units long, 6 units wide) with: asphalt base, double yellow center lines (split at intersection), white stop bars (6 units wide), zebra crossing stripes, directional text labels (EASTBOUND, WESTBOUND, SOUTHBOUND, NORTHBOUND) |
| `src/components/simulation/TrafficLight.tsx` | **UPDATED** Complex 3D traffic light with: cantilever pole + bracket arm, single housing with 3 lens spheres (red/yellow/green) with emissive glow, **arrows inside lenses** (↑→ for through/right, ← for left-turn phases), point lights matching active color, CCTV camera unit with blinking status LED, direction-specific positioning |
| `src/components/simulation/Vehicle.tsx` | **UPDATED** 3D vehicle system with: 6 types (sedan, suv, hatchback, sportscar, bike, ambulance), hash-based color diversity, **CurvePath-based paths** (LineCurve3 for straight, QuadraticBezierCurve3 for turns) with **piecewise arclength mapping** from backend [0,1] position to visual parameter, smooth position interpolation between WS updates, dynamic wheel rotation, emergency vehicle siren lights (alternating red/blue with point lights) |

#### Dashboard Components

| File | Purpose |
|---|---|
| `src/components/dashboard/AIStatusBadge.tsx` | Shows Training/Ready/Idle status based on training state |
| `src/components/dashboard/LiveSnapshot.tsx` | Real-time stats panel: connection/running/mode badges, training pulse badge, grid: Last Frame time, Active Vehicles, Avg Wait Time, Max Queue, "CCTV AI Scanner" card with vehicle detection count |
| `src/components/dashboard/TrainingChart.tsx` | Recharts area chart with 4 toggleable metrics: Reward (cyan), Avg Wait (orange), Epsilon (yellow), Loss (purple), last 100 episodes, interactive summary cards |
| `src/components/dashboard/MetricsPanel.tsx` | 2×2 card grid: Avg Wait Time, Throughput, Max Queue, Episode. Animated numbers, progress bars, SVG sparklines (20-point rolling) |
| `src/components/dashboard/EpisodeHistory.tsx` | Paginated table (10/page): Episode #, Reward (color-coded), Wait Time, Throughput, Epsilon, Duration. Best episode highlighted green. Live training indicator. |
| `src/components/dashboard/ComparisonChart.tsx` | Bar chart comparing Fixed vs AI vs Manual: Avg Wait Time and Throughput, improvement percentage display (green positive, red negative) |

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
| `server/app/main.py` | FastAPI application entry point: lifespan creates TrafficEnv, DQNAgent, Trainer; stores in app_state dict; CORS middleware with allowlist + regex fallback; includes 3 routers; registers 2 WebSocket routes; `/` and `/health` endpoints |
| `server/app/config.py` | Pydantic Settings: loads `SUPABASE_URL`, `supabase_service_key` (with alias resolution from 4 env var names), `CORS_ORIGINS`; validates service key is admin-level (decodes JWT, checks `role=service_role`) |
| `server/app/routers/simulation.py` | REST endpoints: POST `/simulation/start`, POST `/simulation/stop`, POST `/simulation/reset`, PUT `/simulation/mode`, GET `/simulation/status` (MetricsSnapshot) |
| `server/app/routers/training.py` | REST endpoints: POST `/training/start`, POST `/training/stop`, GET `/training/status`, GET `/training/models`, POST `/training/load` |
| `server/app/routers/metrics.py` | REST endpoint: GET `/metrics/current` (MetricsSnapshot) |
| `server/app/schemas/simulation_schema.py` | Pydantic models: `VehicleState`, `SimulationFrame`, `build_frame()` |
| `server/app/schemas/training_schema.py` | Pydantic models: `TrainingMetric`, `StartTrainingRequest` |
| `server/app/schemas/metrics_schema.py` | `MetricsSnapshot`: avg_wait_time, throughput, max_queue, current_phase, is_training, current_episode, epsilon |

#### Services

| File | Purpose |
|---|---|
| `server/app/services/supabase_service.py` | All DB writes: `create_simulation`, `update_simulation`, `save_episode`, `save_traffic_logs_bulk`, `save_signal_states_bulk`, `save_performance_metric`, `save_model_metadata` (upsert), `set_active_model`. All sync, called via `asyncio.to_thread`. Error logging on every failure. |
| `server/app/services/model_service.py` | Checkpoint management: `save_checkpoint` (local disk + Supabase Storage), `load_checkpoint` (Storage with local fallback), `list_checkpoints`, `list_all_models` (3-tier: DB → Storage listing → local disk, deduplicated) |

#### Simulation Engine

| File | Purpose |
|---|---|
| `server/app/simulation/environment.py` | Gymnasium RL environment (`TrafficEnv`): 8-dim observation (queue lengths×4, phase, time_in_phase, color_val, normalized_timestep), Discrete(4) action space. `reset()` resets intersection, `step(action)` advances simulation, computes reward (wait_penalty + throughput_bonus + switch_penalty + overflow_penalty), terminal at 500 steps. **Observation includes pending phase** during yellow/red transitions. |
| `server/app/simulation/intersection.py` | **MAJOR UPDATE** Core traffic intersection: 12 lanes (4 directions × 3 turns), TrafficSignal, PoissonSpawner, timestep counter, intersection reservation system (by direction group: NS vs EW), emergency override. **`get_queue_lengths()` now counts only `state=="waiting"` vehicles**. **Yield-on-left logic**: left-turning vehicles at stop line during phases 0/1 must yield to oncoming straight/right traffic. **Per-lane queues** with `_spawned_this_interval` / `_passed_this_interval` counters for telemetry. |
| `server/app/simulation/vehicle.py` | Vehicle dataclass: id, lane (direction), turn, position, wait_time, speed, state, is_emergency. `tick(dt, can_move)` moves vehicle at DEFAULT_SPEED (0.12) if allowed, tracks wait time, transitions to "passed" at position ≥ 1.0 |
| `server/app/simulation/traffic_signal.py` | **MAJOR UPDATE** Traffic signal logic: 4 phases (NS_GREEN, EW_GREEN, NS_LEFT, EW_LEFT), 3 colors (GREEN, YELLOW, RED). **Added `red_duration=1.0` for all-red clearance**. **Manual mode support**: `is_manual` flag holds current green indefinitely. Phase-to-lane mapping and allowed turns per phase. Fixed timing: 8s green default, 2s yellow, 1s red, 4s minimum green. Smart phase selection (highest queue after minimum green). AI phase requests go through yellow-red-green transition. `is_green_for(lane, turn)` checks phase + color + turn restrictions. |
| `server/app/simulation/spawner.py` | **UPDATED** `PoissonSpawner`: configurable λ (default 0.3), spawns into one random direction per tick, 50% straight / 25% left / 25% right, max 10 vehicles per lane. Lanes now keyed by `{direction}_{turn}`. |
| `server/app/simulation/metrics.py` | `MetricsTracker`: rolling calculation of avg_wait_time, avg_throughput, avg_queue_length with running totals. (Currently unused but retained) |

#### Reinforcement Learning

| File | Purpose |
|---|---|
| `server/app/rl/dqn_network.py` | Neural network architecture: 3 hidden layers — Linear(8,128) → ReLU → Linear(128,128) → ReLU → Linear(128,64) → ReLU → Linear(64,4) |
| `server/app/rl/dqn_agent.py` | DQN Agent: online + target networks, Adam optimizer, MSELoss. `select_action(state, epsilon)` — epsilon-greedy. `train_step(batch)` — Q-learning targets with γ=0.95. `sync_target_network()` — copies online weights to target. `save()` / `load()` — PyTorch state dict serialization. |
| `server/app/rl/replay_buffer.py` | Deque-based buffer (max 10,000 transitions). `push(state, action, reward, next_state, done)`. `sample(batch_size)` — returns batched torch tensors. |
| `server/app/rl/hyperparams.py` | Dataclass: lr=1e-3, γ=0.95, ε_start=1.0, ε_end=0.05, ε_decay=0.995, batch_size=64, replay_buffer=10000, target_update_freq=500, max_steps=500, episodes=500, min_replay_size=64 |
| `server/app/rl/trainer.py` | Training orchestrator: async episodes loop. Every 4th step: sample buffer → train (via `asyncio.to_thread`). Target sync every 500 steps. Yields event loop every 10 steps. Episode completion: saves to Supabase, broadcasts via WebSocket. Checkpoint every 50 episodes: saves model + metadata. Epsilon decay per episode. Rolling 50-episode reward window for metadata. |

#### WebSocket Handlers

| File | Purpose |
|---|---|
| `server/app/websockets/simulation_ws.py` | Simulation WebSocket: ConnectionManager for multi-client broadcast. Main loop at 10 Hz. Fixed mode: `intersection.tick(action=None)`. AI mode: `env._get_obs()` → `agent.select_action(ε=0)` → `env.step()`. **Manual mode**: `intersection.tick(action=None, is_manual=True)`. DB sampling every 50 ticks, flushing every 10 samples. Handles 7 commands (start, stop, reset, set_mode, set_spawn_rate, emergency_override, **manual_override**). Flushes buffer on cancel/crash. |
| `server/app/websockets/training_ws.py` | Training WebSocket: separate ConnectionManager. `broadcast_training_metric()` used by Trainer. Handles start_training/stop_training commands. Creates simulation record if needed. |

### Server Config Files

| File | Purpose |
|---|---|
| `server/requirements.txt` | Production dependencies (11 packages) |
| `server/requirements-dev.txt` | Test dependencies (pytest, pytest-asyncio, pytest-cov, httpx, pytest-mock) |
| `server/pytest.ini` | Pytest config: asyncio auto mode, coverage on `app/`, term-missing report |
| `server/runtime.txt` | Python 3.11.9 version pin |
| `server/SUPABASE_KEYS_SETUP.txt` | Detailed Supabase key setup guide explaining service_role vs anon key distinction |
| `server/Dockerfile` | Multi-stage Docker build: python:3.11-slim, installs build deps, CPU-only PyTorch, runs uvicorn on port 8000 |

### Tests

| File | Purpose |
|---|---|
| `server/tests/conftest.py` | Pytest fixtures: `mock_supabase`, `mock_model_service`, `client` (FastAPI TestClient with lifespan), `app_state` |
| `server/tests/api/test_main.py` | Tests root (`/`) and `/health` endpoints |
| `server/tests/api/test_simulation.py` | Tests start/stop/reset/set_mode/get_status — 5 test functions |
| `server/tests/api/test_training.py` | Tests start/stop/status/models — 4 test functions |
| `server/tests/rl/test_replay_buffer.py` | Tests buffer push and sample — 2 test functions |
| `server/tests/rl/test_dqn_agent.py` | Tests init, random action, greedy action, train_step — 4 test functions |
| `server/tests/simulation/test_vehicle.py` | Tests init, movement, waiting, passed state — 4 test functions |
| `server/tests/simulation/test_traffic_signal.py` | Tests init, phase change, yellow→red→green transitions, fixed duration rollover, green permission — 6 test functions |

---

## Appendix: Git History Summary (30+ Commits)

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
| **Recent** | `f042669`, `7ad81e8`, `7ca7d8c` | Emergency preemption UI, multi-vehicle intersection locks, 3D lighting fixes with CCTV cameras |
| **Latest** | `df5a3a4`...`462b560` | **Manual (MNL) mode**, 3-lane roads, yield-on-left, vehicle interpolation fixes, traffic light arrows, environment scaling, get_queue_lengths fix |

---

*Generated: 2026-07-11 — Comprehensive project analysis of FlowSync (updated with Manual mode, 3-lane roads, yield-on-left, 3D visual overhaul, and side-by-side layout)*
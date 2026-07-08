# FlowSync — Comprehensive Project Summary

> **AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning**

---

## 1. Project Overview

### What Is FlowSync?

FlowSync is a full-stack, real-time traffic simulation system that demonstrates how Deep Reinforcement Learning (DQN) can optimize traffic signal control at a 4-way city intersection. It serves as a **proof-of-concept Digital Twin** for smart-city infrastructure modernization, replacing traditional fixed-timer traffic signals with an autonomous, learning AI agent.

**Mission:** To show that Reinforcement Learning can significantly outperform static traffic systems, reducing urban congestion, wait times, and vehicle emissions.

**Problem It Solves:**
- Traditional fixed-timer traffic signals waste time by ignoring real-time demand
- Urban congestion costs billions annually in lost productivity and fuel
- Municipalities lack low-risk tools to evaluate AI traffic control before real-world deployment
- FlowSync provides a sandbox to train, test, and compare AI vs. traditional control

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

**Active Development / MVP.** The project is fully functional with a landing page, 3D simulation dashboard, live training, and data persistence. Not yet deployed for production-scale use — designed as a demonstration/research tool.

---

## 2. Core Features & Functionality

### 2.1 Real-Time 3D Intersection Visualization

**What:** A detailed 3D-rendered 4-way intersection with vehicles, traffic lights, roads, buildings, parks, and trees — all rendered via Three.js / React Three Fiber.

**How It Works:**
- Backend runs physics at ~10 Hz and streams JSON frames via WebSocket
- Frontend interpolates vehicle positions between frames for smooth 60 fps rendering
- Orthographic camera with orbit controls; auto-rotates while simulation is running
- Bloom + Vignette postprocessing for visual polish

**User Flow:** Navigate to `/simulation` → immediately see the 3D scene → orbit/zoom with mouse → watch vehicles spawn and move.

**Priority:** ★★★★★ (core experience)

### 2.2 Fixed-Timer Signal Control

**What:** Traditional traffic signal timing with smart queue-based phase selection.

**How It Works:**
- 4 phases: NS Green, EW Green, NS Left, EW Left
- Default 8s green, 2s yellow, minimum 4s green
- After minimum green, system can switch early if current phase has no waiting vehicles
- At timeout, selects the phase with the highest queue count (not just round-robin)
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

**User Flow:** Launch simulation → toggle "AI" mode → watch AI decisions → see live metrics improve over time.

**Priority:** ★★★★★ (core differentiator)

### 2.4 Live Training Dashboard

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

### 2.5 Performance Comparison (AI vs Fixed)

**What:** Side-by-side bar charts comparing AI-controlled vs fixed-timer performance.

**How It Works:**
- Aggregates all performance metrics from the database
- Shows avg wait time and throughput side-by-side
- Calculates and displays improvement percentage (green positive, red negative)
- Data persisted via `performance_metrics` table

**User Flow:** Run simulations in both modes → switch to "Compare" tab → view bar chart.

**Priority:** ★★★★☆ (proves value)

### 2.6 Episode History

**What:** Paginated table of all training episodes with color-coded rewards.

**How It Works:**
- Fetches from `/api/episodes` (Next.js API route → Prisma)
- Auto-refreshes every 10 seconds during training
- Columns: Episode #, Reward (color-coded), Wait Time, Throughput, Epsilon, Duration
- Best episode highlighted in green
- 10 per page with pagination

**User Flow:** Switch to "History" tab → browse episodes → identify best-performing episode.

**Priority:** ★★★☆☆

### 2.7 Real-Time Metrics Panel

**What:** Live stats updating during simulation.

**How It Works:**
- 2×2 card grid showing avg wait time, throughput, max queue, episode
- Animated number transitions, progress bars, SVG sparklines
- 20-point rolling history displayed per metric
- Live Snapshot panel (bottom-left overlay) shows connection status, active vehicles, etc.

**User Flow:** Watch metrics update live as simulation runs.

**Priority:** ★★★★☆

### 2.8 Model Persistence & Loading

**What:** Save and load trained model checkpoints.

**How It Works:**
- Checkpoints saved every 50 episodes (configurable)
- Dual storage: Supabase Storage (`model-checkpoints` bucket) + local disk fallback
- Model metadata upserted into `rl_models` table (prevents duplicates per run)
- "Load Model" dropdown in Training Controls panel
- Loading a model sets its state dict into the agent's online + target networks

**User Flow:** Train agent → checkpoints auto-save → click "Load Model" → select checkpoint → run AI inference with loaded weights.

**Priority:** ★★★★☆

### 2.9 Emergency Vehicle Preemption

**What:** Spawn emergency vehicles that force priority green lights.

**How It Works:**
- 4 directional buttons in the control panel (North/South/East/West)
- Spawns an emergency vehicle with siren lights (red/blue alternating) and point lights
- Forces the traffic signal to the priority phase immediately
- Skips normal RL/fixed control while emergency is active
- Only one emergency vehicle per lane at a time

**User Flow:** Click "Emergency" button for a direction → watch emergency vehicle spawn → see signals change → ambulance clears intersection.

**Priority:** ★★★☆☆ (showcase feature)

### 2.10 Configurable Traffic Flow

**What:** Slider to adjust vehicle arrival rate.

**How It Works:**
- Poisson distribution spawner (default λ = 0.3)
- Slider range: 0.1–1.0
- 50% straight, 25% left, 25% right turn probability
- Max 10 vehicles per lane
- Spawns into one random lane per tick

**User Flow:** Drag slider → see traffic density change immediately.

**Priority:** ★★★☆☆

### 2.11 Keep-Alive Ping

**What:** Prevents backend cold-start on free-tier hosting.

**How It Works:**
- Frontend `KeepAlivePing` component pings `/api/keep-alive` on mount
- The Next.js API route forwards to FastAPI `/health`
- Replaced an earlier Vercel cron job approach

**Priority:** ★★☆☆☆ (infrastructure)

### 2.12 Dark Theme UI

**What:** Comprehensive dark mode with cyberpunk aesthetic.

**How It Works:**
- Tailwind v4 custom CSS variables for light/dark
- Semi-transparent glassmorphism panels (backdrop-blur)
- Animated borders, glow effects, and floating holographic queue labels
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
4. Watch queue lengths, wait times, and throughput on the right panel
5. Click **Stop** — simulation pauses, metrics finalized
6. Click **Reset** — intersection clears

#### Journey B: Compare AI vs Fixed Control
1. Start simulation in **Fixed mode** → let it run for a while → Stop
2. Toggle to **AI mode** → Start again → let it run → Stop
3. Switch to **Compare tab** → side-by-side bar chart shows wait time and throughput
4. Improvement percentage displayed if data exists

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
| `PUT` | `/simulation/mode` | Toggle fixed/ai mode | `{"mode": "fixed" \| "ai"}` | `{"mode": "fixed" \| "ai"}` |
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
  - `{"command": "set_mode", "mode": "fixed" | "ai"}`
  - `{"command": "set_spawn_rate", "value": 0.1-1.0}`
  - `{"command": "emergency_override", "lane": "north"|"south"|"east"|"west"}`

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
  ├── mode          (String: "fixed" | "ai")
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

- No user accounts or PII is collected
- Simulation data persists indefinitely (no retention policy configured)
- The Supabase project is on the free tier (500 MB database, 1 GB storage)
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
| **This Summary** | `Summary.md` | Comprehensive project analysis |

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
| **V2X Integration** | Long-term | Communicate directly with smart vehicles |
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
| `ppt.txt` | 8-slide presentation outline (abstract, modules, requirements, architecture, algorithms, working, features, future scope) |

### Client (`client/`) — Next.js Frontend

#### Configuration Files

| File | Purpose |
|---|---|
| `package.json` | Dependencies: Next.js 16, React 19, Three.js, Tailwind v4, shadcn/ui, Zustand, TanStack Query, Recharts, Framer Motion |
| `next.config.ts` | Image optimization, env defaults (production backend URL), strict mode, compression |
| `tsconfig.json` | TypeScript config: ES2017 target, strict mode, `@/` → `./src/*` alias |
| `postcss.config.mjs` | PostCSS with `@tailwindcss/postcss` |
| `eslint.config.mjs` | ESLint v9 flat config (Next.js core-web-vitals + TS presets) |
| `components.json` | shadcn/ui config: Nova style, RSC enabled, neutral base, lucide icons |
| `prisma/schema.prisma` | Database schema with 6 models (details in §5.1) |
| `next-env.d.ts` | Auto-generated Next.js type references |

#### Source Files

| File | Purpose |
|---|---|
| `src/app/globals.css` | Tailwind v4 with custom theme variables (light/dark), shadcn/ui integration, scrollbar styles |
| `src/app/layout.tsx` | Root layout — Geist fonts, TooltipProvider, KeepAlivePing, QueryClient Provider |
| `src/app/providers.tsx` | Client component — initializes TanStack React Query's QueryClient |
| `src/app/page.tsx` | Landing page — hero, "How it works" (Simulate-Train-Compare), feature cards, tech stack, CTA |
| `src/app/simulation/page.tsx` | Main dashboard — Three.js canvas background, right sidebar (controls + metrics + analytics tabs), bottom-left Live Snapshot |
| `src/app/api/simulations/route.ts` | GET — returns 20 most recent simulations via Prisma |
| `src/app/api/models/route.ts` | GET — returns all RL models (descending by creation) via Prisma |
| `src/app/api/metrics/route.ts` | GET — returns performance metrics, optional `?simulationId` filter (max 100) |
| `src/app/api/episodes/route.ts` | GET — returns episodes, optional `?simulationId` filter (max 500) |
| `src/app/api/keep-alive/route.ts` | GET — pings FastAPI `/health` to prevent backend cold start |
| `src/types/simulation.ts` | TypeScript interfaces: `SimulationMode`, `VehicleState`, `SimulationFrame`, `TrainingMetric` |
| `src/store/simulationStore.ts` | Zustand store — connection/running/training state, current frame, training metrics (capped at 1000), action methods |
| `src/lib/utils.ts` | `cn()` class merging, `getFastApiUrls()` — environment-aware backend URL resolution |
| `src/lib/prisma.ts` | Singleton PrismaClient (prevents hot-reload connection leaks) |

#### Hooks

| File | Purpose |
|---|---|
| `src/hooks/useSimulationSocket.ts` | WebSocket hook for `/ws/simulation` — auto-connect, exponential backoff retry (max 5), frame logging, `sendCommand()` |
| `src/hooks/useTrainingSocket.ts` | WebSocket hook for `/ws/training` — same reconnect strategy, handles training metric streaming |
| `src/hooks/useSimulations.ts` | React Query hook — fetches `/api/simulations` |
| `src/hooks/useEpisodes.ts` | React Query hook — fetches episodes, auto-refresh every 10s |

#### Control Components

| File | Purpose |
|---|---|
| `src/components/controls/SimulationControls.tsx` | Start/Stop/Reset buttons, mode toggle (Fixed/AI) with debounce, spawn rate slider, emergency override buttons (4 directions), status indicators |
| `src/components/controls/TrainingControls.tsx` | Train Agent button with config modal (1-2000 episodes), live training stats (reward with trend + sparkline, avg wait, epsilon phases, loss), progress bar + ETA + speed, Load Model dropdown with success/error feedback |

#### Simulation (3D) Components

| File | Purpose |
|---|---|
| `src/components/simulation/SimulationCanvas.tsx` | Three.js canvas — orthographic camera (zoom 45), multi-light setup (ambient + 2 directional + hemisphere), OrbitControls with auto-rotate, Bloom + Vignette postprocessing, status overlay, bottom legend |
| `src/components/simulation/IntersectionScene.tsx` | Main scene composer — grid, roads, traffic lights, floating holographic queue labels (color-coded: cyan <5, yellow <8, red >=8), vehicle instances |
| `src/components/simulation/IntersectionGrid.tsx` | Ground plane + 4 corner zones: NW/SE parks (grass, trees), NE/SW city blocks (neon skyscrapers with cyan/amber/purple stripes) |
| `src/components/simulation/Road.tsx` | Detailed 3D road — asphalt base, double yellow lines, white stop bars, zebra crossings (7 stripes), directional text labels (EASTBOUND, WESTBOUND, etc.) |
| `src/components/simulation/TrafficLight.tsx` | Cantilever pole + bracket arm, housing with 3 lens spheres (red/yellow/green) with emissive glow, point lights, CCTV camera with blinking LED, direction-specific positioning |
| `src/components/simulation/Vehicle.tsx` | 6 vehicle types (sedan, suv, hatchback, sportscar, bike, ambulance), hash-based color selection, cubic Bezier path curves per turn, position interpolation, wheel rotation, emergency siren lights (red/blue alternating + point lights) |

#### Dashboard Components

| File | Purpose |
|---|---|
| `src/components/dashboard/AIStatusBadge.tsx` | Training/Ready/Idle status badge |
| `src/components/dashboard/LiveSnapshot.tsx` | Real-time stats — connection/running/mode badges, training pulse, last frame time, active vehicles, avg wait, max queue, "CCTV AI Scanner" detection count |
| `src/components/dashboard/TrainingChart.tsx` | Recharts area chart — 4 toggleable metrics (reward cyan, avg wait orange, epsilon yellow, loss purple), last 100 episodes, summary cards |
| `src/components/dashboard/MetricsPanel.tsx` | 2x2 card grid — avg wait time, throughput, max queue, episode. Animated numbers, progress bars, SVG sparklines (20-point rolling) |
| `src/components/dashboard/EpisodeHistory.tsx` | Paginated table (10/page) — episode #, reward (color-coded), wait time, throughput, epsilon, duration. Best episode green highlight. Live training indicator. |
| `src/components/dashboard/ComparisonChart.tsx` | Bar chart — Fixed vs AI avg wait + throughput, improvement % (green positive, red negative). Aggregates all performance metrics. |

#### Layout Components

| File | Purpose |
|---|---|
| `src/components/layout/Header.tsx` | Top bar — FlowSync branding, connection status badge (green/red), current mode badge |
| `src/components/layout/KeepAlivePing.tsx` | Pings `/api/keep-alive` on mount to prevent backend cold start |

#### shadcn/ui Components

| File | Purpose |
|---|---|
| `src/components/ui/badge.tsx` | Badge component with variants (default, secondary, destructive, outline) |
| `src/components/ui/button.tsx` | Button with variants (default, destructive, outline, secondary, ghost, link) and sizes |
| `src/components/ui/card.tsx` | Card layout components (Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter) |
| `src/components/ui/chart.tsx` | Chart container with Recharts integration, custom tooltip, legend |
| `src/components/ui/scroll-area.tsx` | Scrollable container with Radix ScrollArea primitive |
| `src/components/ui/select.tsx` | Select dropdown with Radix Select primitive |
| `src/components/ui/separator.tsx` | Horizontal/vertical divider |
| `src/components/ui/slider.tsx` | Range slider with Radix Slider primitive |
| `src/components/ui/switch.tsx` | Toggle switch with Radix Switch primitive |
| `src/components/ui/table.tsx` | Table component (Table, TableHeader, TableBody, TableRow, TableHead, TableCell) |
| `src/components/ui/tabs.tsx` | Tab navigation with Radix Tabs primitive |
| `src/components/ui/tooltip.tsx` | Tooltip with Radix Tooltip primitive |

### Server (`server/`) — FastAPI Backend

#### Configuration

| File | Purpose |
|---|---|
| `requirements.txt` | Production dependencies (11 packages) |
| `requirements-dev.txt` | Test dependencies (pytest, pytest-asyncio, pytest-cov, httpx, pytest-mock) |
| `pytest.ini` | Pytest config: asyncio auto-mode, coverage on `app/`, term-missing report |
| `runtime.txt` | Python 3.11.9 version pin |
| `SUPABASE_KEYS_SETUP.txt` | Guide explaining service_role vs anon key distinction |
| `Dockerfile` | Multi-stage build — python:3.11-slim, build deps, CPU-only PyTorch, uvicorn on port 8000 |

#### Application Core

| File | Purpose |
|---|---|
| `app/__init__.py` | Empty package init |
| `app/main.py` | FastAPI entry — lifespan creates TrafficEnv, DQNAgent, Trainer; stores in app_state dict; CORS with allowlist + regex; registers 3 routers + 2 WebSocket routes; `/` and `/health` endpoints |
| `app/config.py` | Pydantic Settings — loads `SUPABASE_URL`, `supabase_service_key` (with alias resolution from 4 env var names), `CORS_ORIGINS`; validates service key is admin-level (decodes JWT, checks `role=service_role`); default CORS origins include Vercel URLs + localhost |

#### Routers

| File | Purpose |
|---|---|
| `app/routers/simulation.py` | 5 endpoints: POST `/start` (reset + create simulation record), POST `/stop` (update simulation), POST `/reset` (clear intersection), PUT `/mode` (toggle fixed/ai), GET `/status` (MetricsSnapshot) |
| `app/routers/training.py` | 5 endpoints: POST `/start` (async training with configurable episodes), POST `/stop` (graceful stop + cancel task), GET `/status` (trainer state), GET `/models` (all saved models), POST `/load` (load checkpoint into agent) |
| `app/routers/metrics.py` | 1 endpoint: GET `/current` (returns MetricsSnapshot) |

#### Schemas

| File | Purpose |
|---|---|
| `app/schemas/simulation_schema.py` | Pydantic models: `VehicleState` (id, lane, turn, position, state, wait_time, is_emergency), `SimulationFrame` (complete frame), `build_frame()` (constructs from Intersection) |
| `app/schemas/training_schema.py` | Pydantic models: `TrainingMetric` (episode reward, avg wait, throughput, epsilon, loss, is_training), `StartTrainingRequest` (num_episodes default 500, simulation_id optional) |
| `app/schemas/metrics_schema.py` | `MetricsSnapshot`: avg_wait_time, throughput, max_queue, current_phase, is_training, current_episode, epsilon |

#### Services

| File | Purpose |
|---|---|
| `app/services/supabase_service.py` | All DB writes — `create_simulation`, `update_simulation`, `save_episode`, `save_traffic_logs_bulk`, `save_traffic_log`, `save_signal_states_bulk`, `save_signal_state`, `save_performance_metric`, `save_model_metadata` (upsert), `set_active_model`. All sync, called via `asyncio.to_thread`. Error logging on every failure. |
| `app/services/model_service.py` | Checkpoint management — `save_checkpoint` (local disk + Supabase Storage), `load_checkpoint` (Storage with local fallback), `list_checkpoints`, `list_all_models` (3-tier discovery: DB → Storage listing → local disk, deduplicated), `list_local_models` (backward compat) |

#### Simulation Engine

| File | Purpose |
|---|---|
| `app/simulation/environment.py` | Gymnasium `TrafficEnv` — 8-dim observation space (queue lengths x4, phase, time_in_phase, color_val, normalized_timestep), Discrete(4) action space. `reset()` resets intersection, `step(action)` computes reward (wait penalty + throughput bonus + switch penalty + overflow penalty), terminal at 500 timesteps. `render()` returns SimulationFrame. |
| `app/simulation/intersection.py` | Core `Intersection` — 4 lane queues (north/south/east/west), TrafficSignal, PoissonSpawner, timestep counter, intersection reservation system (vehicles wait for perpendicular traffic to clear), emergency override (forces priority green). `tick(dt, action)` — resolves emergency, ticks signal, spawns vehicles, moves vehicles with stop-line collision detection + signal checking + intersection entrance reservation + vehicle-ahead collision avoidance. |
| `app/simulation/vehicle.py` | `Vehicle` dataclass — id, lane, turn, position, wait_time, speed, state, is_emergency. `tick(dt, can_move)` — moves at DEFAULT_SPEED (0.12) if allowed, tracks wait time, transitions to "passed" at position ≥ 1.0. |
| `app/simulation/traffic_signal.py` | `TrafficSignal` — 4 phases (NS_GREEN, EW_GREEN, NS_LEFT, EW_LEFT), 3 colors (GREEN, YELLOW, RED). Phase-to-lane mapping, allowed turns per phase. Fixed timing: 8s green default, 2s yellow, 4s minimum green. Smart phase selection (highest queue after minimum green). AI requests go through yellow-red-green transition. `is_green_for(lane, turn)` checks phase + color + turn restrictions. |
| `app/simulation/spawner.py` | `PoissonSpawner` — configurable λ (default 0.3), Poisson distribution per tick, spawns into one random lane, 50% straight / 25% left / 25% right, max 10 vehicles per lane. |
| `app/simulation/metrics.py` | `MetricsTracker` — rolling calculation of avg_wait_time, avg_throughput, avg_queue_length with running totals. `get_snapshot()` returns current state dict. |

#### Reinforcement Learning

| File | Purpose |
|---|---|
| `app/rl/dqn_network.py` | Neural network — 3 hidden layers: Linear(8,128) → ReLU → Linear(128,128) → ReLU → Linear(128,64) → ReLU → Linear(64,4) |
| `app/rl/dqn_agent.py` | DQN Agent — online + target networks, Adam optimizer, MSELoss. `select_action(state, epsilon)` — epsilon-greedy. `train_step(batch)` — Q-learning targets with γ=0.95. `sync_target_network()` — copies online weights to target. `save()` / `load()` — PyTorch state dict serialization. |
| `app/rl/replay_buffer.py` | Deque-based buffer (max 10,000 transitions). `push(state, action, reward, next_state, done)`. `sample(batch_size)` — returns batched torch tensors. |
| `app/rl/hyperparams.py` | Dataclass: lr=1e-3, γ=0.95, ε_start=1.0, ε_end=0.05, ε_decay=0.995, batch_size=64, replay_buffer=10000, target_update_freq=500, max_steps=500, episodes=500, min_replay_size=64 |
| `app/rl/trainer.py` | Training orchestrator — async episodes loop. Every 4th step: sample buffer → train (via `asyncio.to_thread`). Target sync every 500 steps. Yields event loop every 10 steps. Epsilon decays per episode. Saves episode to Supabase + broadcasts via WebSocket. Checkpoints every 50 episodes (model save + metadata upsert). Rolling 50-episode reward window for metadata. |

#### WebSocket Handlers

| File | Purpose |
|---|---|
| `app/websockets/simulation_ws.py` | Simulation WebSocket — ConnectionManager for multi-client broadcast. Main loop at 10 Hz. Fixed mode: `intersection.tick(action=None)`. AI mode: `env._get_obs()` → `agent.select_action(ε=0)` → `env.step()`. DB sampling every 50 ticks, flushing every 10 samples. Handles 6 commands (start, stop, reset, set_mode, set_spawn_rate, emergency_override). Flushes buffer on cancel/crash. |
| `app/websockets/training_ws.py` | Training WebSocket — separate ConnectionManager. `broadcast_training_metric()` used by Trainer. Handles start_training/stop_training commands. Creates simulation record if needed. |

### Tests (`server/tests/`)

| File | Purpose |
|---|---|
| `conftest.py` | Pytest fixtures — `mock_supabase` (patches supabase_client), `mock_model_service` (patches save/load/list), `client` (FastAPI TestClient with lifespan), `app_state` |
| `tests/api/test_main.py` | Tests root (`/`) and `/health` endpoints |
| `tests/api/test_simulation.py` | Tests start/stop/reset/set_mode/get_status — 5 test functions |
| `tests/api/test_training.py` | Tests start/stop/status/models — 4 test functions |
| `tests/rl/test_replay_buffer.py` | Tests buffer push and sample — 2 test functions |
| `tests/rl/test_dqn_agent.py` | Tests init, random action, greedy action, train_step — 4 test functions |
| `tests/simulation/test_vehicle.py` | Tests init, movement, waiting, passed state — 4 test functions |
| `tests/simulation/test_traffic_signal.py` | Tests init, phase change, yellow→red→green transitions, fixed duration rollover, green permission — 6 test functions |

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

---

*Generated: 2026-07-08 — Comprehensive project analysis of FlowSync*

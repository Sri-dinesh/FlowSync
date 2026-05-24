# PLAN.md — Smart Traffic Management Simulation

### AI-Powered Real-Time Traffic Control using Deep Reinforcement Learning

---

> **Agent Instructions:**
> This document is your execution roadmap. Complete tasks strictly phase-by-phase and in order.
> **After completing each task, mark it as done:** `- [x]`
> **After every task:**
>
> - Commit changes
> - Push to GitHub
> - Use a clear commit message
>   **Supabase MCP is configured — use it whenever required.**
>   Do not skip ahead. Verify each task before moving to the next.

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Folder Structure](#3-folder-structure)
4. [Database Design](#4-database-design)
5. [Simulation Engine Design](#5-simulation-engine-design)
6. [Reinforcement Learning System Design](#6-reinforcement-learning-system-design)
7. [Phase 0 — Project Bootstrapping](#phase-0--project-bootstrapping)
8. [Phase 1 — Database & Schema](#phase-1--database--schema)
9. [Phase 2 — Simulation Engine (FastAPI)](#phase-2--simulation-engine-fastapi)
10. [Phase 3 — RL Agent (DQN)](#phase-3--rl-agent-dqn)
11. [Phase 4 — FastAPI Server & WebSockets](#phase-4--fastapi-server--websockets)
12. [Phase 5 — Next.js Application Shell](#phase-5--nextjs-application-shell)
13. [Phase 6 — Three.js Visualization](#phase-6--threejs-visualization)
14. [Phase 7 — Dashboards & UI](#phase-7--dashboards--ui)
15. [Phase 8 — Integration & End-to-End Flow](#phase-8--integration--end-to-end-flow)
16. [Phase 9 — Performance Optimization](#phase-9--performance-optimization)
17. [Phase 10 — Deployment](#phase-10--deployment)
18. [Future Expansions](#future-expansions)

---

## 1. PROJECT OVERVIEW

### What We're Building

A full-stack, real-time AI traffic simulation system. A Deep Q-Network (DQN) agent learns to control traffic signals at a city intersection to minimize vehicle wait times. Users watch the simulation live, trigger training sessions, compare RL-controlled signals vs fixed-timer signals side-by-side, and monitor training metrics on a dashboard.

### Core User Flows

1. User opens app → lands on hero page → clicks "Launch App"
2. User arrives at simulation dashboard → sees a live intersection rendered in Three.js
3. User can run simulation in **Fixed Mode** (dumb timer-based signals) or **AI Mode** (DQN agent controls signals)
4. User can click **"Train Agent"** → watches the agent learn in real-time (live reward/loss charts)
5. User can compare Fixed vs AI metrics side by side
6. All episode data, metrics, and model checkpoints are persisted in Supabase

### Key Engineering Pillars

- **Simulation Engine** — Python-based, runs inside FastAPI, models a 4-way intersection
- **DQN Agent** — PyTorch, observes queue lengths, outputs signal phase actions
- **WebSocket Stream** — FastAPI pushes simulation frames + training metrics to frontend at ~10fps
- **Three.js Visualization** — React Three Fiber renders the intersection live from WebSocket data
- **Next.js Dashboard** — reads historical data from Supabase, shows charts, episode history, model status

---

## 2. ARCHITECTURE

### 2.1 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Next.js App (Vercel)                       │  │
│  │                                                          │  │
│  │  ┌─────────────────┐    ┌──────────────────────────┐    │  │
│  │  │  Three.js Scene  │    │   Dashboard / Charts     │    │  │
│  │  │  (R3F Renderer)  │    │   (TanStack Query)       │    │  │
│  │  └────────┬─────────┘    └──────────┬───────────────┘    │  │
│  │           │ WebSocket                │ HTTP (API Routes)  │  │
│  └───────────┼──────────────────────────┼───────────────────┘  │
└──────────────┼──────────────────────────┼──────────────────────┘
               │                          │
               │ ws://                    │ REST
               ▼                          ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   FastAPI Server         │   │   Next.js API Routes     │
│   (Railway / Docker)     │   │   (Vercel)               │
│                          │   │                          │
│  ┌────────────────────┐  │   │  → /api/simulations      │
│  │  Simulation Engine  │  │   │  → /api/episodes         │
│  │  (Python classes)   │  │   │  → /api/metrics          │
│  └─────────┬──────────┘  │   │  → /api/models            │
│            │              │   └──────────┬───────────────┘
│  ┌─────────▼──────────┐  │              │
│  │   DQN RL Agent      │  │              │
│  │   (PyTorch)         │  │              │
│  └─────────┬──────────┘  │              │
│            │              │              │
│  ┌─────────▼──────────┐  │              │
│  │  Supabase Client    │──┼──────────────┘
│  │  (writes metrics)   │  │         (reads metrics)
│  └────────────────────┘  │
└──────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│       Supabase           │
│  PostgreSQL + Storage    │
└──────────────────────────┘
```

### 2.2 Communication Flow

| From                     | To                 | Protocol           | Purpose                              |
| ------------------------ | ------------------ | ------------------ | ------------------------------------ |
| Browser (Three.js)       | FastAPI            | WebSocket          | Live simulation frames ~10fps        |
| Browser (Training Panel) | FastAPI            | WebSocket          | Live training metrics stream         |
| Browser (Dashboard)      | Next.js API Routes | HTTP/REST          | Historical data reads                |
| Next.js API Routes       | Supabase           | HTTP (Prisma)      | DB reads for dashboard               |
| FastAPI                  | Supabase           | HTTP (supabase-py) | DB writes during simulation/training |
| FastAPI                  | Supabase Storage   | HTTP               | Model checkpoint uploads             |

### 2.3 WebSocket Architecture Detail

Two distinct WebSocket endpoints on FastAPI:

**`/ws/simulation`**

- Client connects → server starts simulation loop
- Server pushes a `SimulationFrame` JSON every 100ms (10fps)
- Frame contains: vehicle positions, signal states, queue lengths, timestep
- Client disconnects → simulation pauses

**`/ws/training`**

- Client connects → server starts/resumes training loop
- Server pushes a `TrainingMetric` JSON after each episode
- Contains: episode number, total reward, avg wait time, epsilon, loss
- Training continues even if client disconnects (background task)

### 2.4 Deployment Architecture

```
Vercel (Next.js)
    ├── Static assets + SSR
    ├── API Routes → reads Supabase
    └── env: NEXT_PUBLIC_FASTAPI_WS_URL, NEXT_PUBLIC_FASTAPI_HTTP_URL

Railway (FastAPI Docker Container)
    ├── FastAPI app on port 8000
    ├── PyTorch DQN model
    ├── Gymnasium simulation
    └── env: SUPABASE_URL, SUPABASE_SERVICE_KEY

Supabase
    ├── PostgreSQL database
    └── Storage bucket: model-checkpoints
```

---

## 3. FOLDER STRUCTURE

```
/
├── client/                          # Next.js fullstack app
│   ├── src/
│   │   ├── app/                     # App Router
│   │   │   ├── layout.tsx           # Root layout (fonts, theme)
│   │   │   ├── page.tsx             # Landing page (hero)
│   │   │   ├── globals.css          # Tailwind v4 + Vercel theme vars
│   │   │   └── simulation/
│   │   │       └── page.tsx         # Main simulation app page
│   │   ├── components/
│   │   │   ├── ui/                  # Shadcn/ui components
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Sidebar.tsx
│   │   │   ├── simulation/
│   │   │   │   ├── SimulationCanvas.tsx     # R3F canvas wrapper
│   │   │   │   ├── IntersectionScene.tsx    # Main Three.js scene
│   │   │   │   ├── Road.tsx                 # Road mesh component
│   │   │   │   ├── Vehicle.tsx              # Vehicle mesh component
│   │   │   │   ├── TrafficLight.tsx         # Signal light component
│   │   │   │   └── IntersectionGrid.tsx     # Ground/grid
│   │   │   ├── controls/
│   │   │   │   ├── SimulationControls.tsx   # Start/stop/reset/mode toggle
│   │   │   │   ├── TrainingControls.tsx     # Train/pause/load model
│   │   │   │   └── ParameterPanel.tsx       # Tune spawn rate, etc.
│   │   │   └── dashboard/
│   │   │       ├── MetricsPanel.tsx         # Live metrics cards
│   │   │       ├── TrainingChart.tsx        # Reward/loss over episodes
│   │   │       ├── ComparisonChart.tsx      # Fixed vs AI comparison
│   │   │       ├── EpisodeHistory.tsx       # Table of past episodes
│   │   │       └── AIStatusBadge.tsx        # Training state indicator
│   │   ├── hooks/
│   │   │   ├── useSimulationSocket.ts       # WebSocket hook for sim frames
│   │   │   ├── useTrainingSocket.ts         # WebSocket hook for training
│   │   │   ├── useSimulations.ts            # TanStack Query hooks
│   │   │   └── useEpisodes.ts
│   │   ├── lib/
│   │   │   ├── prisma.ts                    # Prisma client singleton
│   │   │   ├── supabase.ts                  # Supabase browser client
│   │   │   └── utils.ts                     # cn(), formatters
│   │   ├── store/
│   │   │   └── simulationStore.ts           # Zustand store
│   │   ├── types/
│   │   │   └── simulation.ts                # Shared TypeScript types
│   │   └── api/                             # Next.js API Routes
│   │       ├── simulations/
│   │       │   └── route.ts
│   │       ├── episodes/
│   │       │   └── route.ts
│   │       └── metrics/
│   │           └── route.ts
│   ├── prisma/
│   │   └── schema.prisma
│   ├── public/
│   ├── .env.local
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── server/                          # FastAPI + ML server
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings (env vars, hyperparams)
│   │   ├── routers/
│   │   │   ├── simulation.py        # REST: start/stop/reset simulation
│   │   │   ├── training.py          # REST: start/stop training, load model
│   │   │   └── metrics.py           # REST: fetch current metrics snapshot
│   │   ├── websockets/
│   │   │   ├── simulation_ws.py     # /ws/simulation handler
│   │   │   └── training_ws.py       # /ws/training handler
│   │   ├── simulation/
│   │   │   ├── __init__.py
│   │   │   ├── environment.py       # Gymnasium env (TrafficEnv)
│   │   │   ├── intersection.py      # Intersection state model
│   │   │   ├── vehicle.py           # Vehicle entity
│   │   │   ├── traffic_signal.py    # Signal phase controller
│   │   │   ├── spawner.py           # Poisson vehicle spawner
│   │   │   └── metrics.py           # Wait time, throughput calc
│   │   ├── rl/
│   │   │   ├── __init__.py
│   │   │   ├── dqn_agent.py         # DQN agent (PyTorch)
│   │   │   ├── dqn_network.py       # Neural network architecture
│   │   │   ├── replay_buffer.py     # Experience replay memory
│   │   │   ├── trainer.py           # Training loop orchestrator
│   │   │   └── hyperparams.py       # All hyperparameter constants
│   │   ├── services/
│   │   │   ├── supabase_service.py  # All Supabase read/write ops
│   │   │   └── model_service.py     # Checkpoint save/load (Storage)
│   │   └── schemas/
│   │       ├── simulation_schema.py # Pydantic models for sim data
│   │       ├── training_schema.py   # Pydantic models for training data
│   │       └── metrics_schema.py    # Pydantic models for metrics
│   ├── models/                      # Local model checkpoint cache
│   │   └── .gitkeep
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── railway.toml
│
└── README.md
```

---

## 4. DATABASE DESIGN

### 4.1 Tables Overview

| Table                 | Written by | Read by               | Purpose                       |
| --------------------- | ---------- | --------------------- | ----------------------------- |
| `simulations`         | FastAPI    | Next.js API           | Simulation session records    |
| `episodes`            | FastAPI    | Next.js API           | Each RL training episode      |
| `signal_states`       | FastAPI    | Next.js API           | Signal phase log per timestep |
| `traffic_logs`        | FastAPI    | Next.js API           | Vehicle throughput log        |
| `rl_models`           | FastAPI    | Next.js API + FastAPI | Saved model metadata          |
| `performance_metrics` | FastAPI    | Next.js API           | Aggregated metrics per run    |

### 4.2 Prisma Schema (`client/prisma/schema.prisma`)

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Simulation {
  id          String   @id @default(cuid())
  createdAt   DateTime @default(now())
  mode        String   // "fixed" | "ai"
  status      String   // "running" | "completed" | "stopped"
  totalSteps  Int      @default(0)
  durationMs  Int      @default(0)

  episodes    Episode[]
  metrics     PerformanceMetric[]
  trafficLogs TrafficLog[]

  @@map("simulations")
}

model Episode {
  id            String     @id @default(cuid())
  simulationId  String
  simulation    Simulation @relation(fields: [simulationId], references: [id])
  episodeNumber Int
  totalReward   Float
  avgWaitTime   Float
  throughput    Int
  epsilon       Float
  loss          Float?
  steps         Int
  createdAt     DateTime   @default(now())

  @@map("episodes")
}

model SignalState {
  id           String   @id @default(cuid())
  simulationId String
  timestep     Int
  phase        Int      // 0=NS_GREEN, 1=EW_GREEN, 2=NS_LEFT, 3=EW_LEFT
  duration     Int      // seconds this phase was held
  queueNorth   Int
  queueSouth   Int
  queueEast    Int
  queueWest    Int
  createdAt    DateTime @default(now())

  @@map("signal_states")
}

model TrafficLog {
  id            String     @id @default(cuid())
  simulationId  String
  simulation    Simulation @relation(fields: [simulationId], references: [id])
  timestep      Int
  vehiclesSpawned    Int
  vehiclesPassed     Int
  avgWaitTime        Float
  maxQueueLength     Int
  createdAt     DateTime   @default(now())

  @@map("traffic_logs")
}

model RLModel {
  id          String   @id @default(cuid())
  name        String
  version     String
  storagePath String   // Supabase Storage path
  avgReward   Float
  epsilon     Float
  totalEpisodes Int
  createdAt   DateTime @default(now())
  isActive    Boolean  @default(false)

  @@map("rl_models")
}

model PerformanceMetric {
  id               String     @id @default(cuid())
  simulationId     String
  simulation       Simulation @relation(fields: [simulationId], references: [id])
  mode             String     // "fixed" | "ai"
  avgWaitTimeFixed Float?
  avgWaitTimeAI    Float?
  throughputFixed  Int?
  throughputAI     Int?
  improvementPct   Float?
  createdAt        DateTime   @default(now())

  @@map("performance_metrics")
}
```

### 4.3 Supabase Storage

- Bucket name: `model-checkpoints`
- Path pattern: `models/{model_id}/checkpoint_{episode}.pt`
- Public: false (accessed via service key from FastAPI)

---

## 5. SIMULATION ENGINE DESIGN

### 5.1 Intersection Model

A single 4-way intersection. Each arm (North, South, East, West) has:

- 1 incoming lane (vehicles arriving)
- 1 outgoing lane (vehicles leaving)
- A queue of vehicles waiting at the stop line
- A traffic signal head

```
         NORTH
          |||
   ───────╋───────
   WEST   ╋   EAST
   ───────╋───────
          |||
         SOUTH
```

### 5.2 Signal Phases

4 phases (standard US intersection):

- **Phase 0**: North-South Green (East-West Red)
- **Phase 1**: East-West Green (North-South Red)
- **Phase 2**: North-South Left-Turn Green
- **Phase 3**: East-West Left-Turn Green

Phase transitions always pass through a 2-second yellow phase (do not skip).

### 5.3 Vehicle Model

Each vehicle has:

- `id`: unique string
- `lane`: "north" | "south" | "east" | "west"
- `position`: float 0.0 → 1.0 (0=spawn point, 1=past intersection)
- `wait_time`: int (seconds spent at queue)
- `speed`: float (normal speed 0.02/tick, 0 when stopped at red)
- `state`: "moving" | "waiting" | "passed"

### 5.4 Vehicle Spawning (Poisson Process)

Vehicles arrive at each lane following a Poisson distribution:

- Default λ = 0.3 vehicles/second/lane (configurable)
- Each simulation tick: for each lane, sample from Poisson(λ × dt)
- Max queue length per lane: 10 vehicles (prevents unbounded growth)
- Spawned vehicles are added to the tail of the lane queue

### 5.5 Simulation Loop (runs inside FastAPI)

```
tick() every 100ms (simulation dt = 0.1s):
  1. spawner.spawn_vehicles(dt)          → add new vehicles to queues
  2. signal_controller.step(dt)          → advance signal timer
  3. for each lane:
       if signal is GREEN for this lane:
         move front vehicle forward (position += speed)
         if position >= 1.0: mark as "passed", remove from queue
       else:
         all vehicles in lane: speed = 0 (waiting)
  4. metrics.update()                    → recalculate queue lengths, wait times
  5. return SimulationFrame              → pushed via WebSocket
```

### 5.6 Fixed-Timer Controller

- Each phase runs for a fixed duration (default: 30s green, 2s yellow, 30s green other direction)
- Cycle repeats indefinitely
- Serves as the **baseline** for RL comparison

### 5.7 SimulationFrame (WebSocket payload)

```python
class SimulationFrame(BaseModel):
    timestep: int
    mode: str                     # "fixed" | "ai"
    signal_phase: int             # 0-3
    signal_color: str             # "green" | "yellow" | "red"
    vehicles: List[VehicleState]
    queue_lengths: Dict[str, int] # {"north": 3, "south": 1, ...}
    avg_wait_time: float
    throughput: int               # vehicles passed this episode
    reward: float                 # current step reward (AI mode only)
```

---

## 6. REINFORCEMENT LEARNING SYSTEM DESIGN

### 6.1 Environment (`TrafficEnv` — Gymnasium)

Wraps the simulation engine as a standard Gymnasium environment.

```python
class TrafficEnv(gymnasium.Env):
    observation_space = Box(low=0, high=10, shape=(8,), dtype=np.float32)
    # [q_north, q_south, q_east, q_west,
    #  current_phase(0-3), time_in_phase,
    #  total_waiting_vehicles, normalized_timestep]

    action_space = Discrete(4)
    # 0 = switch to Phase 0 (NS Green)
    # 1 = switch to Phase 1 (EW Green)
    # 2 = switch to Phase 2 (NS Left)
    # 3 = switch to Phase 3 (EW Left)
```

### 6.2 State Space (8 values)

| Index | Value                                 | Range |
| ----- | ------------------------------------- | ----- |
| 0     | Queue length North                    | 0–10  |
| 1     | Queue length South                    | 0–10  |
| 2     | Queue length East                     | 0–10  |
| 3     | Queue length West                     | 0–10  |
| 4     | Current signal phase                  | 0–3   |
| 5     | Time spent in current phase (seconds) | 0–60  |
| 6     | Total vehicles currently waiting      | 0–40  |
| 7     | Normalized timestep in episode        | 0–1   |

### 6.3 Action Space

Discrete(4) — agent selects which phase to activate next. If agent selects the **same phase** that is currently active, simulation continues with no change (valid action, no penalty).

### 6.4 Reward Function

```python
def compute_reward(prev_state, current_state) -> float:
    # Primary: minimize total wait time
    wait_penalty = -0.1 * total_waiting_vehicles

    # Bonus: reward vehicles clearing the intersection
    throughput_bonus = +1.0 * vehicles_passed_this_step

    # Penalty: unnecessary phase switching (costs yellow transition time)
    switch_penalty = -0.5 if phase_changed else 0.0

    # Penalty: any queue exceeding 8 vehicles (near overflow)
    overflow_penalty = -2.0 * sum(1 for q in queues if q >= 8)

    return wait_penalty + throughput_bonus + switch_penalty + overflow_penalty
```

### 6.5 DQN Architecture

```
Input (8,)
  → Linear(8, 128) + ReLU
  → Linear(128, 128) + ReLU
  → Linear(128, 64) + ReLU
  → Linear(64, 4)   → Q-values for each action
```

Two networks: **online network** (trained every step) + **target network** (synced every 500 steps). This is standard Double DQN stabilization.

### 6.6 Training Hyperparameters (`server/app/rl/hyperparams.py`)

```python
LEARNING_RATE      = 1e-3
GAMMA              = 0.95        # discount factor
EPSILON_START      = 1.0
EPSILON_END        = 0.05
EPSILON_DECAY      = 0.995       # per episode
BATCH_SIZE         = 64
REPLAY_BUFFER_SIZE = 10_000
TARGET_UPDATE_FREQ = 500         # steps
MAX_STEPS_PER_EPISODE = 500
EPISODES           = 500         # default training run
```

### 6.7 Replay Buffer

Standard circular buffer storing `(state, action, reward, next_state, done)` tuples. Size 10,000. Randomly sampled in batches of 64 for training. Training begins only after buffer has ≥ 1,000 samples.

### 6.8 Training Loop

```
for episode in range(EPISODES):
    state = env.reset()
    total_reward = 0

    for step in range(MAX_STEPS_PER_EPISODE):
        action = agent.select_action(state, epsilon)   # ε-greedy
        next_state, reward, done, info = env.step(action)
        replay_buffer.push(state, action, reward, next_state, done)

        if len(replay_buffer) >= 1000:
            loss = agent.train_step(replay_buffer.sample(BATCH_SIZE))

        if step % TARGET_UPDATE_FREQ == 0:
            agent.sync_target_network()

        total_reward += reward
        state = next_state
        if done: break

    epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)

    # Write to Supabase
    supabase_service.save_episode(episode, total_reward, avg_wait, epsilon, loss)

    # Stream to WebSocket clients
    await ws_manager.broadcast_training_metric({...})
```

---

## PHASE 0 — PROJECT BOOTSTRAPPING

**Goal:** Initialize both projects, install all dependencies, configure environment, set up the Vercel theme.

---

### 0.1 — Repository & Root Setup

- [x] Create root `/` folder with `README.md`
- [ ] Create `client/` and `server/` subdirectories
- [ ] Initialize git repo at root: `git init`
- [ ] Create root `.gitignore` covering `node_modules/`, `__pycache__/`, `.env`, `*.pt`, `models/`

---

### 0.2 — Next.js Client Setup

- [ ] Inside `client/`, bootstrap Next.js: `pnpm create next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
- [ ] Install core dependencies:
  ```
  pnpm add @prisma/client @supabase/supabase-js
  pnpm add @tanstack/react-query zustand
  pnpm add three @react-three/fiber @react-three/drei
  pnpm add framer-motion
  pnpm add recharts
  pnpm add -D prisma
  ```
- [ ] Install Shadcn/ui: `pnpm dlx shadcn@latest init`
- [ ] Apply Vercel theme: `pnpm dlx shadcn@latest add https://tweakcn.com/r/themes/vercel.json`
- [ ] Add Shadcn components needed:
  ```
  pnpm dlx shadcn@latest add button card badge tabs select slider switch tooltip separator scroll-area
  ```
- [ ] Replace `client/src/app/globals.css` with the Vercel theme CSS (provided `index.css` content)
- [ ] Update `client/src/app/layout.tsx` with Geist + Geist Mono fonts exactly as specified
- [ ] Configure `next.config.ts`:
  - Add `NEXT_PUBLIC_FASTAPI_WS_URL` and `NEXT_PUBLIC_FASTAPI_HTTP_URL` to env passthrough
- [ ] Create `client/.env.local`:
  ```
  DATABASE_URL=...
  NEXT_PUBLIC_SUPABASE_URL=...
  NEXT_PUBLIC_SUPABASE_ANON_KEY=...
  NEXT_PUBLIC_FASTAPI_WS_URL=ws://localhost:8000
  NEXT_PUBLIC_FASTAPI_HTTP_URL=http://localhost:8000
  ```
- [ ] Verify `pnpm dev` runs with no errors

---

### 0.3 — FastAPI Server Setup

- [ ] Inside `server/`, create Python virtual environment: `python -m venv venv`
- [ ] Create `server/requirements.txt`:
  ```
  fastapi==0.115.0
  uvicorn[standard]==0.30.0
  websockets==12.0
  pydantic==2.7.0
  pydantic-settings==2.3.0
  torch==2.3.0+cpu          # CPU-only
  numpy==1.26.4
  gymnasium==0.29.1
  supabase==2.4.6
  python-dotenv==1.0.1
  httpx==0.27.0
  ```
- [ ] Install: `pip install -r requirements.txt`
- [ ] Create `server/.env`:
  ```
  SUPABASE_URL=...
  SUPABASE_SERVICE_KEY=...
  CORS_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app
  ```
- [ ] Create `server/app/main.py` with bare FastAPI app, CORS middleware, health check `GET /health`
- [ ] Create `server/app/config.py` using `pydantic-settings` to load `.env` values
- [ ] Verify `uvicorn app.main:app --reload` starts on port 8000

---

### 0.4 — Supabase Project Setup

- [ ] Create new Supabase project at supabase.com
- [ ] Copy `DATABASE_URL` (direct connection), `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` into both `.env` files
- [ ] Create Storage bucket `model-checkpoints` (private)
- [ ] Initialize Prisma in `client/`: `pnpm prisma init`
- [ ] Paste the schema from Section 4.2 into `client/prisma/schema.prisma`
- [ ] Run `pnpm prisma db push` to create all tables in Supabase
- [ ] Run `pnpm prisma generate` to generate client
- [ ] Create `client/src/lib/prisma.ts`:
  ```typescript
  import { PrismaClient } from "@prisma/client";
  const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };
  export const prisma = globalForPrisma.prisma ?? new PrismaClient();
  if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
  ```

**✅ Phase 0 Deliverable:** Both projects boot. DB schema is live. Environment configured.

---

## PHASE 1 — DATABASE & SCHEMA

**Goal:** Wire up all data access layers — Prisma on Next.js side, supabase-py on FastAPI side.

---

### 1.1 — Supabase Service (FastAPI)

- [ ] Create `server/app/services/supabase_service.py`
- [ ] Initialize Supabase client using `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- [ ] Implement `create_simulation(mode: str) -> str` → inserts into `simulations`, returns `id`
- [ ] Implement `update_simulation(id, status, total_steps, duration_ms)`
- [ ] Implement `save_episode(simulation_id, episode_num, total_reward, avg_wait, throughput, epsilon, loss, steps)`
- [ ] Implement `save_traffic_log(simulation_id, timestep, spawned, passed, avg_wait, max_queue)`
- [ ] Implement `save_signal_state(simulation_id, timestep, phase, duration, queues: dict)`
- [ ] Implement `save_performance_metric(simulation_id, mode, avg_wait, throughput)`
- [ ] Implement `save_model_metadata(name, version, storage_path, avg_reward, epsilon, total_episodes) -> str`
- [ ] Implement `set_active_model(model_id: str)` → sets `isActive=true` for this model, false for others

### 1.2 — Model Service (FastAPI)

- [ ] Create `server/app/services/model_service.py`
- [ ] Implement `save_checkpoint(model_id: str, episode: int, state_dict: dict)` → uploads `.pt` file to Supabase Storage bucket `model-checkpoints`
- [ ] Implement `load_checkpoint(model_id: str, episode: int) -> dict` → downloads and loads `.pt` file
- [ ] Implement `list_checkpoints(model_id: str) -> List[str]`

### 1.3 — Next.js API Routes

- [ ] Create `client/src/app/api/simulations/route.ts`
  - `GET` → `prisma.simulation.findMany({ orderBy: { createdAt: 'desc' }, take: 20 })`
- [ ] Create `client/src/app/api/episodes/route.ts`
  - `GET ?simulationId=` → `prisma.episode.findMany({ where: { simulationId } })`
- [ ] Create `client/src/app/api/metrics/route.ts`
  - `GET ?simulationId=` → `prisma.performanceMetric.findMany({ where: { simulationId } })`
- [ ] Create `client/src/app/api/models/route.ts`
  - `GET` → `prisma.rLModel.findMany({ orderBy: { createdAt: 'desc' } })`

### 1.4 — TanStack Query Setup

- [ ] Create `client/src/app/providers.tsx` wrapping `QueryClientProvider`
- [ ] Wrap root `layout.tsx` with `<Providers>`
- [ ] Create `client/src/hooks/useSimulations.ts`:
  ```typescript
  export const useSimulations = () =>
    useQuery({
      queryKey: ["simulations"],
      queryFn: () => fetch("/api/simulations").then((r) => r.json()),
    });
  ```
- [ ] Create `client/src/hooks/useEpisodes.ts` (similar pattern, takes `simulationId`)

**✅ Phase 1 Deliverable:** Data layer complete. API routes respond. Supabase writes confirmed.

---

## PHASE 2 — SIMULATION ENGINE (FastAPI)

**Goal:** Build the full Python simulation — intersection, vehicles, signals, spawner, metrics, simulation loop.

---

### 2.1 — Vehicle Entity

- [ ] Create `server/app/simulation/vehicle.py`
- [ ] Define `Vehicle` dataclass:
  ```python
  @dataclass
  class Vehicle:
      id: str
      lane: str          # "north" | "south" | "east" | "west"
      position: float    # 0.0 (spawn) → 1.0 (passed)
      wait_time: float   # seconds spent waiting
      speed: float       # current speed
      state: str         # "moving" | "waiting" | "passed"
  ```
- [ ] Implement `Vehicle.tick(dt: float, is_green: bool)`:
  - If `is_green` and `position < 1.0`: `position += speed * dt`; `state = "moving"`
  - If not `is_green`: `speed = 0`; `state = "waiting"`; `wait_time += dt`
  - If `position >= 1.0`: `state = "passed"`

### 2.2 — Traffic Signal Controller

- [ ] Create `server/app/simulation/traffic_signal.py`
- [ ] Define `SignalPhase` enum: `NS_GREEN=0`, `EW_GREEN=1`, `NS_LEFT=2`, `EW_LEFT=3`
- [ ] Define `SignalColor` enum: `GREEN`, `YELLOW`, `RED`
- [ ] Define which lanes get GREEN per phase:
  ```python
  PHASE_GREEN_LANES = {
      0: ["north", "south"],
      1: ["east", "west"],
      2: ["north_left", "south_left"],
      3: ["east_left", "west_left"],
  }
  ```
- [ ] Implement `TrafficSignal` class:
  - `current_phase: int`
  - `color: SignalColor`
  - `time_in_phase: float`
  - `fixed_duration: float = 30.0`
  - `yellow_duration: float = 2.0`
  - `set_phase(phase: int)` → starts yellow transition first, then switches
  - `tick(dt: float)` → advances timer; handles yellow→red→green transitions
  - `is_green_for(lane: str) -> bool`

### 2.3 — Vehicle Spawner

- [ ] Create `server/app/simulation/spawner.py`
- [ ] Implement `PoissonSpawner`:
  - `lambda_rate: float = 0.3` (vehicles/second/lane, configurable)
  - `spawn(dt: float, lanes: dict) -> List[Vehicle]`:
    - For each lane: sample `n ~ Poisson(lambda_rate * dt)`
    - If `len(lane_queue) < MAX_QUEUE (10)`: add `n` new vehicles
    - Each vehicle gets unique UUID, `position=0.0`, `speed=0.02`

### 2.4 — Intersection State

- [ ] Create `server/app/simulation/intersection.py`
- [ ] Implement `Intersection` class:
  - `lanes: Dict[str, List[Vehicle]]` — queues for north/south/east/west
  - `signal: TrafficSignal`
  - `timestep: int`
  - `total_passed: int`
  - `spawner: PoissonSpawner`
  - `tick(dt: float, action: Optional[int] = None)`:
    1. If `action is not None` (AI mode): `signal.set_phase(action)`
    2. Else (fixed mode): `signal.tick(dt)` — auto-advance timer
    3. `spawner.spawn(dt, lanes)` — add new vehicles
    4. For each lane: advance vehicles, collect passed vehicles, update `total_passed`
    5. Remove passed vehicles from queues
    6. `timestep += 1`
  - `get_queue_lengths() -> Dict[str, int]`
  - `get_total_waiting() -> int`
  - `get_avg_wait_time() -> float`
  - `reset()` — clears all queues, resets signal, timestep=0

### 2.5 — Metrics Calculator

- [ ] Create `server/app/simulation/metrics.py`
- [ ] Implement `MetricsTracker`:
  - Tracks running averages: wait time, throughput, queue lengths per tick
  - `update(intersection: Intersection, reward: float)`
  - `get_snapshot() -> dict` — returns current metrics dict
  - `reset()`

### 2.6 — Simulation Frame Builder

- [ ] Create `server/app/schemas/simulation_schema.py`
- [ ] Define Pydantic models:

  ```python
  class VehicleState(BaseModel):
      id: str
      lane: str
      position: float
      state: str
      wait_time: float

  class SimulationFrame(BaseModel):
      timestep: int
      mode: str
      signal_phase: int
      signal_color: str
      vehicles: List[VehicleState]
      queue_lengths: Dict[str, int]
      avg_wait_time: float
      throughput: int
      reward: float
      episode: int
  ```

- [ ] Implement `build_frame(intersection, mode, reward, episode) -> SimulationFrame`

### 2.7 — Gymnasium Environment

- [ ] Create `server/app/simulation/environment.py`
- [ ] Implement `TrafficEnv(gymnasium.Env)`:
  - `__init__`: create `Intersection`, define `observation_space` (Box 8,) and `action_space` (Discrete 4)
  - `reset(seed=None) -> (obs, info)`: call `intersection.reset()`, return initial observation
  - `step(action) -> (obs, reward, terminated, truncated, info)`:
    - Call `intersection.tick(dt=0.1, action=action)`
    - Compute observation vector (8 values per Section 6.1)
    - Compute reward (per Section 6.4)
    - `terminated = timestep >= MAX_STEPS_PER_EPISODE`
    - Return tuple
  - `_get_obs() -> np.ndarray`: extract 8-value state vector from intersection
  - `render() -> SimulationFrame`: return current frame for WebSocket streaming

**✅ Phase 2 Deliverable:** `TrafficEnv` runs standalone. Can step through episodes. `SimulationFrame` builds correctly.

---

## PHASE 3 — RL AGENT (DQN)

**Goal:** Implement the full DQN agent with replay buffer, target network, training loop, and checkpoint system.

---

### 3.1 — DQN Neural Network

- [ ] Create `server/app/rl/dqn_network.py`
- [ ] Implement `DQNNetwork(nn.Module)`:
  ```python
  class DQNNetwork(nn.Module):
      def __init__(self, state_dim=8, action_dim=4):
          super().__init__()
          self.net = nn.Sequential(
              nn.Linear(state_dim, 128),
              nn.ReLU(),
              nn.Linear(128, 128),
              nn.ReLU(),
              nn.Linear(128, 64),
              nn.ReLU(),
              nn.Linear(64, action_dim)
          )
      def forward(self, x):
          return self.net(x)
  ```

### 3.2 — Replay Buffer

- [ ] Create `server/app/rl/replay_buffer.py`
- [ ] Implement `ReplayBuffer(maxlen=10_000)`:
  - Internal: `collections.deque(maxlen=maxlen)`
  - `push(state, action, reward, next_state, done)`
  - `sample(batch_size) -> Tuple[Tensors]`: returns batched tensors for training
  - `__len__() -> int`

### 3.3 — DQN Agent

- [ ] Create `server/app/rl/dqn_agent.py`
- [ ] Implement `DQNAgent`:
  - `__init__`: create `online_net`, `target_net` (both `DQNNetwork`), Adam optimizer, `ReplayBuffer`
  - `select_action(state: np.ndarray, epsilon: float) -> int`:
    - With probability `epsilon`: random action
    - Otherwise: `argmax(online_net(state))`
  - `train_step(batch) -> float`:
    - Compute Q-values from online net for current states
    - Compute target Q-values from target net for next states (Bellman equation)
    - Compute MSE loss, backprop, optimizer step
    - Return loss value
  - `sync_target_network()`: `target_net.load_state_dict(online_net.state_dict())`
  - `save(path: str)`: `torch.save(online_net.state_dict(), path)`
  - `load(path: str)`: `online_net.load_state_dict(torch.load(path))`

### 3.4 — Trainer Orchestrator

- [ ] Create `server/app/rl/trainer.py`
- [ ] Implement `Trainer`:
  - `__init__(env, agent, supabase_service, model_service, ws_broadcast_fn)`
  - `is_training: bool = False`
  - `current_episode: int = 0`
  - `epsilon: float = EPSILON_START`
  - `async train(simulation_id: str, num_episodes: int)`:
    - Main async training loop from Section 6.8
    - After each episode: call `supabase_service.save_episode(...)` and `ws_broadcast_fn({...})`
    - Every 50 episodes: call `model_service.save_checkpoint(...)`
  - `stop()`: sets `is_training = False`
  - `get_status() -> dict`: returns current episode, epsilon, is_training

### 3.5 — Hyperparameters

- [ ] Create `server/app/rl/hyperparams.py` with all constants from Section 6.6
- [ ] Ensure all hyperparams are importable as a single `HyperParams` dataclass

**✅ Phase 3 Deliverable:** DQN trains standalone on `TrafficEnv`. Reward improves over episodes. Checkpoints save.

---

## PHASE 4 — FASTAPI SERVER & WEBSOCKETS

**Goal:** Build all REST endpoints and both WebSocket endpoints. Wire up simulation + training orchestration.

---

### 4.1 — Pydantic Schemas

- [ ] Create `server/app/schemas/training_schema.py`:

  ```python
  class TrainingMetric(BaseModel):
      episode: int
      total_reward: float
      avg_wait_time: float
      throughput: int
      epsilon: float
      loss: Optional[float]
      is_training: bool

  class StartTrainingRequest(BaseModel):
      num_episodes: int = 500
      simulation_id: Optional[str] = None
  ```

- [ ] Create `server/app/schemas/metrics_schema.py`:
  ```python
  class MetricsSnapshot(BaseModel):
      avg_wait_time: float
      throughput: int
      max_queue: int
      current_phase: int
      is_training: bool
      current_episode: int
      epsilon: float
  ```

### 4.2 — Global State / App State

- [ ] In `server/app/main.py` define app-level singletons using `lifespan`:
  ```python
  app_state = {
      "env": None,           # TrafficEnv
      "agent": None,         # DQNAgent
      "trainer": None,       # Trainer
      "intersection": None,  # Intersection (for standalone sim)
      "sim_running": False,
      "mode": "fixed",       # "fixed" | "ai"
      "current_simulation_id": None,
  }
  ```
- [ ] Initialize all singletons on FastAPI startup using `@asynccontextmanager` lifespan

### 4.3 — WebSocket Connection Manager

- [ ] Create `server/app/websockets/simulation_ws.py`
- [ ] Implement `ConnectionManager`:
  ```python
  class ConnectionManager:
      def __init__(self):
          self.active_connections: List[WebSocket] = []
      async def connect(self, ws: WebSocket)
      def disconnect(self, ws: WebSocket)
      async def broadcast(self, data: dict)
  ```
- [ ] Single manager instance shared between simulation and training WS handlers

### 4.4 — Simulation WebSocket (`/ws/simulation`)

- [ ] Create handler in `server/app/websockets/simulation_ws.py`
- [ ] On connect: accept WebSocket, start simulation loop as background task
- [ ] Simulation loop:
  ```python
  while sim_running:
      if mode == "fixed":
          intersection.tick(dt=0.1, action=None)
      elif mode == "ai":
          state = env._get_obs()
          action = agent.select_action(state, epsilon=0.0)  # no exploration in live mode
          intersection.tick(dt=0.1, action=action)
      frame = build_frame(intersection, mode, reward, episode)
      await ws.send_json(frame.model_dump())
      await asyncio.sleep(0.1)  # 10fps
  ```
- [ ] On disconnect: mark sim as paused (don't destroy state)
- [ ] Handle client messages: `{"command": "start"}`, `{"command": "stop"}`, `{"command": "reset"}`, `{"command": "set_mode", "mode": "ai"|"fixed"}`

### 4.5 — Training WebSocket (`/ws/training`)

- [ ] Create handler in `server/app/websockets/training_ws.py`
- [ ] On connect: accept WebSocket
- [ ] Handle client messages: `{"command": "start_training", "num_episodes": 500}`, `{"command": "stop_training"}`
- [ ] On `start_training`: launch `trainer.train(...)` as background `asyncio.Task`
- [ ] Trainer's `ws_broadcast_fn` sends `TrainingMetric` JSON to all connected clients
- [ ] On disconnect: training continues in background

### 4.6 — REST Routers

- [ ] Create `server/app/routers/simulation.py`:
  - `POST /simulation/start` → creates Supabase simulation record, starts sim loop, returns `simulation_id`
  - `POST /simulation/stop` → stops sim loop, updates simulation status
  - `POST /simulation/reset` → resets intersection state
  - `PUT /simulation/mode` → switches between "fixed" and "ai"
  - `GET /simulation/status` → returns current `MetricsSnapshot`

- [ ] Create `server/app/routers/training.py`:
  - `POST /training/start` → `StartTrainingRequest` → launches training
  - `POST /training/stop` → calls `trainer.stop()`
  - `GET /training/status` → returns `trainer.get_status()`
  - `POST /training/load` → `{"model_id": "..."}` → loads checkpoint from Supabase Storage

- [ ] Create `server/app/routers/metrics.py`:
  - `GET /metrics/current` → returns current simulation `MetricsSnapshot`

### 4.7 — CORS & Main App Assembly

- [ ] In `server/app/main.py`:
  - Add `CORSMiddleware` with `allow_origins` from config
  - Register all routers: `app.include_router(simulation_router)`, etc.
  - Register WebSocket routes: `app.add_api_websocket_route("/ws/simulation", ...)`
  - Add `GET /health` returning `{"status": "ok"}`

**✅ Phase 4 Deliverable:** `curl localhost:8000/health` returns OK. WebSocket connects. Simulation streams frames. Training runs via WS command.

---

## PHASE 5 — NEXT.JS APPLICATION SHELL

**Goal:** Build the Next.js app structure — landing page, simulation page layout, state management, WebSocket hooks.

---

### 5.1 — Zustand Store

- [ ] Create `client/src/store/simulationStore.ts`:

  ```typescript
  interface SimulationStore {
    // Connection state
    isConnected: boolean;
    isTraining: boolean;
    mode: "fixed" | "ai";

    // Live simulation data (from WebSocket)
    currentFrame: SimulationFrame | null;
    trainingMetrics: TrainingMetric[];

    // Actions
    setFrame: (frame: SimulationFrame) => void;
    addTrainingMetric: (metric: TrainingMetric) => void;
    setMode: (mode: "fixed" | "ai") => void;
    setConnected: (v: boolean) => void;
    setTraining: (v: boolean) => void;
    resetMetrics: () => void;
  }
  ```

- [ ] Implement with `create` from Zustand

### 5.2 — TypeScript Types

- [ ] Create `client/src/types/simulation.ts` with all shared types:
  ```typescript
  export interface VehicleState {
    id: string;
    lane: string;
    position: number;
    state: string;
    wait_time: number;
  }
  export interface SimulationFrame {
    timestep: number;
    mode: string;
    signal_phase: number;
    signal_color: string;
    vehicles: VehicleState[];
    queue_lengths: Record<string, number>;
    avg_wait_time: number;
    throughput: number;
    reward: number;
    episode: number;
  }
  export interface TrainingMetric {
    episode: number;
    total_reward: number;
    avg_wait_time: number;
    throughput: number;
    epsilon: number;
    loss: number | null;
    is_training: boolean;
  }
  ```

### 5.3 — WebSocket Hooks

- [ ] Create `client/src/hooks/useSimulationSocket.ts`:

  ```typescript
  export function useSimulationSocket() {
    const setFrame = useSimulationStore((s) => s.setFrame);
    const setConnected = useSimulationStore((s) => s.setConnected);

    useEffect(() => {
      const ws = new WebSocket(
        `${process.env.NEXT_PUBLIC_FASTAPI_WS_URL}/ws/simulation`,
      );
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onmessage = (e) => setFrame(JSON.parse(e.data));
      return () => ws.close();
    }, []);

    const sendCommand = (cmd: object) => ws.send(JSON.stringify(cmd));
    return { sendCommand };
  }
  ```

- [ ] Create `client/src/hooks/useTrainingSocket.ts` (same pattern, pushes to `addTrainingMetric`)
- [ ] Both hooks: handle reconnect logic with exponential backoff (max 5 retries)

### 5.4 — Landing Page

- [ ] Create `client/src/app/page.tsx` — hero section:
  - Full viewport height
  - Centered content: project title, one-line description
  - "Launch App" `Button` → `router.push('/simulation')`
  - Subtle animated background (CSS only — grid pattern or noise using Tailwind)
  - Keep it minimal — this is not the focus

### 5.5 — Simulation Page Layout

- [ ] Create `client/src/app/simulation/page.tsx`
- [ ] Layout: two-column on desktop, stacked on mobile
  - **Left column (60%)**: Three.js simulation canvas
  - **Right column (40%)**: controls + metrics panels + tabs for charts
- [ ] Create `client/src/components/layout/Header.tsx`:
  - Logo/project name left
  - Connection status badge right (`isConnected` from store)
  - Mode indicator (Fixed / AI)
- [ ] Wire `useSimulationSocket` and `useTrainingSocket` into page-level component
- [ ] Wrap simulation page in `<QueryClientProvider>` if not already in root layout

**✅ Phase 5 Deliverable:** App navigates. Simulation page renders shell. WebSocket hooks connect and push data to Zustand store.

---

## PHASE 6 — THREE.JS VISUALIZATION

**Goal:** Build the real-time 3D intersection visualization driven by WebSocket simulation frames.

---

### 6.1 — Canvas Setup

- [ ] Create `client/src/components/simulation/SimulationCanvas.tsx`:
  - Use `<Canvas>` from `@react-three/fiber`
  - Camera: orthographic, top-down view, positioned at (0, 10, 0) looking at (0,0,0)
  - Lighting: ambient light (0.6) + directional light from top
  - Background: dark (`#0a0a0a`) matching Vercel dark theme
  - Enable shadows
  - Add `<OrbitControls>` (limited — allow zoom only, no pan/rotate for clean top-down)

### 6.2 — Intersection Ground & Roads

- [ ] Create `client/src/components/simulation/IntersectionGrid.tsx`:
  - Ground plane: `PlaneGeometry(20, 20)` with dark gray material
  - Grid lines using `GridHelper` or custom line geometry (subtle)

- [ ] Create `client/src/components/simulation/Road.tsx`:
  - Props: `direction: 'horizontal' | 'vertical'`
  - `BoxGeometry` for road surface (dark asphalt color `#1a1a1a`)
  - White lane markings using thin `PlaneGeometry` with white material
  - Stop lines at intersection entry points
  - Rendered once, static geometry — never re-created

### 6.3 — Traffic Light Component

- [ ] Create `client/src/components/simulation/TrafficLight.tsx`:
  - Props: `phase: number`, `color: 'green' | 'yellow' | 'red'`, `position: [x,y,z]`
  - 3 sphere geometries stacked: red top, yellow middle, green bottom
  - Active color uses emissive material with matching `emissiveIntensity: 2.0`
  - Inactive colors: dark/dim versions
  - 4 traffic lights placed at each arm of intersection
  - Phase determines which directional lights are active
  - Smooth color transition using `useSpring` from `@react-spring/three` (or frame lerp)

### 6.4 — Vehicle Component

- [ ] Create `client/src/components/simulation/Vehicle.tsx`:
  - Props: `vehicle: VehicleState`
  - Small `BoxGeometry(0.4, 0.2, 0.8)` with white or accent color material
  - **Position mapping**: `lane` + `position` (0→1) → world (x, y, z) coordinates:
    ```
    north lane: x = -0.5, z = position mapped from 8 → 0 (approaching center)
    south lane: x = 0.5,  z = position mapped from -8 → 0
    east lane:  z = -0.5, x = position mapped from 8 → 0
    west lane:  z = 0.5,  x = position mapped from -8 → 0
    ```
  - Vehicle color: white when moving, amber/yellow when waiting
  - `useFrame` for smooth interpolation between position updates (lerp factor 0.15)
  - Rotation: face direction of travel

### 6.5 — Main Scene Component

- [ ] Create `client/src/components/simulation/IntersectionScene.tsx`:
  - Reads `currentFrame` from Zustand store
  - Renders: `<IntersectionGrid>`, `<Road direction="vertical">`, `<Road direction="horizontal">`
  - Renders 4 `<TrafficLight>` components with current `signal_phase` and `signal_color`
  - Maps `currentFrame.vehicles` → array of `<Vehicle>` components (keyed by `vehicle.id`)
  - **Performance**: use `useMemo` to avoid re-creating vehicle list on every render
  - **Instance optimization**: use `<InstancedMesh>` for vehicles (all vehicles share one geometry, positions set via matrix). This handles 40 vehicles with zero performance cost.

### 6.6 — WebSocket-Driven Rendering

- [ ] Simulation frames arrive via WebSocket → Zustand store → React re-render triggers scene update
- [ ] `useFrame` in vehicle components interpolates position smoothly between discrete WebSocket ticks
- [ ] Vehicles spawning: appear with a brief scale-up animation (`scale: 0 → 1` over 200ms)
- [ ] Vehicles passing: fade out (`opacity: 1 → 0` over 150ms) then unmount
- [ ] Traffic light color changes: instant (no lerp needed, signal changes are intentional)

### 6.7 — Queue Length Indicators

- [ ] Above each road arm, render a text overlay showing queue length (use `<Text>` from `@react-three/drei`)
- [ ] Color: white when queue < 5, amber when 5–7, red when ≥ 8
- [ ] Updates every frame from `queue_lengths` in SimulationFrame

**✅ Phase 6 Deliverable:** Intersection renders live. Vehicles move in real-time. Traffic lights change. Queue numbers show.

---

## PHASE 7 — DASHBOARDS & UI

**Goal:** Build all control panels, metric cards, charts, and training dashboard.

---

### 7.1 — Simulation Controls Panel

- [ ] Create `client/src/components/controls/SimulationControls.tsx`:
  - **Mode Toggle**: `Switch` component — "Fixed Timer" / "AI Agent" — sends `set_mode` command via WS
  - **Start/Stop Button**: sends `start` / `stop` command
  - **Reset Button**: sends `reset` command (with confirmation)
  - **Spawn Rate Slider**: `Slider` 0.1–1.0, label "Vehicle Arrival Rate (λ)" — sends config update
  - All buttons disabled when `!isConnected`
  - Show spinner on mode switch during yellow transition

### 7.2 — Training Controls Panel

- [ ] Create `client/src/components/controls/TrainingControls.tsx`:
  - **Train Agent Button**: opens a small config popover → set `num_episodes` (default 500) → starts training via WS
  - **Stop Training Button**: visible only when `isTraining`
  - **Load Model Select**: dropdown of saved models from `useQuery(['models'])` → on select, sends `load` REST call
  - **AI Status Badge**: `<AIStatusBadge>` — shows "Idle" / "Training (Ep 43/500)" / "Ready"
  - Episode progress bar when training

### 7.3 — Live Metrics Cards

- [ ] Create `client/src/components/dashboard/MetricsPanel.tsx`:
  - 4 metric cards using Shadcn `<Card>`:
    1. **Avg Wait Time** — `currentFrame.avg_wait_time` seconds
    2. **Throughput** — `currentFrame.throughput` vehicles passed
    3. **Queue Length** — max of all 4 queue lengths
    4. **Current Episode** — from training metrics or simulation
  - Numbers animate on change using Framer Motion `animate` on value change
  - Each card shows a tiny sparkline (last 20 values) using recharts `<SparklineChart>`

### 7.4 — Training Chart

- [ ] Create `client/src/components/dashboard/TrainingChart.tsx`:
  - Recharts `<LineChart>` showing `trainingMetrics` from Zustand store
  - Two lines: **Total Reward** (primary) and **Avg Wait Time** (secondary, right Y-axis)
  - X-axis: episode number
  - Live updates as new `TrainingMetric` entries push into store
  - Smooth: only show last 100 episodes by default, scrollable
  - Epsilon shown as faded area chart below (exploration rate decaying)

### 7.5 — Fixed vs AI Comparison Chart

- [ ] Create `client/src/components/dashboard/ComparisonChart.tsx`:
  - `<BarChart>` with grouped bars: Fixed vs AI
  - Metrics: Avg Wait Time, Throughput, Max Queue Length
  - Data source: `useQuery(['metrics', simulationId])` from Supabase via Next.js API
  - Shows after at least one completed simulation of each mode
  - Improvement percentage badge (e.g., "AI reduced wait time by 34%")

### 7.6 — Episode History Table

- [ ] Create `client/src/components/dashboard/EpisodeHistory.tsx`:
  - Shadcn `<Table>` showing past episodes
  - Columns: Episode #, Reward, Avg Wait, Throughput, Epsilon, Duration
  - Data: `useEpisodes(simulationId)`
  - Pagination: show 10 per page
  - Highlight best episode (highest reward) in green

### 7.7 — Main Simulation Page Assembly

- [ ] Update `client/src/app/simulation/page.tsx` with full layout:
  ```
  ┌─────────────────────────────────────────────────────┐
  │                    Header                           │
  ├─────────────────────────┬───────────────────────────┤
  │                         │  SimulationControls       │
  │   SimulationCanvas      │  TrainingControls         │
  │   (Three.js / R3F)      ├───────────────────────────┤
  │                         │  MetricsPanel (4 cards)   │
  │                         ├───────────────────────────┤
  │                         │  Tabs:                    │
  │                         │  [Training] [Compare]     │
  │                         │  [History]                │
  └─────────────────────────┴───────────────────────────┘
  ```
- [ ] Use Shadcn `<Tabs>` for the bottom-right panel
- [ ] Responsive: on mobile, stack canvas on top, panels below

**✅ Phase 7 Deliverable:** Full UI is functional. All panels render with live data. Charts update during training.

---

## PHASE 8 — INTEGRATION & END-TO-END FLOW

**Goal:** Ensure the complete system works end-to-end. Verify all data flows, edge cases, and UX transitions.

---

### 8.1 — End-to-End Simulation Flow

- [ ] Start FastAPI server + Next.js dev server simultaneously
- [ ] Open app → landing page renders → click "Launch App" → simulation page loads
- [ ] `useSimulationSocket` connects to `ws://localhost:8000/ws/simulation`
- [ ] Connection status badge turns green
- [ ] Three.js scene renders intersection
- [ ] Click "Start" → simulation begins → vehicles appear → traffic lights cycle
- [ ] Toggle mode "Fixed → AI" → verify agent controls signals (no timer cycling)
- [ ] Verify `SimulationFrame` JSON is well-formed in browser Network tab

### 8.2 — End-to-End Training Flow

- [ ] Click "Train Agent" with 100 episodes (quick test)
- [ ] `useTrainingSocket` connects to `ws://localhost:8000/ws/training`
- [ ] Training chart populates episode by episode
- [ ] Epsilon decays visibly in chart
- [ ] After training: episode history table in Supabase populates (verify in Supabase dashboard)
- [ ] Model checkpoint uploaded to Supabase Storage (verify in Storage bucket)
- [ ] Load trained model → switch to AI mode → verify improved signal behavior

### 8.3 — Comparison Flow

- [ ] Run 50-episode fixed-mode simulation → stop → save metrics
- [ ] Switch to AI mode → load trained model → run 50-step simulation → stop
- [ ] Comparison chart shows both results side by side
- [ ] Improvement percentage calculated correctly

### 8.4 — Edge Cases & Resilience

- [ ] WebSocket disconnect mid-simulation: verify reconnect hook retries, simulation resumes
- [ ] FastAPI server restart: Next.js app shows disconnected state, reconnects when server is back
- [ ] Training stop mid-episode: verify partial episode is NOT written to DB (or written with `partial` flag)
- [ ] Max queue overflow (λ=1.0): verify vehicles are dropped, no crash
- [ ] Load non-existent model ID: FastAPI returns 404, UI shows toast error

### 8.5 — Environment Variables Verification

- [ ] All `NEXT_PUBLIC_*` vars accessible in browser
- [ ] `DATABASE_URL` only on server-side (never leaked to client)
- [ ] FastAPI `SUPABASE_SERVICE_KEY` never exposed to frontend

**✅ Phase 8 Deliverable:** Full system works end-to-end. All flows verified. No crashes on edge cases.

---

## PHASE 9 — PERFORMANCE OPTIMIZATION

**Goal:** Ensure smooth 60fps rendering, fast API responses, and efficient training loop.

---

### 9.1 — Three.js / R3F Optimization

- [ ] **InstancedMesh for vehicles**: Replace individual `<Vehicle>` mesh components with a single `<InstancedMesh count={40}>`. Update instance matrices each frame. Zero garbage collection pressure.
  ```typescript
  const meshRef = useRef<THREE.InstancedMesh>(null);
  useFrame(() => {
    vehicles.forEach((v, i) => {
      dummy.position.set(...vehicleWorldPos(v));
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });
  ```
- [ ] **Memoize static geometry**: Road, grid, intersection ground — use `useMemo` so geometry is created once
- [ ] **Dispose on unmount**: All geometries, materials, and textures must be disposed in useEffect cleanup
- [ ] **Pixel ratio**: Set `<Canvas dpr={[1, 1.5]}>` — cap at 1.5× to avoid 4K overhead
- [ ] **Frame budget**: Target ≤ 4ms render time. Profile with `r3f-perf` during development

### 9.2 — WebSocket Optimization

- [ ] FastAPI sends simulation frames at exactly 10fps (`asyncio.sleep(0.1)`) — do not exceed this
- [ ] JSON frame size: keep under 2KB per frame. Avoid sending full vehicle history, only current state
- [ ] Training metrics: batch per episode (not per step) — ~0.5fps during training is fine
- [ ] Use `ujson` in FastAPI for faster JSON serialization: `pip install ujson`

### 9.3 — React Rendering Optimization

- [ ] Simulation canvas component: wrap in `React.memo` — only re-renders when `currentFrame` changes
- [ ] Dashboard charts: `useMemo` on data arrays passed to Recharts
- [ ] Training chart: only re-render on new metric added (use `trainingMetrics.length` as dep)
- [ ] Zustand selectors: use granular selectors (not full store) to minimize re-renders

### 9.4 — FastAPI Async Optimization

- [ ] All Supabase calls in FastAPI are `async` — use `asyncio.gather()` where multiple DB writes happen together
- [ ] Simulation loop runs in `asyncio` background task — never blocks the event loop
- [ ] Training loop: runs in `asyncio.to_thread()` for CPU-bound PyTorch work — keeps FastAPI responsive
  ```python
  await asyncio.to_thread(agent.train_step, batch)
  ```

### 9.5 — Memory Management

- [ ] Replay buffer: fixed max size 10,000 (deque auto-evicts old samples) — memory bounded
- [ ] Training metrics in Zustand: cap at 1,000 entries in store (older ones trimmed)
- [ ] Vehicle list: max 40 vehicles total (4 lanes × 10 max queue) — bounded

**✅ Phase 9 Deliverable:** Simulation runs at stable 60fps. No memory leaks. FastAPI stays responsive during training.

---

## PHASE 10 — DEPLOYMENT

**Goal:** Deploy FastAPI to Railway, Next.js to Vercel, configure production environment.

---

### 10.1 — Docker Setup (FastAPI)

- [ ] Create `server/Dockerfile`:

  ```dockerfile
  FROM python:3.11-slim

  WORKDIR /app

  # Install system dependencies
  RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

  # Install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy app
  COPY app/ ./app/

  # Create models directory
  RUN mkdir -p models

  # Expose port
  EXPOSE 8000

  # Start server
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] Create `server/.dockerignore`:
  ```
  __pycache__/
  *.pyc
  venv/
  .env
  models/*.pt
  ```
- [ ] Test Docker build locally: `docker build -t traffic-server .`
- [ ] Test Docker run: `docker run -p 8000:8000 --env-file .env traffic-server`
- [ ] Verify `http://localhost:8000/health` returns OK from Docker container

### 10.2 — Railway Deployment

- [ ] Create `server/railway.toml`:

  ```toml
  [build]
  builder = "DOCKERFILE"
  dockerfilePath = "Dockerfile"

  [deploy]
  startCommand = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
  restartPolicyType = "ON_FAILURE"
  restartPolicyMaxRetries = 3
  ```

- [ ] Create new Railway project, connect GitHub repo
- [ ] Set Railway root directory to `server/`
- [ ] Add Railway environment variables:
  ```
  SUPABASE_URL=...
  SUPABASE_SERVICE_KEY=...
  CORS_ORIGINS=https://your-app.vercel.app
  ```
- [ ] Deploy and verify Railway URL is live
- [ ] Note Railway public URL: `https://traffic-server-xxx.railway.app`

### 10.3 — Vercel Deployment

- [ ] Push `client/` to GitHub
- [ ] Create new Vercel project, connect repo
- [ ] Set Vercel root directory to `client/`
- [ ] Add Vercel environment variables:
  ```
  DATABASE_URL=...
  NEXT_PUBLIC_SUPABASE_URL=...
  NEXT_PUBLIC_SUPABASE_ANON_KEY=...
  NEXT_PUBLIC_FASTAPI_WS_URL=wss://traffic-server-xxx.railway.app
  NEXT_PUBLIC_FASTAPI_HTTP_URL=https://traffic-server-xxx.railway.app
  ```
- [ ] Deploy and verify Vercel URL is live
- [ ] Update Railway `CORS_ORIGINS` with actual Vercel URL
- [ ] Test full production flow: open Vercel app → simulate → train → compare

### 10.4 — Production WebSocket Configuration

- [ ] Verify WebSocket URL uses `wss://` (not `ws://`) in production — TLS required
- [ ] Railway automatically handles TLS termination — no extra config needed
- [ ] Test WebSocket connection from Vercel → Railway in browser Network tab
- [ ] Confirm `Connection: Upgrade` headers are passing through

### 10.5 — Final Production Checks

- [ ] CORS: verify Railway allows requests from Vercel domain
- [ ] Supabase RLS: since no auth, ensure Row Level Security is disabled or open for these tables
- [ ] Environment variables: double-check none are missing in production
- [ ] Health check endpoint: verify Railway health check pings `/health`
- [ ] First deployment smoke test: run a 10-episode training run on production

**✅ Phase 10 Deliverable:** App is live on Vercel. AI server running on Railway. Full system works in production.

---

## FUTURE EXPANSIONS

> These are NOT part of the current build. Implement only after the core project is complete and stable.

### F.1 — Multi-Intersection Support

- Grid of N×M intersections, each with its own signal controller
- Multi-agent RL: one DQN agent per intersection, or one shared agent with larger state space
- Requires significant changes to `TrafficEnv` and `Intersection` classes
- Frontend: pan/zoom camera to see full grid
- Database: `intersections` table linked to simulation

### F.2 — Emergency Vehicle Priority

- Special vehicle type with higher priority
- Agent gets large negative reward if emergency vehicle is blocked
- Visual: flashing red/blue lights in Three.js

### F.3 — Pedestrian Crossings

- Pedestrian phase added to signal cycle
- New lane type: crosswalk
- Spawner: pedestrian Poisson process

### F.4 — Weather System

- Rain/fog/ice conditions affect vehicle speed and spawn rates
- Environment parameter: `weather: "clear" | "rain" | "fog" | "ice"`
- Visual: particle system in Three.js for rain/snow

### F.5 — Advanced RL Algorithms

- Replace DQN with PPO (via Stable-Baselines3) for better sample efficiency
- Implement A3C for multi-intersection (async multi-agent)
- Add curriculum learning: start with low traffic, increase λ as agent improves

### F.6 — Accident Simulation

- Random accident events block a lane for N seconds
- Agent must respond by prioritizing other phases
- New vehicle state: `"blocked"`

### F.7 — Historical Replay

- Save full simulation state sequence to Supabase Storage
- UI: timeline scrubber to replay any past simulation frame-by-frame

---

_End of PLAN.md_

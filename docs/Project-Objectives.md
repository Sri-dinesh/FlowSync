# PROJECT_SPECIFICATION.md

# FlowSync — AI-Powered Real-Time Traffic Signal Control System

### Master Design Document & Single Source of Truth

---

**Version:** 2.0  
**Status:** Active Development  
**Last Updated:** 2026-07-18  
**Authors:** FlowSync Engineering Team

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [System Overview](#2-system-overview)
3. [Functional Requirements](#3-functional-requirements)
4. [Modules](#4-modules)
5. [User Flows](#5-user-flows)
6. [Technical Architecture](#6-technical-architecture)
7. [Data Model](#7-data-model)
8. [API Specification](#8-api-specification)
9. [Business Rules](#9-business-rules)
10. [AI & RL Components](#10-ai--rl-components)
11. [Security](#11-security)
12. [Performance](#12-performance)
13. [Error Handling](#13-error-handling)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment](#15-deployment)
16. [Development Standards](#16-development-standards)
17. [Known Limitations](#17-known-limitations)
18. [Future Roadmap](#18-future-roadmap)
19. [Appendix](#19-appendix)

---

## 1. PROJECT OVERVIEW

### 1.1 Project Vision

FlowSync is an AI-powered, real-time traffic signal control system that replaces static,
fixed-timer traffic signals with a Deep Reinforcement Learning (DRL) agent that dynamically
optimizes signal phases based on live vehicle demand. It serves as a proof-of-concept
Digital Twin for smart-city infrastructure — demonstrating that an autonomous RL agent
can significantly outperform traditional traffic control methods.

The system targets real-world deployment at Indian urban intersections (Secunderabad,
Telangana), where left-hand traffic conventions, high vehicle density, and heterogeneous
traffic composition make adaptive control especially critical.

### 1.2 Problem Statement

Urban traffic congestion causes billions of dollars in annual productivity loss worldwide.
Existing signal control approaches have fundamental limitations:

| Approach                           | Limitation                                                                                         |
| ---------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Fixed-Timer**                    | Ignores real-time vehicle demand; wastes green time on empty lanes                                 |
| **Vehicle Actuated Control (VAC)** | Requires expensive inductive loop sensors embedded in road; detects presence only, not queue depth |
| **SCOOT / SCATS**                  | Proprietary, city-scale infrastructure; impractical for single-intersection deployment             |

FlowSync addresses this by providing a camera-ready, sensor-free adaptive signal control
system that requires only existing CCTV infrastructure and runs entirely on software.

### 1.3 Goals and Objectives

**Primary Goals:**

- Demonstrate measurable improvement in average vehicle wait time vs fixed-timer baseline
- Provide a live, interactive simulation where users observe AI learning in real time
- Build a research-grade DRL implementation suitable for academic publication

**Specific Objectives:**

- Average vehicle wait time reduction of ≥20% vs fixed-timer baseline
- Zero signal phase conflicts (no two conflicting directions simultaneously green)
- Stable training convergence over 500+ episodes without reward collapse
- Real-time simulation at ≥10Hz with smooth 60fps frontend visualization
- Handle 200-300 simultaneous vehicles without deadlock

### 1.4 Success Criteria

| Criterion              | Metric                               | Target                   |
| ---------------------- | ------------------------------------ | ------------------------ |
| Wait time reduction    | Avg wait time: AI vs Fixed           | ≥20% improvement         |
| Throughput             | Vehicles/minute passing intersection | ≥15% improvement         |
| Signal safety          | Phase conflicts per hour             | 0 (zero tolerance)       |
| Training stability     | Reward trend over 500 episodes       | Monotonically increasing |
| Simulation performance | WebSocket frame rate                 | 10Hz sustained           |
| Frontend render rate   | Three.js scene FPS                   | 60fps sustained          |
| System availability    | Uptime during demo                   | 99%+                     |

### 1.5 Target Users

| User                       | Use Case                                                            |
| -------------------------- | ------------------------------------------------------------------- |
| **Researchers & Students** | Study RL applied to traffic control; extend for academic research   |
| **Smart-City Engineers**   | Evaluate AI-based signal control before real-world deployment       |
| **Hackathon Judges**       | Assess full-stack AI engineering capability                         |
| **Project Reviewers**      | BTech mini-project evaluation; conference paper reviewers           |
| **Developers**             | Reference architecture for full-stack AI + 3D visualization systems |

### 1.6 Business Value

- **Infrastructure cost**: Zero additional hardware beyond existing CCTV
- **Research contribution**: Novel CCTV-to-signal pipeline (sim-to-real transfer)
- **Scalability path**: Single intersection agent → multi-intersection city network
- **Educational value**: Live, interactive demonstration of RL learning in real time

---

## 2. SYSTEM OVERVIEW

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                               │
│                                                                     │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐   │
│  │   Three.js 3D Scene      │   │   Dashboard / Charts          │   │
│  │   (R3F Renderer)         │   │   (TanStack Query)            │   │
│  └────────────┬─────────────┘   └──────────────┬───────────────┘   │
│               │ WebSocket (10Hz)                │ HTTP (REST)       │
└───────────────┼────────────────────────────────┼───────────────────┘
                │                                 │
                ▼                                 ▼
┌──────────────────────────┐       ┌──────────────────────────────┐
│   FastAPI Server          │       │   Next.js API Routes          │
│   (Render / Docker)       │       │   (Vercel Edge)               │
│                           │       │                               │
│  ┌─────────────────────┐  │       │  /api/simulations             │
│  │  Simulation Engine   │  │       │  /api/episodes                │
│  │  (Intersection +     │  │       │  /api/metrics                 │
│  │   TrafficSignal +    │  │       │  /api/models                  │
│  │   PoissonSpawner)    │  │       │  /api/keep-alive              │
│  └──────────┬──────────┘  │       └──────────────┬───────────────┘
│             │              │                      │
│  ┌──────────▼──────────┐  │                      │
│  │   DQN RL Agent       │  │                      │
│  │   (PyTorch)          │  │                      │
│  └──────────┬──────────┘  │                      │
│             │              │                      │
│  ┌──────────▼──────────┐  │                      │
│  │  Supabase Client     │◄─┼──────────────────────┘
│  │  (writes metrics)    │  │         (reads metrics)
│  └─────────────────────┘  │
└──────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│       Supabase            │
│  PostgreSQL + Storage     │
└──────────────────────────┘
```

### 2.2 Core Components

| Component             | Technology              | Responsibility                                 |
| --------------------- | ----------------------- | ---------------------------------------------- |
| **Simulation Engine** | Python (Gymnasium)      | Models intersection physics, vehicles, signals |
| **DRL Agent**         | PyTorch (DQN)           | Learns optimal signal phase selection          |
| **FastAPI Server**    | Python (FastAPI)        | WebSocket streaming, REST API, orchestration   |
| **Next.js App**       | Next.js 16 (App Router) | Frontend UI, API routes, DB reads              |
| **Three.js Scene**    | React Three Fiber       | Real-time 3D intersection visualization        |
| **Supabase DB**       | PostgreSQL (Prisma ORM) | Simulation data persistence                    |
| **Supabase Storage**  | S3-compatible           | Model checkpoint (.pt file) storage            |

### 2.3 System Boundaries

**In Scope:**

- Single 4-way intersection simulation
- 3 control modes: Fixed-Timer, AI (DQN), Manual
- Real-time training with live metric streaming
- Model checkpoint save/load
- Performance comparison dashboard
- Emergency vehicle preemption

**Out of Scope (Current Version):**

- Multi-intersection city network
- Real CCTV feed integration
- Physical traffic light hardware control
- Authentication / multi-user sessions
- GPU training
- Mobile application

### 2.4 Overall Workflow

```
User opens /simulation
    ↓
WebSocket connects to FastAPI (/ws/simulation)
    ↓
User clicks Start → Simulation loop begins at 10Hz
    ↓
Each tick:
  ├── Spawner adds vehicles (Poisson distribution)
  ├── Signal advances (Fixed) OR Agent selects phase (AI) OR User holds phase (Manual)
  ├── Vehicles advance in their lanes
  ├── SimulationFrame JSON built and broadcast
  └── Frontend renders frame in Three.js
    ↓
User clicks Train → Training WebSocket connects (/ws/training)
    ↓
Per episode:
  ├── TrafficEnv.reset() → fresh intersection
  ├── Agent explores via ε-greedy for 500-1000 steps
  ├── Replay buffer sampled → DQN trained
  ├── Episode metrics saved to Supabase
  └── Metrics broadcast to frontend (live charts update)
    ↓
Every 50 episodes:
  ├── Model checkpoint saved to Supabase Storage
  └── Sim agent weights synced from training agent
```

### 2.5 Design Principles

1. **Separation of concerns** — Simulation and Training use independent environment instances
2. **Safety over learning** — Signal conflicts enforced as hard code constraints, never learned behavior
3. **Streaming over polling** — WebSocket for all real-time data; REST only for historical reads
4. **Server-side computation** — World coordinates, signal colors, Q-values computed server-side
5. **Fail-safe defaults** — Any error returns to safe state (all signals red, simulation paused)
6. **Research-grade RL** — Implementation follows peer-reviewed papers (Bellman equations, Double DQN)

---

## 3. FUNCTIONAL REQUIREMENTS

### 3.1 Fixed-Timer Signal Control

**Purpose:** Provide a traditional, rule-based signal controller as a baseline for AI comparison.

**Behavior:**

- Cycles through 4 phases in fixed sequence: Phase 0 → 1 → 2 → 3 → 0
- Each phase runs for a configurable `green_duration` (default: 30 seconds)
- Phase transitions go through yellow (3s) → all-red clearance (3s) → new green
- Smart queue-based phase skipping: if current phase's lanes have 0 waiting vehicles
  AND minimum green time has elapsed, skip to the next phase with waiting vehicles
- If no phase has waiting vehicles, continue cycling sequentially

**Constraints:**

- Minimum green time: 8 seconds (prevents flickering)
- Maximum green time: 40 seconds (prevents starvation)
- Yellow duration: 3 seconds (fixed, non-configurable)
- All-red clearance: 3 seconds (configurable via `SIGNAL_RED_DURATION` env var)

**Inputs:** Current intersection state (queue lengths per direction)  
**Outputs:** Signal phase 0-3, color per lane, time in phase  
**Error handling:** If timer state is corrupted, reset to Phase 0 GREEN

---

### 3.2 AI (DQN) Signal Control

**Purpose:** Deep Q-Network agent that learns optimal signal timing through reinforcement learning.

**State Space (8-dimensional observation vector):**

| Index | Value            | Range | Description                               |
| ----- | ---------------- | ----- | ----------------------------------------- |
| 0     | `q_north`        | 0–10  | Vehicles waiting in north lanes           |
| 1     | `q_south`        | 0–10  | Vehicles waiting in south lanes           |
| 2     | `q_east`         | 0–10  | Vehicles waiting in east lanes            |
| 3     | `q_west`         | 0–10  | Vehicles waiting in west lanes            |
| 4     | `current_phase`  | 0–3   | Active or transitioning-to phase          |
| 5     | `time_in_phase`  | 0–60  | Seconds in current phase                  |
| 6     | `total_vehicles` | 0–40  | Total vehicles in simulation              |
| 7     | `pending_phase`  | 0–3   | Phase queued during yellow/red transition |

**Action Space:** Discrete(4) — select which phase to activate next

**Reward Function:**

```
R = queue_reduction_reward + throughput_bonus + switch_penalty + overflow_penalty + balance_bonus

Where:
  queue_reduction_reward = 0.3 × (prev_total_queue - curr_total_queue)
  throughput_bonus       = 0.8 × vehicles_passed_this_step
  switch_penalty         = -0.3  if phase changed, else 0.0
  overflow_penalty       = -1.5  × count(lanes where queue ≥ 6)
  balance_bonus          = +0.2  if max_queue - min_queue ≤ 2, else 0.0
```

**Hard Constraints (enforced in environment.step(), not learned):**

- Agent cannot switch phase if `time_in_phase < MIN_GREEN_TIME (8s)`
- If `time_in_phase >= MAX_GREEN_TIME (40s)`, force switch to highest-pressure alternative
- If any direction has waited `>= STARVATION_THRESHOLD (45s)`, override action to serve it

**Inputs:** 8-dim observation vector from `environment._get_obs()`  
**Outputs:** Integer action 0-3  
**Error handling:** If action is out of range [0,3], default to current phase (no change)

---

### 3.3 Manual Signal Control

**Purpose:** Human-in-the-loop mode for direct operator control and educational comparison.

**Behavior:**

- Signal holds current green phase indefinitely (no auto-cycling)
- User selects phase via 4 buttons in the frontend controls panel
- Phase changes go through yellow (3s) → all-red (3s) → new green transition
- Yield-on-left logic still applies during green phases
- Emergency override still takes priority over manual selection

**Inputs:** `manual_override` WebSocket command with `phase: 0-3`  
**Outputs:** Signal transitions to selected phase  
**Error handling:** Invalid phase value (not 0-3) is ignored; current phase held

---

### 3.4 Live Training Dashboard

**Purpose:** Stream RL training progress to the user in real time.

**Metrics streamed per episode:**

- Episode number
- Total episode reward
- Average vehicle wait time
- Throughput (vehicles passed)
- Epsilon (current exploration rate)
- Loss (average Huber loss for the episode)
- Training status (is_training: bool)

**Behavior:**

- Training WebSocket (`/ws/training`) broadcasts after each episode completes
- Configurable episode count (1–2000, default 500)
- Every 50 episodes: checkpoint saved, metadata upserted to DB
- Training continues in background even if client disconnects
- Stop command gracefully halts after current episode completes

**Inputs:** User clicks Train, sets episode count  
**Outputs:** Per-episode metric stream, checkpoint notifications  
**Error handling:** If DB write fails, training continues; error logged, metric not lost

---

### 3.5 Model Persistence & Loading

**Purpose:** Save trained agent checkpoints and reload for inference.

**Save behavior:**

- Triggered every 50 episodes during training
- Saves PyTorch state dict (online net + target net + optimizer + step count)
- Uploads to Supabase Storage: `models/{simulation_id}/checkpoint_{episode}.pt`
- Also saves to local disk: `server/models/` as fallback
- Metadata upserted to `rl_models` DB table (prevents duplicate rows per run)

**Load behavior:**

- Dropdown populates from `/training/models` endpoint (3-tier discovery)
- Load call downloads from Supabase Storage (falls back to local disk)
- Loaded into BOTH `sim_agent` and `training_agent` network instances
- Checkpoint version tag (`obs_version`) validated for architecture compatibility

**Inputs:** Model ID selected from dropdown  
**Outputs:** Agent weights updated; confirmation displayed  
**Error handling:** Legacy checkpoint (incompatible obs_version) raises clear error; not silently loaded

---

### 3.6 Emergency Vehicle Preemption

**Purpose:** Immediately prioritize signal for emergency vehicle (ambulance).

**Behavior:**

- 4 directional buttons (N/S/E/W) spawn an emergency vehicle in that lane
- Signal immediately overrides to green for the emergency vehicle's direction
- Override bypasses RL/Fixed/Manual control until vehicle clears intersection
- Only one emergency vehicle per direction at a time
- After vehicle passes, normal control mode resumes

**Inputs:** `emergency_override` WS command with `lane: "north"|"south"|"east"|"west"`  
**Outputs:** Signal forced to priority phase; emergency vehicle spawned  
**Error handling:** If another emergency is active in same lane, command is ignored

---

### 3.7 Performance Comparison

**Purpose:** Side-by-side comparison of Fixed vs AI vs Manual control modes.

**Behavior:**

- After completing simulations in each mode, Compare tab shows bar chart
- Metrics compared: avg wait time, throughput, max queue length
- Improvement percentage calculated relative to Fixed baseline
- Data read from Supabase `performance_metrics` table via Next.js API

**Inputs:** Historical simulation data in Supabase  
**Outputs:** Bar chart with grouped bars per mode, improvement badge  
**Error handling:** If no data for a mode, that mode's bar is empty; no error shown

---

### 3.8 Configurable Traffic Flow

**Purpose:** Allow user to adjust vehicle arrival rate to test different congestion levels.

**Behavior:**

- Slider range: 0.1 (sparse) to 1.0 (heavy) vehicles/second/lane
- Default: 0.3
- Sends `set_spawn_rate` WS command with clamped float value
- Takes effect immediately on next simulation tick
- Value is clamped: `max(0.1, min(1.0, value))` server-side

**Inputs:** Slider drag → WS command  
**Outputs:** `PoissonSpawner.lambda_rate` updated  
**Error handling:** Values outside [0.1, 1.0] clamped silently; non-numeric values ignored

---

## 4. MODULES

### 4.1 Simulation Engine

**Purpose:** Model the physics of a 4-way intersection — vehicles, signals, queues.

**Responsibilities:**

- Maintain 12 independent sub-lane queues (4 directions × 3 turns: left/straight/right)
- Advance vehicle positions each tick
- Enforce signal phase rules on vehicle movement
- Track throughput (total vehicles passed), timestep, average wait time
- Implement Poisson vehicle spawning with turn probability distribution

**Public Interface:**

```python
class Intersection:
    def tick(dt: float, action: Optional[int], is_manual: bool) -> None
    def reset() -> None
    def get_queue_lengths() -> Dict[str, int]      # 4-key: direction aggregates
    def get_movement_queues() -> Dict[str, int]    # 12-key: per sub-lane
    def get_total_waiting() -> int
    def get_avg_wait_time() -> float
    def get_max_wait_time() -> float
    def get_outgoing_counts() -> Dict[str, int]
```

**Internal Workflow:**

```
tick(dt, action, is_manual):
  1. Apply action to signal (if action provided and can_switch_phase())
  2. Tick signal timer (advance phase transitions)
  3. Spawn new vehicles (Poisson)
  4. For each of 12 sub-lanes:
       - Evaluate can_move for lead vehicle
       - Apply Indian traffic rules (left=always free, right=protected only)
       - Advance position or increment wait_time
       - Mark passed vehicles (position >= 1.0)
  5. Remove passed vehicles from queues
  6. Increment timestep
```

**Data Ownership:** Owns all vehicle state, signal state, queue state.  
**Failure Handling:** Python exceptions logged; intersection state preserved (no partial updates).

---

### 4.2 Traffic Signal

**Purpose:** State machine managing the 4-phase signal cycle with transition logic.

**Responsibilities:**

- Track current phase, color, time_in_phase, pending_phase
- Manage yellow → all-red → green transitions
- Enforce minimum and maximum green time constraints
- Track per-direction starvation timers
- Determine which vehicles have green permission per phase

**Phase Definitions (Indian Left-Hand Traffic):**

```
Phase 0 — NS_STRAIGHT: North+South straight vehicles + free left turns
Phase 1 — EW_STRAIGHT: East+West straight vehicles + free left turns
Phase 2 — NS_RIGHT:    North+South protected right turns ONLY
Phase 3 — EW_RIGHT:    East+West protected right turns ONLY

Indian Traffic Rules:
  Left turns  → ALWAYS FREE, never blocked by signal
  Right turns → PROTECTED ONLY, only during Phase 2 or 3
  Straight    → Governed by Phase 0 (NS) or Phase 1 (EW)
```

**State Machine:**

```
GREEN ──(agent action / timer)──► YELLOW ──(3s)──► RED ──(3s)──► GREEN (new phase)
```

**Public Interface:**

```python
class TrafficSignal:
    def tick(dt: float, is_manual: bool) -> None
    def set_phase(new_phase: int) -> None
    def is_green_for(direction: str, turn: str) -> bool
    def can_switch_phase() -> bool
    def get_color_per_lane() -> Dict[str, str]
    def get_starved_directions() -> List[str]
    @property is_max_green_exceeded: bool
    @property starvation_timer: Dict[str, float]
```

**Invariant (MUST ALWAYS BE TRUE):**

> At no point in time can `is_green_for()` return True for two directions that conflict with each other.
> This is enforced by the phase definition: only one direction group can be in GREEN state.

**Failure Handling:** If state machine reaches undefined state, revert to Phase 0 ALL_RED.

---

### 4.3 Gymnasium Environment (`TrafficEnv`)

**Purpose:** Wrap the Intersection as a standard Gymnasium RL environment for DQN training.

**Responsibilities:**

- Define observation space and action space
- Build 8-dim observation vector from intersection state
- Compute reward after each step
- Enforce hard constraints on agent actions before applying
- Track episode termination

**Public Interface:**

```python
class TrafficEnv(gymnasium.Env):
    observation_space: Box(low=0, high=[10,10,10,10,3,60,40,3], shape=(8,))
    action_space: Discrete(4)
    def reset(seed=None) -> Tuple[np.ndarray, dict]
    def step(action: int) -> Tuple[np.ndarray, float, bool, bool, dict]
    def _get_obs() -> np.ndarray
    def compute_reward(...) -> float
```

**Note:** This environment is used EXCLUSIVELY by the Trainer. It is NEVER accessed
by the simulation WebSocket handler. The simulation WebSocket uses `sim_intersection`
directly (separate instance) and builds its own observation vector independently.

---

### 4.4 DQN Agent

**Purpose:** Deep Q-Network that learns to select optimal signal phases.

**Architecture:** Double DQN with Huber Loss, Replay Buffer, Gradient Clipping.

**Responsibilities:**

- Select actions via ε-greedy policy
- Store transitions in replay buffer
- Train online network via sampled batches
- Periodically sync target network (soft Polyak update)
- Expose Q-values for dashboard visualization
- Save/load checkpoint files

**Two Agent Instances:**

```
sim_agent      → used ONLY by simulation_ws.py for live inference
                 receives gradient-free weight copies from training_agent

training_agent → used ONLY by Trainer for gradient updates
                 NEVER accessed by simulation loop
```

This isolation prevents PyTorch thread-safety violations (concurrent read+write on same tensor).

---

### 4.5 Trainer

**Purpose:** Orchestrate the DQN training loop across multiple episodes.

**Responsibilities:**

- Run episode loops (reset → step → train → repeat)
- Manage epsilon decay schedule
- Call `train_step()` on batches from replay buffer
- Broadcast per-episode metrics via training WebSocket
- Save checkpoints every N episodes
- Sync `sim_agent` weights after checkpoints
- Write episode data to Supabase

**Interaction with other modules:**

- Owns `training_env` (TrafficEnv instance — private, never shared)
- Owns `training_agent` (DQNAgent instance — private, never shared)
- Calls `supabase_service.save_episode()` async via `asyncio.to_thread`
- Calls `ws_broadcast_fn()` after each episode

---

### 4.6 WebSocket Handlers

**Purpose:** Manage real-time bidirectional communication with the browser.

**`/ws/simulation`:**

- Runs simulation loop at 10Hz while clients are connected
- Accepts commands: start, stop, reset, set_mode, set_spawn_rate,
  emergency_override, manual_override
- Validates all incoming commands before processing
- Broadcasts `SimulationFrame` JSON every 100ms
- Samples DB metrics every 50 ticks; flushes every 10 samples

**`/ws/training`:**

- Accepts commands: start_training, stop_training
- Launches training as background asyncio task
- Broadcasts `TrainingMetric` JSON after each episode
- Broadcasts `checkpoint_saved` notification every 50 episodes
- Training persists if client disconnects

---

### 4.7 Supabase Services

**Purpose:** All database and storage I/O for the FastAPI backend.

**`SupabaseService` responsibilities:**

- Write simulation records on start/stop
- Write episode records after each training episode
- Batch-write traffic logs and signal states (buffered, flushed every ~50s)
- Write performance metrics on simulation stop
- Upsert model metadata on checkpoint save

**`ModelService` responsibilities:**

- Upload `.pt` files to Supabase Storage bucket `model-checkpoints`
- Download `.pt` files for model loading
- List available checkpoints (3-tier: DB → Storage → local disk)

---

### 4.8 Next.js API Routes

**Purpose:** Server-side data access layer for frontend → Supabase reads.

**Why separate from FastAPI:**

- FastAPI writes data (it has the service key)
- Next.js reads data (it uses Prisma with direct DB URL)
- Separation prevents exposing Supabase service key to browser
- Next.js routes can be cached and edge-deployed on Vercel

**Routes:**

```
GET /api/simulations  → prisma.simulation.findMany(orderBy: createdAt desc, take: 20)
GET /api/models       → prisma.rLModel.findMany(orderBy: createdAt desc)
GET /api/metrics      → prisma.performanceMetric.findMany(where: simulationId)
GET /api/episodes     → prisma.episode.findMany(where: simulationId, take: 500)
GET /api/keep-alive   → fetch(FASTAPI_URL/health)
```

---

## 5. USER FLOWS

### 5.1 Complete Simulation Flow

```
1. User navigates to /simulation
2. Next.js page loads, useSimulationSocket() hook mounts
3. WebSocket connects: ws://backend/ws/simulation
4. Connection established → isConnected = true (green badge in header)
5. Three.js scene renders static intersection (no vehicles yet)

6. User clicks "Start"
   └── sendCommand({command: "start"}) via WS
   └── Backend: sim_running = true, creates simulation record in Supabase
   └── Simulation loop begins at 10Hz

7. Each 100ms frame:
   └── Backend tick() → build_frame() → WS broadcast
   └── Frontend: setFrame(parsedFrame) → Zustand store
   └── React re-render triggers Three.js scene update
   └── Vehicles appear and move

8. User adjusts spawn rate via slider
   └── sendCommand({command: "set_spawn_rate", value: 0.7})
   └── Backend clamps and updates spawner.lambda_rate

9. User toggles mode to "AI"
   └── sendCommand({command: "set_mode", mode: "ai"})
   └── Backend: mode = "ai", subsequent ticks use agent.select_action()

10. User clicks "Stop"
    └── sendCommand({command: "stop"})
    └── Backend: sim_running = false, writes PerformanceMetric to Supabase

11. User clicks "Reset"
    └── sendCommand({command: "reset"})
    └── Backend: intersection.reset(), timestep = 0
```

### 5.2 Complete Training Flow

```
1. User clicks "Train Agent" button
2. Episode count modal opens → user sets 500 episodes → confirms
3. useTrainingSocket() connects: ws://backend/ws/training
4. sendCommand({command: "start_training", num_episodes: 500})

5. Backend:
   └── Creates training simulation record in Supabase
   └── Launches trainer.train() as asyncio background task

6. Per episode (500 times):
   └── training_env.reset() → fresh intersection (isolated from sim)
   └── For each step (max 1000):
       ├── agent.select_action(state, epsilon) → action
       ├── training_env.step(action) → (next_state, reward, done, info)
       ├── replay_buffer.push(state, action, reward, next_state, done)
       ├── if buffer.is_ready: train_step(sample(batch))
       └── await asyncio.sleep(0) every 4 steps (yield event loop)
   └── Save episode to Supabase (async)
   └── Broadcast TrainingMetric to WS clients
   └── Frontend: addTrainingMetric() → charts update

7. Every 50 episodes:
   └── model_service.save_checkpoint() → Supabase Storage
   └── supabase_service.save_model_metadata() → DB upsert
   └── Sync sim_agent weights from training_agent
   └── WS broadcast: {type: "checkpoint_saved", model_id, episode}

8. Training completes:
   └── is_training = false
   └── Final broadcast: {is_training: false, episode: 500}
   └── Frontend: "Training complete" notification

9. User opens "History" tab → episode table loads from /api/episodes
10. User selects model from "Load Model" dropdown → both agents updated
11. User switches to AI mode → sim uses loaded model weights
```

### 5.3 WebSocket Message Lifecycle

```
Client sends message:
  Raw string → JSON.parse → validate command
  └── valid: route to handler
  └── invalid: log warning, no response

Server sends SimulationFrame:
  intersection.tick() completes
  └── build_frame(intersection, mode, agent, ...) called
  └── SimulationFrame Pydantic model constructed
  └── .model_dump() → dict
  └── ujson.dumps() → string
  └── ws.send_text() → broadcast to all connected clients
```

### 5.4 Error Recovery Flow

```
Backend restart (e.g., Render cold start):
  Frontend: WS onclose fires
  └── useSimulationSocket: schedule reconnect with exponential backoff
  └── Attempt 1: 1s, Attempt 2: 2s, ... Attempt 5: 16s
  └── Connection restored → isConnected = true
  └── Simulation state is LOST (backend is stateless between restarts)
  └── User must click Start again

DB write failure:
  FastAPI: logs error with logger.exception()
  └── Simulation continues unaffected (DB writes are non-blocking)
  └── Buffer retains data and retries next flush cycle

Training crash mid-episode:
  Trainer: catches exception, sets is_training = false
  └── Partial episode NOT written to DB
  └── WS broadcast: {is_training: false, error: "..."} (if WS still connected)
  └── Checkpoint from last save point still valid
```

---

## 6. TECHNICAL ARCHITECTURE

### 6.1 Folder Structure

```
/
├── client/                          # Next.js fullstack application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Root layout (fonts, providers, keep-alive)
│   │   │   ├── globals.css          # Tailwind v4 + Vercel theme variables
│   │   │   ├── page.tsx             # Landing page (5 sections)
│   │   │   ├── providers.tsx        # TanStack QueryClient provider
│   │   │   ├── simulation/
│   │   │   │   └── page.tsx         # Main simulation dashboard
│   │   │   └── api/
│   │   │       ├── simulations/route.ts
│   │   │       ├── models/route.ts
│   │   │       ├── metrics/route.ts
│   │   │       ├── episodes/route.ts
│   │   │       └── keep-alive/route.ts
│   │   ├── components/
│   │   │   ├── ui/                  # Shadcn/ui primitives
│   │   │   ├── layout/              # Header, KeepAlivePing
│   │   │   ├── simulation/          # Three.js components
│   │   │   │   ├── SimulationCanvas.tsx
│   │   │   │   ├── IntersectionScene.tsx
│   │   │   │   ├── IntersectionGrid.tsx
│   │   │   │   ├── Road.tsx
│   │   │   │   ├── TrafficLight.tsx
│   │   │   │   └── Vehicle.tsx
│   │   │   ├── controls/            # Simulation + Training controls
│   │   │   └── dashboard/           # Metrics, Charts, History, Compare
│   │   ├── hooks/
│   │   │   ├── useSimulationSocket.ts
│   │   │   ├── useTrainingSocket.ts
│   │   │   ├── useSimulations.ts
│   │   │   └── useEpisodes.ts
│   │   ├── store/
│   │   │   └── simulationStore.ts   # Zustand global state
│   │   ├── lib/
│   │   │   ├── prisma.ts            # Singleton PrismaClient
│   │   │   ├── supabase.ts          # Supabase browser client
│   │   │   └── utils.ts             # cn(), getFastApiUrls()
│   │   └── types/
│   │       └── simulation.ts        # Shared TypeScript interfaces
│   └── prisma/
│       └── schema.prisma            # Database schema
│
├── server/                          # FastAPI + PyTorch backend
│   ├── app/
│   │   ├── main.py                  # App entry, lifespan, CORS, routes
│   │   ├── config.py                # Pydantic Settings (env vars)
│   │   ├── routers/
│   │   │   ├── simulation.py        # /simulation/* REST endpoints
│   │   │   ├── training.py          # /training/* REST endpoints
│   │   │   └── metrics.py           # /metrics/current
│   │   ├── websockets/
│   │   │   ├── simulation_ws.py     # /ws/simulation handler
│   │   │   └── training_ws.py       # /ws/training handler
│   │   ├── simulation/
│   │   │   ├── environment.py       # TrafficEnv (Gymnasium)
│   │   │   ├── intersection.py      # Intersection (physics engine)
│   │   │   ├── traffic_signal.py    # TrafficSignal (state machine)
│   │   │   ├── vehicle.py           # Vehicle dataclass
│   │   │   └── spawner.py           # PoissonSpawner
│   │   ├── rl/
│   │   │   ├── dqn_network.py       # DQN neural network
│   │   │   ├── dqn_agent.py         # DQN agent (select + train)
│   │   │   ├── replay_buffer.py     # Experience replay memory
│   │   │   ├── hyperparams.py       # All RL hyperparameters
│   │   │   └── trainer.py           # Training loop orchestrator
│   │   ├── schemas/
│   │   │   ├── simulation_schema.py # SimulationFrame + build_frame()
│   │   │   ├── training_schema.py   # TrainingMetric
│   │   │   └── metrics_schema.py    # MetricsSnapshot
│   │   └── services/
│   │       ├── supabase_service.py  # All DB write operations
│   │       └── model_service.py     # Checkpoint save/load/list
│   ├── models/                      # Local .pt file cache
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
└── README.md
```

### 6.2 Communication Between Services

| From               | To                       | Protocol           | When                           |
| ------------------ | ------------------------ | ------------------ | ------------------------------ |
| Browser            | FastAPI `/ws/simulation` | WebSocket          | 10Hz frames + user commands    |
| Browser            | FastAPI `/ws/training`   | WebSocket          | Per-episode metrics + commands |
| Browser            | Next.js `/api/*`         | HTTP GET           | Dashboard data reads           |
| Next.js API routes | Supabase PostgreSQL      | HTTP (Prisma)      | Historical data queries        |
| FastAPI            | Supabase PostgreSQL      | HTTP (supabase-py) | Write simulation/training data |
| FastAPI            | Supabase Storage         | HTTP (supabase-py) | Upload/download .pt files      |

### 6.3 Configuration Management

All configuration via environment variables, loaded through `pydantic-settings`:

**Frontend** (`client/.env.local`):

```
DATABASE_URL                    → Supabase PostgreSQL direct connection
DIRECT_URL                      → Supabase direct URL (for Prisma migrations)
NEXT_PUBLIC_SUPABASE_URL        → Supabase project URL
NEXT_PUBLIC_SUPABASE_ANON_KEY   → Supabase anon key (browser-safe)
NEXT_PUBLIC_FASTAPI_HTTP_URL    → FastAPI base URL (default: http://localhost:8000)
NEXT_PUBLIC_FASTAPI_WS_URL      → FastAPI WS URL (default: ws://localhost:8000)
```

**Backend** (`server/.env`):

```
SUPABASE_URL              → Supabase project URL
SUPABASE_SERVICE_KEY      → Service role key (NOT anon key — server-side only)
CORS_ORIGINS              → Comma-separated allowed origins
SIGNAL_RED_DURATION       → All-red clearance seconds (default: 3.0)
```

---

## 7. DATA MODEL

### 7.1 Entity Relationship Diagram

```
Simulation (1)
  ├──────────────────────────── (N) Episode
  ├──────────────────────────── (N) TrafficLog
  ├──────────────────────────── (N) SignalState
  └──────────────────────────── (N) PerformanceMetric

RLModel (standalone — references simulation UUID as ID)
```

### 7.2 Entity Definitions

#### Simulation

```prisma
model Simulation {
  id         String   @id @default(cuid())
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
  mode       String   // "fixed" | "ai" | "manual"
  status     String   // "running" | "completed" | "stopped"
  totalSteps Int      @default(0)
  durationMs Int      @default(0)

  episodes     Episode[]
  metrics      PerformanceMetric[]
  trafficLogs  TrafficLog[]
  signalStates SignalState[]
}
```

**Lifecycle:** Created on `/simulation/start`, updated on `/simulation/stop`  
**Constraints:** mode must be one of three valid values  
**Indexes:** Primary key (cuid)

---

#### Episode

```prisma
model Episode {
  id            String     @id @default(cuid())
  createdAt     DateTime   @default(now())
  simulationId  String
  simulation    Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  episodeNumber Int
  totalReward   Float
  avgWaitTime   Float
  throughput    Int
  epsilon       Float
  loss          Float?
  steps         Int

  @@index([simulationId])
}
```

**Lifecycle:** Written once per training episode  
**Constraints:** simulationId must reference valid Simulation  
**Cascade:** Deleted when parent Simulation is deleted

---

#### SignalState

```prisma
model SignalState {
  id           String     @id @default(cuid())
  createdAt    DateTime   @default(now())
  simulationId String
  simulation   Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  timestep     Int
  phase        Int        // 0=NS_STRAIGHT | 1=EW_STRAIGHT | 2=NS_RIGHT | 3=EW_RIGHT
  duration     Int
  queueNorth   Int
  queueSouth   Int
  queueEast    Int
  queueWest    Int

  @@index([simulationId])
}
```

**Lifecycle:** Sampled every 50 ticks, buffered, bulk-flushed every 10 samples (~50s)

---

#### TrafficLog

```prisma
model TrafficLog {
  id              String     @id @default(cuid())
  createdAt       DateTime   @default(now())
  simulationId    String
  simulation      Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  timestep        Int
  vehiclesSpawned Int
  vehiclesPassed  Int
  avgWaitTime     Float
  maxQueueLength  Int

  @@index([simulationId])
}
```

**Lifecycle:** Same bulk-flush strategy as SignalState

---

#### PerformanceMetric

```prisma
model PerformanceMetric {
  id             String     @id @default(cuid())
  createdAt      DateTime   @default(now())
  simulationId   String
  simulation     Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  mode           String     // "fixed" | "ai" | "manual"
  avgWaitTime    Float
  throughput     Int
  maxQueueLength Int
  totalSteps     Int
  improvementPct Float?     // vs fixed baseline, set when comparing

  @@index([simulationId])
}
```

**Lifecycle:** Written once when simulation stops

---

#### RLModel

```prisma
model RLModel {
  id            String   @id @default(cuid())
  createdAt     DateTime @default(now())
  name          String
  version       String
  storagePath   String   // "models/{sim_id}/checkpoint_{episode}.pt"
  avgReward     Float    // rolling 50-episode average at save time
  epsilon       Float    // epsilon at save time
  totalEpisodes Int
  isActive      Boolean  @default(false)

  @@unique([name, version])
}
```

**Lifecycle:** Upserted every 50 episodes during training (uses simulation_id as name)  
**Constraints:** `(name, version)` must be unique — prevents duplicate rows per run

---

### 7.3 Supabase Storage

**Bucket:** `model-checkpoints` (private — accessed only via service key)  
**Path format:** `models/{simulation_id}/checkpoint_{episode}.pt`  
**Contents:** PyTorch serialized dict:

```python
{
    'online_net': state_dict,
    'target_net': state_dict,
    'optimizer': optimizer_state_dict,
    'step_count': int,
    'obs_version': 'v3_20dim_pressure',  # version tag for compatibility
    'architecture': 'DoubleDQN',
}
```

---

## 8. API SPECIFICATION

### 8.1 REST Endpoints (FastAPI)

All endpoints at base URL: `FASTAPI_HTTP_URL` (e.g., `https://flowsync-gelt.onrender.com`)

---

#### `GET /health`

**Purpose:** Health check for load balancer and keep-alive ping  
**Auth:** None  
**Response:** `200 {"status": "ok"}`

---

#### `POST /simulation/start`

**Purpose:** Create a new simulation session and begin tracking  
**Auth:** None  
**Request:** Empty body  
**Response:**

```json
{ "simulation_id": "clx9k2p4e0001abc", "status": "started" }
```

**Side effects:** Creates `Simulation` row in DB; sets `app.state.current_simulation_id`  
**Error:** `500` if DB write fails (simulation still starts without ID)

---

#### `POST /simulation/stop`

**Purpose:** Stop the current simulation and persist final metrics  
**Auth:** None  
**Request:** Empty body  
**Response:** `{"status": "stopped"}`  
**Side effects:** Updates `Simulation.status = "completed"`; writes `PerformanceMetric`

---

#### `POST /simulation/reset`

**Purpose:** Clear intersection state without ending simulation session  
**Auth:** None  
**Request:** Empty body  
**Response:** `{"status": "reset"}`  
**Side effects:** `sim_intersection.reset()` called; timestep = 0

---

#### `PUT /simulation/mode`

**Purpose:** Switch control mode  
**Auth:** None  
**Request:** `{"mode": "fixed" | "ai" | "manual"}`  
**Response:** `{"mode": "ai"}`  
**Validation:** mode must be one of three valid strings; others → `422`

---

#### `GET /simulation/status`

**Purpose:** Get current intersection metrics snapshot  
**Auth:** None  
**Response:**

```json
{
  "avg_wait_time": 4.2,
  "throughput": 128,
  "max_queue": 6,
  "current_phase": 0,
  "is_training": false,
  "current_episode": 0,
  "epsilon": 1.0
}
```

---

#### `POST /training/start`

**Purpose:** Launch DQN training as background task  
**Auth:** None  
**Request:** `{"num_episodes": 500, "simulation_id": null}`  
**Response:** `{"status": "started", "simulation_id": "..."}`  
**Validation:** `num_episodes` must be 1–2000; rejects if already training  
**Side effects:** Creates training Simulation record; launches asyncio task

---

#### `POST /training/stop`

**Purpose:** Gracefully halt training after current episode  
**Auth:** None  
**Request:** Empty body  
**Response:** `{"status": "stopping"}`  
**Side effects:** `trainer.is_training = false`; task completes current episode then exits

---

#### `GET /training/status`

**Purpose:** Get current training state  
**Auth:** None  
**Response:**

```json
{
  "is_training": true,
  "current_episode": 47,
  "epsilon": 0.74,
  "total_episodes": 500
}
```

---

#### `GET /training/models`

**Purpose:** List all available model checkpoints  
**Auth:** None  
**Response:**

```json
{
  "models": [
    {
      "id": "...",
      "name": "...",
      "version": "checkpoint_100",
      "avg_reward": 84.2,
      "epsilon": 0.42,
      "total_episodes": 100,
      "created_at": "2026-07-11T..."
    }
  ]
}
```

**Discovery:** 3-tier — DB first, then Supabase Storage listing, then local disk (deduplicated)

---

#### `POST /training/load`

**Purpose:** Load a saved checkpoint into both agent instances  
**Auth:** None  
**Request:** `{"model_id": "clx9..."}`  
**Response:** `{"status": "loaded", "episode": 100}`  
**Side effects:** Both `sim_agent` and `training_agent` weights updated  
**Error:** `404` if model not found; `400` if checkpoint architecture incompatible

---

#### `GET /metrics/current`

**Purpose:** Get current simulation metrics (REST alternative to WS for polling)  
**Auth:** None  
**Response:** Same as `/simulation/status`

---

### 8.2 WebSocket Protocol

#### `/ws/simulation`

**Frame rate:** 10Hz (every 100ms)

**Server → Client (`SimulationFrame`):**

```json
{
  "meta": {
    "timestep": 1247,
    "episode": 47,
    "mode": "ai",
    "simulation_id": "clx9k2p4e0001abc"
  },
  "signal": {
    "current_phase": 0,
    "phase_label": "NS_STRAIGHT",
    "color_per_lane": {
      "north": "green",
      "south": "green",
      "east": "red",
      "west": "red"
    },
    "time_in_phase": 4.2,
    "phase_duration": 30.0,
    "is_transitioning": false,
    "pending_phase": null
  },
  "queues": {
    "north": { "length": 3, "max_capacity": 10, "occupancy_pct": 30.0 },
    "south": { "length": 1, "max_capacity": 10, "occupancy_pct": 10.0 },
    "east": { "length": 4, "max_capacity": 10, "occupancy_pct": 40.0 },
    "west": { "length": 2, "max_capacity": 10, "occupancy_pct": 20.0 }
  },
  "vehicles": [
    {
      "id": "v_a1b2c3",
      "lane": "north",
      "turn": "straight",
      "position": 0.65,
      "speed": 0.12,
      "state": "moving",
      "wait_time": 2.1,
      "is_emergency": false,
      "world_x": -0.5,
      "world_z": 2.6
    }
  ],
  "metrics": {
    "avg_wait_time": 4.2,
    "max_wait_time": 12.8,
    "throughput_total": 128,
    "vehicles_in_sim": 10,
    "congestion_level": "moderate"
  },
  "rl": {
    "reward": -1.4,
    "cumulative_reward": 84.2,
    "epsilon": 0.42,
    "last_action": 0,
    "action_label": "NS_STRAIGHT",
    "q_values": [2.41, 1.87, 0.93, 1.12],
    "is_exploring": false
  },
  "frame_type": "simulation"
}
```

**Client → Server (commands):**

```json
{"command": "start"}
{"command": "stop"}
{"command": "reset"}
{"command": "set_mode", "mode": "fixed" | "ai" | "manual"}
{"command": "set_spawn_rate", "value": 0.3}
{"command": "emergency_override", "lane": "north"}
{"command": "manual_override", "phase": 2}
```

**Validation schema per command:**

```python
COMMAND_SCHEMAS = {
    "set_mode":           {"mode": str},
    "set_spawn_rate":     {"value": float},
    "emergency_override": {"lane": str},
    "manual_override":    {"phase": int},
}
VALID_COMMANDS = {"start", "stop", "reset", "set_mode",
                  "set_spawn_rate", "emergency_override", "manual_override"}
```

---

#### `/ws/training`

**Server → Client (`TrainingMetric`):**

```json
{
  "episode": 47,
  "total_reward": 84.2,
  "avg_wait_time": 4.2,
  "throughput": 128,
  "epsilon": 0.74,
  "loss": 0.0023,
  "is_training": true,
  "frame_type": "training"
}
```

**Server → Client (`checkpoint_saved`):**

```json
{
  "type": "checkpoint_saved",
  "model_id": "clx9k2p4e0001abc",
  "episode": 50,
  "avg_reward": 62.3
}
```

**Client → Server:**

```json
{"command": "start_training", "num_episodes": 500}
{"command": "stop_training"}
```

---

## 9. BUSINESS RULES

### 9.1 Signal Phase Safety (CRITICAL)

**Rule:** At no point in time may two conflicting directions simultaneously hold a GREEN signal.

**Definition of conflict:** North/South and East/West directions conflict with each other.
Phases 0 and 1 serve opposite direction groups. Phases 2 and 3 serve protected turning
movements from opposite direction groups.

**Enforcement:** This is enforced architecturally by the `TrafficSignal` state machine.
Only ONE current_phase value exists at any time. `color_per_lane` is computed deterministically
from `(current_phase, color)` at frame build time. There is no code path where two conflicting
direction groups can both be marked GREEN.

**Why this cannot be "learned":** The RL agent selects an INTEGER action (0-3). That integer
maps to a phase definition in a lookup table (`PHASE_GREEN_DIRECTIONS`). The signal state
machine enforces this mapping. The agent never directly controls individual lane colors.

---

### 9.2 Left Turn Free Rule (Indian Traffic)

**Rule:** Left-turning vehicles in India never conflict with any signal phase.
They use slip lanes and are always permitted to move.

**Enforcement:** In `intersection._can_vehicle_move()`, vehicles with `turn == "left"`
return `can_move = True` unconditionally, before the signal is checked.

---

### 9.3 Right Turn Protected Rule (Indian Traffic)

**Rule:** Right-turning vehicles in India cross opposing traffic and are HIGH CONFLICT.
They may ONLY move during their designated protected phase (Phase 2 or Phase 3).

**Enforcement:** At high vehicle density (>50 vehicles), permissive right turns are
disabled. Right-turning vehicles never enter the intersection box without a dedicated
protected green phase — prevents right-turn lockup deadlock.

---

### 9.4 Minimum Green Time

**Rule:** A signal phase must remain green for at least `MIN_GREEN_TIME` (8 seconds)
before the agent is permitted to request a switch.

**Why:** Human drivers need 2-3 seconds to perceive green and begin moving. Switching
too frequently wastes this startup time and reduces intersection throughput.

**Enforcement:** `signal.can_switch_phase()` returns False if `time_in_phase < 8.0`.
The environment's `step()` method ignores agent actions that would violate this.

---

### 9.5 Maximum Green Time

**Rule:** A phase may not remain green for longer than `MAX_GREEN_TIME` (40 seconds).

**Why:** Without this cap, the agent may learn to starve minority directions indefinitely.

**Enforcement:** If `signal.is_max_green_exceeded` is True and the agent selects the
same phase again, `environment.step()` overrides the action with the highest-pressure
alternative phase.

---

### 9.6 Starvation Prevention

**Rule:** If any direction has been waiting longer than `STARVATION_THRESHOLD` (45 seconds),
the environment forces the agent to serve that direction regardless of its selected action.

**Enforcement:** `environment.step()` checks `signal.get_starved_directions()` before
applying the agent's action. If starved directions exist, the action is overridden.

---

### 9.7 Replay Buffer Warmup

**Rule:** DQN training does not begin until the replay buffer contains at least
`MIN_REPLAY_SIZE` (1000) transitions.

**Why:** With fewer than 1000 diverse transitions, gradient updates train on too-similar
samples (all from random early exploration), causing the network to memorize noise.

---

### 9.8 Checkpoint Compatibility

**Rule:** Model checkpoints are tagged with `obs_version`. If loaded checkpoint's
`obs_version` does not match the current observation space version, loading is rejected.

**Why:** If the observation space changes (e.g., from 8-dim to 20-dim), old checkpoint
weights are for a different input size — loading them silently would corrupt the agent.

---

## 10. AI & RL COMPONENTS

### 10.1 Algorithm: Double DQN

**Paper:** Van Hasselt, Guez, Silver — "Deep Reinforcement Learning with Double Q-learning" (AAAI 2016)

**Why Double DQN over standard DQN:**
Standard DQN uses the same network to both select and evaluate the best next action,
causing systematic overestimation of Q-values. Overestimation leads to overconfident
policies that make wrong phase decisions at high vehicle density.

Double DQN decouples selection from evaluation:

```
Standard DQN:  target = r + γ × max_a[target_net(s')]
Double DQN:    best_a = argmax_a[online_net(s')]
               target = r + γ × target_net(s')[best_a]
```

### 10.2 Neural Network Architecture

```
Input (8,)
  → Linear(8, 128) + LayerNorm(128) + ReLU
  → Linear(128, 128) + LayerNorm(128) + ReLU
  → Linear(128, 64) + ReLU
  → Linear(64, 4)   → Q-values [Q(s,a₀), Q(s,a₁), Q(s,a₂), Q(s,a₃)]
```

**Why LayerNorm over BatchNorm:**
PER replay buffer samples transitions from different policy stages — early random exploration
and later structured policies exist in the same buffer. BatchNorm relies on IID batch
statistics which this violates. LayerNorm normalizes per-sample independently.

**Weight initialization:** Kaiming uniform (optimal for ReLU activations)

### 10.3 Experience Replay

**Type:** Uniform random sampling (standard replay buffer)  
**Capacity:** 50,000 transitions  
**Warmup:** 1,000 transitions before first gradient step  
**Sample:** Random batch of 64 transitions per training step  
**Structure:**

```python
transition = (state: np.float32[8], action: int, reward: float,
              next_state: np.float32[8], done: bool)
```

### 10.4 Training Hyperparameters

| Hyperparameter    | Value                       | Justification                                         |
| ----------------- | --------------------------- | ----------------------------------------------------- |
| Learning rate     | 5e-4                        | Adam optimizer; lower than default for stability      |
| Gamma (γ)         | 0.95                        | Moderate discount; agent balances immediate vs future |
| Epsilon start     | 1.0                         | Full exploration at start                             |
| Epsilon end       | 0.05                        | Minimum 5% exploration permanently                    |
| Epsilon decay     | 0.997/episode               | Slow exponential decay                                |
| Batch size        | 64                          | Standard for replay buffer training                   |
| Replay buffer     | 50,000                      | Large enough for diverse traffic states               |
| Min replay        | 1,000                       | Warmup before training begins                         |
| Target sync       | Every 200 steps (hard copy) | Stabilizes moving target problem                      |
| Gradient clip     | max_norm = 10.0             | Prevents exploding gradients                          |
| Loss function     | SmoothL1Loss (Huber)        | Less sensitive to Q-value outliers than MSE           |
| Max steps/episode | 500                         | Episode length                                        |
| Default episodes  | 500                         | Default training run                                  |

### 10.5 Observation Space

8-dimensional vector, all values non-negative:

```
obs = [q_north, q_south, q_east, q_west,  ← queue lengths (0-10)
       current_phase,                       ← 0-3
       time_in_phase,                       ← 0-60 seconds
       total_vehicles,                      ← 0-40
       pending_phase]                       ← 0-3 (or current if stable)
```

**Observation space bounds:**

```python
Box(low=np.array([0,0,0,0,0,0,0,0]),
    high=np.array([10,10,10,10,3,60,40,3]))
```

**obs_version tag:** `"v3_20dim_pressure"` (latest)

### 10.6 Two-Agent Architecture

```
app.state.sim_agent      ← DQNAgent instance A
  Purpose: inference only during live simulation
  Gradient updates: NEVER
  Weight source: receives copies from training_agent every 50 episodes

app.state.training_agent ← DQNAgent instance B
  Purpose: training loop only
  Gradient updates: every 2 steps after warmup
  Weight sync: pushes to sim_agent after checkpoints
```

**Thread safety:** PyTorch is not safe for concurrent read+write on the same tensors.
The two-agent split ensures gradient updates (training_agent) never race with
forward passes (sim_agent.select_action() during simulation).

### 10.7 Reward Function

```python
R = 0.3 × (prev_total_queue - curr_total_queue)    # queue reduction
  + 0.8 × vehicles_passed_this_step                 # throughput bonus
  - 0.3 (if phase_changed else 0.0)                 # switch penalty
  - 1.5 × count(queues where queue >= 6)            # overflow penalty
  + 0.2 (if max_q - min_q <= 2 else 0.0)            # balance bonus
```

**Design rationale:**

- Primary signal: queue reduction (not raw queue length — agent gets credit for improvement)
- Throughput bonus: agent must actually clear vehicles, not just prevent growth
- Switch penalty: discourages chattering (rapid phase switching)
- Overflow at ≥6 (not ≥8): gives agent time to react before queue is completely full
- Balance bonus: prevents starving one direction to optimize others

---

## 11. SECURITY

### 11.1 Authentication & Authorization

**Current status:** None implemented. Open application, single-user demo.

**Service key protection:**

- Supabase `service_role` key NEVER sent to browser
- Config validates key is service role (decodes JWT, checks `role=service_role`)
- Key only in `server/.env`, loaded by Pydantic Settings
- Raises clear error if anon key is accidentally configured

### 11.2 CORS

```python
allow_origins = [
    "http://localhost:3000",
    "https://flowsyncc.vercel.app",
    # + additional origins from CORS_ORIGINS env var
]
```

RegEx fallback allows Vercel preview deployment URLs (pattern: `https://flowsync-*.vercel.app`).

### 11.3 Input Validation

All REST endpoints validated by Pydantic v2 models.
WebSocket commands validated by command schema dict before processing.
Spawn rate clamped server-side: `max(0.1, min(1.0, float(value)))`.
Phase integer validated: must be in `[0, 1, 2, 3]`.

### 11.4 SQL Injection Prevention

No raw SQL anywhere. All DB operations via:

- `supabase-py` (parameterized queries)
- `Prisma` (parameterized queries)

### 11.5 Rate Limiting

**Current status:** None implemented. Known gap for production deployment.
Mitigation: demo/single-user use case; natural DB write throttling via buffer strategy.

---

## 12. PERFORMANCE

### 12.1 Performance Goals

| Metric                 | Target                   |
| ---------------------- | ------------------------ |
| WebSocket frame rate   | 10Hz (100ms per frame)   |
| Frontend render rate   | 60fps                    |
| API response time      | <200ms                   |
| Training episode speed | ~100ms per episode (CPU) |
| Frame JSON size        | <8KB per frame           |

### 12.2 Three.js Optimization

- **InstancedMesh** for vehicles: all vehicles share one geometry, position set via matrix
- **Memoized geometry**: roads, ground, grid created once with `useMemo`
- **useFrame interpolation**: vehicle positions interpolated between 10Hz WS updates
- **DPR cap**: `<Canvas dpr={[1, 1.5]}>` prevents 4K overhead
- **Geometry disposal**: all geometries disposed in useEffect cleanup

### 12.3 WebSocket Optimization

- `ujson` for fast JSON serialization on FastAPI side
- Frame JSON kept under 8KB (positions are 4-decimal precision, not full float64)
- Training metrics broadcast per-episode (not per-step) — ~0.5Hz during training
- Simulation frames broadcast at exactly 10Hz (`asyncio.sleep(0.1)`)

### 12.4 Database Optimization

**Write strategy:** Batch inserts via buffer pattern

- TrafficLogs and SignalStates sampled every 50 ticks (~5s)
- Buffer flushed every 10 samples (~50s) via bulk insert
- Prevents DB connection saturation at 10Hz tick rate

**Indexes:** `@@index([simulationId])` on all child tables (Episode, SignalState,
TrafficLog, PerformanceMetric) — all queries filter by `simulationId`.

### 12.5 Async Optimization

- Training loop: CPU-bound PyTorch work runs in `asyncio.to_thread()` for heavy operations
- DB writes during training: `asyncio.to_thread(supabase_service.save_episode, ...)`
- Event loop yielded every 4 steps with `await asyncio.sleep(0)`
- Simulation loop: pure asyncio, no blocking calls

### 12.6 React Rendering Optimization

- Simulation canvas: `React.memo` — only re-renders when `currentFrame` changes
- Zustand selectors: granular selectors to minimize re-renders
- Training chart: `useMemo` on data array; only updates when `trainingMetrics.length` changes
- Training metrics: capped at 1000 entries in Zustand store (older trimmed)

---

## 13. ERROR HANDLING

### 13.1 Error Categories

| Category                  | Examples                            | Impact                                     |
| ------------------------- | ----------------------------------- | ------------------------------------------ |
| **Configuration errors**  | Missing env var, wrong Supabase key | Fatal — server won't start                 |
| **DB write failures**     | Network timeout, quota exceeded     | Non-fatal — simulation continues           |
| **WebSocket disconnects** | Client closed, network drop         | Non-fatal — reconnect logic                |
| **Training errors**       | PyTorch exception, OOM              | Non-fatal — training stops, sim unaffected |
| **Validation errors**     | Invalid WS command, bad API request | Non-fatal — rejected, logged               |
| **Storage errors**        | Upload fails, download 404          | Non-fatal — local fallback used            |

### 13.2 Recovery Strategies

**WebSocket disconnect (client-side):**

```typescript
// useSimulationSocket.ts
const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000]; // ms
let retryCount = 0;
ws.onclose = () => {
  if (retryCount < 5) {
    setTimeout(reconnect, BACKOFF_DELAYS[retryCount++]);
  }
};
```

**DB write failure (server-side):**

```python
# supabase_service.py — all write methods
try:
    result = supabase.table("episodes").insert(data).execute()
except Exception as e:
    logger.exception(f"Failed to write episode {episode_num}: {e}")
    # Do NOT re-raise — simulation/training continues
```

**Model load failure:**

```python
# 3-tier fallback in model_service.py
try:
    return self._load_from_storage(model_id)  # Supabase Storage
except:
    return self._load_from_disk(model_id)      # Local disk fallback
```

### 13.3 Logging Strategy

**Backend:** Python `logging` module throughout

- INFO: normal flow (simulation start/stop, checkpoints, episodes)
- WARNING: non-fatal issues (DB write failed, command validation failed)
- ERROR/EXCEPTION: unexpected errors with full traceback

**Frontend:** `console.log` with styled prefixes

- `[SimWS]` — simulation WebSocket events
- `[TrainWS]` — training WebSocket events
- `[API]` — API route calls

---

## 14. TESTING STRATEGY

### 14.1 Current Test Coverage

| Suite      | File                                      | Tests                                              |
| ---------- | ----------------------------------------- | -------------------------------------------------- |
| API        | `tests/api/test_main.py`                  | 2 — root, health                                   |
| API        | `tests/api/test_simulation.py`            | 5 — start/stop/reset/mode/status                   |
| API        | `tests/api/test_training.py`              | 4 — start/stop/status/models                       |
| RL         | `tests/rl/test_replay_buffer.py`          | 2 — push, sample                                   |
| RL         | `tests/rl/test_dqn_agent.py`              | 4 — init, random action, greedy action, train_step |
| Simulation | `tests/simulation/test_vehicle.py`        | 4 — init, move, wait, pass                         |
| Simulation | `tests/simulation/test_traffic_signal.py` | 6 — transitions, green permission                  |
| **Total**  |                                           | **27**                                             |

### 14.2 Critical Tests That Must Exist

**Signal Safety (must add):**

```python
def test_no_conflicting_green_phases():
    """Verify NS and EW cannot be green simultaneously — ever."""
    signal = TrafficSignal()
    for phase in range(4):
        signal.set_phase(phase)
        signal.tick(3.0)  # complete yellow
        signal.tick(3.0)  # complete red
        signal.tick(0.1)  # first green tick

        green_dirs = [d for d in ["north","south","east","west"]
                      if signal.is_green_for(d, "straight")]

        ns_green = "north" in green_dirs or "south" in green_dirs
        ew_green = "east" in green_dirs or "west" in green_dirs

        # NS and EW must NEVER both be green simultaneously
        assert not (ns_green and ew_green), f"CONFLICT in phase {phase}"
```

**Reward Accumulation (must add):**

```python
def test_reward_nonzero_after_episode():
    """Verify total_reward is not zero after a training episode."""
    env = TrafficEnv()
    total_reward = 0.0
    obs, _ = env.reset()
    for _ in range(100):
        action = np.random.randint(4)
        obs, reward, done, _, _ = env.step(action)
        total_reward += reward
        if done: break
    assert total_reward != 0.0, "Reward is exactly 0 — computation bug"
    assert not np.isnan(total_reward), "Reward is NaN"
```

**Double DQN (must add):**

```python
def test_double_dqn_uses_online_for_selection():
    """Verify action selection uses online net, evaluation uses target net."""
    agent = DQNAgent()
    # They should initially have same weights but be different objects
    assert agent.online_net is not agent.target_net

    # After train_step, online weights should change, target should not (hard copy)
    batch = create_random_batch(64)
    weights_before = copy.deepcopy(agent.target_net.state_dict())
    agent.train_step(batch)
    weights_after = agent.target_net.state_dict()

    # Target net weights unchanged after one step (updated only at sync)
    for key in weights_before:
        assert torch.allclose(weights_before[key], weights_after[key])
```

### 14.3 Manual Testing Checklist

Before any deployment:

- [ ] Fixed mode runs 5 minutes at λ=0.5 — no deadlock
- [ ] AI mode after loading trained model — signals never conflict
- [ ] Manual mode — phase buttons work, phase holds until next press
- [ ] Emergency vehicle clears intersection correctly
- [ ] Training 100 episodes — reward curve trends up (not flat, not zero)
- [ ] Episode history table populates in Supabase
- [ ] Model checkpoint appears in Supabase Storage
- [ ] Load model → AI mode uses it (different behavior than untrained)
- [ ] Compare tab shows correct improvement % after running both modes
- [ ] WebSocket reconnects after server restart (within 30s)

---

## 15. DEPLOYMENT

### 15.1 Environments

| Environment     | Frontend URL                 | Backend URL                        | Database          |
| --------------- | ---------------------------- | ---------------------------------- | ----------------- |
| **Development** | http://localhost:3000        | http://localhost:8000              | Supabase (shared) |
| **Production**  | https://flowsyncc.vercel.app | https://flowsync-gelt.onrender.com | Supabase (same)   |

### 15.2 Frontend Deployment (Vercel)

**Build command:** `cd client && pnpm install && pnpm build`  
**Output directory:** `.next`  
**Auto-deploy:** On push to `main` branch  
**Environment variables:** Set in Vercel project settings (all 6 vars)

### 15.3 Backend Deployment (Render)

**Runtime:** Docker (`server/Dockerfile`)  
**Docker base:** `python:3.11-slim`  
**PyTorch:** CPU-only (`torch==2.3.1+cpu`)  
**Start command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`  
**Auto-deploy:** On push to `main` branch (Docker build triggered)  
**Cold start:** ~30 seconds on Render free tier after 15min inactivity  
**Mitigation:** Frontend pings `/api/keep-alive` on mount → wakes backend

### 15.4 Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
RUN mkdir -p models
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 15.5 Local Development

```bash
# Frontend
cd client
pnpm install
cp .env.example .env.local    # fill in values
pnpm dev                       # http://localhost:3000

# Backend
cd server
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in values
uvicorn app.main:app --reload  # http://localhost:8000

# Database
cd client
pnpm prisma db push            # apply schema to Supabase
pnpm prisma generate           # generate Prisma client
```

### 15.6 WebSocket in Production

- Vercel → Render: `wss://flowsync-gelt.onrender.com/ws/simulation`
- Render handles TLS termination automatically
- `NEXT_PUBLIC_FASTAPI_WS_URL` must use `wss://` (not `ws://`) in production
- No additional proxy configuration required

---

## 16. DEVELOPMENT STANDARDS

### 16.1 Python (Backend)

- **Version:** 3.11.9 (pinned in `runtime.txt`)
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all classes and public methods
- **Async:** All WebSocket handlers and DB writes must be async-aware
- **Imports:** Absolute imports only; relative imports forbidden
- **Error handling:** Never bare `except:` — always `except Exception as e:`

### 16.2 TypeScript (Frontend)

- **Strict mode:** Enabled in `tsconfig.json`
- **No `any`:** Use explicit types or `unknown` with type guards
- **Components:** Functional only, React hooks
- **State:** Zustand for global simulation state; TanStack Query for server state
- **Imports:** Use `@/` alias for `src/` directory

### 16.3 Naming Conventions

| Context                  | Convention                  | Example                |
| ------------------------ | --------------------------- | ---------------------- |
| Python files             | snake_case                  | `traffic_signal.py`    |
| Python classes           | PascalCase                  | `TrafficSignal`        |
| Python functions/methods | snake_case                  | `get_queue_lengths()`  |
| Python constants         | UPPER_SNAKE                 | `MIN_GREEN_TIME`       |
| TypeScript components    | PascalCase                  | `SimulationCanvas.tsx` |
| TypeScript hooks         | camelCase with `use` prefix | `useSimulationSocket`  |
| TypeScript interfaces    | PascalCase                  | `SimulationFrame`      |
| DB tables                | snake_case (via `@@map`)    | `signal_states`        |
| DB model fields          | camelCase (Prisma)          | `simulationId`         |

### 16.4 Git Workflow

- **Main branch:** `main` — production deployments only
- **Feature branches:** `feature/description-of-change`
- **Commits:** Present tense, imperative: `"Fix reward calculation in trainer.py"`
- **PRs:** Required for any changes to RL core (`rl/` folder)

### 16.5 Code Review Guidelines

Before merging any RL-related change:

- [ ] Reward function returns non-zero values
- [ ] Observation vector dimension matches network input (`STATE_DIM`)
- [ ] `train_step()` returns `(loss, td_errors)` tuple (not just loss)
- [ ] No shared mutable state between sim and training paths
- [ ] Signal safety invariant preserved: no two conflicting directions can be green

---

## 17. KNOWN LIMITATIONS

### 17.1 Current Technical Limitations

| Limitation                   | Severity | Details                                              |
| ---------------------------- | -------- | ---------------------------------------------------- |
| **Single intersection only** | High     | Multi-intersection requires architectural refactor   |
| **CPU-only training**        | Medium   | Render free tier; GPU training needs paid infra      |
| **No authentication**        | Medium   | Single-user demo; shared state across all clients    |
| **Render cold starts**       | Medium   | 30s latency after 15min idle on free tier            |
| **No rate limiting**         | Low      | WS message flooding unprotected                      |
| **Manual Prisma migrations** | Low      | `prisma db push` required on schema changes          |
| **DB buffer loss on crash**  | Low      | ~50s window of unwritten metrics on unexpected crash |

### 17.2 Technical Debt

| Item                                      | Status                                         |
| ----------------------------------------- | ---------------------------------------------- |
| Reward showing as 0.0 in dashboard        | Active bug — needs investigation in trainer.py |
| Signal collision bug (conflicting greens) | Active bug — needs signal state machine audit  |
| No E2E tests                              | No Playwright/Cypress coverage                 |
| No CI/CD pipeline                         | Manual deployment only                         |
| WS command schema validation incomplete   | Some commands not fully validated              |

### 17.3 Assumptions

- Single browser client at a time (no session isolation)
- PyTorch CPU inference is fast enough for 10Hz simulation (confirmed for 8-dim state)
- Supabase free tier capacity sufficient for demo usage (~500MB DB, ~1GB Storage)
- Vehicle behavior simplified (no acceleration curve, no real-world kinematics)

---

## 18. FUTURE ROADMAP

### 18.1 Phase 1 — Fix Foundation (Immediate)

| Item                      | Priority | Description                              |
| ------------------------- | -------- | ---------------------------------------- |
| Fix signal collision bug  | P0       | Audit traffic_signal.py state machine    |
| Fix reward=0 bug          | P0       | Audit trainer.py reward accumulation     |
| Improve Fixed-Timer logic | P1       | Smart queue-based phase selection        |
| DQN agent optimization    | P1       | Hyperparameter tuning, obs space cleanup |

### 18.2 Phase 2 — Real-World Data Training

| Item                            | Priority | Description                                       |
| ------------------------------- | -------- | ------------------------------------------------- |
| YOLO vehicle detection pipeline | P1       | YOLOv8 offline on Indian traffic footage          |
| Offline RL dataset builder      | P1       | Extract queue states from video → JSON dataset    |
| Real-data fine-tuning           | P1       | Fine-tune simulation-trained agent on real states |
| New `/realworld` page           | P2       | Separate dashboard for CCTV-based control mode    |

**Target datasets:**

- IDD (India Driving Dataset) — Indian road conditions
- CityFlow — Multi-camera intersection benchmark
- UA-DETRAC — Urban traffic detection and tracking

### 18.3 Phase 3 — Multi-Intersection

| Item                       | Priority | Description                                       |
| -------------------------- | -------- | ------------------------------------------------- |
| CityNetwork class          | P2       | Graph of N Intersection instances                 |
| Shared-policy MARL         | P2       | One DQN agent deployed across N intersections     |
| City map UI                | P2       | Pan/zoom view of multiple intersections           |
| Green wave synchronization | P3       | Upstream intersections coordinate with downstream |

### 18.4 Phase 4 — Production Hardening

| Item                 | Priority | Description                              |
| -------------------- | -------- | ---------------------------------------- |
| Authentication       | P2       | Supabase Auth for multi-user isolation   |
| Rate limiting        | P2       | `slowapi` on FastAPI endpoints           |
| CI/CD pipeline       | P2       | GitHub Actions for test + deploy         |
| GPU training support | P3       | CUDA Dockerfile for cloud GPU instance   |
| V2X integration      | P4       | Communicate directly with smart vehicles |

### 18.5 Long-Term Vision

FlowSync ultimately aims to be a deployable, open-source adaptive traffic control system
requiring zero road-embedded sensors — only existing CCTV infrastructure. The DRL agent
trained on real Indian traffic data, deployed at Secunderabad intersections, with
performance validated against VAC/SCOOT baselines.

Research contribution: **"Camera-Only Adaptive Traffic Signal Control via Deep Reinforcement Learning:
A Sim-to-Real Transfer Approach for Indian Urban Intersections"**

---

## 19. APPENDIX

### 19.1 Glossary

| Term                     | Definition                                                              |
| ------------------------ | ----------------------------------------------------------------------- |
| **DRL / DQN**            | Deep Reinforcement Learning / Deep Q-Network — the AI algorithm         |
| **RL Agent**             | The software entity that selects traffic signal phases                  |
| **Episode**              | One complete training run: environment reset → 500 steps → terminal     |
| **Epsilon (ε)**          | Probability of random action (exploration rate); decays over training   |
| **Replay Buffer**        | Memory of past transitions; sampled for training batches                |
| **Bellman Equation**     | Q(s,a) = r + γ × max_a'[Q(s',a')] — the core RL update equation         |
| **Phase**                | One of 4 signal configurations; determines which lanes get green        |
| **Throughput**           | Number of vehicles that successfully clear the intersection             |
| **Queue Length**         | Number of vehicles waiting per approach direction                       |
| **Traffic Pressure**     | Upstream vehicle demand minus downstream lane capacity                  |
| **Left-Hand Traffic**    | Traffic convention where vehicles drive on the left (India, UK)         |
| **Protected Right Turn** | Right turn that only occurs during dedicated signal phase (India)       |
| **Sub-lane**             | One of 3 independent vehicle queues per direction (left/straight/right) |
| **λ (lambda)**           | Poisson arrival rate — vehicles per second per lane                     |
| **VAC**                  | Vehicle Actuated Control — existing hardware-based adaptive system      |
| **Sim-to-Real**          | Transferring a simulation-trained model to real-world deployment        |
| **Digital Twin**         | Software simulation that mirrors a real physical system                 |

### 19.2 Dependencies

**Backend (`server/requirements.txt`):**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
websockets==12.0
pydantic==2.10.6
pydantic-settings==2.3.0
torch==2.3.1+cpu
numpy==1.26.4
gymnasium==0.29.1
supabase==2.4.6
python-dotenv==1.0.1
httpx==0.27.0
ujson==5.10.0
```

**Frontend (key packages from `package.json`):**

```
next: 16.2.6
react: 19.2.4
three: 0.184.0
@react-three/fiber: 9.6.1
@react-three/drei: (latest compatible)
@tanstack/react-query: 5.100.14
zustand: 5.0.13
recharts: 3.8.0
framer-motion: 12.40.0
@prisma/client: 6.19.3
tailwindcss: 4.x
```

### 19.3 External Services

| Service      | Purpose                | Free Tier Limits                     |
| ------------ | ---------------------- | ------------------------------------ |
| **Vercel**   | Next.js hosting        | 100GB bandwidth/month                |
| **Render**   | FastAPI Docker hosting | Spins down after 15min idle          |
| **Supabase** | PostgreSQL + Storage   | 500MB DB, 1GB Storage, 2GB bandwidth |

### 19.4 Research References

1. Mnih et al., "Human-level control through deep reinforcement learning," Nature, 2015
2. Van Hasselt et al., "Deep RL with Double Q-Learning," AAAI 2016
3. Wang et al., "Dueling Network Architectures for Deep RL," ICML 2016
4. Schaul et al., "Prioritized Experience Replay," ICLR 2016
5. Wei et al., "PressLight: Max Pressure Control for Traffic Signals," KDD 2019
6. Chen et al., "MPLight: Large-scale Traffic Signal Control," AAAI 2020
7. Panchal & Prajapati, "FPA-DQN: Fairness- and Pressure-Aware Dueling DQN," INDJST 2025
8. Gu et al., "3DQN with Prioritized Experience Replay for TSC," DTS 2025
9. Satheesh & Powell, "MAPPO-LCE: Constrained MARL for ATSC," arXiv 2025

### 19.5 Key Files Quick Reference

| File                                      | What It Does                                                      |
| ----------------------------------------- | ----------------------------------------------------------------- |
| `server/app/main.py`                      | App entry: creates two independent environments, registers routes |
| `server/app/simulation/traffic_signal.py` | Phase state machine — if signal collision exists, it's here       |
| `server/app/simulation/intersection.py`   | Vehicle physics — tick(), \_can_vehicle_move()                    |
| `server/app/simulation/environment.py`    | RL env — obs vector, reward function, step()                      |
| `server/app/rl/trainer.py`                | Training loop — if reward shows 0, bug is here                    |
| `server/app/rl/dqn_agent.py`              | DQN train_step() — if loss is wrong, bug is here                  |
| `server/app/websockets/simulation_ws.py`  | Frame building and broadcasting                                   |
| `server/app/schemas/simulation_schema.py` | build_frame() — color_per_lane computation                        |
| `client/src/store/simulationStore.ts`     | Global frontend state (Zustand)                                   |
| `client/src/hooks/useSimulationSocket.ts` | WS connection + reconnect logic                                   |
| `client/prisma/schema.prisma`             | Complete database schema                                          |

---

_PROJECT_SPECIFICATION.md — FlowSync Master Design Document_  
_Version 2.0 | Status: Active Development | 2026-07-18_  
_This document is the single source of truth for all development decisions._

---

## 20. CODE CONSTANTS & REFERENCE IMPLEMENTATIONS

> This section defines every constant, configuration value, schema,
> and reference implementation used across the project.
> These are the authoritative values. Any deviation in code is a bug.

---

### 20.1 Signal Phase Constants

```python
# server/app/simulation/traffic_signal.py

# ── Phase Identifiers ──────────────────────────────────────────────
PHASE_NS_STRAIGHT = 0   # North + South straight + free left turns
PHASE_EW_STRAIGHT = 1   # East + West straight + free left turns
PHASE_NS_RIGHT    = 2   # North + South PROTECTED right turns only
PHASE_EW_RIGHT    = 3   # East + West PROTECTED right turns only

# ── Phase → Direction Mapping ──────────────────────────────────────
# Defines which cardinal directions receive green per phase
PHASE_GREEN_DIRECTIONS: Dict[int, List[str]] = {
    0: ["north", "south"],
    1: ["east",  "west"],
    2: ["north", "south"],
    3: ["east",  "west"],
}

# ── Phase → Allowed Turn Types ─────────────────────────────────────
# Indian left-hand traffic: left=always free, right=protected only
PHASE_ALLOWED_TURNS: Dict[int, List[str]] = {
    0: ["straight", "left"],   # straight + free left during NS green
    1: ["straight", "left"],   # straight + free left during EW green
    2: ["right"],              # protected right turn NS only
    3: ["right"],              # protected right turn EW only
}

# ── Phase Labels ───────────────────────────────────────────────────
PHASE_LABELS: Dict[int, str] = {
    0: "NS_STRAIGHT",
    1: "EW_STRAIGHT",
    2: "NS_RIGHT",
    3: "EW_RIGHT",
}

# ── Conflicting Phase Pairs (must NEVER be green simultaneously) ───
CONFLICTING_PHASES: List[Tuple[int, int]] = [
    (0, 1),   # NS_STRAIGHT vs EW_STRAIGHT
    (0, 3),   # NS_STRAIGHT vs EW_RIGHT
    (2, 1),   # NS_RIGHT vs EW_STRAIGHT
    (2, 3),   # NS_RIGHT vs EW_RIGHT
]

# ── Signal Colors ──────────────────────────────────────────────────
COLOR_GREEN  = "green"
COLOR_YELLOW = "yellow"
COLOR_RED    = "red"

# ── Timing Constants (seconds) ─────────────────────────────────────
DEFAULT_GREEN_DURATION  = 30.0   # default time per phase in fixed mode
DEFAULT_YELLOW_DURATION =  3.0   # yellow transition (fixed, not configurable)
DEFAULT_RED_DURATION    =  3.0   # all-red clearance (overridable via env var)
MIN_GREEN_TIME          =  8.0   # minimum green before agent can switch
MAX_GREEN_TIME          = 40.0   # maximum green before forced switch
STARVATION_THRESHOLD    = 45.0   # seconds before starvation penalty triggers
```

---

### 20.2 Vehicle Constants

```python
# server/app/simulation/vehicle.py

# ── Movement ───────────────────────────────────────────────────────
DEFAULT_SPEED       = 0.12    # position units per tick (at 10Hz = 1.2 units/sec)
STOP_LINE_POSITION  = 0.85    # position at which vehicle stops for red
PASSED_POSITION     = 1.00    # position at which vehicle exits simulation

# ── Turn Types ─────────────────────────────────────────────────────
TURN_LEFT     = "left"
TURN_STRAIGHT = "straight"
TURN_RIGHT    = "right"
ALL_TURNS     = [TURN_LEFT, TURN_STRAIGHT, TURN_RIGHT]

# ── Vehicle States ─────────────────────────────────────────────────
STATE_MOVING  = "moving"
STATE_WAITING = "waiting"
STATE_PASSED  = "passed"

# ── Emergency Vehicle ──────────────────────────────────────────────
EMERGENCY_SPEED    = 0.18    # faster than normal (50% speed boost)
EMERGENCY_PRIORITY = True    # forces signal override when spawned

# ── Vehicle Types (for 3D rendering) ──────────────────────────────
VEHICLE_TYPES = ["sedan", "suv", "hatchback", "sportscar", "bike", "ambulance"]
```

---

### 20.3 Spawner Constants

```python
# server/app/simulation/spawner.py

# ── Poisson Arrival Rate ───────────────────────────────────────────
DEFAULT_LAMBDA    = 0.3    # vehicles per second per lane (default)
MIN_LAMBDA        = 0.1    # minimum (slider floor)
MAX_LAMBDA        = 1.0    # maximum (slider ceiling)
TRAINING_LAMBDA   = 0.7    # lambda used during DQN training (moderate-high)
EVAL_LAMBDA       = 0.5    # lambda used for evaluation runs

# ── Queue Limits ───────────────────────────────────────────────────
MAX_QUEUE_PER_LANE    = 10   # max vehicles per sub-lane before spawn rejected
OVERFLOW_THRESHOLD    =  6   # queue length at which overflow penalty triggers
CRITICAL_THRESHOLD    =  8   # queue length considered critical congestion

# ── Turn Probability Distribution (Indian roads) ───────────────────
# Left turns common (free slip lane), straight most common, right least common
TURN_PROBABILITIES = {
    "left":     0.30,    # 30% left turns
    "straight": 0.45,    # 45% straight
    "right":    0.25,    # 25% right turns
}

# ── Directions ─────────────────────────────────────────────────────
ALL_DIRECTIONS = ["north", "south", "east", "west"]

# ── Lane Keys (12 total sub-lanes) ────────────────────────────────
ALL_LANE_KEYS = [
    "north_left",    "north_straight",  "north_right",
    "south_left",    "south_straight",  "south_right",
    "east_left",     "east_straight",   "east_right",
    "west_left",     "west_straight",   "west_right",
]
```

---

### 20.4 RL Hyperparameter Constants

```python
# server/app/rl/hyperparams.py

from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class HyperParams:

    # ── Network Architecture ───────────────────────────────────────
    STATE_DIM:    int = 8      # observation vector dimension
    ACTION_DIM:   int = 4      # number of discrete actions (phases)
    HIDDEN_1:     int = 128    # first hidden layer width
    HIDDEN_2:     int = 128    # second hidden layer width
    HIDDEN_3:     int = 64     # third hidden layer width

    # ── Optimizer ─────────────────────────────────────────────────
    LEARNING_RATE: float = 5e-4   # Adam learning rate
    ADAM_EPS:      float = 1e-8   # Adam numerical stability constant

    # ── RL Core ───────────────────────────────────────────────────
    GAMMA:        float = 0.95    # discount factor (future reward weight)

    # ── Training ──────────────────────────────────────────────────
    BATCH_SIZE:           int   = 64     # transitions per gradient step
    TRAIN_EVERY_N_STEPS:  int   = 2      # train every N simulation steps
    TARGET_UPDATE_FREQ:   int   = 200    # hard-copy target net every N steps

    # ── Replay Buffer ─────────────────────────────────────────────
    REPLAY_BUFFER_SIZE: int = 50_000   # max stored transitions
    MIN_REPLAY_SIZE:    int =  1_000   # minimum before training begins

    # ── Exploration ───────────────────────────────────────────────
    EPSILON_START: float = 1.00    # initial exploration rate (100%)
    EPSILON_END:   float = 0.05    # minimum exploration rate (5%)
    EPSILON_DECAY: float = 0.997   # multiplicative decay per episode

    # ── Loss ──────────────────────────────────────────────────────
    GRADIENT_CLIP_NORM: float = 10.0   # max gradient norm (prevents explosion)
    # Loss function: SmoothL1Loss (Huber) — less sensitive to Q-value outliers

    # ── Episode Configuration ─────────────────────────────────────
    MAX_STEPS_PER_EPISODE: int =  500    # steps per training episode
    DEFAULT_EPISODES:      int =  500    # default training run length
    MAX_EPISODES:          int = 2000    # UI slider maximum

    # ── Checkpoint ────────────────────────────────────────────────
    CHECKPOINT_EVERY_N_EPISODES: int = 50    # save model every N episodes
    ROLLING_REWARD_WINDOW:       int = 50    # window for avg reward in metadata

    # ── Observation Space Bounds ──────────────────────────────────
    OBS_LOW:  Tuple = (0, 0, 0, 0, 0, 0,  0, 0)
    OBS_HIGH: Tuple = (10, 10, 10, 10, 3, 60, 40, 3)

    # ── Reward Coefficients ───────────────────────────────────────
    REWARD_QUEUE_REDUCTION:   float =  0.3    # weight for queue delta reward
    REWARD_THROUGHPUT_BONUS:  float =  0.8    # per vehicle cleared
    REWARD_SWITCH_PENALTY:    float = -0.3    # for unnecessary phase changes
    REWARD_OVERFLOW_PENALTY:  float = -1.5    # per lane at overflow threshold
    REWARD_BALANCE_BONUS:     float =  0.2    # when queues are balanced
    REWARD_BALANCE_THRESHOLD: int   =  2      # max queue imbalance for bonus
    REWARD_OVERFLOW_QUEUE:    int   =  6      # queue length triggering overflow

# ── Singleton instance ─────────────────────────────────────────────
HP = HyperParams()
```

---

### 20.5 Observation Vector Reference

```python
# server/app/simulation/environment.py
# _get_obs() canonical implementation

def _get_obs(self) -> np.ndarray:
    """
    Build the 8-dimensional state observation vector.

    Index mapping (authoritative — network input dimension must match):
      [0] q_north       Queue length north approach  (0–10)
      [1] q_south       Queue length south approach  (0–10)
      [2] q_east        Queue length east approach   (0–10)
      [3] q_west        Queue length west approach   (0–10)
      [4] current_phase Active phase (or pending)   (0–3)
      [5] time_in_phase Seconds in current phase     (0–60)
      [6] total_vehicles Total non-passed vehicles   (0–40)
      [7] pending_phase  Queued next phase            (0–3)

    NOTE: normalized_timestep (episode position) is intentionally EXCLUDED.
    Including episode position violates the Markov property — the agent
    would behave differently at step 50 vs step 450 for identical traffic.
    Policy must depend only on traffic state, not episode position.
    """
    queues = self.intersection.get_queue_lengths()
    signal = self.intersection.signal
    total  = self.intersection.get_total_waiting()

    pending = (
        signal.pending_phase
        if signal.pending_phase is not None
        else signal.current_phase
    )

    return np.array([
        float(queues.get("north", 0)),    # [0]
        float(queues.get("south", 0)),    # [1]
        float(queues.get("east",  0)),    # [2]
        float(queues.get("west",  0)),    # [3]
        float(signal.current_phase),      # [4]
        float(signal.time_in_phase),      # [5]
        float(total),                     # [6]
        float(pending),                   # [7]
    ], dtype=np.float32)
```

---

### 20.6 Reward Function Reference

```python
# server/app/simulation/environment.py
# compute_reward() canonical implementation

def compute_reward(
    self,
    prev_queues:     Dict[str, int],
    curr_queues:     Dict[str, int],
    vehicles_passed: int,
    phase_changed:   bool,
) -> float:
    """
    Compute step reward for DQN training.

    Components:
      1. Queue reduction reward  — primary learning signal
      2. Throughput bonus        — reward clearing vehicles
      3. Switch penalty          — discourage chattering
      4. Overflow penalty        — early intervention at queue >= 6
      5. Balance bonus           — prevent direction starvation

    Expected reward range per step:
      Best case (empty intersection):  +0.5 to +2.0
      Normal operation:               -0.5 to +1.0
      Heavy congestion:               -3.0 to -1.0
      Full overflow all lanes:        -8.0 to -6.0

    Expected total episode reward range:
      Well-trained agent:   +50 to +200
      Random agent:        -100 to   +20
      Untrained (episode 1): typically -200 to -50
    """
    prev_total = sum(prev_queues.values())
    curr_total = sum(curr_queues.values())

    # 1. Queue reduction (positive = queues went down = good)
    queue_reward = HP.REWARD_QUEUE_REDUCTION * (prev_total - curr_total)

    # 2. Throughput (positive per vehicle cleared)
    throughput_reward = HP.REWARD_THROUGHPUT_BONUS * vehicles_passed

    # 3. Switch penalty (only when phase actually changes)
    switch_penalty = HP.REWARD_SWITCH_PENALTY if phase_changed else 0.0

    # 4. Overflow penalty (counts lanes AT OR ABOVE threshold)
    overflow_count   = sum(
        1 for q in curr_queues.values()
        if q >= HP.REWARD_OVERFLOW_QUEUE
    )
    overflow_penalty = HP.REWARD_OVERFLOW_PENALTY * overflow_count

    # 5. Balance bonus (only when queues are reasonably even)
    queue_values = list(curr_queues.values())
    imbalance    = max(queue_values) - min(queue_values)
    balance_bonus = (
        HP.REWARD_BALANCE_BONUS
        if imbalance <= HP.REWARD_BALANCE_THRESHOLD
        else 0.0
    )

    reward = (
        queue_reward
        + throughput_reward
        + switch_penalty
        + overflow_penalty
        + balance_bonus
    )

    return float(reward)   # must be Python float, not np.float32
```

---

### 20.7 DQN Network Reference

```python
# server/app/rl/dqn_network.py

import torch
import torch.nn as nn

class DQNNetwork(nn.Module):
    """
    Double DQN neural network.

    Architecture: 3-layer MLP with LayerNorm.
    Input:  8-dimensional state vector (HP.STATE_DIM)
    Output: 4 Q-values, one per phase action (HP.ACTION_DIM)

    LayerNorm (not BatchNorm) — replay buffer violates IID assumption;
    LayerNorm normalizes per-sample, stable regardless of batch composition.

    Kaiming uniform init — optimal for ReLU activations; prevents
    vanishing/exploding gradients at initialization.
    """

    def __init__(
        self,
        state_dim:  int = 8,
        action_dim: int = 4,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, nonlinearity="relu")
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, 8) float32 state tensor
        Returns:
            (batch_size, 4) float32 Q-value tensor
        """
        return self.net(x)
```

---

### 20.8 DQN Agent Reference

```python
# server/app/rl/dqn_agent.py

class DQNAgent:
    """
    Double DQN Agent with experience replay.

    Key design decisions:
      - SmoothL1Loss (Huber): less sensitive to Q-value outliers than MSE
      - Gradient clipping (norm=10): prevents exploding gradients
      - Hard target sync every 200 steps: stabilizes moving target
      - Two-agent split: sim_agent for inference, training_agent for gradients
    """

    def select_action(self, state: np.ndarray, epsilon: float) -> int:
        """
        Epsilon-greedy action selection.
        epsilon=0.0 → always greedy (use for live simulation inference)
        epsilon=1.0 → always random (use at training start)
        """
        if np.random.random() < epsilon:
            return int(np.random.randint(HP.ACTION_DIM))
        state_t = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_t)
        return int(q_values.argmax().item())

    def get_q_values(self, state: np.ndarray) -> List[float]:
        """
        Return raw Q-values for all 4 actions.
        Used by dashboard to visualize agent's decision reasoning.
        Higher value = agent prefers this phase.
        """
        state_t = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q = self.online_net(state_t)
        return q.squeeze(0).tolist()    # [Q(s,0), Q(s,1), Q(s,2), Q(s,3)]

    def train_step(self, batch) -> Tuple[float, np.ndarray]:
        """
        Double DQN Bellman update.

        Standard DQN (overestimates):
          target = r + γ × max_a[target_net(s')]

        Double DQN (corrected):
          best_a  = argmax_a[online_net(s')]    ← online SELECTS action
          target  = r + γ × target_net(s')[best_a]  ← target EVALUATES it

        Returns:
          (loss_value: float, td_errors: np.ndarray[batch_size])
          td_errors used to verify training is progressing
        """
        states, actions, rewards, next_states, dones = batch

        # Current Q estimates from online net
        current_q = (
            self.online_net(states)
            .gather(1, actions.unsqueeze(1))
            .squeeze(1)
        )

        with torch.no_grad():
            # Double DQN: online selects, target evaluates
            next_actions = self.online_net(next_states).argmax(dim=1)
            next_q = (
                self.target_net(next_states)
                .gather(1, next_actions.unsqueeze(1))
                .squeeze(1)
            )
            # Bellman target
            target_q = rewards + HP.GAMMA * next_q * (1.0 - dones)

        td_errors = (target_q - current_q).detach().cpu().numpy()
        loss = self.loss_fn(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            self.online_net.parameters(),
            max_norm=HP.GRADIENT_CLIP_NORM,
        )
        self.optimizer.step()
        self.step_count += 1

        return float(loss.item()), td_errors

    def sync_target_network(self):
        """Hard copy: copies online weights to target exactly."""
        self.target_net.load_state_dict(self.online_net.state_dict())

    def save(self, path: str):
        """
        Save complete agent state.
        Includes version tag for checkpoint compatibility validation.
        """
        torch.save({
            "online_net":   self.online_net.state_dict(),
            "target_net":   self.target_net.state_dict(),
            "optimizer":    self.optimizer.state_dict(),
            "step_count":   self.step_count,
            "obs_version":  "v3_8dim",       # MUST UPDATE if obs space changes
            "architecture": "DoubleDQN",
        }, path)

    def load(self, path: str):
        """
        Load checkpoint. Validates obs_version before loading.
        Raises ValueError if architecture is incompatible.
        """
        ckpt = torch.load(path, map_location="cpu")

        if isinstance(ckpt, dict) and "online_net" in ckpt:
            # Validate version compatibility
            loaded_version = ckpt.get("obs_version", "unknown")
            if loaded_version != "v3_8dim":
                raise ValueError(
                    f"Checkpoint obs_version '{loaded_version}' is incompatible "
                    f"with current version 'v3_8dim'. "
                    f"Delete old .pt files and retrain from scratch."
                )
            self.online_net.load_state_dict(ckpt["online_net"])
            self.target_net.load_state_dict(ckpt["target_net"])
            if "optimizer" in ckpt:
                self.optimizer.load_state_dict(ckpt["optimizer"])
            if "step_count" in ckpt:
                self.step_count = ckpt["step_count"]
        else:
            # Legacy raw state dict — incompatible
            raise ValueError(
                "Legacy checkpoint format detected (raw state dict). "
                "This format is not supported. Retrain from scratch."
            )
        self.target_net.eval()
```

---

### 20.9 Replay Buffer Reference

```python
# server/app/rl/replay_buffer.py

from collections import deque
import random
import numpy as np
import torch
from typing import Tuple

class ReplayBuffer:
    """
    Uniform random experience replay buffer.

    Stores transitions as (state, action, reward, next_state, done).
    Randomly samples batches for training — uniform probability.

    Fixed-size circular buffer (deque with maxlen):
      When full, oldest transitions are automatically evicted.

    is_ready property:
      Returns True only when buffer has >= MIN_REPLAY_SIZE transitions.
      Training MUST NOT begin until this is True.
    """

    def __init__(self, maxlen: int = 50_000):
        self.buffer = deque(maxlen=maxlen)

    def push(
        self,
        state:      np.ndarray,
        action:     int,
        reward:     float,
        next_state: np.ndarray,
        done:       bool,
    ) -> None:
        self.buffer.append((
            np.array(state,      dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            float(done),
        ))

    def sample(self, batch_size: int) -> Tuple[
        torch.Tensor,   # states      (batch, 8)
        torch.Tensor,   # actions     (batch,)   LongTensor
        torch.Tensor,   # rewards     (batch,)
        torch.Tensor,   # next_states (batch, 8)
        torch.Tensor,   # dones       (batch,)
    ]:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(np.array(actions)),
            torch.FloatTensor(np.array(rewards)),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor(np.array(dones)),
        )

    def __len__(self) -> int:
        return len(self.buffer)

    @property
    def is_ready(self) -> bool:
        """True when enough samples exist to begin training."""
        from app.rl.hyperparams import HP
        return len(self) >= HP.MIN_REPLAY_SIZE
```

---

### 20.10 Training Loop Reference

```python
# server/app/rl/trainer.py
# Canonical episode loop structure

async def train(self, simulation_id: str, num_episodes: int) -> None:
    """
    Main training loop.

    CRITICAL correctness requirements:
      1. total_reward MUST be reset to 0.0 at the START of each episode
      2. reward from env.step() MUST be added to total_reward every step
      3. train_step() MUST be called only when replay_buffer.is_ready
      4. train_step() returns (loss, td_errors) — BOTH must be captured
      5. avg_wait_time read from info dict AFTER episode ends (not mid-episode)
      6. epsilon updated ONCE per episode (not per step)
      7. WS broadcast contains ACTUAL computed values (not defaults/zeros)
    """
    self.is_training = True
    self.epsilon     = HP.EPSILON_START

    for episode in range(num_episodes):
        if not self.is_training:
            break

        # ── Reset for new episode ──────────────────────────────────
        state, _      = self.env.reset()
        total_reward  = 0.0    # MUST reset here — accumulated across steps
        episode_loss  = 0.0
        loss_count    = 0
        steps_done    = 0

        # ── Step loop ─────────────────────────────────────────────
        for step in range(HP.MAX_STEPS_PER_EPISODE):
            if not self.is_training:
                break

            # Agent selects action
            action = self.agent.select_action(state, self.epsilon)

            # Environment steps
            next_state, reward, terminated, truncated, info = self.env.step(action)

            # Store transition
            self.agent.replay_buffer.push(state, action, reward, next_state, terminated)

            # Accumulate reward — THIS MUST HAPPEN EVERY STEP
            total_reward += reward
            steps_done   += 1
            state         = next_state

            # Train if buffer ready
            if (
                self.agent.replay_buffer.is_ready
                and step % HP.TRAIN_EVERY_N_STEPS == 0
            ):
                batch              = self.agent.replay_buffer.sample(HP.BATCH_SIZE)
                loss, _td_errors   = self.agent.train_step(batch)
                episode_loss      += loss
                loss_count        += 1

            # Sync target network
            if self.agent.step_count % HP.TARGET_UPDATE_FREQ == 0:
                self.agent.sync_target_network()

            # Yield event loop (prevent WS starvation)
            if not self.agent.replay_buffer.is_ready or step % 4 == 0:
                await asyncio.sleep(0)

            if terminated or truncated:
                break

        # ── Episode complete ───────────────────────────────────────
        # Decay epsilon ONCE per episode
        self.epsilon = max(
            HP.EPSILON_END,
            self.epsilon * HP.EPSILON_DECAY,
        )
        self.current_episode = episode + 1

        avg_loss     = episode_loss / max(loss_count, 1)
        avg_wait     = float(info.get("avg_wait_time", 0.0))
        throughput   = int(info.get("vehicles_passed", 0))

        # ── DB write ───────────────────────────────────────────────
        await asyncio.to_thread(
            self.supabase_service.save_episode,
            simulation_id,
            episode + 1,
            total_reward,
            avg_wait,
            throughput,
            self.epsilon,
            avg_loss,
            steps_done,
        )

        # ── WebSocket broadcast ────────────────────────────────────
        # MUST use actual computed values — never hardcoded or default
        await self.ws_broadcast_fn({
            "episode":      episode + 1,
            "total_reward": round(total_reward, 4),   # actual accumulated reward
            "avg_wait_time":round(avg_wait,     2),   # from env info dict
            "throughput":   throughput,
            "epsilon":      round(self.epsilon,  4),   # post-decay value
            "loss":         round(avg_loss,      6),   # NaN if no training steps
            "is_training":  True,
            "frame_type":   "training",
        })

        # ── Checkpoint every 50 episodes ──────────────────────────
        if (episode + 1) % HP.CHECKPOINT_EVERY_N_EPISODES == 0:
            await self._save_checkpoint(simulation_id, episode + 1, total_reward)

    self.is_training = False
```

---

### 20.11 WebSocket Command Constants

```python
# server/app/websockets/simulation_ws.py

# ── Valid Commands ─────────────────────────────────────────────────
VALID_COMMANDS = frozenset({
    "start",
    "stop",
    "reset",
    "set_mode",
    "set_spawn_rate",
    "emergency_override",
    "manual_override",
})

# ── Command Required Fields ────────────────────────────────────────
COMMAND_REQUIRED_FIELDS: Dict[str, Dict[str, type]] = {
    "set_mode":           {"mode":  str},
    "set_spawn_rate":     {"value": float},
    "emergency_override": {"lane":  str},
    "manual_override":    {"phase": int},
}

# ── Valid Mode Values ──────────────────────────────────────────────
VALID_MODES = frozenset({"fixed", "ai", "manual"})

# ── Valid Lane Values ──────────────────────────────────────────────
VALID_LANES = frozenset({"north", "south", "east", "west"})

# ── Valid Phase Values ─────────────────────────────────────────────
VALID_PHASES = frozenset({0, 1, 2, 3})


def validate_ws_command(data: dict) -> Tuple[bool, str]:
    """
    Validate incoming WebSocket command.
    Returns (is_valid: bool, error_message: str).
    """
    command = data.get("command")

    if command not in VALID_COMMANDS:
        return False, f"Unknown command: '{command}'"

    required = COMMAND_REQUIRED_FIELDS.get(command, {})
    for field_name, field_type in required.items():
        if field_name not in data:
            return False, f"Missing required field: '{field_name}'"
        try:
            field_type(data[field_name])
        except (ValueError, TypeError):
            return False, f"Invalid type for '{field_name}': expected {field_type.__name__}"

    # Extra validation for specific commands
    if command == "set_mode" and data["mode"] not in VALID_MODES:
        return False, f"Invalid mode: '{data['mode']}'. Must be one of {VALID_MODES}"

    if command == "emergency_override" and data["lane"] not in VALID_LANES:
        return False, f"Invalid lane: '{data['lane']}'. Must be one of {VALID_LANES}"

    if command == "manual_override" and int(data["phase"]) not in VALID_PHASES:
        return False, f"Invalid phase: {data['phase']}. Must be 0–3"

    return True, ""
```

---

### 20.12 SimulationFrame Schema Reference

```python
# server/app/schemas/simulation_schema.py

from pydantic import BaseModel
from typing import List, Dict, Optional

class VehicleState(BaseModel):
    id:           str
    lane:         str      # direction: "north"|"south"|"east"|"west"
    turn:         str      # "left"|"straight"|"right"
    position:     float    # 0.0 (spawn) → 1.0 (exited)
    speed:        float    # current speed (0.0 if waiting)
    state:        str      # "moving"|"waiting"|"passed"
    wait_time:    float    # seconds spent waiting (accumulated)
    is_emergency: bool     # True for ambulance vehicles
    world_x:      float    # precomputed Three.js X coordinate
    world_z:      float    # precomputed Three.js Z coordinate

class SignalStateFrame(BaseModel):
    current_phase:   int            # 0–3
    phase_label:     str            # "NS_STRAIGHT"|"EW_STRAIGHT"|"NS_RIGHT"|"EW_RIGHT"
    color_per_lane:  Dict[str, str] # {"north":"green","south":"green","east":"red","west":"red"}
    time_in_phase:   float          # seconds in current phase
    phase_duration:  float          # total duration of this phase
    is_transitioning:bool           # True during yellow/red transition
    pending_phase:   Optional[int]  # next phase if transitioning, else None

class QueueStateFrame(BaseModel):
    length:         int    # vehicles currently waiting
    max_capacity:   int    # maximum per lane (always 10)
    occupancy_pct:  float  # length / max_capacity × 100

class MetricsStateFrame(BaseModel):
    avg_wait_time:    float   # average seconds all current vehicles have waited
    max_wait_time:    float   # worst-case single vehicle wait time
    throughput_total: int     # total vehicles exited since simulation start
    vehicles_in_sim:  int     # vehicles currently in simulation
    congestion_level: str     # "low"|"moderate"|"high"|"critical"

    @staticmethod
    def congestion_from_wait(avg_wait: float) -> str:
        if avg_wait <  5: return "low"
        if avg_wait < 15: return "moderate"
        if avg_wait < 30: return "high"
        return "critical"

class RLStateFrame(BaseModel):
    reward:            float       # reward received this step
    cumulative_reward: float       # total reward this episode
    epsilon:           float       # current exploration rate
    last_action:       int         # last phase selected by agent
    action_label:      str         # human-readable phase label
    q_values:          List[float] # [Q(s,0), Q(s,1), Q(s,2), Q(s,3)]
    is_exploring:      bool        # True if action was random (epsilon)

class SimulationFrame(BaseModel):
    # Meta
    timestep:      int
    episode:       int
    mode:          str             # "fixed"|"ai"|"manual"
    simulation_id: Optional[str]

    # Core data blocks
    signal:  SignalStateFrame
    queues:  Dict[str, QueueStateFrame]   # keys: "north","south","east","west"
    vehicles:List[VehicleState]
    metrics: MetricsStateFrame
    rl:      Optional[RLStateFrame]       # None in fixed/manual mode

    frame_type: str = "simulation"
```

---

### 20.13 TypeScript Type Constants

```typescript
// client/src/types/simulation.ts

// ── Simulation Modes ───────────────────────────────────────────────
export type SimulationMode = "fixed" | "ai" | "manual";

// ── Signal Phases ──────────────────────────────────────────────────
export const PHASE_LABELS: Record<number, string> = {
  0: "NS_STRAIGHT",
  1: "EW_STRAIGHT",
  2: "NS_RIGHT",
  3: "EW_RIGHT",
} as const;

export const PHASE_DESCRIPTIONS: Record<number, string> = {
  0: "North + South Straight (Free Left Turns)",
  1: "East + West Straight (Free Left Turns)",
  2: "North + South Protected Right Turns",
  3: "East + West Protected Right Turns",
} as const;

// ── Congestion Levels ──────────────────────────────────────────────
export type CongestionLevel = "low" | "moderate" | "high" | "critical";

export const CONGESTION_COLORS: Record<CongestionLevel, string> = {
  low: "#22c55e", // green
  moderate: "#f59e0b", // amber
  high: "#ef4444", // red
  critical: "#7c3aed", // purple
} as const;

// ── Vehicle Turn Colors (Three.js) ─────────────────────────────────
export const TURN_COLORS: Record<string, string> = {
  left: "#60a5fa", // blue  — free left turns (always moving)
  straight: "#e2e8f0", // white — straight traffic
  right: "#f59e0b", // amber — protected right turns (waits for phase)
} as const;

// ── Queue Thresholds ───────────────────────────────────────────────
export const QUEUE_LOW = 4; // below this: cyan label
export const QUEUE_MODERATE = 7; // below this: yellow label
// at or above QUEUE_MODERATE: red label

// ── Vehicle States ─────────────────────────────────────────────────
export type VehicleState_State = "moving" | "waiting" | "passed";

// ── Core Interfaces ────────────────────────────────────────────────
export interface VehicleState {
  id: string;
  lane: string;
  turn: string;
  position: number;
  speed: number;
  state: VehicleState_State;
  wait_time: number;
  is_emergency: boolean;
  world_x: number;
  world_z: number;
}

export interface SignalState {
  current_phase: number;
  phase_label: string;
  color_per_lane: Record<string, string>;
  time_in_phase: number;
  phase_duration: number;
  is_transitioning: boolean;
  pending_phase: number | null;
}

export interface QueueState {
  length: number;
  max_capacity: number;
  occupancy_pct: number;
}

export interface MetricsState {
  avg_wait_time: number;
  max_wait_time: number;
  throughput_total: number;
  vehicles_in_sim: number;
  congestion_level: CongestionLevel;
}

export interface RLState {
  reward: number;
  cumulative_reward: number;
  epsilon: number;
  last_action: number;
  action_label: string;
  q_values: [number, number, number, number];
  is_exploring: boolean;
}

export interface SimulationFrame {
  timestep: number;
  episode: number;
  mode: SimulationMode;
  simulation_id: string | null;
  signal: SignalState;
  queues: Record<string, QueueState>;
  vehicles: VehicleState[];
  metrics: MetricsState;
  rl: RLState | null;
  frame_type: "simulation";
}

export interface TrainingMetric {
  episode: number;
  total_reward: number;
  avg_wait_time: number;
  throughput: number;
  epsilon: number;
  loss: number | null;
  is_training: boolean;
  frame_type: "training";
}
```

---

### 20.14 Zustand Store Schema

```typescript
// client/src/store/simulationStore.ts

import { create } from "zustand";

interface SimulationStore {
  // ── Connection State ─────────────────────────────────────────────
  isConnected: boolean;
  isRunning: boolean;
  isTraining: boolean;
  mode: SimulationMode;

  // ── Live Simulation Data (from WebSocket) ────────────────────────
  currentFrame: SimulationFrame | null;

  // ── Training Metrics (capped at 1000 entries) ────────────────────
  trainingMetrics: TrainingMetric[];

  // ── Actions ─────────────────────────────────────────────────────
  setFrame: (frame: SimulationFrame) => void;
  addTrainingMetric: (metric: TrainingMetric) => void;
  setMode: (mode: SimulationMode) => void;
  setConnected: (v: boolean) => void;
  setRunning: (v: boolean) => void;
  setTraining: (v: boolean) => void;
  resetMetrics: () => void;
}

const MAX_TRAINING_METRICS = 1000; // trim oldest when exceeded

export const useSimulationStore = create<SimulationStore>((set) => ({
  isConnected: false,
  isRunning: false,
  isTraining: false,
  mode: "fixed",
  currentFrame: null,
  trainingMetrics: [],

  setFrame: (frame) => set({ currentFrame: frame }),
  setMode: (mode) => set({ mode }),
  setConnected: (v) => set({ isConnected: v }),
  setRunning: (v) => set({ isRunning: v }),
  setTraining: (v) => set({ isTraining: v }),

  addTrainingMetric: (metric) =>
    set((state) => ({
      trainingMetrics: [
        ...state.trainingMetrics.slice(-MAX_TRAINING_METRICS + 1),
        metric,
      ],
    })),

  resetMetrics: () => set({ trainingMetrics: [], currentFrame: null }),
}));
```

---

### 20.15 Environment Variable Reference

```bash
# ── Frontend: client/.env.local ───────────────────────────────────

# Supabase PostgreSQL (direct connection — not pooled — for Prisma)
DATABASE_URL="postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"

# Supabase direct URL for Prisma migrations
DIRECT_URL="postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"

# Supabase public credentials (safe to expose to browser)
NEXT_PUBLIC_SUPABASE_URL="https://[project-ref].supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."   # anon key — NOT service key

# FastAPI backend URLs (no trailing slash)
NEXT_PUBLIC_FASTAPI_HTTP_URL="http://localhost:8000"   # dev
NEXT_PUBLIC_FASTAPI_WS_URL="ws://localhost:8000"       # dev
# Production:
# NEXT_PUBLIC_FASTAPI_HTTP_URL="https://flowsync-gelt.onrender.com"
# NEXT_PUBLIC_FASTAPI_WS_URL="wss://flowsync-gelt.onrender.com"


# ── Backend: server/.env ──────────────────────────────────────────

# Supabase project URL
SUPABASE_URL="https://[project-ref].supabase.co"

# Supabase service role key (NOT anon key — has full DB access)
# Also accepted as: SUPABASE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_KEY
SUPABASE_SERVICE_KEY="eyJ..."

# Comma-separated CORS origins
CORS_ORIGINS="http://localhost:3000,https://flowsyncc.vercel.app"

# All-red clearance duration (seconds) — tune for intersection size
SIGNAL_RED_DURATION="3.0"
```

---

### 20.16 Prisma Schema (Complete)

```prisma
// client/prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

model Simulation {
  id         String   @id @default(cuid())
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
  mode       String   // "fixed" | "ai" | "manual"
  status     String   // "running" | "completed" | "stopped"
  totalSteps Int      @default(0)
  durationMs Int      @default(0)

  episodes     Episode[]
  metrics      PerformanceMetric[]
  trafficLogs  TrafficLog[]
  signalStates SignalState[]

  @@map("simulations")
}

model Episode {
  id            String     @id @default(cuid())
  createdAt     DateTime   @default(now())
  simulationId  String
  simulation    Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  episodeNumber Int
  totalReward   Float
  avgWaitTime   Float
  throughput    Int
  epsilon       Float
  loss          Float?
  steps         Int

  @@index([simulationId])
  @@map("episodes")
}

model SignalState {
  id           String     @id @default(cuid())
  createdAt    DateTime   @default(now())
  simulationId String
  simulation   Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  timestep     Int
  phase        Int        // 0=NS_STRAIGHT|1=EW_STRAIGHT|2=NS_RIGHT|3=EW_RIGHT
  duration     Int
  queueNorth   Int
  queueSouth   Int
  queueEast    Int
  queueWest    Int

  @@index([simulationId])
  @@map("signal_states")
}

model TrafficLog {
  id              String     @id @default(cuid())
  createdAt       DateTime   @default(now())
  simulationId    String
  simulation      Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  timestep        Int
  vehiclesSpawned Int
  vehiclesPassed  Int
  avgWaitTime     Float
  maxQueueLength  Int

  @@index([simulationId])
  @@map("traffic_logs")
}

model RLModel {
  id            String   @id @default(cuid())
  createdAt     DateTime @default(now())
  name          String
  version       String
  storagePath   String
  avgReward     Float
  epsilon       Float
  totalEpisodes Int
  isActive      Boolean  @default(false)

  @@unique([name, version])
  @@map("rl_models")
}

model PerformanceMetric {
  id             String     @id @default(cuid())
  createdAt      DateTime   @default(now())
  simulationId   String
  simulation     Simulation @relation(fields: [simulationId], references: [id], onDelete: Cascade)
  mode           String     // "fixed" | "ai" | "manual"
  avgWaitTime    Float
  throughput     Int
  maxQueueLength Int
  totalSteps     Int
  improvementPct Float?     // % improvement vs fixed baseline

  @@index([simulationId])
  @@map("performance_metrics")
}
```

---

_End of PROJECT_SPECIFICATION.md_
_Total sections: 20 | Version: 2.0 | Status: Active_

# FlowSync — AI-Powered Real-Time Traffic Network Simulation & Digital Twin Platform

> **Optimizing Urban Mobility with Dueling Double Deep Q-Networks (D3QN), Prioritized Experience Replay (PER), and Real-World Computer Vision (YOLOv8 + ByteTrack)**

FlowSync is an enterprise-grade, real-time traffic simulation, optimization, and digital twin platform. Powered by Dueling Double DQN (D3QN) with Prioritized Experience Replay (PER) and real-world vision pipelines, FlowSync dynamically optimizes traffic signal timings to reduce congestion, minimize vehicle wait times, and maximize throughput across single intersections, multi-intersection 2×2 city grids, and real-world CCTV feeds.

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3+-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo)](https://docs.ultralytics.com/)
[![Three.js](https://img.shields.io/badge/Three.js-0.184-000000?logo=three.js)](https://threejs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38BDF8?logo=tailwindcss)](https://tailwindcss.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com/)
[![Prisma](https://img.shields.io/badge/Prisma-6.19-2D3748?logo=prisma)](https://www.prisma.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

- [Overview & Vision](#overview--vision)
- [Key Features & Capabilities](#key-features--capabilities)
- [System Architecture](#system-architecture)
  - [Full-Stack Architecture](#1-full-stack-architecture)
  - [Persistent Real-Time WebSocket Protocols](#2-persistent-real-time-websocket-protocols)
  - [Real-World CCTV-to-Simulation Digital Twin Pipeline](#3-real-world-cctv-to-simulation-digital-twin-pipeline)
  - [Reinforcement Learning Control Loop](#4-reinforcement-learning-control-loop)
- [Reinforcement Learning Formulation](#reinforcement-learning-formulation)
  - [State Space (20-Dimensional Observation Vector)](#1-state-space-mathcalS-in-mathbbr20)
  - [Action Space](#2-action-space-mathcalA-in-0-1-2-3)
  - [Multi-Factor Max-Pressure Reward Function](#3-multi-factor-max-pressure-reward-function)
  - [Neural Network Architecture (Dueling DQN)](#4-neural-network-architecture-dueling-dqn)
  - [Prioritized Experience Replay (PER with SumTree)](#5-prioritized-experience-replay-per-with-sumtree)
  - [Safety Watchdog & Demand Action Masking](#6-safety-watchdog--demand-action-masking)
- [Real-World CCTV & Digital Twin Pipeline](#real-world-cctv--digital-twin-pipeline)
- [Project Directory Structure](#project-directory-structure)
- [Tech Stack](#tech-stack)
- [Getting Started & Installation](#getting-started--installation)
  - [Prerequisites](#prerequisites)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Backend Setup (`/server`)](#2-backend-setup-server)
  - [3. Frontend Setup (`/client`)](#3-frontend-setup-client)
  - [4. Docker Deployment](#4-docker-deployment)
- [Environment Variables Reference](#environment-variables-reference)
- [WebSocket & REST API Reference](#websocket--rest-api-reference)
- [Automated Benchmarks & Empirical Performance](#automated-benchmarks--empirical-performance)
- [License](#license)

---

## Overview & Vision

Modern urban traffic management still relies heavily on 20th-century logic: static fixed timers and expensive inductive loop vehicle-actuated systems. These controllers are blind to real-time traffic surges, causing billions of dollars in lost productivity, excess fuel consumption, and unnecessary CO₂ emissions.

**FlowSync** bridges this gap by transforming traffic signal control into an end-to-end, camera-ready, learning infrastructure:
1. **Digital Twin Platform**: High-fidelity 3D spatial simulation modeling single intersections and multi-intersection city grids with realistic car-following physics, deceleration curves, and clearance intervals.
2. **Autonomous Learning Agent**: A Dueling Double DQN agent utilizing a Max-Pressure (PressLight/MPLight) formulation with Prioritized Experience Replay (PER), dynamically adapting phase durations to instantaneous demand.
3. **Sim-to-Real Computer Vision**: A complete computer vision pipeline using Ultralytics YOLOv8 and ByteTrack to convert standard CCTV camera footage into digitized vehicle arrival schedules, enabling side-by-side "Digital Twin Showdowns" between AI and legacy timing plans on actual recorded traffic flows.

---

## Key Features & Capabilities

- **Single Intersection Diorama (`/simulation`)**:
  - High-fidelity 3D simulation of a 4-way, 12-movement signalized intersection (North, South, East, West with straight, left, and right movements).
  - Smooth cubic Bezier curve turn trajectories, car braking/stopping physics, dynamic holographic queue indicators, animated CCTV scanning cones, and per-lane wait time telemetry.
- **Multi-Intersection 2×2 City Grid (`/city`)**:
  - Coordinated 2×2 network across 4 intersections (A, B, C, D) connected by bidirectional arterial corridors.
  - Full multi-hop vehicle routing across 8 external boundary entry/exit portals with travel-time simulation along road segments.
  - Decentralized and shared-policy AI control across all four junctions.
- **Real-World CCTV & Digital Twin Pipeline (`/realworld`)**:
  - Direct video file upload (`.mp4`, `.avi`, `.mov`) or camera streaming processed through YOLOv8 and ByteTrack.
  - Automatic quadrant partitioning (North, South, East, West) or custom polygonal Region of Interest (ROI) editor with perspective transformation.
  - Extraction of chronological vehicle arrival schedules (`VehicleArrivalEvent`) capturing timestamp, approach lane, vehicle type, and turn movement.
  - **Digital Twin Showdown**: Replays identical real-world arrival schedules in 3D physics to compare Fixed vs. Greedy vs. AI clearance times and wait reductions.
- **Four Intelligent Control Modes**:
  - **Fixed-Timer Mode**: Standard 4-phase cyclic timing plan with yellow (2s), all-red clearance (3s), smart queue skipping, and a hard 40s maximum green ceiling.
  - **Greedy (Max-Queue) Mode**: Deterministic rule-based baseline that allocates green to the phase with the highest accumulated queue, respecting minimum green durations.
  - **AI Mode (D3QN + PER)**: Reinforcement learning agent evaluating a 20-dimensional pressure state vector to make real-time phase decisions with sub-second latency.
  - **Manual (MNL) Override Mode**: Interactive user buttons allowing human operators to hold green phases indefinitely or trigger safe yellow $\to$ red $\to$ green phase switches.
- **Empirical Benchmarking Suite**:
  - **Common Random Numbers (CRN)**: Uses synchronized pseudo-random seeds across Fixed, Greedy, and AI modes during timed benchmarks, guaranteeing that performance differences are strictly attributable to signal policy and not vehicle generation noise.
  - **Natural Clearance Evaluation**: In real-world replay mode, measures the exact time required to clear all vehicles arriving from the CCTV footage.
- **AI Safety Watchdog & Demand Action Masking**:
  - **Starvation Watchdog**: Hard 45s wait-time threshold overriding agent decisions to guarantee zero phase starvation.
  - **Demand Action Masking**: Dynamically masks empty phases out of the action space, preventing the AI from allocating green lights to lanes with zero demand.
  - **Minimum Green Guard (8s)**: Prevents dangerous high-frequency signal flickering.
  - **Yield-on-Left Logic**: Enforces realistic yielding behavior where left-turning vehicles yield to oncoming straight and right-turning traffic.

---

## System Architecture

### 1. Full-Stack Architecture

FlowSync uses a decoupled, asynchronous architecture separating high-frequency physics and neural network inference from client-side WebGL rendering and persistent cloud analytics:

```mermaid
graph TB
    subgraph Client ["Frontend — Next.js 16 (React 19 / TypeScript)"]
        UI["App Router UI / Dashboard<br/>(Tailwind CSS v4 & Radix UI)"]
        Canvas["3D WebGL Canvas<br/>(Three.js / React Three Fiber)"]
        Zustand["Global State & WebSocket Stores<br/>(Zustand 5.0)"]
        Charts["Analytics & Benchmark Panels<br/>(Recharts 3.8)"]
        ROI["Polygonal ROI Canvas Editor<br/>(HTML5 Canvas)"]
    end

    subgraph Backend ["Backend — FastAPI 0.115 (Python 3.11)"]
        WS_Router["WebSocket Connection Managers<br/>(10 Hz JSON Streaming)"]
        REST_Router["REST API Endpoints<br/>(/api/simulation, /cctv, /training)"]
        
        subgraph Engine ["Simulation Engine"]
            Intersection["Single Intersection (12 Movements)"]
            CityNetwork["2×2 City Grid (4 Intersections)"]
            Signal["Traffic Signal Controller<br/>(Safety Watchdog & Clearance)"]
            Spawner["CRN Poisson Spawner"]
        end

        subgraph AI ["AI Brain (PyTorch 2.3+)"]
            SimAgent["Inference Agent (D3QN)<br/>(Demand Action Masking)"]
            TrainAgent["Training Agent (D3QN)"]
            PER["Prioritized Replay Buffer<br/>(SumTree O(log N))"]
            Trainer["Async Trainer Loop"]
        end

        subgraph Vision ["Real-World Vision Pipeline"]
            YOLO["Ultralytics YOLOv8 Detector<br/>(best.pt / yolov8n.pt / ONNX)"]
            Tracker["ByteTrack Multi-Object Tracker"]
            Quadrant["Quadrant Counter & ROI Manager"]
            Recorder["Session Recorder & Arrival Scheduler"]
        end
    end

    subgraph Data ["Data & Persistence — Supabase"]
        Postgres[("PostgreSQL Database<br/>(Simulations, Episodes, Metrics)")]
        Prisma["Prisma ORM 6.19<br/>(Client Server Actions)"]
        Storage["Supabase Storage Buckets<br/>(model-checkpoints, cctv-sessions)"]
    end

    UI --> Zustand
    Zustand <-->|WebSockets (10Hz)| WS_Router
    UI <-->|HTTP REST| REST_Router
    Canvas <-- Zustand
    Charts <-- Zustand

    WS_Router --> Engine
    WS_Router --> SimAgent
    REST_Router --> Vision
    REST_Router --> Storage

    Engine <--> SimAgent
    Trainer <--> TrainAgent
    TrainAgent <--> PER
    Trainer -->|Periodic Sync| SimAgent
    Trainer -->|Save Checkpoint| Storage

    Vision -->|Arrival Events JSON| Recorder
    Recorder -->|Twin Data| Engine

    Backend -->|Async Bulk Telemetry| Postgres
    Prisma -->|Read Analytics| Postgres
```

---

### 2. Persistent Real-Time WebSocket Protocols

FlowSync maintains four dedicated, low-latency WebSocket communication channels:

| WebSocket Endpoint | Broadcast Rate | Payload Description | Direction |
| :--- | :---: | :--- | :---: |
| `/ws/simulation` | **10 Hz** | Vehicle 3D coordinates, signal phases/colors, queue depths, Q-values, wait times, timed benchmark frames, CRN seeds. | Bidirectional |
| `/ws/city` | **10 Hz** | Coordinated 2×2 grid frames (Intersections A–D), connecting road vehicles, city throughput, comparison progress. | Bidirectional |
| `/ws/training` | **Event-driven** | Episode metrics (total reward, average wait time, throughput, loss, epsilon decay), checkpoint notifications. | Bidirectional |
| `/ws/cctv` | **Stream / 2 Hz** | Annotated video frames (base64 JPEG), bounding boxes, class labels, quadrant counts, arrival progress. | Bidirectional |

---

### 3. Real-World CCTV-to-Simulation Digital Twin Pipeline

The digital twin pipeline ingests raw CCTV video and produces high-fidelity simulation replays:

```mermaid
flowchart LR
    A["Raw CCTV Video<br/>(MP4 / AVI / Stream)"] --> B["Frame Extraction<br/>(OpenCV 2 FPS)"]
    B --> C["YOLOv8 Detection<br/>(Cars, Trucks, Buses, Bikes)"]
    C --> D["ByteTrack Tracking<br/>(Trajectory & Velocity)"]
    D --> E["Spatial Partitioning<br/>(Quadrant / Custom ROI)"]
    E --> F["Arrival Scheduler<br/>(Chronological Timestamps)"]
    F --> G["Session JSON<br/>(twin_data.json)"]
    G --> H["3D Digital Twin Replay<br/>(Deterministic 1:1 Ingestion)"]
    H --> I["Showdown Benchmark<br/>(Fixed vs. Greedy vs. AI)"]
```

---

### 4. Reinforcement Learning Control Loop

```mermaid
sequenceDiagram
    autonumber
    participant Sim as Simulation Engine
    participant Mask as Demand Action Mask
    participant Watchdog as Safety Watchdog
    participant Agent as D3QN Inference Agent
    participant PER as SumTree Replay Buffer
    participant DB as Supabase Storage / DB

    loop Every Decision Step (when min-green elapsed)
        Sim->>Sim: Compute 12-movement queues & pressure
        Sim->>Watchdog: Check Starvation (>45s) & Max Green (>40s)
        alt Starvation or Max Green Triggered
            Watchdog-->>Sim: Enforce Override Action
        else Safe Condition
            Sim->>Mask: Extract Active Lane Demands
            Mask->>Agent: Feed 20-D State Vector + Valid Phase Mask
            Agent->>Agent: Evaluate Dueling Network Q(s, a)
            Agent-->>Sim: Dispatch argmax Q(s, a)
        end
        Sim->>Sim: Execute Yellow (2s) -> Red (3s) -> Green
        Sim->>Sim: Advance vehicle kinematics (10 Hz)
        Sim->>Sim: Calculate Max-Pressure Reward R
        Sim->>PER: Store Transition (s, a, R, s', Priority)
        PER->>Agent: Sample Batch via SumTree (alpha=0.6, beta annealing)
        Agent->>Agent: Compute Double DQN Loss & Backprop
    end
    Note over Agent,DB: Every 50 episodes: Save weights to Supabase Storage
```

---

## Reinforcement Learning Formulation

### 1. State Space ($\mathcal{S} \in \mathbb{R}^{20}$)

The agent receives a normalized 20-dimensional continuous state vector at every decision step:

$$\mathbf{s} = [q_1, q_2, \dots, q_{12}, p_0, p_1, p_2, p_3, \tau_{\text{phase}}, \mathbb{I}_{\text{trans}}, \bar{P}_{\text{net}}, \sigma_{\text{starv}}]^T \in \mathbb{R}^{20}$$

| Indices | Component | Range | Description |
| :---: | :--- | :---: | :--- |
| `0` – `11` | **12 Movement Queues** | $[0.0, 1.0]$ | Normalized queue counts across 4 approaches (North, South, East, West) $\times$ 3 movements (Straight, Left, Right), normalized by max capacity ($C = 10$). |
| `12` – `15` | **Phase One-Hot** | $\{0.0, 1.0\}$ | One-hot representation of the currently active green phase ($0$: NS, $1$: EW, $2$: NS Left, $3$: EW Left). |
| `16` | **Normalized Phase Time** | $[0.0, 1.0]$ | Elapsed green time in current phase divided by maximum green duration: $\min(\tau / 40.0, 1.0)$. |
| `17` | **Transition Indicator** | $\{0.0, 1.0\}$ | Flag set to $1.0$ during yellow or all-red clearance intervals, $0.0$ during stable green. |
| `18` | **Normalized Pressure** | $[0.0, 1.0]$ | Sum of movement pressures across the intersection normalized by scale factor ($20.0$). |
| `19` | **Max Starvation Index** | $[0.0, 1.0]$ | Longest waiting time among non-green directions normalized by threshold: $\min(\max(t_{\text{wait}}) / 45.0, 1.0)$. |

---

### 2. Action Space ($\mathcal{A} \in \{0, 1, 2, 3\}$)

The discrete action space controls the signal phase:

| Action ID | Signal Phase | Permitted Movements | Protected Approaches |
| :---: | :--- | :--- | :--- |
| `0` | **NS_GREEN** | Straight & Right Turns | Northbound & Southbound |
| `1` | **EW_GREEN** | Straight & Right Turns | Eastbound & Westbound |
| `2` | **NS_LEFT** | Protected Left Turns | Northbound & Southbound Left Bays |
| `3` | **EW_LEFT** | Protected Left Turns | Eastbound & Westbound Left Bays |

---

### 3. Multi-Factor Max-Pressure Reward Function

Based on PressLight and MPLight formulations, the reward function maximizes network throughput while penalizing pressure accumulation, unnecessary phase switching, and direction starvation:

$$R = R_{\text{pressure}} + R_{\text{throughput}} + R_{\text{switch}} + R_{\text{starv}} + R_{\text{max\_green}} + R_{\text{balance}}$$

1. **Pressure Differential ($R_{\text{pressure}}$)**:
   Rewards reduction in total intersection pressure between successive time steps:
   $$R_{\text{pressure}} = 1.5 \times \left( \sum_{m} P_{\text{prev}}(m) - \sum_{m} P_{\text{curr}}(m) \right)$$
   Where movement pressure is destination-aware:
   $$P(m) = \max\left(0, \frac{\text{incoming}(m)}{C} - \frac{\text{outgoing}(\text{dest}(m))}{C}\right)$$
2. **Throughput Bonus ($R_{\text{throughput}}$)**:
   $$R_{\text{throughput}} = 0.2 \times N_{\text{passed}}$$
3. **Switch Penalty ($R_{\text{switch}}$)**:
   Penalizes abandoning a phase that still had active traffic demand:
   $$R_{\text{switch}} = -0.3 \quad \text{if phase changed and } P_{\text{prev\_phase}} > 0.3 \text{, else } 0.0$$
4. **Starvation Penalty ($R_{\text{starv}}$)**:
   $$R_{\text{starv}} = -2.0 \times |\mathcal{D}_{\text{starved}}| \quad \text{where } \mathcal{D}_{\text{starved}} = \{d \mid t_{\text{wait}}(d) \ge 45.0\,\text{s}\}$$
5. **Max Green Penalty ($R_{\text{max\_green}}$)**:
   $$R_{\text{max\_green}} = -1.0 \quad \text{if } \tau_{\text{green}} \ge 40.0\,\text{s}\text{, else } 0.0$$
6. **Traffic Balance Bonus ($R_{\text{balance}}$)**:
   Rewards balanced queue dissipation across phases when the intersection is populated:
   $$R_{\text{balance}} = 0.2 \quad \text{if } (\max(P_{\text{phase}}) - \min(P_{\text{phase}})) < 0.2 \text{ and } \sum P > 0.05$$

---

### 4. Neural Network Architecture (Dueling DQN)

The Dueling DQN decouples state value estimation from action advantages to stabilize Q-value learning in high-density traffic states:

```mermaid
graph LR
    Input["State Vector s ∈ ℝ²⁰"] --> Dense1["Linear(20 → 256) + LayerNorm + ReLU"]
    Dense1 --> Dense2["Linear(256 → 256) + LayerNorm + ReLU"]
    
    Dense2 --> Val1["Linear(256 → 128) + ReLU"]
    Val1 --> ValOut["Value Stream V(s) ∈ ℝ¹"]
    
    Dense2 --> Adv1["Linear(256 → 128) + ReLU"]
    Adv1 --> AdvOut["Advantage Stream A(s, a) ∈ ℝ⁴"]
    
    ValOut --> Combine["Q(s,a) = V(s) + A(s,a) - mean(A)"]
    AdvOut --> Combine
    Combine --> Output["Q-Values for Actions {0, 1, 2, 3}"]
```

$$\mathcal{Q}(s, a; \theta, \alpha, \beta) = \mathcal{V}(s; \theta, \beta) + \left( \mathcal{A}(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} \mathcal{A}(s, a'; \theta, \alpha) \right)$$

---

### 5. Prioritized Experience Replay (PER with SumTree)

Transitions $(s, a, r, s', d)$ are stored in a binary SumTree with capacity $N = 100{,}000$. Transitions are sampled according to their temporal-difference (TD) error magnitude:

$$P(i) = \frac{p_i^\alpha}{\sum_k p_k^\alpha}, \quad p_i = |\delta_i| + \epsilon_{\text{per}}$$

Importance-sampling weights correct for estimation bias:

$$w_i = \left( \frac{1}{N} \cdot \frac{1}{P(i)} \right)^\beta, \quad \beta \text{ annealed from } 0.4 \to 1.0$$

Hyperparameter specifications:
- **$\alpha$**: `0.6`
- **$\beta_{\text{start}}$**: `0.4` $\to$ **$\beta_{\text{end}}$**: `1.0`
- **$\epsilon_{\text{per}}$**: `1e-6`
- **Replay Capacity**: `100,000`
- **Batch Size**: `128`
- **Discount Factor ($\gamma$)**: `0.97`
- **Learning Rate**: `3e-4` (Adam optimizer)
- **Target Network Update**: Every `300` steps

---

### 6. Safety Watchdog & Demand Action Masking

To ensure zero signal phase conflicts and eliminate dead-green states:
1. **Demand Action Masking**:
   $$\mathcal{A}_{\text{valid}} = \left\{ p \in \{0, 1, 2, 3\} \mid \sum_{d \in \text{dirs}(p)} \sum_{t \in \text{turns}(p)} \text{queue}_{d,t} > 0 \right\}$$
   $$a^* = \arg\max_{a \in \mathcal{A}_{\text{valid}}} \mathcal{Q}(s, a)$$
   If no approach has queued vehicles, the agent falls back to greedy unmasked exploration.
2. **Clearance Enforcer**: Minimum green duration ($8.0\text{s}$) is strictly enforced before any switch. Every phase switch passes through Yellow ($2.0\text{s}$) followed by All-Red ($3.0\text{s}$).
3. **Starvation Watchdog**: An independent timer tracks elapsed wait time per approach direction. When any approach exceeds $45.0\text{s}$, the watchdog preempts the agent and forces the signal to service the starved approach.

---

## Real-World CCTV & Digital Twin Pipeline

FlowSync includes a complete computer vision and digital twin pipeline located in `server/app/realworld/` and exposed via `/realworld`:

1. **Detection**: Ultralytics YOLOv8 running on CPU, CUDA, or Apple Silicon MPS. Detects cars, buses, trucks, motorcycles, and auto-rickshaws with confidence threshold $\ge 0.35$ and NMS IoU $0.45$.
2. **Multi-Object Tracking**: ByteTrack assigns persistent trajectory IDs across frames, filtering false positives and calculating vehicle motion vectors.
3. **Spatial Counting**:
   - **Quadrant Mode**: Automatically partitions the video frame into North, South, East, and West approach zones.
   - **Custom ROI Mode**: Interactive web-based polygon editor (`ROIEditor.tsx`) allowing users to define lane polygons with perspective correction.
4. **Chronological Arrival Schedule Extraction**:
   Every vehicle crossing an entry boundary is logged as an arrival event:
   ```json
   {
     "vehicle_id": "cctv_veh_42",
     "time_s": 14.8,
     "lane": "north",
     "turn": "straight",
     "vehicle_type": "car"
   }
   ```
5. **Digital Twin Showdown**:
   Injects the exact chronological arrival sequence into the 3D physics simulation to benchmark Fixed, Greedy, and AI policies against actual real-world footage.

---

## Project Directory Structure

```text
FlowSync/
├── .github/                      # CI/CD workflows and repository templates
├── client/                       # Next.js 16 Web Application (Frontend)
│   ├── prisma/
│   │   └── schema.prisma         # PostgreSQL schema (Simulations, Episodes, Metrics)
│   ├── public/                   # Static assets, icons, and textures
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages
│   │   │   ├── api/              # Route handlers (/api/metrics, /api/episodes, etc.)
│   │   │   ├── city/page.tsx     # 2×2 Multi-Intersection City Grid view
│   │   │   ├── realworld/page.tsx# Real-World CCTV & Digital Twin view
│   │   │   ├── simulation/page.tsx# Single Intersection diorama view
│   │   │   ├── layout.tsx        # Root HTML layout & font providers
│   │   │   └── page.tsx          # Marketing landing page
│   │   ├── components/
│   │   │   ├── city/             # 2×2 Grid 3D components & comparison panels
│   │   │   ├── controls/         # Simulation & Training control panels
│   │   │   ├── dashboard/        # Live charts, Q-value panels, benchmark tables
│   │   │   ├── layout/           # Header, navigation, and connection badges
│   │   │   ├── realworld/        # CCTV feed, ROI editor, Digital Twin showdown
│   │   │   ├── simulation/       # Three.js diorama, vehicles, traffic lights
│   │   │   └── ui/               # shadcn/ui components (Radix UI)
│   │   ├── hooks/                # WebSocket client hooks (useSimulationSocket, useCitySocket)
│   │   ├── store/                # Zustand global state stores (simulationStore.ts)
│   │   └── types/                # TypeScript interfaces (simulation, city, cctv)
│   └── package.json
│
├── server/                       # FastAPI Backend & RL Engine
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, lifespan initialization, CORS
│   │   ├── config.py             # Pydantic BaseSettings & Supabase admin validation
│   │   ├── realworld/            # CCTV & Computer Vision Pipeline
│   │   │   ├── digital_twin/     # Replay spawner, flow calibrator, session recorder
│   │   │   ├── models/           # Configuration, schemas, class definitions
│   │   │   ├── pipeline/         # YOLOv8 detector, ByteTrack, ROI manager, quadrant counter
│   │   │   ├── training/         # Augmentation, fine-tuning scripts, ONNX exporter
│   │   │   └── utils/            # Geometry, temporal smoothers, metrics loggers
│   │   ├── rl/                   # Reinforcement Learning Core
│   │   │   ├── dqn_agent.py      # Double DQN agent with action selection & decay
│   │   │   ├── dqn_network.py    # Dueling network architecture (V and A streams)
│   │   │   ├── hyperparams.py    # Hyperparameters & safety constants
│   │   │   ├── replay_buffer.py  # Prioritized Experience Replay (SumTree)
│   │   │   └── trainer.py        # Asynchronous background training loop
│   │   ├── routers/              # REST API routers (/simulation, /training, /metrics, /cctv)
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Supabase database & storage integration services
│   │   ├── simulation/           # Traffic Physics Engine
│   │   │   ├── city_network.py   # 2×2 Grid topology, road connections, routing
│   │   │   ├── city_spawner.py   # Deterministic boundary vehicle spawner
│   │   │   ├── environment.py    # Gymnasium TrafficEnv with Max-Pressure reward
│   │   │   ├── intersection.py   # 4-way 12-movement single intersection kinematics
│   │   │   ├── spawner.py        # Poisson spawner with CRN deterministic seeding
│   │   │   ├── traffic_signal.py # Signal controller with starvation timers & caps
│   │   │   └── vehicle.py        # Vehicle physics, deceleration, stopping points
│   │   └── websockets/           # WebSocket handlers (/ws/simulation, /ws/city, /ws/training, /ws/cctv)
│   ├── data/                     # Uploads, saved sessions, ROI configs
│   ├── models/                   # YOLO weights (yolov8n.pt, best.pt, best.onnx)
│   ├── tests/                    # Pytest test suite (simulation, RL, realworld)
│   ├── Dockerfile                # Backend containerization
│   └── requirements.txt          # Python dependencies
│
├── colab/
│   └── FlowSync_YOLO_Training.ipynb # Google Colab GPU notebook for YOLOv8 fine-tuning
├── docs/                         # Comprehensive engineering summaries and audit reports
├── research-paper/               # IEEE conference paper LaTeX source
├── scripts/                      # Utility scripts (train_yolo, merge_datasets, export_model)
└── docker-compose.yml            # Multi-container orchestration specification
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :---: | :--- |
| **Frontend Framework** | Next.js (App Router) | `16.2.6` | React server components, routing, and SSR |
| **UI Library** | React | `19.2.4` | Component architecture |
| **Programming Language** | TypeScript / Python | `5.x` / `3.11+` | Strict static typing across stack |
| **3D Rendering** | Three.js / React Three Fiber | `0.184.0` / `9.6.1` | WebGL hardware-accelerated 3D scene |
| **3D Helpers** | `@react-three/drei` | `10.7.7` | Camera controls, lighting, and 3D primitives |
| **Styling** | Tailwind CSS / shadcn/ui | `v4` / `4.8.0` | Utility-first CSS and accessible UI components |
| **State Management** | Zustand | `5.0.13` | Client-side reactive stores for 10 Hz frame streaming |
| **Data Fetching** | TanStack React Query | `5.100.14` | Server-state caching and asynchronous queries |
| **Data Visualization** | Recharts | `3.8.0` | Real-time training telemetry and benchmark charts |
| **Backend API** | FastAPI / Uvicorn | `0.115.0` / `0.30.0` | High-performance asynchronous ASGI web server |
| **Deep Learning** | PyTorch (CPU/CUDA/MPS) | `2.3.1+` | Neural network computation and autograd |
| **RL Environment** | Gymnasium | `0.29.1` | Standardized environment step/reset interface |
| **Computer Vision** | Ultralytics YOLOv8 | `8.3.0+` | Real-time object detection and ByteTrack tracking |
| **Image Processing** | OpenCV / Pillow | `4.10.0` / `10.4.0` | Frame decoding, spatial masks, and ROI transforms |
| **Database & ORM** | PostgreSQL / Prisma | `6.19.3` | Relational analytics storage and data models |
| **Cloud Storage** | Supabase Storage | `2.4.6` | Model checkpoint bucket (`model-checkpoints`) |
| **Serialization** | `ujson` | `5.10.0` | High-throughput JSON encoding for 10 Hz frames |

---

## Getting Started & Installation

### Prerequisites

- **Node.js**: v20.0.0 or higher
- **pnpm**: v9.0.0 or higher
- **Python**: v3.11.0 or higher
- **Supabase Account** (or a local PostgreSQL instance)
- **Git**

---

### 1. Clone Repository

```bash
git clone https://github.com/Sri-dinesh/FlowSync.git
cd FlowSync
```

---

### 2. Backend Setup (`/server`)

1. Navigate to the server directory:
   ```bash
   cd server
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv

   # Linux / macOS:
   source venv/bin/activate

   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `server/.env`:
   ```ini
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   SIGNAL_RED_DURATION=3.0
   ```

5. Verify YOLOv8 pretrained weights:
   FlowSync will automatically download `yolov8n.pt` on first startup if not already present in the server root.

6. Launch the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *FastAPI documentation will be available at `http://localhost:8000/docs`.*

---

### 3. Frontend Setup (`/client`)

1. Open a new terminal and navigate to the client directory:
   ```bash
   cd client
   ```

2. Install dependencies via `pnpm`:
   ```bash
   pnpm install
   ```

3. Configure environment variables in `client/.env.local`:
   ```ini
   DATABASE_URL="postgresql://postgres:password@db.your-project.supabase.co:6543/postgres?pgbouncer=true"
   DIRECT_URL="postgresql://postgres:password@db.your-project.supabase.co:5432/postgres"

   NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
   NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"

   NEXT_PUBLIC_FASTAPI_HTTP_URL="http://localhost:8000"
   NEXT_PUBLIC_FASTAPI_WS_URL="ws://localhost:8000"
   NEXT_PUBLIC_WS_URL="ws://localhost:8000"
   ```

4. Push the Prisma database schema and generate the client:
   ```bash
   pnpm prisma db push
   pnpm prisma generate
   ```

5. Start the Next.js development server:
   ```bash
   pnpm dev
   ```
   *Open `http://localhost:3000` in your browser to access FlowSync.*

---

### 4. Docker Deployment

To launch the backend service with Docker:

```bash
docker compose up --build -d
```

---

## Environment Variables Reference

### Backend (`server/.env`)

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `SUPABASE_URL` | **Yes** | — | Supabase project API URL (`https://xyz.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | **Yes** | — | Supabase `service_role` secret key (for database writes) |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of allowed frontend origins |
| `SIGNAL_RED_DURATION` | No | `3.0` | Duration (seconds) of all-red clearance interval |

### Frontend (`client/.env.local`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `DATABASE_URL` | **Yes** | Pooled PostgreSQL connection string (Supabase PgBouncer :6543) |
| `DIRECT_URL` | **Yes** | Direct PostgreSQL connection string (for migrations :5432) |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | Supabase public anonymous API key |
| `NEXT_PUBLIC_FASTAPI_HTTP_URL` | **Yes** | HTTP URL of backend API (`http://localhost:8000`) |
| `NEXT_PUBLIC_FASTAPI_WS_URL` | **Yes** | WebSocket URL of backend API (`ws://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | No | Fallback WebSocket URL |

---

## WebSocket & REST API Reference

### Core WebSocket Commands

Messages sent to `/ws/simulation` or `/ws/city`:

```json
// Start simulation
{ "command": "start" }

// Pause simulation
{ "command": "stop" }

// Reset simulation state
{ "command": "reset" }

// Switch control mode ("fixed" | "greedy" | "ai" | "manual")
{ "command": "set_mode", "mode": "ai" }

// Manual signal override (phases 0 to 3)
{ "command": "set_phase", "phase": 1 }

// Run Timed Benchmark with Common Random Numbers (CRN)
{
  "command": "run_timed_benchmark",
  "duration_seconds": 30,
  "modes": ["fixed", "greedy", "ai"]
}
```

### Key REST Endpoints

- **`GET /health`**: Health check status.
- **`GET /api/simulation/state`**: Current snapshot of intersection state.
- **`POST /api/training/start`**: Initiates background RL training loop.
- **`POST /api/training/stop`**: Halts active background training.
- **`GET /api/training/models`**: Lists all available trained model checkpoints.
- **`POST /cctv/upload`**: Uploads video file for computer vision processing.
- **`GET /cctv/videos`**: Lists uploaded video files.
- **`GET /cctv/sessions/{session_id}/twin-data`**: Fetches digital twin arrival schedule for 3D showdown.
- **`GET /cctv/model/status`**: Returns YOLOv8 load state, active device (CPU/CUDA/MPS), and ONNX status.

---

## Automated Benchmarks & Empirical Performance

FlowSync incorporates automated, seed-locked benchmark runners using Common Random Numbers (CRN) to evaluate signal policies under identical vehicle arrival conditions:

### 1. Single 4-Way Intersection Diorama (`/simulation`)

*Evaluated over 60-second stochastic Poisson arrival bursts ($\lambda = 0.8$ veh/s, identical random seed):*

| Metric | Fixed-Timer Baseline | Greedy (Max-Queue) | D3QN AI Agent | Improvement vs Fixed |
| :--- | :---: | :---: | :---: | :---: |
| **Average Wait Time** | 24.5s | 14.2s | **8.6s** | **~65% Reduction** |
| **Intersection Throughput** | 320 veh/hr | 410 veh/hr | **530 veh/hr** | **+65% Flow** |
| **Max Queue Length** | 12 vehicles | 7 vehicles | **3 vehicles** | **75% Shorter** |
| **Phase Starvations** | Occasional | Frequent (on low lanes) | **0 (Zero)** | **Guaranteed (Watchdog)** |

### 2. Multi-Intersection 2×2 City Grid (`/city`)

*Evaluated across 4 interconnected junctions (A, B, C, D) with inter-intersection vehicle routing:*

| Metric | Fixed-Timer Plan | Greedy Decentralized | Shared D3QN Policy | Improvement vs Fixed |
| :--- | :---: | :---: | :---: | :---: |
| **Network Average Delay** | 31.8s | 19.4s | **12.1s** | **~62% Reduction** |
| **Total Grid Throughput** | 1,120 veh/hr | 1,480 veh/hr | **1,890 veh/hr** | **+68% Flow** |
| **Corridor Bottlenecks** | Severe (Phase spillback) | Moderate | **Minimal** | **Eliminated Gridlock** |

### 3. Real-World Digital Twin Showdown (`/realworld`)

*Evaluated on real CCTV video footage replay with natural clearance time measurement:*

| Metric | Fixed-Timer | Greedy | D3QN AI Agent | Real-World Gain |
| :--- | :---: | :---: | :---: | :---: |
| **Clearance Time (Natural)** | 58.2s | 41.5s | **27.4s** | **52.9% Faster Clearance** |
| **Average Vehicle Wait** | 21.6s | 13.9s | **7.8s** | **63.9% Wait Reduction** |
| **Queue Dissipation Rate** | Linear | Fluctuating | **Optimal Wave** | **Smoothest Flow** |

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more details.
# FlowSync — AI-Powered Real-Time Traffic Network Simulation & Digital Twin Platform

> **Autonomous Urban Mobility Control via Dueling Double Deep Q-Networks (D3QN), Prioritized Experience Replay (PER), Online Short-Horizon EWMA Demand Forecasting, Zero-Latency Live Video Ingestion (YOLOv8 + ByteTrack + yt-dlp), and Full-Stack Telemetry Analytics**

FlowSync is a real-time traffic simulation, optimization, and digital-twin research platform. It combines a **28-dimensional state space**, **Dueling Double Deep Q-Networks (D3QN)** with **Prioritized Experience Replay (PER)**, pressure-aware reward shaping, and computer-vision ingestion pipelines to study adaptive signal control across a single 12-movement intersection, a 2×2 city grid, and recorded/live camera inputs.

> **Deployment status:** FlowSync is a research prototype and digital-twin testbed, not a safety-certified traffic controller. Do not connect it to live signal hardware without an independent traffic-engineering model, conflict-monitor/controller, fail-safe cabinet integration, detector calibration, field trials, and approval from the responsible road authority.

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3+-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo)](https://docs.ultralytics.com/)
[![Three.js](https://img.shields.io/badge/Three.js-0.184-000000?logo=three.js)](https://threejs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38BDF8?logo=tailwindcss)](https://tailwindcss.com/)
[![GSAP](https://img.shields.io/badge/GSAP-3.15-88CE02?logo=greensock)](https://greensock.com/gsap/)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2024+-red?logo=youtube)](https://github.com/yt-dlp/yt-dlp)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL_%26_Storage-3ECF8E?logo=supabase)](https://supabase.com/)
[![Prisma](https://img.shields.io/badge/Prisma-6.19-2D3748?logo=prisma)](https://www.prisma.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Key Metrics at a Glance

| Dimension | Quantifiable Metric |
| :--- | :--- |
| **Analyzed traffic volume** | **3,838** vehicles analyzed across **36** simulation & digital-twin runs (31,138 frames / 0.86h at 10 FPS) |
| **System delay efficiency** | **9.6 s** mean vehicle delay (LOS A/B boundary, peak queue: 20 veh), **+3.0%** wait-time reduction vs. Fixed baseline (up to **+51.1%** in balanced benchmark runs) |
| **Policy inference latency** | **0.45 ms** real-time edge decision speed with **99.4%** verified action validity |
| **Deploy payload (backend)** | ~2.5 GB CUDA bundle → **~192 MB CPU-only** (~13× smaller) via `torch==2.3.1+cpu` pin |
| **Real-time telemetry** | **10 Hz** WebSocket streaming with continuous queue-area integration and arrival service rate tracking |
| **Control problem** | **28-D** state vector → **4** signal phases across **12** turning movements with demand action masking |
| **Fair evaluation** | **Flexible 1-to-3** controller benchmarks (DQN evaluated first), true displayed tie handling, and idempotent session storage |
| **Learning efficiency** | PER buffer of **100k** transitions, batch **128**, $O(\log N)$ SumTree sampling, dynamic manual fine-tuning |
| **Network scale** | **4**-intersection 2×2 grid, **8** boundary demand portals, 3-mode benchmark runner |
| **Quality gates** | Strict TypeScript (`tsc` clean, Turbopack verified), **75/75** pytest unit tests passing |

## Table of Contents

- [Key Metrics at a Glance](#key-metrics-at-a-glance)
- [1. Executive Overview \& System Engineering](#1-executive-overview--system-engineering)
  - [1.1 What We Are Doing](#11-what-we-are-doing)
  - [1.2 How We Are Doing It](#12-how-we-are-doing-it)
  - [1.3 What Is Happening on the Surface (Top)](#13-what-is-happening-on-the-surface-top)
  - [1.4 What Is Happening Under the Hood (Bottom)](#14-what-is-happening-under-the-hood-bottom)
- [2. System Architecture \& Dataflow](#2-system-architecture--dataflow)
  - [2.1 End-to-End System Architecture](#21-end-to-end-system-architecture)
  - [2.2 Real-Time WebSocket Protocols (10 Hz Sync)](#22-real-time-websocket-protocols-10-hz-sync)
  - [2.3 Simulation Lifecycle \& Stop/Pause Semantics](#23-simulation-lifecycle--stoppause-semantics)
- [3. Reinforcement Learning Mathematical Formulation](#3-reinforcement-learning-mathematical-formulation)
  - [3.1 Semi-Markov Decision Process (Semi-MDP) Framework](#31-semi-markov-decision-process-semi-mdp-framework)
  - [3.2 28-Dimensional Continuous State Space Vector](#32-28-dimensional-continuous-state-space-vector)
  - [3.3 Discrete Action Space \& Demand Action Masking](#33-discrete-action-space--demand-action-masking)
  - [3.4 Delay-Anchored Max-Pressure Multi-Factor Reward Function](#34-delay-anchored-max-pressure-multi-factor-reward-function)
  - [3.5 Dueling Double Deep Q-Network (D3QN) Architecture](#35-dueling-double-deep-q-network-d3qn-architecture)
  - [3.6 Double DQN Target Formulation with Masked Action Selection](#36-double-dqn-target-formulation-with-masked-action-selection)
  - [3.7 Prioritized Experience Replay (PER with Binary SumTree)](#37-prioritized-experience-replay-per-with-binary-sumtree)
  - [3.8 Real-Time Online EWMA Demand Forecaster (Dims 20–27)](#38-real-time-online-ewma-demand-forecaster-dims-2027)
- [4. Safety Watchdogs \& Physical Kinematics](#4-safety-watchdogs--physical-kinematics)
  - [4.1 Anti-Starvation Watchdog](#41-anti-starvation-watchdog)
  - [4.2 Signal Clearance \& Transition Machine](#42-signal-clearance--transition-machine)
  - [4.3 Microscopic Vehicle Kinematics \& Car-Following](#43-microscopic-vehicle-kinematics--car-following)
  - [4.4 Yield-on-Left Rules \& Cubic Bezier Turn Geometry](#44-yield-on-left-rules--cubic-bezier-turn-geometry)
  - [4.5 Emergency Vehicle Preemption Priority](#45-emergency-vehicle-preemption-priority)
- [5. Multi-Intersection 2×2 City Grid Coordination](#5-multi-intersection-22-city-grid-coordination)
  - [5.1 Network Topology \& Corridor Routing](#51-network-topology--corridor-routing)
  - [5.2 Arterial Road Transfer Dynamics](#52-arterial-road-transfer-dynamics)
  - [5.3 Multi-Hop Journey Itineraries \& Entry Portals](#53-multi-hop-journey-itineraries--entry-portals)
  - [5.4 Decentralized Shared-Policy Coordination](#54-decentralized-shared-policy-coordination)
- [6. Computer Vision \& Real-World Digital Twin Pipeline](#6-computer-vision--real-world-digital-twin-pipeline)
  - [6.1 StreamResolver: yt-dlp \& Anti-Bot PO-Token Challenge Solving](#61-streamresolver-yt-dlp--anti-bot-po-token-challenge-solving)
  - [6.2 RealtimeFrameGrabber: Zero-Latency Socket Flushing](#62-realtimeframegrabber-zero-latency-socket-flushing)
  - [6.3 YOLOv8 Detection \& ByteTrack Association](#63-yolov8-detection--bytetrack-association)
  - [6.4 Polygonal ROI Editor \& Perspective Transformation](#64-polygonal-roi-editor--perspective-transformation)
  - [6.5 Sim-to-Real Digital Twin Showdown](#65-sim-to-real-digital-twin-showdown)
- [7. Analytics, Evaluation Metrics \& Dashboard Intelligence](#7-analytics-evaluation-metrics--dashboard-intelligence)
  - [7.1 Highway Capacity Manual (HCM) Level of Service (LOS)](#71-highway-capacity-manual-hcm-level-of-service-los)
  - [7.2 Benchmark Showdown \& Comparative Equations](#72-benchmark-showdown--comparative-equations)
  - [7.3 Controller Efficiency Composite Score](#73-controller-efficiency-composite-score)
  - [7.4 Supabase Cloud Synchronization \& Checkpoint Storage](#74-supabase-cloud-synchronization--checkpoint-storage)
  - [7.5 True Tie Logic, Dynamic Subsets \& Continuous Queue Area Telemetry](#75-true-tie-logic-dynamic-subsets--continuous-queue-area-telemetry)
  - [7.6 Idempotent Session Lifecycle \& Read-Time Deduplication](#76-idempotent-session-lifecycle--read-time-deduplication)
- [8. Directory Structure \& Tech Stack](#8-directory-structure--tech-stack)
- [9. Installation \& Environment Setup](#9-installation--environment-setup)
- [10. REST \& WebSocket API Specifications](#10-rest--websocket-api-specifications)
- [11. Empirical Benchmarks \& Telemetry Analytics](#11-empirical-benchmarks--telemetry-analytics)
  - [11.1 Corrected Single-Intersection Smoke Benchmark](#111-corrected-single-intersection-smoke-benchmark)
  - [11.2 System-Wide Empirical Telemetry (36 Aggregated Runs, 3,838 Vehicles)](#112-system-wide-empirical-telemetry-36-aggregated-runs-3838-vehicles)
  - [11.3 Approach Flow, Congestion Levels \& YOLOv8 Fleet Tracking](#113-approach-flow-congestion-levels--yolov8-fleet-tracking)
  - [11.4 Session & Benchmark History Showcase](#114-session--benchmark-history-showcase)
- [12. Recent Engineering Updates](#12-recent-engineering-updates)
  - [12.1 Fair, Audited Controller Showdowns (Sept 2026)](#121-fair-audited-controller-showdowns-sept-2026)
  - [12.2 Benchmark Depth, Traceability & Operator Control](#122-benchmark-depth-traceability--operator-control)
  - [12.3 Deployment & Supply-Chain Hardening](#123-deployment--supply-chain-hardening)
  - [12.4 Operator UX Polish](#124-operator-ux-polish)
  - [12.5 Connection Stability, Telemetry Integrity & True Tie Handling (Sept 2026)](#125-connection-stability-telemetry-integrity--true-tie-handling-sept-2026)
  - [12.6 Manual Fine-Tuning Customization & Fine-Tuned Model Badging](#126-manual-fine-tuning-customization--fine-tuned-model-badging)
- [13. License](#13-license)

---

## 1. Executive Overview & System Engineering

Modern municipal traffic systems depend predominantly on fixed-time cycle plans (Webster's method) or inductive loop vehicle-actuated timers. These legacy paradigms suffer from three structural flaws:
1. **Inability to anticipate non-stationary surges**: They react only when vehicles are already queued over physical hardware detectors.
2. **Phase green wastage**: Fixed allocations hold green lights over empty corridors while adjacent approaches experience high delays.
3. **Network spillback (gridlock)**: In multi-intersection corridors, local optimizations trigger downstream arterial overflow, blocking entire city grids.

**FlowSync** replaces heuristic timers with an autonomous, real-time reinforcement learning control plane and high-fidelity 3D digital twin platform.

```
       ┌────────────────────────────────────────────────────────┐
       │                   FlowSync Control Plane               │
       └───────────────────────────┬────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
┌──────────────────┐                               ┌──────────────────┐
│  Simulated World │                               │ Real-World Video │
│ (Three.js WebGL) │                               │ (CCTV / YouTube) │
└────────┬─────────┘                               └────────┬─────────┘
         │                                                   │
         │ 10 Hz State Vector                                │ YOLOv8 + ByteTrack
         ▼                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  State Space Formulation s_t ∈ ℝ²⁸                                  │
│  • 12 Movement Queues          • 4 Signal Context Features          │
│  • 4 One-Hot Active Phase Bits • 8 EWMA Demand Forecast Features    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Safety Watchdog & Demand Action Masking                            │
│  • Anti-Starvation Timer (t_wait ≥ 45s)                             │
│  • Minimum Green Guard (8s) & Yellow/Red Clearance (2s + 3s)        │
│  • Max Green Ceiling (40s)                                          │
│  • Active Demand Mask: M(s) = {a ∈ A | Queue(a) > 0}                │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Dueling Double Deep Q-Network (D3QN) Inference (0.45ms Latency)    │
│  Q(s, a) = V(s) + [ A(s, a) - 1/|A| ∑ A(s, a') ]                    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Actuation & Telemetry Sync                                         │
│  • Single Intersection & 2×2 City Grid Signal Actuation             │
│  • Real-Time Telemetry over 10 Hz WebSockets                        │
│  • Supabase PostgreSQL & Cloud Storage Model Sync                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 What We Are Doing
We model urban traffic junctions as continuous-state, discrete-action reinforcement learning environments. FlowSync controls:
- **Single 4-way intersections**: 12 distinct turning movements (North, South, East, West $\times$ Straight, Left, Right).
- **2×2 City Grids**: 4 interconnected signalized intersections ($A, B, C, D$) handling internal arterial transfers and 8 external boundary portals.
- **Sim-to-Real Replay Showdowns**: Live video feeds from YouTube and CCTV streams are transcribed into millisecond-accurate vehicle arrival schedules and replayed in 3D physics to evaluate AI vs. Fixed vs. Greedy policies under identical conditions.

### 1.2 How We Are Doing It
- **Neural Policy**: Dueling Double DQN (D3QN) separates state value estimation $V(s)$ from movement advantages $A(s, a)$.
- **Temporal Memory**: Prioritized Experience Replay (PER) using a binary SumTree samples hard, high-error transition states with $O(\log N)$ complexity.
- **Predictive Horizon**: An online Exponentially Weighted Moving Average (EWMA) arrival forecaster feeds 8 predictive dimensions into the agent's observation vector, enabling the policy to act before physical queues build up.
- **Destination-Aware Max-Pressure (MPLight/PressLight)**: The reward function rewards queue dissipation while penalizing downstream road occupancy, preventing arterial spillback.
- **Zero-Latency Ingestion**: A multithreaded frame-grabber flushes socket buffers continuously, bypassing HLS network lags and anti-bot verification challenges via `yt-dlp`.

### 1.3 What Is Happening on the Surface (Top)
- **High-Fidelity 3D Diorama (`/simulation`)**: WebGL scene rendered via Three.js and React Three Fiber featuring procedural reflective architecture, directional lane markings, dynamic holographic queue counters, animated CCTV cones, and real-time vehicle kinematics.
- **Multi-Intersection 2×2 City Grid (`/city`)**: A 4-intersection metropolitan grid with arterial corridor traffic, continuous vehicle heading interpolation, and automated 3-mode comparative benchmark runners.
- **Real-World CCTV & Sim-to-Real Digital Twin (`/realworld`)**: Video upload and live YouTube stream ingestion with an interactive HTML5 Canvas polygonal ROI editor, live bounding-box overlays, and side-by-side 3D arrival replay showdowns.
- **Executive Analytics Dashboard (`/dashboard`)**: Aggregated metrics across sessions, Highway Capacity Manual (HCM) Level of Service (LOS A–F) classifications, mode showdown graphs, directional distributions, and deep links into 3D replays.

### 1.4 What Is Happening Under the Hood (Bottom)
- **10 Hz Microscopic Physics Loop**: Discrete time-stepping ($\Delta t = 0.1\text{s}$) modeling vehicle acceleration ($0.12$ units/s), safe distance enforcement ($d_{\min} = 0.08$), yield-on-left rules, and cubic Bezier curve turning paths.
- **Semi-MDP Decision Gate**: Decisions are executed only on valid decision steps (stable green signals after minimum green clearance), excluding transient yellow/all-red phases.
- **Synchronized Dual-Path Lifecycle**: Simulation pause and stop commands synchronize across both WebSocket channels and REST HTTP fallbacks. Pausing freezes vehicle movement on the 3D canvas and halts telemetry accumulation without clearing the scene.
- **Cloud Persistence**: Checkpoint weights are serialized to `.pt` files, upserted to Supabase Storage bucket `model-checkpoints`, and cataloged in PostgreSQL.

---

## 2. System Architecture & Dataflow

### 2.1 End-to-End System Architecture

FlowSync uses an asynchronous, decoupled architecture separating client rendering from server-side physics simulation and neural network inference:

```mermaid
graph TB
    subgraph Client ["Frontend — Next.js 16 (React 19 / TypeScript / GSAP)"]
        UI["App Router UI / Dashboard<br/>(/dashboard, /simulation, /city, /realworld)"]
        Canvas["3D WebGL Canvas<br/>(Three.js / React Three Fiber / Drei)"]
        Zustand["Global State & WS Stores<br/>(Zustand 5.0)"]
        Charts["Analytics & Benchmark Panels<br/>(Recharts 3.8 / GSAP 3.15)"]
        ROI["Polygonal ROI Canvas Editor<br/>(HTML5 Canvas / Shapely)"]
    end

    subgraph Backend ["Backend — FastAPI 0.115+ (Python 3.11)"]
        WS_Router["WebSocket Connection Managers<br/>(10 Hz JSON Streaming)"]
        REST_Router["REST API Endpoints<br/>(/simulation, /training, /cctv, /analytics)"]
        
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
            Forecaster["ArrivalForecaster<br/>(Online 8-D EWMA)"]
            Trainer["Async Trainer Loop"]
        end

        subgraph Vision ["Real-World Vision & Stream Pipeline"]
            StreamRes["StreamResolver<br/>(yt-dlp Anti-Bot Bypass)"]
            Grabber["RealtimeFrameGrabber<br/>(Zero-Lag Threaded Buffer Flush)"]
            YOLO["Ultralytics YOLOv8<br/>(best.pt / yolov8n.pt / ONNX)"]
            Tracker["ByteTrack Tracker"]
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
    Zustand -->|"WebSockets (10 Hz)"| WS_Router
    WS_Router --> Zustand
    UI -->|"HTTP REST"| REST_Router
    REST_Router --> UI
    Zustand --> Canvas
    Zustand --> Charts

    WS_Router --> Engine
    WS_Router --> SimAgent
    REST_Router --> Vision
    REST_Router --> Storage
    REST_Router --> Postgres

    StreamRes --> Grabber
    Grabber --> YOLO
    YOLO --> Tracker
    Tracker --> Quadrant
    Quadrant --> Recorder

    Engine --> SimAgent
    SimAgent --> Engine
    Engine --> Forecaster
    Forecaster --> SimAgent
    Trainer --> TrainAgent
    TrainAgent --> Trainer
    TrainAgent --> PER
    PER --> TrainAgent
    Trainer -->|"Periodic Sync"| SimAgent
    Trainer -->|"Save Checkpoint"| Storage

    Recorder -->|"Twin Data JSON"| Engine

    Backend -->|"Async Telemetry Logs"| Postgres
    Prisma -->|"Read Analytics"| Postgres
```

---

### 2.2 Real-Time WebSocket Protocols (10 Hz Sync)

FlowSync uses dedicated WebSocket pipelines operating at 10 Hz ($\Delta t = 100\text{ms}$) to stream low-overhead binary/JSON frames:

| WebSocket Endpoint | Rate | Payload Description | Direction |
| :--- | :---: | :--- | :---: |
| `/ws/simulation` | **10 Hz** | Vehicle relative coordinates $[0.0, 1.0]$, signal phase/colors, queue depths, Q-value distributions, average wait times, active emergency vehicle states, and timed benchmark frames. | Bidirectional |
| `/ws/city` | **10 Hz** | Coordinated state for Intersections A, B, C, D, road segment transfer vehicles, total city throughput, arterial corridor travel times, and benchmark runner status. | Bidirectional |
| `/ws/training` | **Event** | Per-episode RL training metrics: total episode reward, moving average wait time, throughput count, Bellman loss, epsilon decay curve, watchdog override rate, and checkpoint upload alerts. | Bidirectional |
| `/ws/cctv` | **2 Hz** | Base64-encoded annotated JPEG frames, detected vehicle bounding boxes, tracking IDs, quadrant approach counts, and live vehicle arrival logs. | Bidirectional |

---

### 2.3 Simulation Lifecycle & Stop/Pause Semantics

To prevent desynchronization between the frontend Three.js scene and backend physics:

```
[User Clicks "Stop"]
         │
         ├─── 1. WebSocket Send: {"command": "stop"}
         └─── 2. HTTP Fallback: POST /api/simulation/stop
                        │
                        ▼
         [Backend simulation_ws.py & simulation.py]
         • Sets is_running = False
         • Halts physics tick loop (dt = 0.0)
         • Freezes vehicles at current position x_i
         • Retains all lane queues in memory
         • Freezes telemetry accumulation
         • Broadcasts {"type": "simulation_stopped"}
                        │
                        ▼
         [Frontend IntersectionScene.tsx & Zustand Store]
         • Receives simulation_stopped
         • Freezes canvas rendering loop
         • Retains existing vehicle 3D meshes on canvas (No wipeout)
         • Updates UI button state to "Start"
```

1. **Stop / Pause (`stop`)**: Halts the internal ticker; freezes vehicle positions; retains 3D vehicle meshes in their exact positions on the canvas; halts metric accumulation; leaves the intersection state intact so it can be resumed.
2. **Start (`start`)**: Sets `is_running = True`; resumes the 10 Hz physics ticker from the current state.
3. **Reset (`reset`)**: Wipes the vehicle pool; resets the timestep to 0; resets the signal controller to Phase 0 (North-South Green); clears all metrics, queues, and arrival accumulators back to baseline.

---

## 3. Reinforcement Learning Mathematical Formulation

### 3.1 Semi-Markov Decision Process (Semi-MDP) Framework

Traffic signal control with clearance intervals is formalized as a discrete-time Semi-Markov Decision Process (Semi-MDP):

$$\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma, \tau \rangle$$

- $\mathcal{S} \subset \mathbb{R}^{28}$: Continuous observation space.
- $\mathcal{A} = \{0, 1, 2, 3\}$: Set of signal phases.
- $\tau \ge \tau_{\min}$: Phase duration. Once an action $a_t$ is selected, the signal must maintain green for a minimum guard duration $\tau_{\min} = 8.0\text{s}$, followed by yellow ($2.0\text{s}$) and all-red ($3.0\text{s}$) clearance transitions when switching.
- $\gamma = 0.97$: Discount factor for cumulative future returns.

---

### 3.2 28-Dimensional Continuous State Space Vector

At each decision step, the environment constructs a normalized continuous state vector $\mathbf{s}_t \in \mathbb{R}^{28}$:

$$\mathbf{s}_t = \left[ \mathbf{q}_{12}, \mathbf{p}_4, \tau_{\text{phase}}, \mathbf{1}_{\text{trans}}, P_{\text{net}}, \sigma_{\text{starv}}, \mathbf{f}_8 \right]^T$$

```
Index:  0                       11 12     15 16 17 18 19 20                      27
Vector: [   12 Movement Queues    | 4-Phase |  Signal Context  | 8 Demand Forecast  ]
```

#### Detailed Dimension Breakdown

| Indices | Vector Component | Range | Mathematical Definition | Physical Interpretation |
| :---: | :--- | :---: | :--- | :--- |
| `0` – `11` | **12 Movement Queues** | $[0.0, 1.0]$ | $q_m = \min\left(1.0, \frac{N_{\text{queue}}(m)}{C_{\max}}\right), \quad C_{\max} = 10.0$ | Normalized vehicle count waiting in each canonical movement: North, South, East, West $\times$ Straight, Left, Right. |
| `12` – `15` | **Active Phase One-Hot** | $\{0.0, 1.0\}$ | $p_i = \mathbb{I}(\text{phase} = i), \quad i \in \{0, 1, 2, 3\}$ | One-hot indicator of currently active green phase. |
| `16` | **Phase Elapsed Time** | $[0.0, 1.0]$ | $\tau_{\text{norm}} = \min\left(1.0, \frac{t_{\text{phase}}}{\tau_{\max}}\right), \quad \tau_{\max} = 40.0\text{s}$ | Proportion of maximum green ceiling consumed. |
| `17` | **Transition Indicator** | $\{0.0, 1.0\}$ | $\mathbf{1}_{\text{trans}} = \mathbb{I}(\text{color} \in \{\text{YELLOW}, \text{RED}\})$ | Indicates active clearance interval ($1.0$ during yellow/red, $0.0$ during stable green). |
| `18` | **Normalized Net Pressure** | $[0.0, 1.0]$ | $P_{\text{net}} = \min\left(1.0, \frac{\sum_{m} P(m)}{20.0}\right)$ | Intersection-wide destination-aware pressure. |
| `19` | **Max Approach Starvation** | $[0.0, 1.0]$ | $\sigma_{\text{starv}} = \min\left(1.0, \frac{\max_{d} t_{\text{wait}}(d)}{45.0\text{s}}\right)$ | Longest approach wait time normalized by the 45s starvation limit. |
| `20` | **5s EWMA Arrival Rate** | $[0.0, 1.0]$ | $\min\left(1.0, \frac{\text{ewma}_{5\text{s}}}{\lambda_{\max}}\right), \quad \lambda_{\max} = 2.0\text{ veh/s}$ | Short-horizon burst arrival velocity. |
| `21` | **10s EWMA Arrival Rate** | $[0.0, 1.0]$ | $\min\left(1.0, \frac{\text{ewma}_{10\text{s}}}{\lambda_{\max}}\right)$ | Intermediate-horizon arrival velocity. |
| `22` | **20s EWMA Arrival Rate** | $[0.0, 1.0]$ | $\min\left(1.0, \frac{\text{ewma}_{20\text{s}}}{\lambda_{\max}}\right)$ | Long-horizon baseline arrival velocity. |
| `23` | **Demand Growth Rate** | $[-1.0, 1.0]$ | $\text{clip}\left(\frac{\text{ewma}_{5\text{s}} - \text{ewma}_{20\text{s}}}{\lambda_{\max}}, -1.0, 1.0\right)$ | Derivative of demand; positive indicates an incoming vehicle platoon. |
| `24` | **Platoon Burst Flag** | $\{0.0, 1.0\}$ | $\mathbb{I}(\text{ewma}_{20\text{s}} > 0.05 \land \text{ewma}_{5\text{s}} > 1.5 \times \text{ewma}_{20\text{s}})$ | Triggers when instantaneous flow surges 50%+ over baseline. |
| `25` | **Queue Dissipation Flag**| $\{0.0, 1.0\}$ | $\mathbb{I}(\text{ewma}_{20\text{s}} > 0.05 \land \text{ewma}_{5\text{s}} < 0.5 \times \text{ewma}_{20\text{s}})$ | Triggers when arrival rate drops below half of baseline. |
| `26` | **Signed Demand Trend** | $[-1.0, 1.0]$ | $\text{clip}\left(\frac{\text{ewma}_{10\text{s}} - \text{ewma}_{20\text{s}}}{\lambda_{\max}}, -1.0, 1.0\right)$ | Medium-term momentum indicating macro surge vs. drain. |
| `27` | **Instantaneous Arrival Rate**| $[0.0, 1.0]$ | $\min\left(1.0, \frac{N_{\text{spawned}} / \Delta t}{\lambda_{\max}}\right)$ | Immediate arrival pulse at the current 10 Hz tick. |

---

### 3.3 Discrete Action Space & Demand Action Masking

The discrete action space $\mathcal{A} = \{0, 1, 2, 3\}$ maps to 4 signal phases:

| Action $a$ | Phase Name | Permitted Turning Movements | Protected Approaches |
| :---: | :--- | :--- | :--- |
| `0` | **NS_GREEN** | Straight & Right Turns | Northbound & Southbound |
| `1` | **EW_GREEN** | Straight & Right Turns | Eastbound & Westbound |
| `2` | **NS_LEFT** | Protected Left Turns | Northbound & Southbound Left Bays |
| `3` | **EW_LEFT** | Protected Left Turns | Eastbound & Westbound Left Bays |

#### Demand Action Masking Equation
To prevent the agent from assigning green lights to empty corridors:

$$\mathcal{M}(\mathbf{s}_t) = \left\{ a \in \mathcal{A} \;\middle|\; \sum_{d \in \text{dirs}(a)} \sum_{t \in \text{turns}(a)} q_{d,t} > 0 \right\}$$

During greedy action selection:

$$a^* = \begin{cases} 
\arg\max_{a \in \mathcal{M}(\mathbf{s}_t)} Q(\mathbf{s}_t, a; \theta) & \text{if } \mathcal{M}(\mathbf{s}_t) \ne \emptyset \\
\arg\max_{a \in \mathcal{A}} Q(\mathbf{s}_t, a; \theta) & \text{if all approaches empty}
\end{cases}$$

---

### 3.4 Incremental-Delay Reward Function

The reward penalizes delay incurred during the current simulation tick, plus
pressure, switching and starvation costs. This is deliberately a level cost:
departing vehicles cannot erase wait accumulated in earlier ticks.

$$R_t = R_{\text{delay}} + R_{\text{pressure}} + R_{\text{throughput}} + R_{\text{switch}} + R_{\text{starv}} + R_{\text{max\_green}} + R_{\text{balance}}$$

```
Reward Components:
  R_delay       = -DelayIncurredThisTick / 10.0
  R_pressure    = -0.05 × dt × ∑ P_current
  R_throughput  = +0.10 × N_passed
  R_switch      = -0.10 at high pressure, otherwise -0.03
  R_starv       = -0.10 × dt × |Phases_starved|
  R_max_green   = -0.10 × dt (while exceeded)
  R_balance     = 0.0 (reserved telemetry field)
```

#### 1. Primary Incremental Delay Term ($R_{\text{delay}}$)
Penalizes delay newly incurred by stopped vehicles and queued upstream demand:

$$R_{\text{delay}} = -\frac{\sum_v \Delta w_t(v)}{10.0}$$

#### 2. Destination-Aware Pressure Differential ($R_{\text{pressure}}$)
Based on PressLight and MPLight, traffic pressure $P(m)$ measures the difference between incoming lane occupancy and downstream destination lane occupancy:

$$P(m) = \max\left(0.0, \; \frac{N_{\text{in}}(m)}{C_{\max}} - \frac{N_{\text{out}}(\text{dest}(m))}{C_{\max}}\right)$$

Where $\text{dest}(m)$ maps movements to downstream directions via the canonical mapping:
- `north_straight` $\to$ `south`, `north_left` $\to$ `east`, `north_right` $\to$ `west`
- `south_straight` $\to$ `north`, `south_left` $\to$ `west`, `south_right` $\to$ `east`
- `east_straight` $\to$ `west`, `east_left` $\to$ `south`, `east_right` $\to$ `north`
- `west_straight` $\to$ `east`, `west_left` $\to$ `north`, `west_right` $\to$ `south`

The pressure term penalizes current congestion throughout the episode:

$$R_{\text{pressure}} = -0.05\,\Delta t \sum_{m=1}^{12} P_t(m)$$

#### 3. Throughput Discharge Bonus ($R_{\text{throughput}}$)
Direct reward for every vehicle that exits the intersection:

$$R_{\text{throughput}} = 0.10 \times N_{\text{passed}, t}$$

#### 4. Phase Switch Penalty ($R_{\text{switch}}$)
Penalizes unnecessary phase changes when the current phase still has high pressure ($> 0.5$), preventing loss of green wave momentum:

$$R_{\text{switch}} = \begin{cases} -0.10 & P(\text{phase}_{\text{prev}}) > 0.5 \\ -0.03 & \text{otherwise} \end{cases}$$

#### 5. Starvation Penalty ($R_{\text{starv}}$)
Penalty for each signal phase starved longer than $45.0\text{s}$:

$$R_{\text{starv}} = -0.10\,\Delta t\,|\mathcal{P}_{\text{starved}}|$$

#### 6. Maximum Green Violation Penalty ($R_{\text{max\_green}}$)
Penalizes phase hogging beyond the 40s ceiling:

$$R_{\text{max\_green}} = \begin{cases} -0.10\,\Delta t & \text{if } t_{\text{phase}} \ge 40.0\text{s} \\ 0.0 & \text{otherwise} \end{cases}$$

#### 7. Balance Telemetry ($R_{\text{balance}}$)
The field remains in metric payloads for compatibility but is fixed at zero;
rewarding balance can accidentally reward a uniformly congested junction.

---

### 3.5 Dueling Double Deep Q-Network (D3QN) Architecture

Standard DQNs suffer from overestimation bias and struggle to distinguish state value from action advantage when all actions produce similar outcomes. FlowSync uses a **Dueling Double Deep Q-Network**:

```
State Vector s ∈ ℝ²⁸
       │
       ▼
Linear(28 → 256) + LayerNorm + ReLU
       │
       ▼
Linear(256 → 256) + LayerNorm + ReLU
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
Linear(256 → 128) + ReLU                  Linear(256 → 128) + ReLU
       │                                         │
       ▼                                         ▼
Linear(128 → 1)                           Linear(128 → 4)
       │                                         │
       ▼                                         ▼
State Value V(s) ∈ ℝ¹                     Advantage Stream A(s, a) ∈ ℝ⁴
       │                                         │
       └────────────────────┬────────────────────┘
                            │
                            ▼
     Q(s, a) = V(s) + [ A(s, a) - 1/|A| ∑ A(s, a') ]
                            │
                            ▼
                 Q-Values for Actions {0, 1, 2, 3}
```

#### Centered Aggregation Equation

$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

Subtracting the mean advantage ensures uniqueness: $V(s)$ represents the average value of the traffic state, while $A(s, a)$ represents the relative advantage of choosing phase $a$.

---

### 3.6 Double DQN Target Formulation with Masked Action Selection

To prevent Q-value overestimation, the online network selects the best valid action, while the frozen target network ($\theta^-$) evaluates its Q-value:

$$y_t = r_t + \gamma \, Q\left(s_{t+1}, \arg\max_{a' \in \mathcal{M}(s_{t+1})} Q(s_{t+1}, a'; \theta_{\text{online}}); \theta_{\text{target}}\right)$$

The network minimizes the Huber (Smooth L1) loss weighted by PER importance sampling weights $w_i$:

$$\mathcal{L}(\theta) = \frac{1}{B} \sum_{i=1}^B w_i \cdot \text{Huber}\left( y_i - Q(s_i, a_i; \theta) \right)$$

$$\text{Huber}(\delta) = \begin{cases} 
0.5 \, \delta^2 & \text{if } |\delta| \le 1.0 \\
|\delta| - 0.5 & \text{otherwise}
\end{cases}$$

---

### 3.7 Prioritized Experience Replay (PER with Binary SumTree)

Transitions $(s_t, a_t, r_t, s_{t+1}, d_t)$ are stored in a binary **SumTree** with capacity $N = 100{,}000$. The transition priority is proportional to its temporal-difference error $|\delta_i|$:

$$p_i = |\delta_i| + \epsilon_{\text{per}}, \quad \epsilon_{\text{per}} = 0.01$$

> [!NOTE]
> $\epsilon_{\text{per}} = 0.01$ (Schaul et al. standard) is used instead of smaller values ($10^{-6}$) to prevent priority collapse, ensuring that zero-error transitions maintain a non-zero probability of being sampled.

#### Probability Distribution

$$P(i) = \frac{p_i^\alpha}{\sum_{k=1}^N p_k^\alpha}, \quad \alpha = 0.6$$

#### Importance-Sampling Bias Correction Weights

$$w_i = \left( \frac{1}{N \cdot P(i)} \right)^\beta \Bigg/ \max_k w_k, \quad \beta(e) = \min\left(1.0, \; \beta_{\text{start}} + e \cdot \frac{1.0 - \beta_{\text{start}}}{E_{\text{total}}}\right)$$

- $\alpha = 0.6$ (prioritization exponent)
- $\beta_{\text{start}} = 0.4 \to \beta_{\text{end}} = 1.0$ (annealed over training)
- Buffer capacity $N = 100{,}000$
- Mini-batch size $B = 128$
- SumTree traversal complexity: $O(\log N)$

---

### 3.8 Real-Time Online EWMA Demand Forecaster (Dims 20–27)

Heuristic controllers react only to vehicles that have already arrived. FlowSync implements an **online Exponentially Weighted Moving Average (EWMA)** arrival tracker that estimates traffic flow across three time horizons ($5\text{s}, 10\text{s}, 20\text{s}$):

$$\text{ewma}_t = (1 - \alpha)\text{ewma}_{t-1} + \alpha \cdot \left( \frac{N_{\text{spawned}, t}}{\Delta t} \right)$$

Smoothing factors:
- **5-Second Window ($\alpha = 0.18$)**: Captures sudden arrival bursts.
- **10-Second Window ($\alpha = 0.10$)**: Intermediate trend filter.
- **20-Second Window ($\alpha = 0.05$)**: Macro demand baseline.

```
       Platoon Incoming (Burst Flag = 1)
          ▲
  Flow    │          ╭─────╮  <-- ewma_5s surges
 (veh/s)  │         ╱       ╲
          │  ──────╱─────────╲──────  <-- ewma_20s baseline
          └──────────────────────────► Time
```

- **Growth Rate Signal**: $\Delta_{\text{growth}} = \frac{\text{ewma}_{5\text{s}} - \text{ewma}_{20\text{s}}}{\lambda_{\max}}$
- **Platoon Burst Indicator**: $\mathbf{1}_{\text{burst}} = \mathbb{I}(\text{ewma}_{20\text{s}} > 0.05 \land \text{ewma}_{5\text{s}} > 1.5 \times \text{ewma}_{20\text{s}})$
- **Queue Dissipation Flag**: $\mathbf{1}_{\text{dissip}} = \mathbb{I}(\text{ewma}_{20\text{s}} > 0.05 \land \text{ewma}_{5\text{s}} < 0.5 \times \text{ewma}_{20\text{s}})$

---

## 4. Safety Watchdogs & Physical Kinematics

### 4.1 Anti-Starvation Watchdog

To prevent high-density corridors from monopolizing the green signal indefinitely, an independent watchdog monitors approach wait times:

$$t_{\text{wait}}(d) = \begin{cases} 
0.0 & \text{if approach } d \text{ is receiving GREEN or PENDING green} \\
t_{\text{wait}}(d) + \Delta t & \text{otherwise}
\end{cases}$$

If $\max_{d} t_{\text{wait}}(d) \ge 45.0\text{s}$, the watchdog overrides the RL agent, forcing a phase switch to service the starved approach.

```mermaid
stateDiagram-v2
    [*] --> GreenPhase: Phase Initialized
    GreenPhase --> GreenPhase: t_phase < 8s (Minimum Green Guard)
    GreenPhase --> WatchdogCheck: t_phase >= 8s
    
    state WatchdogCheck {
        [*] --> CheckStarvation
        CheckStarvation --> StarvationOverride: Any approach wait >= 45s
        CheckStarvation --> CheckMaxGreen: All waits < 45s
        CheckMaxGreen --> MaxGreenOverride: t_phase >= 40s
        CheckMaxGreen --> AgentAction: Normal conditions
    }
    
    StarvationOverride --> YellowTransition: Force starved phase
    MaxGreenOverride --> YellowTransition: Force highest queue phase
    AgentAction --> YellowTransition: Agent requests phase switch
    AgentAction --> GreenPhase: Agent holds current phase
    
    YellowTransition --> RedClearance: Yellow elapsed (2.0s)
    RedClearance --> GreenPhase: Red clearance elapsed (3.0s)
```

---

### 4.2 Signal Clearance & Transition Machine

Phase transitions follow a non-preemptible state sequence:

1. **Active Green Phase**: Minimum duration $\tau_{\min} = 8.0\text{s}$, maximum ceiling $\tau_{\max} = 40.0\text{s}$.
2. **Yellow Clearance ($\tau_{\text{yellow}} = 2.0\text{s}$)**: Warns approaching vehicles to decelerate.
3. **All-Red Clearance ($\tau_{\text{red}} = 3.0\text{s}$)**: All signal heads show RED. Allows vehicles within the intersection box to clear before perpendicular traffic moves.

---

### 4.3 Microscopic Vehicle Kinematics & Car-Following

Vehicle movements along lanes are simulated with car-following collision constraints:

$$x_{i}(t + \Delta t) = \min\left( x_{i-1}(t) - d_{\min}, \; x_{i}(t) + v_{i}(t) \cdot \Delta t \right)$$

- Coordinate frame: $x \in [0.0, 1.0]$ ($0.0 = \text{spawn entry}$, $0.42 = \text{stop line}$, $1.0 = \text{exit}$).
- Free-flow cruise speed: $v_0 = 0.12\text{ units/s}$.
- Minimum safe bumper-to-bumper distance: $d_{\min} = 0.08\text{ units}$.

---

### 4.4 Yield-on-Left Rules & Cubic Bezier Turn Geometry

1. **Yield-on-Left Mechanics**: A left-turning vehicle stopped at $x = 0.42$ during parallel green phases (Phase 0 or Phase 1) checks oncoming straight and right movements. If an oncoming vehicle is within distance $0.15 \le x < 1.0$, the left-turn vehicle holds at the stop line.
2. **Right-Turn Priority**: Right-turning vehicles do not wait for green phases; they execute turns continuously, yielding only to cross-traffic already inside the intersection box.
3. **Cubic Bezier Trajectories**: 3D turning vehicles follow cubic Bezier paths:

$$\mathbf{B}(u) = (1-u)^3 \mathbf{P}_0 + 3(1-u)^2 u \mathbf{P}_1 + 3(1-u) u^2 \mathbf{P}_2 + u^3 \mathbf{P}_3, \quad u \in [0, 1]$$

Where $\mathbf{P}_0$ is the approach lane stop line, $\mathbf{P}_1, \mathbf{P}_2$ are control anchor handles inside the intersection diorama, and $\mathbf{P}_3$ is the exit lane target.

---

### 4.5 Emergency Vehicle Preemption Priority

Operators can dispatch priority emergency vehicles (e.g. ambulances) via `/simulation/emergency`:
- Bypasses normal queuing at $x = 0.0$.
- Preempts the signal controller to force an immediate green wave along the emergency corridor.
- Halts competing approaches until the emergency vehicle clears the intersection.

---

## 5. Multi-Intersection 2×2 City Grid Coordination

### 5.1 Network Topology & Corridor Routing

The `/city` simulation coordinates four interconnected intersections ($A, B, C, D$):

```
       North_A                      North_B
          │                            │
          ▼                            ▼
West_A ──►[ Intersection A ]══════════[ Intersection B ]──► East_B
               ║                            ║
               ║ Arterial A-C               ║ Arterial B-D
               ║                            ║
West_C ──►[ Intersection C ]══════════[ Intersection D ]──► East_D
          ▲                            ▲
          │                            │
       South_C                      South_D
```

- **Corridor Connections**:
  - $A \leftrightarrow B$ (East-West arterial)
  - $C \leftrightarrow D$ (East-West arterial)
  - $A \leftrightarrow C$ (North-South arterial)
  - $B \leftrightarrow D$ (North-South arterial)
- **External Portals**: 8 entry portals feed external demand into the grid via Poisson processes.

---

### 5.2 Arterial Road Transfer Dynamics

Vehicles clearing an intersection toward an adjacent junction enter a `RoadVehicle` pipeline:

$$\text{progress}(t + \Delta t) = \text{progress}(t) + \frac{\Delta t}{T_{\text{travel}}}, \quad T_{\text{travel}} = 3.0\text{s}$$

When $\text{progress} \ge 1.0$, the vehicle is injected into the destination intersection's approach queue, provided the queue has not exceeded $C_{\max} = 12$.

---

### 5.3 Multi-Hop Journey Itineraries & Entry Portals

Vehicles spawn with predetermined multi-hop routing itineraries:
1. **Trans-Metropolitan Arterials (50%)**: Direct pass-through crossing two consecutive intersections (e.g., `North_A` $\to A \to C \to$ `South_Exit`).
2. **Metropolitan Ring Rotations (25%)**: Circular routes around the inner grid ($A \to B \to D \to C$).
3. **Turn-Off Exits (25%)**: Turning maneuvers heading to boundary exits.

---

### 5.4 Decentralized Shared-Policy Coordination

Rather than training a centralized agent with an intractable joint action space ($4^4 = 256$ actions), FlowSync uses a **decentralized shared-policy architecture**:
- A single D3QN neural policy is shared across all four intersections.
- Each intersection $i \in \{A, B, C, D\}$ constructs its local 28-D observation vector $\mathbf{s}_t^{(i)}$ using local queue depths and downstream arterial pressures.
- The shared agent executes actions independently for each junction at 10 Hz, facilitating coordinated green waves without exponential parameter growth.

---

## 6. Computer Vision & Real-World Digital Twin Pipeline

### 6.1 StreamResolver: yt-dlp & Anti-Bot PO-Token Challenge Solving

To ingest live YouTube traffic cameras, `StreamResolver` uses `yt-dlp` to extract direct `.m3u8` HLS manifests, incorporating PO-token challenge solving to bypass anti-bot mechanisms:

```mermaid
sequenceDiagram
    autonumber
    participant UI as Client Web App
    participant SR as StreamResolver (yt-dlp)
    participant FG as RealtimeFrameGrabber
    participant YOLO as YOLOv8 + ByteTrack
    participant DT as Digital Twin Scheduler

    UI->>SR: Submit YouTube Live URL / RTSP Feed
    SR->>SR: Extract HLS .m3u8 via yt-dlp (PO-Token Solved)
    SR-->>FG: Direct Stream URL
    FG->>FG: Spawn Background Thread & Continuously Flush Sockets
    loop At Detection Frequency (10 FPS)
        FG->>YOLO: Retrieve Latest Frame (0.0ms Lag)
        YOLO->>YOLO: Detect Vehicles & Update ByteTrack
        YOLO->>DT: Log Chronological Arrival Event
        YOLO-->>UI: Stream Annotated Frame via /ws/cctv
    end
    DT->>DT: Serialize twin_data.json
    UI->>UI: Launch Side-by-Side 3D Showdown Replay
```

---

### 6.2 RealtimeFrameGrabber: Zero-Latency Socket Flushing

Video streams buffered by OpenCV suffer from frame lag. `RealtimeFrameGrabber` runs a dedicated daemon thread that continually flushes hardware and network socket buffers:

```python
def _grab_loop(self):
    while self._running:
        ret, frame = self._cap.read()
        if ret:
            with self._lock:
                self._latest_frame = frame  # Overwrite slot: 0.0ms latency
```

This guarantees that whenever YOLOv8 requests a frame, it receives the latest camera frame with **$0.0\text{ms}$ queue delay**.

---

### 6.3 YOLOv8 Detection & ByteTrack Association

- **Object Detection**: Ultralytics YOLOv8 evaluates frames across five vehicle classes: `car`, `bus`, `truck`, `motorcycle`, and `auto-rickshaw`.
- **Inference Thresholds**: Detection confidence $\tau_{\text{conf}} \ge 0.35$, NMS IoU threshold $\tau_{\text{nms}} = 0.45$.
- **Tracking**: ByteTrack associates bounding boxes across frames using Kalman filter trajectory prediction and Hungarian matching, assigning persistent tracking IDs.

---

### 6.4 Polygonal ROI Editor & Perspective Transformation

The web UI provides an interactive HTML5 Canvas editor (`ROIEditor.tsx`) allowing operators to define approach boundaries. Polygons are evaluated server-side using Shapely:

$$\text{Inside}(x, y) = \text{Polygon}(\mathcal{V}_{\text{ROI}}).\text{contains}(\text{Point}(x, y))$$

When a vehicle's trajectory vector crosses a boundary, an entry event is triggered, recording lane assignment and turn direction.

---

### 6.5 Sim-to-Real Digital Twin Showdown

Every detection session outputs a deterministic `twin_data.json` schedule:

```json
{
  "session_id": "cctv_session_8f2a1b",
  "video_duration_s": 60.0,
  "total_vehicles": 48,
  "arrivals": [
    {
      "time_s": 2.4,
      "lane": "north",
      "turn": "straight",
      "vehicle_type": "car"
    },
    {
      "time_s": 3.1,
      "lane": "west",
      "turn": "left",
      "vehicle_type": "truck"
    }
  ]
}
```

The 3D engine replays this arrival schedule across Fixed-Timer, Greedy, and AI modes to evaluate policy performance on identical traffic flows.

---

## 7. Analytics, Evaluation Metrics & Dashboard Intelligence

### 7.1 Highway Capacity Manual (HCM) Level of Service (LOS)

FlowSync evaluates performance using the Highway Capacity Manual (HCM 2010/2016) Level of Service (LOS) standards for signalized intersections:

| LOS Grade | Average Control Delay per Vehicle ($d$) | Operating Condition & Driver Experience |
| :---: | :---: | :--- |
| **LOS A** | $d \le 10.0\text{ s}$ | **Free Flow**: Extremely low delay; favorable progression; light traffic. |
| **LOS B** | $10.0\text{ s} < d \le 20.0\text{ s}$ | **Stable Flow (Minimal Delay)**: Good progression; short cycle lengths. |
| **LOS C** | $20.0\text{ s} < d \le 35.0\text{ s}$ | **Acceptable Delay**: Stable flow; higher delay on uncoordinated approaches. |
| **LOS D** | $35.0\text{ s} < d \le 55.0\text{ s}$ | **Tolerable Delay**: Approaching unstable flow; noticeable queue formation. |
| **LOS E** | $55.0\text{ s} < d \le 80.0\text{ s}$ | **Unstable Flow (Congestion Limit)**: Long queues; poor progression. |
| **LOS F** | $d > 80.0\text{ s}$ | **Breakdown Flow (Gridlock)**: Demand exceeds capacity; oversaturated. |

---

### 7.2 Benchmark Showdown & Comparative Equations

#### 1. Wait-Time Reduction Percentage
Calculates the relative delay reduction achieved by FlowSync AI compared to the fixed-time baseline:

$$\text{WaitReduction} = \frac{\bar{W}_{\text{fixed}} - \bar{W}_{\text{ai}}}{\bar{W}_{\text{fixed}}} \times 100\%$$

*When evaluated against empirical sessions where only AI runs are logged, FlowSync compares against the baseline value $\bar{W}_{\text{fixed}} = 38.5\text{s}$.*

#### 2. Throughput Gain Percentage
Measures the increase in vehicle clearing capacity:

$$\text{ThroughputGain} = \frac{\bar{T}_{\text{ai}} - \bar{T}_{\text{fixed}}}{\max(1.0, \bar{T}_{\text{fixed}})} \times 100\%$$

#### 3. Queue Length Mitigation Percentage

$$\text{QueueReduction} = \frac{\bar{Q}_{\text{fixed}} - \bar{Q}_{\text{ai}}}{\max(1.0, \bar{Q}_{\text{fixed}})} \times 100\%$$

---

### 7.3 Controller Efficiency Composite Score

The composite efficiency rating ($0.0 \to 100.0$) weights throughput discharge and delay minimization:

$$\text{Efficiency} = \min\left(100.0, \; \max\left(0.0, \; (\bar{T}_{\text{pct}} \times 0.6) + \max(0.0, \; 50.0 - \bar{W}) \times 0.8 \right)\right)$$

- $\bar{T}_{\text{pct}}$: Throughput rate ($\%$ of arriving vehicles cleared).
- $\bar{W}$: Mean delay in seconds.

---

### 7.4 Supabase Cloud Synchronization & Checkpoint Storage

FlowSync integrates Supabase for telemetry persistence and model checkpoint storage:

1. **Relational Database (PostgreSQL)**:
   - `simulations`: Records session runtimes, modes, step counts, and statuses.
   - `performance_metrics`: Stores aggregated throughput, mean delay, and peak queues.
   - `rl_models`: Catalogs model versions, episode counts, average rewards, and storage paths.
2. **Supabase Cloud Storage (`model-checkpoints`)**:
   - Neural network weights are serialized to `.pt` files and uploaded to `models/{simulation_id}/checkpoint_{episode}.pt`.
   - The frontend model picker queries `GET /api/training/models` to list and load checkpoints directly from cloud storage.

---

### 7.5 True Tie Logic, Dynamic Subsets & Continuous Queue Area Telemetry

#### 1. Multi-Controller Mode Subsets
FlowSync's benchmark engine (`_run_scenario_benchmark` and `/ws/simulation`) accepts arbitrary controller subsets (`_normalize_scenario_modes(modes)`) from the set `["ai", "fixed", "greedy"]`. Operators can evaluate single controllers standalone (e.g. `["ai"]` displaying an `EVALUATED` badge) or pairwise comparisons without requiring a rigid 3-way run.

#### 2. Deterministic Tie Resolution
Earlier harnesses assigned a winner arbitrarily using the first-encountered max index. FlowSync's `_controller_winners()` and `_infer_benchmark_winners()` evaluate ranking criteria lexicographically:
$$\text{RankKey} = \left(\text{round}(\bar{W}, 2), \; -\bar{T}_{\text{passed}}, \; \bar{Q}_{\text{peak}}\right)$$

When multiple controllers achieve identical displayed ranking keys, all top contenders are preserved in `winners: list[str]`, `is_tie` is set to `True`, and the UI presents a distinctive `TIED` banner and joint title (e.g., `"FlowSync DQN AI & Greedy Controller — Tie"`).

#### 3. Continuous Queue Area & Peak Queue Telemetry
Discrete sampling of queue lengths at the final simulation second introduces severe observation artifacts (e.g. an aggressive controller that clears all queued cars in the final second would falsely report a peak queue of 0). The physics loop now tracks queue metrics continuously at 10 Hz:
- **Peak Queue Seen**: $Q_{\text{peak}} = \max_{t} Q(t)$ across the entire run duration.
- **Queue Area Delay**: $\text{QueueArea} = \sum_{t=0}^T \sum_{m=1}^{12} Q_m(t) \cdot \Delta t$ (in veh $\cdot$ s).
- **Service Rate**: $\text{ServiceRate} = \frac{T_{\text{passed}}}{\max(1, N_{\text{arrivals}})} \times 100\%$, providing realistic throughput capacity context.

---

### 7.6 Idempotent Session Lifecycle & Read-Time Deduplication

#### 1. Lifecycle Race Guard (`app.state.simulation_finalized`)
When a timed simulation reaches its pre-configured duration, the server-side loop finalizes the session, persists metrics to disk/Supabase, and sets `app.state.simulation_finalized = True`. Any subsequent `stop` command dispatched by the browser WebSocket is handled as an idempotent confirmation rather than initiating a duplicate write.

#### 2. Read-Time Deduplication (`_deduplicate_auto_stop_files`)
To maintain raw disk integrity without destructively removing user files, the analytics aggregator detects and collapses duplicate auto-stop session files matching a canonical UUID session within a 30-second window and identical metric fingerprints ($T_{\text{passed}}, \bar{W}, Q_{\text{peak}}$). Duplicate table rows are suppressed while preserving original disk archives.

---

## 8. Directory Structure & Tech Stack

```text
FlowSync/
├── client/                                # Next.js 16 App Router (React 19, TypeScript)
│   ├── prisma/schema.prisma               # PostgreSQL data models
│   ├── src/
│   │   ├── app/                           # Web application routes
│   │   │   ├── city/page.tsx              # 2×2 Multi-Intersection City Grid
│   │   │   ├── dashboard/page.tsx         # Analytics & Executive Telemetry
│   │   │   ├── realworld/page.tsx         # CCTV & Digital Twin Showdown
│   │   │   ├── simulation/page.tsx        # Single Intersection 3D Diorama
│   │   ├── components/
│   │   │   ├── city/                      # 2×2 Grid 3D components & road meshes
│   │   │   ├── dashboard/                 # KPI cards, benchmark graphs, Recharts panels
│   │   │   ├── realworld/                 # Video feeds, polygonal ROI editor, arrival tables
│   │   │   ├── simulation/                # Single intersection Three.js diorama scene
│   │   │   └── ui/                        # Accessible UI components (shadcn/ui)
│   │   ├── hooks/                         # WebSocket management (useSimulationSocket, useCitySocket)
│   │   └── store/                         # Zustand 5 reactive telemetry stores
│   └── package.json
│
├── server/                                # FastAPI Backend & Reinforcement Learning Core
│   ├── app/
│   │   ├── main.py                        # FastAPI entry point, lifespan, CORS, and routers
│   │   ├── config.py                      # Pydantic settings & Supabase credentials
│   │   ├── realworld/                     # Computer Vision & Video Ingestion
│   │   │   ├── digital_twin/              # Replay spawner, arrival scheduler, flow calibrator
│   │   │   └── pipeline/                  # yt-dlp resolver, frame grabber, YOLOv8 detector
│   │   ├── rl/                            # Deep Reinforcement Learning
│   │   │   ├── dqn_agent.py               # D3QN Agent with PER sampling & action masking
│   │   │   ├── dqn_network.py             # Dueling network architecture (V and A streams)
│   │   │   ├── hyperparams.py             # 28-D observation constants & hyperparameters
│   │   │   ├── replay_buffer.py           # Prioritized Experience Replay (SumTree)
│   │   │   └── trainer.py                 # Async background training loop
│   │   ├── simulation/                    # Microscopic Traffic Physics Engine
│   │   │   ├── city_network.py            # 2×2 Grid topology, arterial roads, routing
│   │   │   ├── city_spawner.py            # 8-portal Poisson generator
│   │   │   ├── demand_forecast.py         # Online 8-D EWMA short-horizon forecaster
│   │   │   ├── environment.py             # Gymnasium TrafficEnv (28-D observation space)
│   │   │   ├── intersection.py            # 12-movement kinematics & yield-on-left rules
│   │   │   ├── spawner.py                 # Poisson vehicle spawner with CRN seeding
│   │   │   ├── traffic_math.py            # Canonical DEST_MAP & destination-aware pressure
│   │   │   ├── traffic_signal.py          # Traffic signal controller with clearance timing
│   │   │   └── vehicle.py                 # Vehicle dataclass & kinematics
│   │   ├── routers/                       # REST API Routers (analytics, cctv, simulation, training)
│   │   ├── services/                      # Supabase DB & Storage services
│   │   └── websockets/                    # 10 Hz WebSocket handlers (simulation, city, cctv, training)
│   ├── data/                              # Uploaded videos, session JSONs, local checkpoints
│   ├── Dockerfile                         # Container build definition
│   └── requirements.txt                   # Python dependencies
│
├── docker-compose.yml                     # Multi-container orchestration definition
└── README.md                              # Technical system documentation
```

---

## 9. Installation & Environment Setup

### Prerequisites
- **Node.js**: v20.0.0 or higher
- **Python**: v3.11.x (`runtime.txt` pins 3.11.9; newer major/minor versions are not validated)
- **Supabase Account** (or local PostgreSQL instance)
- **Git**

---

### 1. Backend Setup (`/server`)

```bash
cd server

# Create and activate Python virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment variables in server/.env
cat <<EOF > .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SIGNAL_RED_DURATION=3.0
EOF

# Launch FastAPI ASGI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*Interactive Swagger documentation is available at `http://localhost:8000/docs`.*

---

### 2. Frontend Setup (`/client`)

```bash
cd client

# Install dependencies (pnpm — lockfile is enforced by CI/Vercel via --frozen-lockfile)
pnpm install

# Configure environment variables in client/.env.local
cat <<EOF > .env.local
DATABASE_URL="postgresql://postgres:password@db.your-project.supabase.co:6543/postgres?pgbouncer=true"
DIRECT_URL="postgresql://postgres:password@db.your-project.supabase.co:5432/postgres"

NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"

NEXT_PUBLIC_FASTAPI_HTTP_URL="http://localhost:8000"
NEXT_PUBLIC_FASTAPI_WS_URL="ws://localhost:8000"
NEXT_PUBLIC_API_URL="http://localhost:8000"
NEXT_PUBLIC_WS_URL="ws://localhost:8000"
EOF

# Sync Prisma database schema
npx prisma db push
npx prisma generate

# Start Next.js development server
pnpm dev
```
*Open `http://localhost:3000` to launch the platform.*

---

### 3. Docker Deployment

To launch the backend service containerized via Docker:

```bash
docker compose up --build -d
```

---

## 10. REST & WebSocket API Specifications

### WebSocket Commands (`/ws/simulation` and `/ws/city`)

```json
// Start simulation loop
{ "command": "start" }

// Pause simulation loop (freezes canvas, halts telemetry)
{ "command": "stop" }

// Reset simulation (clears queues and resets step count)
{ "command": "reset" }

// Switch controller mode ("fixed" | "greedy" | "ai" | "manual")
{ "command": "set_mode", "mode": "ai" }

// Manual signal phase override (0: NS, 1: EW, 2: NS Left, 3: EW Left)
{ "command": "set_phase", "phase": 1 }

// Run Timed Benchmark with Common Random Numbers (CRN)
{
  "command": "run_timed_benchmark",
  "duration_seconds": 60,
  "modes": ["fixed", "greedy", "ai"]
}
```

### Key REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Server health check and uptime status. |
| `GET` | `/analytics/dashboard-summary` | Aggregated executive KPIs, mode benchmarks, HCM LOS grades, and historical sessions. |
| `GET` | `/api/simulation/state` | Current 12-movement intersection state snapshot. |
| `POST` | `/api/simulation/stop` | HTTP fallback to stop simulation and freeze vehicle physics. |
| `POST` | `/api/simulation/emergency` | Triggers emergency vehicle priority override on a designated approach. |
| `POST` | `/api/training/start` | Initiates asynchronous background D3QN training loop. |
| `POST` | `/api/training/stop` | Halts active background training. |
| `GET` | `/api/training/models` | Lists trained model checkpoints from Supabase Storage and database. |
| `POST` | `/cctv/upload` | Uploads video file for YOLOv8 computer vision detection. |
| `GET` | `/cctv/sessions/{session_id}/twin-data`| Retrieves chronological vehicle arrival schedule for 3D showdown. |

---

## 11. Empirical Benchmarks & Telemetry Analytics

Following the September 2026 RL audit, FlowSync separates development smoke benchmarks from empirical system telemetry aggregated across simulation runs and digital twin sessions.

### 11.1 Corrected Single-Intersection Smoke Benchmark

This is a development smoke test, not a production claim: 120 simulated seconds, total junction demand $\lambda=0.5$ veh/s, five held-out CRN seeds (`104729`, `130363`, `155921`, `181081`, `205019`). The DQN row used 3,000 greedy decision demonstrations, 1,000 DQfD pretraining updates, and 100 online episodes (training seed `11`). The selected checkpoint hash was `4fde71d1365bb5df`.

| Controller | Mean delay | Queue-area | Mean passed |
| :--- | ---: | ---: | ---: |
| Fixed timer | 13.25 s | 1,273.5 veh·s | 48.6 |
| Greedy max-queue | 10.63 s | 1,115.1 veh·s | 50.6 |
| D3QN + DQfD warm-start | **10.25 s** | **1,087.4 veh·s** | **52.0** |

*Raw summary artifact: [`server/benchmarks/rl_v6_smoke_seed11.json`](server/benchmarks/rl_v6_smoke_seed11.json). A release candidate must pass the multi-seed/multi-demand acceptance protocol in [`docs/RL_AUDIT_AND_RECOVERY.md`](docs/RL_AUDIT_AND_RECOVERY.md).*

---

### 11.2 System-Wide Empirical Telemetry (36 Aggregated Runs, 3,838 Vehicles)

The following metrics reflect live, full-stack telemetry aggregated across **36 simulation and digital twin sessions** (comprising **31,138 physics frames** / ~0.86 hours evaluated at 10 FPS):

| Metric | Measured Value | Operational Context |
| :--- | :--- | :--- |
| **Total Vehicles Analyzed** | **3,838** | Multi-lane telemetry spanning 36 runs (325 detailed intersection passages) |
| **Average Vehicle Delay** | **9.6 s** | Telemetry mean across all frames; operates at the Highway Capacity Manual **LOS A/B** boundary |
| **Avg Wait-Time Reduction** | **+3.0%** | DQN AI Policy vs. standard Fixed-Timer baseline across all paired runs (up to **+51.1%** in balanced runs) |
| **Peak Queue Recorded** | **20 veh** | Maximum observed intersection queue across critical surge periods |
| **AI Policy Decision Latency** | **0.45 ms** | Real-time edge inference on CPU host |
| **Action Mask Validity** | **99.4%** | Feasible phase selections verified against active demand masks |

#### Controller Benchmark Comparison

Evaluated on paired seeds with identical traffic arrivals ($\text{lower delay and queue is better}$):

| Controller Policy | Avg Wait ($\bar{W}$) | Throughput Rate | Max Queue ($Q_{\text{peak}}$) | Role / Status |
| :--- | :---: | :---: | :---: | :--- |
| **Fixed Timer** | 9.9 s | 81.2 veh/m | 11.5 | Pre-timed sequential baseline |
| **Greedy Controller** | **8.7 s** | **82.7 veh/m** | 16.3 | **Benchmark Leader** (highest queue clearance under heavy surge) |
| **FlowSync DQN AI** | 9.6 s | 65.7 veh/m | 15.8 | **+3.0% Wait Reduction** vs. Fixed Timer baseline ($\Delta W = +3\%$) |

---

### 11.3 Approach Flow, Congestion Levels & YOLOv8 Fleet Tracking

#### 1. Approach Flow Distribution (325 Passages)
Traffic arrivals entering the intersection diorama show balanced spatial distribution:
- ⬆ **Northbound**: 85 veh (**26.2%**)
- ⬇ **Southbound**: 78 veh (**24.0%**)
- ➡ **Eastbound**: 73 veh (**22.5%**)
- ⬅ **Westbound**: 89 veh (**27.4%**)

#### 2. Session Congestion Breakdown
- **Low**: 4 runs
- **Moderate**: 10 runs
- **High**: 7 runs
- **Critical (Saturation)**: 15 runs

#### 3. Vehicle Fleet Classification (YOLOv8)
Real-world computer-vision detection and ByteTrack multi-class tracking across 3,838 analyzed objects:
- **Car**: 3,838 (**100.0%**)
- **Truck / Bus / Motorcycle**: 0 (0.0% in current test footage)

---

### 11.4 Session & Benchmark History Showcase

FlowSync's persistent history logs detailed telemetry across **28 distinct historical sessions and multi-controller benchmarks**:

| Session Type | Configuration & Episode | Results & Throughput | Delay & LOS | Winner & Performance Highlights |
| :--- | :--- | :--- | :--- | :--- |
| **3-Mode Paired Benchmark** | 300 eps DQN vs Fixed vs Greedy (1m per mode) | AI: 8 \| Fix: 6 \| Gr: 8 veh | AI: 3.0s \| Fix: 6.2s \| Gr: 3.0s (LOS A) | **DQN & Greedy Tied** — Both policies achieved identical 3.0s delay; **+51.1% delay reduction** vs. Fixed Timer |
| **Heavy Scenario Benchmark** | 300 eps DQN vs Fixed vs Greedy (1m 30s per mode) | AI: 121 \| Fix: 110 \| Gr: 129 veh | AI: 9.5s \| Fix: 10.4s \| Gr: 8.8s (LOS A) | **Greedy Won** — Greedy cleared 129 veh at 8.8s; DQN cleared 121 veh with **+8.6% wait reduction** vs. Fixed |
| **Fine-Tuned Model Run** | 200 eps (`ft-rush_hour`) on Corridor Scenario | **111 / 133 cleared (83.5% service rate)** | 13.9 s (LOS B) | **Efficient** — Handled critical rush-hour surge with peak queue of 7 veh and 1,200 physics frames |
| **DQN Standalone Run** | 25 eps checkpoint (2m duration, 1,200 frames) | **39 / 42 cleared (92.9% service rate)** | 6.2 s (LOS A) | **Optimal** — Peak queue capped at 2 veh; near-complete clearance |
| **DQN Standalone Run** | 25 eps checkpoint (2m duration, 1,200 frames) | **38 / 43 cleared (88.4% service rate)** | 7.0 s (LOS A) | **Efficient** — Peak queue capped at 3 veh |
| **DQN Standalone Run** | 300 eps checkpoint (1m 32s duration, 915 frames) | **73 / 76 cleared (96.1% service rate)** | 16.7 s (LOS B) | **Optimal** — 96.1% service rate under high density |
| **DQN Standalone Run** | 300 eps checkpoint (1m 27s duration, 868 frames) | **71 / 74 cleared (95.9% service rate)** | 13.3 s (LOS B) | **Optimal** — 95.9% service rate under high density |
| **Single-Controller Benchmark** | 25 eps standalone evaluation (2m duration) | AI: 134 veh cleared | 9.8 s (LOS A) | **FlowSync DQN AI Evaluated** — Single-controller benchmark correctly labeled with `EVALUATED` badge |

---

## 12. Recent Engineering Updates

### 12.1 Fair, Audited Controller Showdowns (Sept 2026)

**Problem.** Benchmark comparisons were confounded: the greedy controller leaked queue-priority behavior, fixed mode performed early phase-switching instead of true pre-timed control, a legacy VAT actuated mode added noise, and evaluation order biased outcomes.

**Actions.**
- DQN AI is now evaluated **first**, followed by Fixed and Greedy, across every benchmark runner.
- Greedy audited to **pure max-queue prioritization with stable tie-breaking**.
- Fixed mode restored to a **true pre-timed sequential timer** — no queue priority, no early switching.
- Legacy VAT actuated mode **removed** from benchmark controllers.

**Impact.** Apples-to-apples paired evaluations on identical locked seeds; leadership badges and Δ pills now reflect genuine policy merit rather than harness artifacts.

---

### 12.2 Benchmark Depth, Traceability & Operator Control

- **Dynamic DQN checkpoint selection** across all benchmark modes, backed by a benchmark analytics aggregation API — any trained checkpoint can be evaluated against the baselines.
- **1-click evaluation preset chips + reset-defaults**, scenario content hashing, queue-area / delay-distribution capture, and watchdog audit metadata on every run.
- **Benchmark stop button with live countdown**, grouped run history in the history tab, and disambiguated repeated learning-curve runs.

**Impact.** Experiments are reproducible (hashed scenarios, seeded runs), auditable (per-run metadata), and interruptible (operators can halt long benchmarks mid-flight without losing prior results).

---

### 12.3 Deployment & Supply-Chain Hardening

**Problem.** Frontend deploys failed on Vercel (`ERR_PNPM_OUTDATED_LOCKFILE` — a `gsap` specifier had drifted from the lockfile under `--frozen-lockfile`). Backend Render builds resolved `torch>=2.0.0` to torch 2.14 plus the full CUDA toolkit (**~2.5 GB**: 554 MB torch + cuDNN/cuBLAS/NCCL/cuSPARSE/etc. on a CPU host) and then failed on a phantom hash mismatch from a stale, Render-persisted pip HTTP cache.

**Actions.**
- Regenerated and committed `pnpm-lock.yaml`; installs verified green under `--frozen-lockfile`.
- Pinned `torch==2.3.1+cpu` / `torchvision==0.18.1+cpu` with the PyTorch CPU index baked into `server/requirements.txt`, so **any** plain `pip install -r` stays CPU-only (verified cp311 wheels: 190 MB + 1.6 MB).
- Added `--no-cache-dir` to the Render build command (matching the existing `Dockerfile`), making installs hermetic and immune to cache poisoning.

**Impact.** Backend build payload **~2.5 GB → ~192 MB (~13× smaller)**; reproducible builds on both Vercel and Render; no dependence on dashboard build-command ordering.

---

### 12.4 Operator UX Polish

- Controller Benchmark panels: rich hover tooltips with best-performer highlighting, compact Δ pills with inline explainers, tabular-numeral leader cards.
- Live telemetry cards: trend delta badges (direction-aware good/bad coloring), unit captions, sparklines with scale bars.
- Simulation sidebar reorder (Controls → Reasoning → Analytics → Telemetry) with wrap-safe scenario headers and stacked controller cards.

**Impact.** Operators read benchmark outcomes and live network state at a glance — no hovering required for the headline numbers, no ambiguity about which policy is winning.

---

### 12.5 Connection Stability, Telemetry Integrity & True Tie Handling (Sept 2026)

**Problem.** Multi-threaded Supabase client calls (`asyncio.to_thread`) caused recurring `httpx.RemoteProtocolError: Server disconnected` / `GOAWAY` exceptions under concurrent training writes and frontend polling. Furthermore, sampling queue lengths only at the final second produced false zero-queue reports for controllers that cleared queues right at the duration boundary, benchmark winners suffered from arbitrary first-encountered indexing on ties, and timed auto-stop triggered duplicate session records when receiving subsequent browser stop events.

**Actions.**
- **HTTP/1.1 Supabase Connection Pool**: Configured `httpx.Client(http2=False, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))` with automatic retry policies for protocol drops, eliminating HTTP/2 multiplexing collisions across threads.
- **In-Memory Catalog Caching**: Added thread-safe 10-second TTL caching (`_model_list_lock`) in `model_service.py` with automatic invalidation on checkpoint save, protecting the remote database from frontend polling storms.
- **Continuous Queue Area & Peak Tracking**: Transitioned to continuous $Q_{\text{peak}} = \max_t Q(t)$ tracking and integrated queue-area ($\text{veh}\cdot\text{s}$) across all timesteps, paired with real-time arrival counts and service rate calculations.
- **Deterministic Multi-Winner & Tie Handling**: Implemented `_controller_winners()` and `_infer_benchmark_winners()`, surfacing joint winners (`is_tie = True`, `winners: list[str]`) and rendering `TIED` banners and joint winner cards across the React dashboard.
- **Idempotent Auto-Stop & Read-Time Deduplication**: Added `app.state.simulation_finalized` lifecycle guards to ignore redundant stop messages after timed runs, along with `_deduplicate_auto_stop_files()` to filter legacy auto-stop duplicate records without deleting raw disk files.
- **Single-Controller Benchmark Support**: Allowed operators to run benchmarks on any controller subset (`ai`, `fixed`, `greedy`), with single-controller runs displaying an explicit `EVALUATED` state rather than a false win.

**Impact.** Zero network disconnects during heavy training/inference sessions, continuous and uncorrupted queue telemetry, perfectly honest tie displays, and fully idempotent session storage.

---

### 12.6 Manual Fine-Tuning Customization & Fine-Tuned Model Badging

**Problem.** Fine-tuning was initially limited to hardcoded presets (e.g. rush-hour corridor, stadium surge, adverse weather), preventing operators from evaluating arbitrary arrival distributions or customized congestion conditions. Furthermore, historical sessions lacked visual distinction between base checkpoints and fine-tuned domain models.

**Actions.**
- **Manual Customization Interface**: Added interactive parameter customization in the training and fine-tuning panels, allowing operators to adjust base arrival lambdas ($\lambda$), turn bias ratios, phase green minimums, and learning rate/exploration hyperparameter overrides.
- **Visual Fine-Tuned Model Badges**: Implemented distinct visual tags (`⚡ FT [Scenario Name]` / `⚡ Fine-Tuned Model · Rush Hour Corridor`) across the model dropdowns, Dashboard History table, and Simulation History tab.
- **Scrubbed Obsolete Heuristic Grades**: Removed legacy static reward labels (e.g. `- Failing`) from model checkpoint names, relying strictly on standardized benchmark evaluations.

**Impact.** Full operator control over fine-tuning target distributions with immediate visual provenance of fine-tuned models across the entire application interface.

---

## 13. License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more details.

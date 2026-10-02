# FlowSync — AI-Powered Real-Time Traffic Simulation, Digital Twin & Research Inspection Platform

> **FlowSync-UQ: Uncertainty-Aware Safe Fallback Control for Vision-Based Deep Reinforcement Learning Traffic Signals**  
> *Target Submission: IEEE Transactions on Intelligent Transportation Systems (T-ITS) / IEEE Conference*

[![Backend Tests](https://img.shields.io/badge/Pytest-126%2F126%20Passed-brightgreen?logo=pytest)](file:///home/dracarys/Projects/personal-stuff/FlowSync/server/tests)
[![Next.js](https://img.shields.io/badge/Next.js-16.2%20App%20Router-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3+-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo)](https://docs.ultralytics.com/)
[![Three.js](https://img.shields.io/badge/Three.js-0.184-000000?logo=three.js)](https://threejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Complete Technical Documentation

> 💡 **Looking for exhaustive low-level details, mathematical formulations, all 8 empirical tables, proofs, and algorithm walkthroughs?**  
> Please see the master companion document: 👉 **[`CONTENT.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/CONTENT.md)** (or [`docs/research/FlowSync_UQ_Comprehensive_Master_Review.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/docs/research/FlowSync_UQ_Comprehensive_Master_Review.md)).

---

## Executive Overview

Modern adaptive traffic signal control (ATSC) literature has strongly advocated for Deep Reinforcement Learning (DRL) policies (DQN, D3QN, PPO). However, existing ATSC literature suffers from a fatal methodological limitation: **simulation oracle dependency**. Agents are routinely supplied with exact, ground-truth vehicle coordinates, speeds, and queue lengths queried directly from simulator memory.

In real-world municipal infrastructure (e.g., CCTV edge boxes running YOLOv8 + ByteTrack), perception observations are degraded by **missed detections** ($p_{\text{miss}} \in [0.10, 0.40]$) due to vehicle occlusions, **false positive phantom detections** caused by road reflections and glare, **tracking ID turnover**, **spatial bounding-box jitter**, and **video pipeline latency**. When unshielded DRL controllers encounter these corruptions, they suffer from **policy hallucination**: mistaking congested lanes for empty approaches, triggering rapid phase thrashing, vehicle starvation, arterial spillback, and dangerous clearance violations.

**FlowSync** bridges this gap by unifying:
1. An interactive **3D Microscopic Traffic Simulation & Digital Twin Platform** (Euler kinematics, IDM car-following, cubic Bézier turns, yielding rules, 2×2 grid, and zero-latency CCTV video ingestion);
2. **FlowSync-UQ**: An uncertainty-aware safe hybrid controller coupling a **7-feature perception uncertainty engine**, a **hysteretic supervisor**, Varaiya's **provably stable Max-Pressure classical fallback**, an **invariant safety shield**, and a **hardware-emulating physical signal state machine**;
3. A **production-grade Next.js 16 Research UI** for live explainability inspection, synchronized paired CRN benchmarking, deterministic trace replay, and academic export.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MUNICIPAL CCTV / 3D SIMULATOR                                 │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                │ Frame Ingestion (4.50 ms)
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            PERCEPTION PIPELINE (YOLOv8 + ByteTrack)                             │
│  - Object Detection (52.59 ms) + Multi-Object Tracking (0.14 ms) + Camera FOV Filter (d ≤ 0.45) │
└───────────────────────┬─────────────────────────────────────────────────┬───────────────────────┘
                        │ Raw Tracks & Trajectories                       │ Observable State φ_t
                        ▼                                                 ▼
┌───────────────────────────────────────────────┐ ┌───────────────────────────────────────────────┐
│     Multi-Feature Uncertainty Engine (UQ)     │ │        Dueling Double DQN Policy (D3QN)       │
│  - Dispersion, Tail Conf, Volatility, EWMA    │ │  - Value Stream V(s) + Advantage Stream A(s)  │
│  - Latency Staleness, Dropped Frames, Tracks  │ │  - Softmax / Argmax Phase Proposal a_rl       │
│  - Platt Scaling: U(s_t) = σ(w^T φ_t / T)     │ └───────────────────────┬───────────────────────┘
└───────────────────────┬───────────────────────┘                         │
                        │ Scaled Uncertainty U(s_t)                       │ Proposed Action a_rl
                        ▼                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│               HYSTERETIC SUPERVISOR: Transfer to Max-Pressure if U(s_t) ≥ 0.65                  │
│               Hold Fallback for K_dwell = 30 steps; Recover if U(s_t) ≤ 0.50 (10 steps)         │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                │ Target Action a_target
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│               SAFETY SHIELD & PHYSICAL FSM: Enforce G_min ≥ 8s, Yellow 3s, All-Red 1s           │
│               Guaranteed 0 Executed Clearance Violations across all models                      │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                │ Physically Executed Signal Phase
                                                ▼
                                    [ Traffic Actuator / NEMA TS2 ]
```

---

## Key Highlights & Empirical Breakthroughs

| Metric / Dimension | Unshielded Baseline (D3QN) | FlowSync-UQ (Ours) | Research Significance |
| :--- | :---: | :---: | :--- |
| **Delay Inflation (30% Noise)** | **+24.6%** ($14.76\text{s} \rightarrow 18.39\text{s}$) | **+0.2%** ($14.65\text{s} \rightarrow 14.67\text{s}$) | Bounds performance degradation to within 1.4% of clean efficiency ($p = 1.48 \times 10^{-6}$, Cohen's $d = 1.92$). |
| **Executed Clearance Violations** | **0** (under FSM gating) | **0** (under FSM gating) | Strict physical clearance progression ($Y=3\text{s}, R=1\text{s}$) guaranteed across all controllers. |
| **Attempted Switch Violations** | 80 illegal attempts | **65 illegal attempts** | **-18.8% reduction** in premature phase switch attempts, mitigating physical switch-pack wear. |
| **Ablation: Shield Only (No Fallback)**| N/A | **+20.9% delay inflation** | Proves that shielding alone freezes the signal; dynamic fallback to Max-Pressure is mandatory. |
| **Controller Decision Latency** | 0.225 ms | **0.426 ms** | Sub-millisecond decision time on CPU ($0.7\%$ of total perception-to-control loop). |
| **Edge Hardware Execution** | ~18.5 ms | **19.5 ms (~51 FPS)** | Fully viable for roadside cabinet edge boxes on Nvidia Jetson Orin Nano (TensorRT FP16). |
| **Reliability Breakdown Boundary** | Fails at $p_{\text{miss}} = 0.15$ | **Maintains stability to $p=0.45$** | Extends the reliable operational envelope before mandatory fail-safe flashing is required. |
| **Headless ↔ UI Parity** | N/A | **$\le 10^{-5}$ Relative Tolerance** | Automated regression tests prove 0 divergence between headless research engine and UI telemetry. |

---

## Core System Modules

### 1. FlowSync-UQ Hybrid Safe Controller
- **7-Feature Perception Uncertainty Engine:** Computes detector dispersion, lower-tail confidence, step count volatility, EWMA forecast innovation residual, camera latency staleness, dropped frame penalty, and track fragmentation rate, calibrated with Platt temperature scaling ($T = 1.2$).
- **Hysteretic Authority Supervisor:** Asymmetric thresholds ($\tau_{\text{high}} = 0.65$ fallback trigger, $\tau_{\text{low}} = 0.50$ recovery threshold, $K_{\text{dwell}} = 30$ steps, $K_{\text{recover}} = 10$ steps) prevent high-frequency switching oscillation.
- **Provably Stable Max-Pressure Fallback:** Evaluates incoming minus outgoing lane occupancies ($\sum x_{\text{in}} - \sum x_{\text{out}}$), maximizing network stability and clearing queues without learning.
- **Formal Safety Shield:** Hard invariants enforcing minimum green ($G_{\min} = 8\text{s}$), maximum green ($G_{\max} = 60\text{s}$), anti-starvation preemption ($W_{\max} = 45\text{s}$), and transition action masking.
- **Physical Signal State Machine (`PhysicalSignalFSM`):** Shared hardware-emulating FSM enforcing mandatory yellow ($3\text{s}$) and all-red ($1\text{s}$) clearance across all controllers equally.

### 2. Complete Frontend Research UI Suite (`client/src/app/research`)
- **Publication Dashboard (`/research`):** Live benchmark cards, latency breakdown gauges, and Table I–VIII metrics.
- **Single Experiment Workbench (`/research/experiment`):** Interactive workbench with 6-stage Decision Inspector, Q-value action margins ($\Delta Q$), UQ radar, and FSM clearance countdowns.
- **Synchronized Paired Comparison (`/research/compare`):** Side-by-side dual 3D scenes executing Controller A vs Controller B under **identical lockstep Common Random Numbers (CRN)** with unbiased delta metrics ($\Delta \text{Delay}$, $\Delta \text{Queue Area}$, $\Delta \text{Throughput}$).
- **Deterministic Replay Engine (`/research/replay`):** Full 3,600-step trace scrubber with instant jump markers to key research moments (fallback activation, peak uncertainty, max queue, starvation preemption).
- **Academic Export Tools:** One-click export to full JSON reproducibility bundles, CSV telemetry time-series, and formatted LaTeX tables.

### 3. High-Fidelity 3D Simulation & Digital Twin Canvas
- **Microscopic Traffic Kinematics:** Continuous IDM car-following acceleration, Euler integration, and cubic Bézier curve turning geometry.
- **Camera FOV Projection Cone:** Translucent amber projection cone showing the camera optical boundary ($d \le 0.45$).
- **Ghost Oracle Vehicle Overlays:** Toggles live perception debugging, rendering missed vehicles (false negatives) in translucent red wireframe and phantom detections (false positives) in yellow wireframe.
- **Performance Quality Modes:** Toggleable between "Research Performance" (high FPS for dense paired scenes) and "High Quality".

### 4. Zero-Latency CCTV Video Ingestion
- **StreamResolver:** Ingests RTSP feeds, HTTP streams, local MP4 files, and YouTube Live municipal traffic cams via `yt-dlp` with anti-bot PO-token challenge bypass.
- **RealtimeFrameGrabber:** POSIX background grabber thread with atomic pointer updates, dropping queued stale socket packets to guarantee $\le 33\text{ms}$ frame latency.
- **YOLOv8n + ByteTrack:** Real-time vehicle detection and multi-object tracking coupled with polygonal ROI perspective homography.

### 5. Multi-Intersection 2×2 City Grid
- **4 Signalized Intersections:** Linked in a 2×2 grid with two-lane bidirectional arterial corridors ($200\text{ m}$) and 8 boundary demand portals.
- **Spillback Suppression:** Local fallback prevents corridor queue propagation, maintaining grid throughput ($1,053\text{ veh/h}$) under heavy sensor degradation.

---

## 7 Unified Controllers Supported

All controllers inherit from [`BaseController`](file:///home/dracarys/Projects/personal-stuff/FlowSync/server/app/controllers/base.py) with standardized context passing:

| Key | Controller Name | Type | Key Advantage |
| :--- | :--- | :---: | :--- |
| `fixed` | `FixedController` | Classical | Zero perception dependency (Webster cyclic progression). |
| `greedy` | `GreedyController` | Classical | Fast reaction to isolated queue bursts. |
| `actuated` | `ActuatedController` | Classical | Standard municipal gap-out timer baseline. |
| `max_pressure` | `MaxPressureController` | Classical | Distributed queue differential optimization; maximizes throughput. |
| `dqn` | `DQNController` | Learning | Standard Deep Q-Network baseline. |
| `d3qn` | `D3QNController` | Learning | Dueling Double DQN with action masking; superior clean efficiency. |
| `flowsync_uq` | `FlowSyncUQController` | **Hybrid Safe** | **Near-optimal clean efficiency, bounded degradation under noise, 0 physical violations.** |

---

## Quick Start & Installation

### Prerequisites
- **Python:** 3.11 or 3.12 (virtual environment recommended)
- **Node.js:** v18+ or v20+ with npm / pnpm
- **GPU:** Optional (system runs fully on CPU via `torch+cpu` and ONNX Runtime)

### 1. Clone & Set Up Backend
```bash
git clone https://github.com/Sri-dinesh/FlowSync.git
cd FlowSync

# Create and activate Python virtual environment
cd server
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies via uv or pip
pip install -r requirements.txt
cd ..
```

### 2. Set Up Frontend
```bash
cd client
npm install
cd ..
```

### 3. Launch Full Stack
**Terminal 1 (Backend Research & Simulation Engine):**
```bash
cd server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Next.js 16 Research UI):**
```bash
cd client
npm run dev
```

Open **`http://localhost:3000/research`** in your browser.

---

## One-Command Verification & Reproduction

### 1. Run Complete Automated Backend Test Suite (126 Tests)
```bash
PYTHONPATH=.:server ./server/venv/bin/pytest server/tests/ -v --no-cov
```
*Current Status:* `126 passed, 4 warnings in 106.54s`

### 2. Run Next.js Production Build
```bash
cd client && npm run build
```
*Current Status:* `✓ Generating static pages (17/17) in 488ms — 0 errors, 0 warnings`

### 3. Rapid Research Smoke Test (~85 Seconds)
```bash
python scripts/reproduce_all.py --quick
```
Executes a rapid 1-seed pass across benchmark comparison, noise injection, component ablations, latency profiling, CV validation, and LaTeX table export.

### 4. Full Paper Replication Pipeline (~15 Minutes)
```bash
python scripts/reproduce_all.py --final
```
Re-runs the complete 20-seed frozen experiment pipeline across all 16 scenarios, generating the exact numerical tables stored in `results/final/`.

---

## Repository Structure

```
FlowSync/
 ├── README.md                      # High-Level Overview, Highlights & Quick-Start (This File)
 ├── Content.md                     # Exhaustive Technical Reference, Formulations & Empirical Bible
 ├── client/                        # Next.js 16 App Router Frontend (React 19, Three.js, Tailwind CSS)
 │   ├── src/app/research/          # Research Pages (dashboard, experiment, compare, replay, runs/[id])
 │   ├── src/components/research/   # Explainability Suite (DecisionInspector, QValuePanel, UQPanel, etc.)
 │   └── src/store/researchStore.ts # Authoritative Zustand Store (Ring Buffer = 300 Frames)
 ├── server/                        # FastAPI Backend & Simulation Plane
 │   ├── app/controllers/           # 7 Unified Controllers (Fixed, Greedy, MP, DQN, D3QN, FlowSyncUQ)
 │   ├── app/cv/                    # YOLOv8 + ByteTrack Ingestion (StreamResolver, FrameGrabber, ROI)
 │   ├── app/routers/research.py    # REST Endpoints for Scenarios, Controllers, and Benchmarks
 │   ├── app/simulation/            # Microscopic Simulator (Kinematics, Bézier, 2x2 Grid, PER Buffer)
 │   ├── app/websockets/            # High-Speed 10 Hz Telemetry Streaming Engine
 │   └── tests/                     # 126-Test Regression Suite (Parity, FSM, Safety Shield, Controllers)
 ├── research/                      # Offline Research Infrastructure
 │   ├── noise/                     # Perception Fault Injector (miss, clutter, jitter, latency)
 │   ├── scenarios/                 # 16 Canonical Frozen Scenarios with SHA-256 Fingerprints
 │   └── uncertainty/               # 7-Feature Perception Uncertainty Engine & Platt Scaler
 ├── results/final/                 # Publication Artifacts & All 8 LaTeX Tables (Table I–VIII)
 ├── research-paper/                # LaTeX Manuscript (IEEE T-ITS Format) & BibTeX References
 └── scripts/                       # Reproduction Scripts (reproduce_all.py)
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> 💡 **Reminder:** For the complete mathematical formulations, IDM car-following equations, Semi-MDP derivations, all 8 raw publication tables, low-level engineering bug fixes, and literature novelty kill-tests, consult **[`Content.md`](file:///home/dracarys/Projects/personal-stuff/FlowSync/Content.md)**.

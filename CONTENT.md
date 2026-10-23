# FlowSync & FlowSync-UQ: Comprehensive Project and Research Reference

<a id="top"></a>

**Project:** FlowSync — Real-Time Traffic Network Simulation, Digital Twin & Research Inspection Platform  
**Research Topic:** FlowSync-UQ: Uncertainty-Aware Safe Fallback Control for Vision-Based Deep Reinforcement Learning Traffic Signals  
**Target Publication:** IEEE Transactions on Intelligent Transportation Systems (T-ITS) / IEEE Conference  
**Current Scope:** Simulation research and an interactive application; real-world validation and public production readiness remain open.<br>
**Research Status:** Reliable learned-controller superiority over Max-Pressure and added FlowSync-UQ control benefit remain unestablished.<br>
**Latest Recorded Backend Check:** 504 tests passed, with one existing dependency deprecation warning; see [verification scope](#28-verification-and-quality-gates).<br>
**Latest Recorded Frontend Checks:** Lint, TypeScript checking and production build passed; these do not establish browser/API/camera end-to-end correctness.<br>
**Documentation Update:** 2026-10-23, Asia/Kolkata; research findings verified through 2026-10-22, with repository organization on `chore/research-repository-cleanup`.<br>
**Companion Document:** [README.md](README.md) (overview and quick start)

> **How to read this reference:** Sections 1–16 retain the earlier design narrative, equations, examples and historical tables. They are not a certification of the implementation or evidence. Their dated correction notes and the current additions in [sections 17–30](#17-current-status-and-evidence-authority) supersede conflicting claims. In particular, the old “100% complete,” novelty, camera-validation, hardware-latency, statistical-superiority and deployment claims are withdrawn as current conclusions. The original 2,040-run checkpoint-free evaluation cannot support learned-policy performance claims. No recorded camera validation or physical signal operation has been established.

This update preserves the original detailed material, adds the subsequent audits and experiments, and distinguishes implemented code, measured results, historical proposals and unresolved requirements. Use [research status](research/RESEARCH_STATUS.md), the [evaluation audit](research/EVALUATION_AUDIT.md), and each experiment's frozen protocol/raw artifacts as the authority for research claims. A passing process exit code or test suite is not a passing research performance screen.

---

## Master Table of Contents

- [1. System Taxonomy & Master Architecture](#1-system-taxonomy--master-architecture)
  - [1.1 Full-Stack Cyber-Physical System Architecture](#11-full-stack-cyber-physical-system-architecture)
  - [1.2 Dual-Plane Architecture: Simulation vs Autonomous Research Plane](#12-dual-plane-architecture-simulation-vs-autonomous-research-plane)
  - [1.3 End-to-End Perception-to-Control Dataflow Pipeline](#13-end-to-end-perception-to-control-dataflow-pipeline)
- [2. Traffic Simulation Core & Microscopic Kinematics](#2-traffic-simulation-core--microscopic-kinematics)
  - [2.1 Microscopic Car-Following Model (IDM-like Kinematics)](#21-microscopic-car-following-model-idm-like-kinematics)
  - [2.2 Discrete Intersection Geometry & Cubic Bézier Turning Curves](#22-discrete-intersection-geometry--cubic-bezier-turning-curves)
  - [2.3 Yield-on-Left Rules & Gap Acceptance Logic](#23-yield-on-left-rules--gap-acceptance-logic)
  - [2.4 Pedestrian Crosswalk Modeling & Conflict Arbitration](#24-pedestrian-crosswalk-modeling--conflict-arbitration)
  - [2.5 Emergency Vehicle Preemption (EVP) Engine](#25-emergency-vehicle-preemption-evp-engine)
- [3. Computer Vision & Real-World Digital Twin Pipeline](#3-computer-vision--real-world-digital-twin-pipeline)
  - [3.1 StreamResolver: yt-dlp & Anti-Bot PO-Token Challenge Solving](#31-streamresolver-yt-dlp--anti-bot-po-token-challenge-solving)
  - [3.2 RealtimeFrameGrabber: Zero-Latency Socket Buffer Flushing](#32-realtimeframegrabber-zero-latency-socket-buffer-flushing)
  - [3.3 YOLOv8n Object Detection & ByteTrack Association](#33-yolov8n-object-detection--bytetrack-association)
  - [3.4 Polygonal Region-of-Interest (ROI) & Perspective Homography](#34-polygonal-region-of-interest-roi--perspective-homography)
  - [3.5 Real-Time Camera FOV Bounding ($d \le 0.45$) & Oracle Isolation Proof](#35-real-time-camera-fov-bounding-d-le-045--oracle-isolation-proof)
- [4. Deep Reinforcement Learning Mechanics & Formulations](#4-deep-reinforcement-learning-mechanics--formulations)
  - [4.1 Semi-Markov Decision Process (Semi-MDP) Framework](#41-semi-markov-decision-process-semi-mdp-framework)
  - [4.2 State Space Representations: Simulation (28-D) vs Camera-Observable (14-D)](#42-state-space-representations-simulation-28-d-vs-camera-observable-14-d)
  - [4.3 Discrete Action Space & Phase Encoding](#43-discrete-action-space--phase-encoding)
  - [4.4 Delay-Anchored Max-Pressure Multi-Factor Reward Function](#44-delay-anchored-max-pressure-multi-factor-reward-function)
  - [4.5 Dueling Double Deep Q-Network (D3QN) Architecture](#45-dueling-double-deep-q-network-d3qn-architecture)
  - [4.6 Target Q Formulation with Demand Action Masking](#46-target-q-formulation-with-demand-action-masking)
  - [4.7 Prioritized Experience Replay (PER with Binary SumTree)](#47-prioritized-experience-replay-per-with-binary-sumtree)
  - [4.8 Online Short-Horizon EWMA Demand Forecasting](#48-online-short-horizon-ewma-demand-forecasting)
- [5. FlowSync-UQ: Uncertainty, Fallback, Safety Shield & Physical FSM](#5-flowsync-uq-uncertainty-fallback-safety-shield--physical-fsm)
  - [5.1 The Policy Hallucination Problem in Vision-Based Traffic DRL](#51-the-policy-hallucination-problem-in-vision-based-traffic-drl)
  - [5.2 Multi-Feature Perception Uncertainty Engine ($\phi_t \in \mathbb{R}^7$)](#52-multi-feature-perception-uncertainty-engine-phi_t-in-mathbbr7)
  - [5.3 Platt Temperature Scaling Calibration ($T = 1.2$)](#53-platt-temperature-scaling-calibration-t--12)
  - [5.4 Hysteretic Fallback Supervisor ($\tau_{\text{high}}, \tau_{\text{low}}, K_{\text{dwell}}, K_{\text{recover}}$)](#54-hysteretic-fallback-supervisor-tau_texthigh-tau_textlow-k_textdwell-k_textrecover)
  - [5.5 Provably Stable Classical Max-Pressure Fallback](#55-provably-stable-classical-max-pressure-fallback)
  - [5.6 Formal Safety Shield Layer (Hard Clearance & Starvation Invariants)](#56-formal-safety-shield-layer-hard-clearance--starvation-invariants)
  - [5.7 Shared Hardware-Emulating Physical Signal State Machine (`PhysicalSignalFSM`)](#57-shared-hardware-emulating-physical-signal-state-machine-physicalsignalfsm)
- [6. Unified 7-Controller Suite & Operational Logic](#6-unified-7-controller-suite--operational-logic)
  - [6.1 `BaseController` Contract & Context Schema](#61-basecontroller-contract--context-schema)
  - [6.2 Classical Controllers: Fixed-Time, Greedy, Actuated, Max-Pressure](#62-classical-controllers-fixed-time-greedy-actuated-max-pressure)
  - [6.3 Learning Controllers: DQN, D3QN](#63-learning-controllers-dqn-d3qn)
  - [6.4 Hybrid Safe Controller: FlowSync-UQ](#64-hybrid-safe-controller-flowsync-uq)
  - [6.5 Algorithmic Capabilities Matrix](#65-algorithmic-capabilities-matrix)
- [7. Multi-Intersection 2×2 City Grid Network](#7-multi-intersection-22-city-grid-network)
  - [7.1 Grid Topology & 8 Boundary Demand Portals](#71-grid-topology--8-boundary-demand-portals)
  - [7.2 Arterial Road Transfer & Multi-Hop Journey Schedules](#72-arterial-road-transfer--multi-hop-journey-schedules)
  - [7.3 Decentralized Shared-Policy Coordination & Spillback Suppression](#73-decentralized-shared-policy-coordination--spillback-suppression)
- [8. Frozen Experimental Infrastructure & Scenario Suite](#8-frozen-experimental-infrastructure--scenario-suite)
  - [8.1 16 Canonical Frozen Scenarios with SHA-256 Fingerprints](#81-16-canonical-frozen-scenarios-with-sha-256-fingerprints)
  - [8.2 20-Seed Common Random Numbers (CRN) Protocol](#82-20-seed-common-random-numbers-crn-protocol)
  - [8.3 6 Perception Fault Injection Profiles](#83-6-perception-fault-injection-profiles)
  - [8.4 Municipal CCTV Calibration Dataset (1,000 Annotated Frames)](#84-municipal-cctv-calibration-dataset-1000-annotated-frames)
- [9. Complete Empirical Findings & All 8 Publication Tables](#9-complete-empirical-findings--all-8-publication-tables)
  - [9.1 Table I: Clean Benchmark Comparison on Held-Out Scenarios](#91-table-i-clean-benchmark-comparison-on-held-out-scenarios)
  - [9.2 Table II: Robustness Evaluation Under 30% Perception Corruption](#92-table-ii-robustness-evaluation-under-30-perception-corruption)
  - [9.3 Table III: Component Architecture Ablations (V1–V5)](#93-table-iii-component-architecture-ablations-v1v5)
  - [9.4 Table IV: Empirical Reliability Breakdown Sweep ($p_{\text{miss}} \in [0.0, 0.50]$)](#94-table-iv-empirical-reliability-breakdown-sweep-p_textmiss-in-00-050)
  - [9.5 Table V: Multi-Intersection 2×2 Network Scalability](#95-table-v-multi-intersection-22-network-scalability)
  - [9.6 Table VI: Edge Hardware Real-Time Latency Profiling](#96-table-vi-edge-hardware-real-time-latency-profiling)
  - [9.7 Table VII: Offline Passive CCTV Shadow-Mode Replay](#97-table-vii-offline-passive-cctv-shadow-mode-replay)
  - [9.8 Table VIII: Computer Vision Quality & Uncertainty Correlation](#98-table-viii-computer-vision-quality--uncertainty-correlation)
- [10. Rigorous Statistical Hypothesis Testing & Failure Science](#10-rigorous-statistical-hypothesis-testing--failure-science)
  - [10.1 Paired Difference Analysis & Normality Tests (Shapiro-Wilk)](#101-paired-difference-analysis--normality-tests-shapiro-wilk)
  - [10.2 Two-Sided Paired Student's $t$-Test & Non-Parametric Wilcoxon Tests](#102-two-sided-paired-students-t-test--non-parametric-wilcoxon-tests)
  - [10.3 Effect Size Analysis (Cohen's $d = 1.92$) & Holm-Bonferroni Correction](#103-effect-size-analysis-cohens-d--192--holm-bonferroni-correction)
  - [10.4 Scientific Honesty on Classical Baseline Competitiveness](#104-scientific-honesty-on-classical-baseline-competitiveness)
- [11. Complete Frontend Research & Digital Twin UI Architecture](#11-complete-frontend-research--digital-twin-ui-architecture)
  - [11.1 Next.js 16 App Router Hierarchy (17 Compiled Routes)](#111-nextjs-16-app-router-hierarchy-17-compiled-routes)
  - [11.2 Single Source of Truth & Zero Frontend Heuristics Audit](#112-single-source-of-truth--zero-frontend-heuristics-audit)
  - [11.3 Zustand Research Store with Bounded Memory Ring Buffer (`MAX_HISTORY = 300`)](#113-zustand-research-store-with-bounded-memory-ring-buffer-max_history--300)
  - [11.4 Explainability Component Suite (Decision Inspector, Q-Values, UQ Radar, FSM)](#114-explainability-component-suite-decision-inspector-q-values-uq-radar-fsm)
  - [11.5 Three.js 3D Research Canvas (Camera FOV Cone, Ghost Oracle Overlays)](#115-threejs-3d-research-canvas-camera-fov-cone-ghost-oracle-overlays)
  - [11.6 Synchronized Paired Comparison under Lockstep CRN](#116-synchronized-paired-comparison-under-lockstep-crn)
  - [11.7 Deterministic Trace Scrubber & Key Event Jump Markers](#117-deterministic-trace-scrubber--key-event-jump-markers)
  - [11.8 Presentation Mode & One-Click Academic Exporters (JSON, CSV, LaTeX)](#118-presentation-mode--one-click-academic-exporters-json-csv-latex)
  - [11.9 Bit-for-Bit Headless/UI Parity Verification Proof](#119-bit-for-bit-headlessui-parity-verification-proof)
- [12. Low-Level Engineering Hardening & Bug Fix History](#12-low-level-engineering-hardening--bug-fix-history)
  - [12.1 Standalone Server Import Resolution (`sys.path` Dynamic Registration)](#121-standalone-server-import-resolution-syspath-dynamic-registration)
  - [12.2 Defensive Controller Parameter Normalization (Dict Unwrapping)](#122-defensive-controller-parameter-normalization-dict-unwrapping)
  - [12.3 `UncertaintyScore` Dataclass Scalar Extraction & Authority Resolution](#123-uncertaintyscore-dataclass-scalar-extraction--authority-resolution)
  - [12.4 Frontend Memory Leak Elimination](#124-frontend-memory-leak-elimination)
  - [12.5 Comprehensive `.gitignore` Overhaul & Path Protection](#125-comprehensive-gitignore-overhaul--path-protection)
  - [12.6 Full Atomic Git Commit History on `feat/research-pov`](#126-full-atomic-git-commit-history-on-feat-research-pov)
- [13. Novelty Kill-Test Audit & Claim-to-Evidence Matrix](#13-novelty-kill-test-audit--claim-to-evidence-matrix)
  - [13.1 10-Paper Systematic Literature Comparison](#131-10-paper-systematic-literature-comparison)
  - [13.2 9 Core Scientific Claims Mapped to Raw Empirical Artifacts](#132-9-core-scientific-claims-mapped-to-raw-empirical-artifacts)
  - [13.3 Superlative Purge & Scholarly Tone Alignment](#133-superlative-purge--scholarly-tone-alignment)
- [14. Full REST & WebSocket API Specifications](#14-full-rest--websocket-api-specifications)
  - [14.1 REST Management Endpoints (`/research/*`, `/api/*`)](#141-rest-management-endpoints-research-api)
  - [14.2 High-Speed 10 Hz Telemetry WebSocket Protocol (`/ws/research`)](#142-high-speed-10-hz-telemetry-websocket-protocol-wsresearch)
  - [14.3 Paired Comparison Dual Telemetry Protocol](#143-paired-comparison-dual-telemetry-protocol)
  - [14.4 Stored Replay Trace Data Schema](#144-stored-replay-trace-data-schema)
- [15. One-Command Clean Reproduction Protocol](#15-one-command-clean-reproduction-protocol)
  - [15.1 Regression Test Suite Execution](#151-regression-test-suite-execution)
  - [15.2 Next.js Production Build Verification](#152-nextjs-production-build-verification)
  - [15.3 Rapid Research Smoke Test (~85s)](#153-rapid-research-smoke-test-85s)
  - [15.4 Full Paper Replication Pipeline (~15 min)](#154-full-paper-replication-pipeline-15-min)
  - [15.5 Live Interactive Demonstration Startup](#155-live-interactive-demonstration-startup)
- [16. Comprehensive Mathematical Formulas, Equations & Algorithmic Index](#16-comprehensive-mathematical-formulas-equations--algorithmic-index)
  - [16.1 Microscopic Kinematics & Traffic Flow Equations](#161-microscopic-kinematics--traffic-flow-equations)
  - [16.2 Computer Vision, Geometry & Fault Injection Formulas](#162-computer-vision-geometry--fault-injection-formulas)
  - [16.3 Deep Reinforcement Learning Equations & Optimization](#163-deep-reinforcement-learning-equations--optimization)
  - [16.4 Perception Uncertainty Estimation & Temperature Calibration](#164-perception-uncertainty-estimation--temperature-calibration)
  - [16.5 Safe Supervisory Fallback, Classical Control & Safety Invariants](#165-safe-supervisory-fallback-classical-control--safety-invariants)
  - [16.6 Statistical Analysis & Hypothesis Testing Equations](#166-statistical-analysis--hypothesis-testing-equations)
- [17. Current Status and Evidence Authority](#17-current-status-and-evidence-authority)
- [18. Current Repository and Research Organization](#18-current-repository-and-research-organization)
- [19. Audited Execution, Sensing and Controller Boundaries](#19-audited-execution-sensing-and-controller-boundaries)
- [20. Current RL Architecture, Observation Versions and Learning Repairs](#20-current-rl-architecture-observation-versions-and-learning-repairs)
- [21. Audited Training and Evaluation History](#21-audited-training-and-evaluation-history)
- [22. Action Labels, Calibration and Future-Arrival Diagnostics](#22-action-labels-calibration-and-future-arrival-diagnostics)
- [23. Upstream Demand, Spatial Pilot and Input-Use Diagnosis](#23-upstream-demand-spatial-pilot-and-input-use-diagnosis)
- [24. Teacher Alignment and Horizon Sensitivity](#24-teacher-alignment-and-horizon-sensitivity)
- [25. Reproducibility, Parent Checkpoints and Experimental Separation](#25-reproducibility-parent-checkpoints-and-experimental-separation)
- [26. Application, API, Storage and Integration Status](#26-application-api-storage-and-integration-status)
- [27. Installation, Operations, Security and Open-Source Conventions](#27-installation-operations-security-and-open-source-conventions)
- [28. Verification and Quality Gates](#28-verification-and-quality-gates)
- [29. Paper Scope, Novelty and Remaining Requirements](#29-paper-scope-novelty-and-remaining-requirements)
- [30. Evidence and Maintenance Index](#30-evidence-and-maintenance-index)

---

<a id="1-system-taxonomy--master-architecture"></a>
## 1. System Taxonomy & Master Architecture

> **2026-10-22 correction:** The architecture below includes conceptual camera/cabinet integration. Audited evidence concerns a custom single-intersection simulator. Physical signal actuation, calibrated traffic geometry and field safety have not been demonstrated.

FlowSync is an end-to-end cyber-physical research and digital twin platform designed to bridge simulated Deep Reinforcement Learning (DRL) with real-world computer vision traffic infrastructure.

<a id="11-full-stack-cyber-physical-system-architecture"></a>
### 1.1 Full-Stack Cyber-Physical System Architecture

The following diagram illustrates the complete hardware-software boundary, networking topology, and process orchestration across the client, backend server, computer vision ingestion engine, and physical traffic signal equipment:

```mermaid
graph TD
    subgraph EdgeSensors["Physical Sensing & Video Ingestion"]
        CCTV["Municipal CCTV (RTSP/HLS/MP4)"] --> StreamRes["StreamResolver (yt-dlp)"]
        StreamRes --> FrameGrab["RealtimeFrameGrabber (POSIX Thread)"]
        FrameGrab --> YOLODet["YOLOv8n Object Detector (PyTorch/TensorRT)"]
        YOLODet --> Tracker["ByteTrack Multi-Object Tracker"]
        Tracker --> ROIMap["Polygonal ROI Homography (d ≤ 0.45)"]
    end

    subgraph ServerBackend["FlowSync FastAPI Backend Engine (Port 8000)"]
        ROIMap --> StateBuild["CameraObservableStateBuilder (14-D Vector)"]
        StateBuild --> UQEngine["PerceptionUncertaintyEstimator (7 Cues + Platt Scaling)"]
        StateBuild --> D3QN["D3QN Policy Inference (Value + Advantage)"]
        
        UQEngine -->|"Uncertainty U(s)"| Sup["Hysteretic Fallback Supervisor"]
        D3QN -->|"Action a_rl"| Sup
        
        MP["Max-Pressure Classical Fallback"] -->|"Action a_mp"| Sup
        
        Sup -->|"Target Action a_target"| Shield["Formal Safety Shield (G_min, G_max, Starvation)"]
        Shield -->|"Shielded Action a_shield"| FSM["PhysicalSignalFSM (Yellow 3s, All-Red 1s)"]
        
        SimEngine["Microscopic Simulator (Euler Kinematics, IDM, Bezier)"] <--> FSM
        
        FSM -->|"10 Hz Telemetry Stream"| WSManager["Research WebSocket Engine (/ws/research)"]
        FSM -->|"REST Endpoints"| RESTRoutes["Research REST Router (/research/*)"]
    end

    subgraph ClientFrontend["Next.js 16 App Router Frontend (Port 3000)"]
        WSManager <-->|"Bi-directional WS (10 Hz)"| SocketHook["useResearchSocket Hook"]
        RESTRoutes <-->|"HTTP GET/POST"| APIClient["Research API Client"]
        
        SocketHook --> ZStore["Zustand Research Store (Ring Buffer = 300)"]
        APIClient --> ZStore
        
        ZStore --> Canvas3D["Three.js 3D Research Canvas (FOV Cone, Ghost Overlays)"]
        ZStore --> DecInspect["Decision Inspector (6-Stage Pipeline)"]
        ZStore --> QPanel["Q-Value & Margin Panel (ΔQ)"]
        ZStore --> UQPanel["Uncertainty Radar & History"]
        ZStore --> FSMPanel["Safety & Clearance Timer Panel"]
        ZStore --> Compare3D["Synchronized Paired CRN Comparison View"]
        ZStore --> ReplayScrub["Deterministic Trace Scrubber & Replay Engine"]
    end

    subgraph PhysicalCabinet["Municipal NEMA TS2 Traffic Cabinet"]
        FSM -.->|"SDLC Bus (153.6 kbps)"| BIU["Bus Interface Unit (BIU)"]
        BIU --> MMU["Malfunction Management Unit (MMU)"]
        MMU --> Heads["Physical Intersection Signal Heads"]
    end
```

<a id="12-dual-plane-architecture-simulation-vs-autonomous-research-plane"></a>
### 1.2 Dual-Plane Architecture: Simulation vs Autonomous Research Plane

FlowSync decouples traffic simulation physics from controller evaluation to guarantee zero scientific bias:
1. **The Digital Twin & Simulation Plane (`server/app/simulation/`):**
   - Implements continuous-time kinematic vehicle updates, IDM car-following equations, collision-free queuing, cubic Bézier turns, yielding logic, and multi-intersection corridor links.
   - Operates behind the single source of truth: simulation memory never leaks directly to controllers.
2. **The Autonomous Research & Control Plane (`server/app/controllers/`):**
   - Bounded strictly by camera field-of-view limits ($d \le 0.45$).
   - Implements the complete unified 7-controller suite (`FixedController`, `GreedyController`, `ActuatedController`, `MaxPressureController`, `DQNController`, `D3QNController`, `FlowSyncUQController`).
   - Governed by the shared hardware-emulating [`PhysicalSignalFSM`](server/app/controllers/physical_fsm.py).

<a id="13-end-to-end-perception-to-control-dataflow-pipeline"></a>
### 1.3 End-to-End Perception-to-Control Dataflow Pipeline

The following flowchart details the sequential transformation from raw video pixels to physical actuation:

```
[ Raw CCTV Video Frame (1920x1080 @ 30 FPS) ]
                     │
                     ▼ Decode & Memory Transfer (4.50 ms)
[ BGR Frame Matrix (640x640 letterbox) ]
                     │
                     ▼ YOLOv8n TensorRT FP16 Inference (52.59 ms)
[ Bounding Boxes B_i = (x, y, w, h), Confidences c_i, Classes cls_i ]
                     │
                     ▼ ByteTrack Multi-Object Tracking (0.14 ms)
[ Persistent Trajectories T_k = { (x_t, y_t), v_t, id_k } ]
                     │
                     ▼ Polygonal Homography & Metric Projection (< 0.01 ms)
[ Lane Approach Assignments & Normalized Distances d_i ∈ [0, 1] ]
                     │
                     ├──────────────────────────────────────────────┐
                     │ Observable Filter (d_i ≤ 0.45)               │ Multi-Feature Extraction
                     ▼                                              ▼
[ Camera State φ_t ∈ ℝ¹⁴ ]                      [ 7-D Uncertainty Vector φ_t^UQ ]
  - Approach Queues (q_N, q_S, q_E, q_W)           - Detector Dispersion (1 - mean c)
  - Approach Speeds (v_N, v_S, v_E, v_W)           - Tail Confidence (1 - min c)
  - Active Phase One-Hot e_p                        - Count Volatility (|ΔN| / N)
  - Phase Elapsed Time τ_t / 60                     - EWMA Forecast Residual
                     │                             - Camera Staleness / Dropped Frames
                     │                             - Track Fragmentation Rate
                     │                                              │
                     │                                              ▼ Platt Scaling (T = 1.2)
                     │                              [ Calibrated Uncertainty U(s_t) ∈ [0, 1] ]
                     │                                              │
                     ▼                                              ▼
     [ D3QN Policy Network ]                       [ Hysteretic Supervisor ]
     - Value V(s) + Advantage A(s)                 - If U(s_t) ≥ 0.65: FALLBACK_ACTIVE
     - Proposed Phase Action a_rl                  - If U(s_t) ≤ 0.50 (10 steps): RL_ACTIVE
                     │                                              │
                     └──────────────────────┬───────────────────────┘
                                            ▼
                           [ Selected Target Phase a_target ]
                                            │
                                            ▼
                           [ Formal Safety Shield Layer ]
                           - Check Minimum Green (τ_t ≥ 8.0s)
                           - Check Maximum Green (τ_t ≤ 60.0s)
                           - Check Starvation Wait (w_l ≤ 45.0s)
                                            │
                                            ▼
                           [ Shielded Phase Action a_shield ]
                                            │
                                            ▼
                           [ Physical Signal State Machine (FSM) ]
                           - If Phase Change: GREEN -> YELLOW (3.0s) -> ALL-RED (1.0s)
                           - Enforce Hardware Clearance Protection
                                            │
                                            ▼
                           [ Physically Executed Signal State a_exec ]
                                            │
                                            ▼
                       [ Traffic Signal Heads / Simulation Actuator ]
```

---

<a id="2-traffic-simulation-core--microscopic-kinematics"></a>
## 2. Traffic Simulation Core & Microscopic Kinematics

> **2026-10-22 correction:** Treat the physical-unit constants, IDM derivation, pedestrian behavior and emergency-handling narrative below as historical design descriptions unless checked against current source. They are not a calibrated microscopic model or validated pedestrian/collision behavior. Current research uses simplified motion and an incident discharge-headway surrogate.

<a id="21-microscopic-car-following-model-idm-like-kinematics"></a>
### 2.1 Microscopic Car-Following Model (IDM-like Kinematics)

FlowSync models vehicle longitudinal dynamics via an enhanced Intelligent Driver Model (IDM) discretized at $\Delta t = 0.1\text{ s}$ ($10\text{ Hz}$).

```mermaid
flowchart LR
    Leader["Lead Vehicle i-1 (x_{i-1}, v_{i-1})"]
    Follower["Following Vehicle i (x_i, v_i)"]
    
    Leader -.->|"Net Gap s_i = x_{i-1} - x_i - L"| Calc["IDM Acceleration Engine"]
    Leader -.->|"Speed Differential Δv_i = v_i - v_{i-1}"| Calc
    Follower -->|"Current Velocity v_i"| Calc
    
    Calc -->|"Desired Gap s*(v, Δv)"| Acc["Compute Acceleration a_i(t)"]
    Acc -->|"Euler Integration"| StateUpdate["Update Position x_i(t+Δt), Velocity v_i(t+Δt)"]
```

#### Longitudinal Acceleration Formula:
$$a_i(t) = a_{\max} \left[ 1 - \left(\frac{v_i(t)}{v_0}\right)^\delta - \left(\frac{s^*(v_i(t), \Delta v_i(t))}{s_i(t)}\right)^2 \right]$$

#### Dynamic Desired Safe Headway Distance $s^*(v, \Delta v)$:
$$s^*(v_i, \Delta v_i) = s_0 + v_i \cdot T_{\text{gap}} + \frac{v_i \cdot \Delta v_i}{2 \sqrt{a_{\max} b}}$$

#### Numerical Parameters & Calibration Limits:
- Free-flow target speed: $v_0 = 13.89\text{ m/s}$ ($50\text{ km/h}$).
- Maximum comfortable acceleration: $a_{\max} = 2.5\text{ m/s}^2$.
- Comfortable deceleration: $b = 3.5\text{ m/s}^2$.
- Emergency deceleration limit: $b_{\text{emergency}} = 7.0\text{ m/s}^2$.
- Minimum standstill distance: $s_0 = 2.0\text{ m}$.
- Safe time headway: $T_{\text{gap}} = 1.2\text{ s}$.
- Vehicle body length: $L_{\text{veh}} = 4.5\text{ m}$.
- Acceleration exponent: $\delta = 4$.

#### Discrete Euler Numerical Integration:
$$v_i(t + \Delta t) = \max\left(0, \min(v_{\max}, v_i(t) + a_i(t) \cdot \Delta t)\right)$$
$$x_i(t + \Delta t) = x_i(t) + v_i(t + \Delta t) \cdot \Delta t$$

---

<a id="22-discrete-intersection-geometry--cubic-bezier-turning-curves"></a>
### 2.2 Discrete Intersection Geometry & Cubic Bézier Turning Curves

Each approach contains 3 distinct movements (Right Turn, Through/Straight, Left Turn), totaling 12 movements across the intersection:

```
                          North Approach
                            │  │  │  ▲
                            │  │  │  │
                            ▼  ▼  ▼  │
               ─────────────┘  │  └──┴─────────────
               East            │     Intersection  East
               Approach ◄──────┤     Box           Exit
               ─────────────┐  │  ┌──┬─────────────
                            ▲  ▲  ▲  │
                            │  │  │  │
                            │  │  │  ▼
                          South Approach
```

When a turning vehicle crosses the stop line ($x_i \ge x_{\text{stop}}$), its trajectory transitions from a 1D lane distance coordinate to a 2D parameterized **Cubic Bézier Curve**:

$$\mathbf{B}(u) = (1-u)^3 \mathbf{P}_0 + 3(1-u)^2 u \mathbf{P}_1 + 3(1-u) u^2 \mathbf{P}_2 + u^3 \mathbf{P}_3, \quad u \in [0, 1]$$

Where the control points guarantee $C^1$ geometric curvature continuity:
- $\mathbf{P}_0$: Exit point of the incoming approach lane at the stop bar.
- $\mathbf{P}_3$: Entry point of the target downstream exit lane.
- $\mathbf{P}_1 = \mathbf{P}_0 + \kappa \cdot \mathbf{t}_{\text{in}}$, where $\mathbf{t}_{\text{in}}$ is the incoming lane tangent vector.
- $\mathbf{P}_2 = \mathbf{P}_3 - \kappa \cdot \mathbf{t}_{\text{out}}$, where $\mathbf{t}_{\text{out}}$ is the outgoing lane tangent vector.
- Tangent scale: $\kappa \approx 0.55 \cdot \|\mathbf{P}_3 - \mathbf{P}_0\|_2$.

Arc-length parameterization advances $u(t)$ proportional to instantaneous vehicle speed $v_i(t)$ divided by the numerical curve arc length $L_{\text{curve}} = \int_0^1 \|\mathbf{B}'(u)\|_2 du$.

---

<a id="23-yield-on-left-rules--gap-acceptance-logic"></a>
### 2.3 Yield-on-Left Rules & Gap Acceptance Logic

In permissive left-turn phases (or turning conflicts), left-turning vehicles must yield to oncoming straight traffic:

```mermaid
flowchart TD
    EnterBox["Vehicle reaches turning staging box (u ≈ 0.35)"] --> ScanOpp["Scan opposing through lane for nearest oncoming vehicle"]
    ScanOpp --> CalcGap["Compute projected time-to-collision: t_arrival = d_opp / v_opp"]
    CalcGap --> EvalGap{"Is t_arrival < t_critical (4.5s)?"}
    
    EvalGap -->|Yes (Unsafe)| Decel["Yield: Apply deceleration b_yield, halt at turning vertex"]
    Decel --> Wait["Wait 0.1s step, re-evaluate"]
    Wait --> ScanOpp
    
    EvalGap -->|No (Safe Gap)| Accelerate["Accept Gap: Accelerate through Cubic Bezier exit path"]
    Accelerate --> ClearBox["Clear intersection box into downstream exit lane"]
```

---

<a id="24-pedestrian-crosswalk-modeling--conflict-arbitration"></a>
### 2.4 Pedestrian Crosswalk Modeling & Conflict Arbitration

Crosswalks span each intersection approach:
- Pedestrian arrivals follow an independent Poisson process with intensity $\lambda_{\text{ped}} \in [0.02, 0.10]\text{ ped/s}$.
- Crossing velocity is drawn from normal distribution $v_{\text{ped}} \sim \mathcal{N}(1.34\text{ m/s}, 0.25^2)$.
- **Conflict Arbitration:** Right-turning and permissive left-turning vehicles detect pedestrians within active crosswalk corridors ($y \in [-W_{\text{walk}}/2, W_{\text{walk}}/2]$). If a pedestrian is present within $10\text{ m}$ of the vehicle path, the vehicle decelerates to standstill, holding until the pedestrian clears the crossing corridor plus a $2.0\text{ s}$ safety buffer.

---

<a id="25-emergency-vehicle-preemption-evp-engine"></a>
### 2.5 Emergency Vehicle Preemption (EVP) Engine

Emergency vehicles (ambulances, fire engines) bypass standard queuing:
- Spawned with `is_emergency = True`, sirens active, and elevated desired velocity $v_0 = 20.0\text{ m/s}$ ($72\text{ km/h}$).
- Normal vehicles detect an approaching emergency vehicle from behind ($d \le 30\text{ m}$) and pull over / yield into adjacent lanes.
- When an EVP vehicle reaches distance $d \le 150\text{ m}$ to the stop line, the controller receives a preemption request:
  - If the active phase serves the EVP movement, maximum green is automatically extended.
  - If the active phase conflicts, the system executes an expedited yellow ($3.0\text{s}$) and all-red ($1.0\text{s}$) clearance sequence, forcing the green phase to the emergency approach until the emergency vehicle clears the junction.

---

<a id="3-computer-vision--real-world-digital-twin-pipeline"></a>
## 3. Computer Vision & Real-World Digital Twin Pipeline

> **2026-10-22 correction:** Camera code is under `server/app/realworld/`, rather than the historical `server/app/cv/` paths. Stream, detector, tracking and ROI tooling exists. Bounded latency, uninterrupted streams, real-camera accuracy and the claimed annotated CCTV dataset have not been established by audited work. Synthetic sensing is not recorded-camera validation.

<a id="31-streamresolver-yt-dlp--anti-bot-po-token-challenge-solving"></a>
### 3.1 StreamResolver: yt-dlp & Anti-Bot PO-Token Challenge Solving
Implemented in `server/app/cv/stream_resolver.py` (historical path; absent from the current tree):
- Supports RTSP feeds, HTTP HLS streams, local MP4/MKV video files, and YouTube Live municipal traffic cams.
- Uses `yt-dlp` with automated PO-token (Proof of Origin) resolution and client impersonation (`--extractor-args "youtube:player_client=web,android"`) to prevent bot challenge blocks on continuous 24/7 public traffic feeds.

---

<a id="32-realtimeframegrabber-zero-latency-socket-buffer-flushing"></a>
### 3.2 RealtimeFrameGrabber: Zero-Latency Socket Buffer Flushing

Standard OpenCV `cv2.VideoCapture` queues incoming video packets in an internal OS socket buffer. When processing latency exceeds the camera frame rate, reading from `cv2.VideoCapture` yields stale frames delayed by several seconds.

Implemented in `server/app/cv/frame_grabber.py` (historical path; absent from the current tree):
- Spawns a dedicated POSIX background thread running at native camera FPS.
- Continuously executes `grab()` calls, keeping only the single newest frame in a thread-safe atomic pointer.
- Stale intermediate frames are discarded instantly, guaranteeing that observation staleness is bounded:
  $$\Delta t_{\text{frame}} \le \frac{1}{\text{FPS}_{\text{cam}}} \approx 33\text{ ms}$$

```mermaid
sequenceDiagram
    autonumber
    participant RTSP as CCTV Camera RTSP Feed
    participant OSBuf as OS Socket Buffer
    participant GrabThread as RealtimeFrameGrabber Thread
    participant AtomicPtr as Atomic Frame Pointer
    participant Consumer as YOLOv8 Inference Consumer

    loop Continuous Capture
        RTSP->>OSBuf: Incoming H.264 Frame Packets
        GrabThread->>OSBuf: Read & Decode Frame
        GrabThread->>AtomicPtr: Atomic Swap (Overwrite Latest Frame)
        Note over GrabThread,AtomicPtr: Stale queued frames instantly dropped
    end

    Consumer->>AtomicPtr: Get Current Frame
    AtomicPtr-->>Consumer: Return Latest Decoded Frame (Staleness ≤ 33ms)
    Consumer->>Consumer: Run YOLOv8 + ByteTrack Detection
```

---

<a id="33-yolov8n-object-detection--bytetrack-association"></a>
### 3.3 YOLOv8n Object Detection & ByteTrack Association
- **Detector:** Ultralytics YOLOv8n (nano variant, 3.2M parameters) optimized for edge deployment. Detects vehicles in COCO classes: `car (2)`, `motorcycle (3)`, `bus (5)`, `truck (7)`.
- **Tracker:** ByteTrack algorithm. Associates detections across frames by evaluating both high-confidence and low-confidence bounding boxes against Kalman filter trajectory forecasts, eliminating track dropouts during temporary vehicle occlusion behind buses or streetlights.

---

<a id="34-polygonal-region-of-interest-roi--perspective-homography"></a>
### 3.4 Polygonal Region-of-Interest (ROI) & Perspective Homography
Implemented in `server/app/cv/roi_manager.py` (historical path; absent from the current tree):
- Operators define 4-point convex polygons defining the physical approach lanes in pixel space:
  $$\mathcal{P}_{\text{pixel}} = \{ (u_1, v_1), (u_2, v_2), (u_3, v_3), (u_4, v_4) \}$$
- A perspective transformation matrix $\mathbf{H} \in \mathbb{R}^{3 \times 3}$ maps pixel coordinates $(u, v)$ to top-down metric ground plane coordinates $(X, Y)$:
  $$\begin{bmatrix} X' \\ Y' \\ W' \end{bmatrix} = \mathbf{H} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}, \quad X = \frac{X'}{W'}, \quad Y = \frac{Y'}{W'}$$
- Vehicles are assigned to specific incoming approaches (North, South, East, West) via point-in-polygon containment testing.

---

<a id="35-real-time-camera-fov-bounding-d-le-045--oracle-isolation-proof"></a>
### 3.5 Real-Time Camera FOV Bounding ($d \le 0.45$) & Oracle Isolation Proof

To eliminate simulation data leakage, observations are restricted to the camera field of view:
- The maximum lane length is $L_{\text{lane}} = 150\text{ m}$.
- The camera optical boundary covers only the approach segment within normalized distance $d_i = \frac{x_i}{L_{\text{lane}}} \le 0.45$ ($67.5\text{ m}$ from the stop line).
- Any vehicle with $d_i > 0.45$ is physically invisible to camera-based policies.
- Formally verified via [`server/tests/test_oracle_isolation.py`](server/tests/test_oracle_isolation.py): querying the controller state confirms that vehicles in the arrival buffer ($d > 0.45$) produce zero change in the observation vector.

```
Approach Lane (150m)
[ Spawner Buffer ] ───► [ Invisible Zone: d > 0.45 ] ───► [ Camera FOV: d ≤ 0.45 ] ───► [ Stop Line ]
     (x = 0m)                 (x = 10m to 82.5m)               (x = 82.5m to 150m)          (x = 150m)
     Zero Data                Simulation Memory                YOLOv8 + ByteTrack           Signal Head
     Leakage                  Blocked to Policy                Only Source of State
```

---

<a id="4-deep-reinforcement-learning-mechanics--formulations"></a>
## 4. Deep Reinforcement Learning Mechanics & Formulations

> **2026-10-22 correction:** The audited policies use versioned 28/36/48/64-input encodings, a 256→256 backbone with 128-unit dueling heads, and masked advantage centering. The phase mapping, normalization, architecture diagram, replay paths and target-update narrative below contain legacy descriptions. Research v5 fixes switch charging and completed macro-action replay. Section 20 gives the current contracts; the 14-input camera description is not the later audited policy input.

<a id="41-semi-markov-decision-process-semi-mdp-framework"></a>
### 4.1 Semi-Markov Decision Process (Semi-MDP) Framework

Because traffic signal phase transitions require non-zero physical clearance intervals (yellow + all-red clearance: $3\text{s} + 1\text{s} = 4\text{s}$), the environment cannot transition instantaneously at every 0.1s step. We formulate the control problem as an infinite-horizon Semi-MDP defined by the tuple $\langle \mathcal{S}, \mathcal{O}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$:
- Decisions are made at variable time intervals $\tau \ge 1$;
- The discount factor $\gamma = 0.99$ discounts rewards over cumulative elapsed steps.

---

<a id="42-state-space-representations-simulation-28-d-vs-camera-observable-14-d"></a>
### 4.2 State Space Representations: Simulation (28-D) vs Camera-Observable (14-D)

#### The Simulation State Space ($s_t \in \mathbb{R}^{28}$)
1. **Movement Queue Lengths (Dims 0–11):** 12 normalized movement queue counts $q_m / K_{\max}$ ($K_{\max} = 25\text{ veh}$).
2. **Signal Context Features (Dims 12–15):** Active phase duration $\tau / 60$, minimum green satisfaction flag, total network stopped vehicles, total network mean speed.
3. **Active Phase One-Hot (Dims 16–19):** One-hot representation of active phase $\mathbf{e}_p \in \{0, 1\}^4$.
4. **Online EWMA Demand Forecasts (Dims 20–27):** 8 approach arrival rate forecasts $\hat{\lambda}_l$.

#### The Camera-Observable State Space ($\phi_t \in \mathbb{R}^{14}$)
Used in all FlowSync-UQ experiments, strictly isolated from simulation memory:
$$\phi_t = \left[ \frac{q_N}{K_{\max}}, \frac{q_S}{K_{\max}}, \frac{q_E}{K_{\max}}, \frac{q_W}{K_{\max}}, \frac{v_N}{V_{\max}}, \frac{v_S}{V_{\max}}, \frac{v_E}{V_{\max}}, \frac{v_W}{V_{\max}}, \mathbf{e}_{p_t}, \frac{\min(\tau_t, 60)}{60} \right] \in \mathbb{R}^{14}$$

---

<a id="43-discrete-action-space--phase-encoding"></a>
### 4.3 Discrete Action Space & Phase Encoding

The action space consists of 4 discrete signal phase configurations ($\mathcal{A} = \{0, 1, 2, 3\}$):

| Action Index ($a$) | Phase Name | Active Green Movements | Non-Conflicting Permissive |
| :---: | :---: | :---: | :---: |
| **0** | `NS_S` | North Straight & South Straight | North Right, South Right |
| **1** | `NS_L` | North Left & South Left (Protected) | North Right, South Right |
| **2** | `EW_S` | East Straight & West Straight | East Right, West Right |
| **3** | `EW_L` | East Left & West Left (Protected) | East Right, West Right |

---

<a id="44-delay-anchored-max-pressure-multi-factor-reward-function"></a>
### 4.4 Delay-Anchored Max-Pressure Multi-Factor Reward Function

$$r_t = - \sum_{l \in \text{in}} \left( d_{l, t} + \alpha \cdot q_{l, t} \right) - \beta \cdot \mathbf{1}_{\text{switch}} - \lambda_{\text{starv}} \sum_{l} \max(0, w_{l, t} - W_{\max})$$
where:
- $d_{l, t} = \sum_{i \in l} \frac{v_0 - v_i}{v_0}$ is normalized instantaneous delay;
- $q_{l, t}$ is total stopped vehicles in lane $l$ ($v_i < 0.1\text{ m/s}$);
- $\mathbf{1}_{\text{switch}} = \mathbb{I}(a_t \ne a_{t-1})$ penalizes unnecessary phase switching ($\beta = 0.5$);
- $w_{l, t}$ is the maximum waiting time of any vehicle currently queued on approach $l$;
- $W_{\max} = 45.0\text{ s}$ is the starvation threshold;
- $\lambda_{\text{starv}} = 2.0$ applies heavy linear penalty scaling when any lane experiences starvation.

---

<a id="45-dueling-double-deep-q-network-d3qn-architecture"></a>
### 4.5 Dueling Double Deep Q-Network (D3QN) Architecture

```mermaid
graph TD
    In["State Input s_t ∈ ℝ¹⁴"] --> L1["Linear(14, 128) + ReLU"]
    L1 --> L2["Linear(128, 128) + ReLU"]
    
    L2 --> VStream["Linear(128, 64) + ReLU"]
    L2 --> AStream["Linear(128, 64) + ReLU"]
    
    VStream --> VOut["Value Head: Linear(64, 1) → V(s) ∈ ℝ"]
    AStream --> AOut["Advantage Head: Linear(64, 4) → A(s, a) ∈ ℝ⁴"]
    
    VOut --> Dueling["Dueling Combination: Q(s, a) = V(s) + [ A(s, a) - mean(A) ]"]
    AOut --> Dueling
    
    Dueling --> QValues["Action Values Q(s, ·) ∈ ℝ⁴"]
```

Mathematically, the Q-values are reconstructed via the mean-subtraction identifiable formulation:
$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

---

<a id="46-target-q-formulation-with-demand-action-masking"></a>
### 4.6 Target Q Formulation with Demand Action Masking

$$Y_t^{\text{DoubleQ}} = r_t + \gamma Q\left(s_{t+1}, \arg\max_{a' \in \mathcal{M}(s_{t+1})} Q(s_{t+1}, a'; \theta_t); \theta_t^-\right)$$
where $\mathcal{M}(s) \subseteq \mathcal{A}$ is the active demand mask, forbidding the selection of phases where all corresponding approach lanes have zero queued vehicles, unless all phases are idle.

---

<a id="47-prioritized-experience-replay-per-with-binary-sumtree"></a>
### 4.7 Prioritized Experience Replay (PER with Binary SumTree)
Implemented in `server/app/simulation/per_buffer.py` (historical path; absent from the current tree):
- Replaces uniform transition sampling with prioritization based on temporal difference (TD) error:
  $$p_i = \left( |\delta_i| + \epsilon \right)^\alpha$$
  where $\delta_i = Y_i - Q(s_i, a_i; \theta)$, $\epsilon = 10^{-5}$, and prioritization exponent $\alpha = 0.6$.
- Stored inside a **Binary SumTree** data structure:
  - Total capacity: $N = 100,000$ transitions;
  - Sampling complexity: $O(\log N)$ (traversing the tree by cumulative priority segments);
  - Update complexity: $O(\log N)$ per transition.
- Unbiased gradient estimation via Importance Sampling (IS) weights:
  $$w_i = \left( \frac{1}{N} \cdot \frac{1}{P(i)} \right)^\beta, \quad P(i) = \frac{p_i}{\sum_k p_k}$$
  where $\beta$ anneals linearly from $\beta_0 = 0.4$ to $1.0$ across training episodes.

---

<a id="48-online-short-horizon-ewma-demand-forecasting"></a>
### 4.8 Online Short-Horizon EWMA Demand Forecasting
Implemented in `server/app/simulation/forecaster.py` (historical path; absent from the current tree):
$$\hat{\lambda}_{l, t} = \alpha_{\text{EWMA}} \cdot \lambda_{l, t}^{\text{inst}} + (1 - \alpha_{\text{EWMA}}) \cdot \hat{\lambda}_{l, t-1}$$
where $\alpha_{\text{EWMA}} = 0.15$ and $\lambda_{l, t}^{\text{inst}} = N_{\text{arrivals}, l, \Delta t} / \Delta t$.

---

<a id="5-flowsync-uq-uncertainty-fallback-safety-shield--physical-fsm"></a>
## 5. FlowSync-UQ: Uncertainty, Fallback, Safety Shield & Physical FSM

> **2026-10-22 correction:** Calibration concerns synthetic count error, not the probability that fallback improves control. Reliable added UQ benefit is unestablished. The additional shield and shared physical FSM are separate layers; phase-service timers are not individual vehicle waits. Max-Pressure theory does not certify this finite, noisy simulator or field safety. The temperature, CCTV and superiority claims below are not current validated findings.

<a id="51-the-policy-hallucination-problem-in-vision-based-traffic-drl"></a>
### 5.1 The Policy Hallucination Problem in Vision-Based Traffic DRL

When standard DRL policies are deployed on real-world camera feeds, perception corruptions induce catastrophic policy collapse:
1. **False Negatives ($p_{\text{miss}} \in [0.1, 0.4]$):** Occluded vehicles disappear from the state vector. The DRL policy misinterprets a heavily congested lane as empty, terminating its green phase prematurely and starving unserved traffic.
2. **False Positives (Phantom Vehicles):** Roadway glare and shadows trigger phantom vehicle detections. The DRL policy switches green to an empty road, wasting phase capacity.
3. **Phase Chattering:** High-frequency perception noise causes rapid fluctuations in the argmax Q-value, causing the agent to attempt phase switches every step, inducing perpetual clearance states.

---

<a id="52-multi-feature-perception-uncertainty-engine-phi_t-in-mathbbr7"></a>
### 5.2 Multi-Feature Perception Uncertainty Engine ($\phi_t \in \mathbb{R}^7$)
Implemented in [`research/uncertainty/estimator.py`](research/uncertainty/estimator.py):
FlowSync-UQ computes a 7-dimensional uncertainty feature vector $\phi_t \in \mathbb{R}^7$:

1. **Mean Detector Uncertainty ($\phi_1$):**
   $$\phi_1 = 1.0 - \frac{1}{|D_t|} \sum_{i \in D_t} c_i$$
2. **Lower-Tail Detector Uncertainty ($\phi_2$):**
   $$\phi_2 = 1.0 - \min_{i \in D_t} c_i$$
3. **Count Volatility ($\phi_3$):**
   $$\phi_3 = \min\left(1.0, \frac{|N_t - N_{t-1}|}{\max(1, N_{t-1})}\right)$$
4. **Forecast Innovation Residual ($\phi_4$):**
   $$\phi_4 = \min\left(1.0, \frac{\|q_t - \hat{q}_{t|t-1}\|_2}{\max(1, \|q_t\|_2)}\right)$$
5. **Observation Staleness / Latency ($\phi_5$):**
   $$\phi_5 = \min\left(1.0, \frac{\Delta t_{\text{cam}}}{0.50}\right)$$
6. **Dropped Frame Penalty ($\phi_6$):**
   $$\phi_6 = \begin{cases} 1.0 & \text{if frame decode fails or is dropped} \\ 0.0 & \text{otherwise} \end{cases}$$
7. **Track Fragmentation Rate ($\phi_7$):**
   $$\phi_7 = \frac{N_{\text{new\_ids}, t}}{N_{\text{active\_tracks}, t}}$$

---

<a id="53-platt-temperature-scaling-calibration-t--12"></a>
### 5.3 Platt Temperature Scaling Calibration ($T = 1.2$)

$$U_{\text{raw}}(s_t) = \mathbf{w}^T \phi_t + b$$
$$U(s_t) = \sigma\left(\frac{U_{\text{raw}}(s_t)}{T}\right) = \frac{1}{1 + \exp\left(-\frac{U_{\text{raw}}(s_t)}{T}\right)} \in [0.0, 1.0]$$
The calibration temperature $T = 1.2$ was empirically fitted against 1,000 ground-truth annotated CCTV video frames, achieving **$r = 0.742$ ($p < 0.001$)** correlation with true vehicle count error.

---

<a id="54-hysteretic-fallback-supervisor-tau_texthigh-tau_textlow-k_textdwell-k_textrecover"></a>
### 5.4 Hysteretic Fallback Supervisor ($\tau_{\text{high}}, \tau_{\text{low}}, K_{\text{dwell}}, K_{\text{recover}}$)

Implemented in [`server/app/controllers/supervisor.py`](server/app/controllers/supervisor.py):

```mermaid
stateDiagram-v2
    [*] --> RL_ACTIVE: System Boot (U < 0.65)
    
    RL_ACTIVE --> FALLBACK_ACTIVE: Trigger Condition: U(s_t) ≥ τ_high (0.65)
    
    state FALLBACK_ACTIVE {
        [*] --> DWELL_LOCKED: Reset dwell_counter = 0
        DWELL_LOCKED --> RECOVERY_MONITORING: dwell_counter ≥ K_dwell (30 steps / 3.0s)
        RECOVERY_MONITORING --> DWELL_LOCKED: U(s_t) > τ_low (0.50) (Reset recover_counter = 0)
        RECOVERY_MONITORING --> RECOVERY_MONITORING: U(s_t) ≤ τ_low (0.50) (recover_counter++)
    }
    
    FALLBACK_ACTIVE --> RL_ACTIVE: Authority Restored: recover_counter ≥ K_recover (10 steps / 1.0s)
```

- **Degradation Trigger:** If $U(s_t) \ge \tau_{\text{high}} = 0.65 \implies$ Control authority is instantly transferred to Max-Pressure.
- **Mandatory Dwell Time:** Once in fallback, authority is locked for a minimum dwell period of $K_{\text{dwell}} = 30\text{ steps}$ ($3.0\text{ s}$).
- **Hysteresis Recovery Band:** Control returns to D3QN only when uncertainty drops below:
  $$U(s_t) \le \tau_{\text{low}} = 0.50$$
  and remains below $\tau_{\text{low}}$ for $K_{\text{recover}} = 10\text{ consecutive steps}$ ($1.0\text{ s}$).

---

<a id="55-provably-stable-classical-max-pressure-fallback"></a>
### 5.5 Provably Stable Classical Max-Pressure Fallback
Implemented in [`server/app/controllers/max_pressure.py`](server/app/controllers/max_pressure.py):
$$P(p) = \sum_{l \in \text{in}(p)} x_l - \sum_{m \in \text{out}(p)} x_m$$
The controller selects the phase maximizing pressure:
$$p^* = \arg\max_{p \in \mathcal{A}} P(p)$$
Under stationary arrival rates within the network capacity region, Max-Pressure is mathematically proven to stabilize all queues without requiring any machine learning or neural inference.

---

<a id="56-formal-safety-shield-layer-hard-clearance--starvation-invariants"></a>
### 5.6 Formal Safety Shield Layer (Hard Clearance & Starvation Invariants)
Implemented in [`server/app/controllers/safety_shield.py`](server/app/controllers/safety_shield.py):
1. **Minimum Green Time Invariant ($G_{\min} = 8.0\text{ s}$):** If the active phase duration $\tau_t < G_{\min}$, proposed switch actions are intercepted and converted to phase hold actions.
2. **Maximum Green Time Invariant ($G_{\max} = 60.0\text{ s}$):** If $\tau_t \ge G_{\max}$, the shield forces a phase termination to prevent arterial starvation.
3. **Anti-Starvation Preemption ($W_{\max} = 45.0\text{ s}$):** If the maximum waiting time on any unserved approach exceeds $W_{\max}$, the shield preempts the controller and forces green allocation to the starving approach.
4. **Clearance Phase Action Masking:** Actions attempting to select conflicting red movements during active yellow or all-red intervals are strictly masked.

---

<a id="57-shared-hardware-emulating-physical-signal-state-machine-physicalsignalfsm"></a>
### 5.7 Shared Hardware-Emulating Physical Signal State Machine (`PhysicalSignalFSM`)

Implemented in [`server/app/controllers/physical_fsm.py`](server/app/controllers/physical_fsm.py):

```mermaid
stateDiagram-v2
    [*] --> GREEN: System Initialized in Phase 0
    
    GREEN --> GREEN: Continue Phase (g_p < G_min or Target == Current)
    GREEN --> YELLOW: Target Phase Changed & g_p ≥ G_min (Start Yellow: 3.0s)
    
    YELLOW --> YELLOW: Yellow Clearance Interval Active (t_yellow < 3.0s)
    YELLOW --> ALL_RED: Yellow Expired (Start All-Red: 1.0s)
    
    ALL_RED --> ALL_RED: All-Red Intersection Clearance (t_red < 1.0s)
    ALL_RED --> GREEN: Clearance Complete (Activate New Green Phase)
    
    note right of YELLOW
        Any immediate switch attempt from Green to Green
        is intercepted, logged as proposed_violation,
        and yellow clearance is enforced.
    end note
```

- **Proposed Violation:** If a policy attempts to transition instantly from one green phase to another without respecting clearance, the FSM logs a `proposed_violation` counter.
- **Physical Execution:** The FSM blocks the premature transition and enforces the mandatory 4.0-second yellow/all-red clearance interval before activating the target phase.
- Across 20 frozen seeds and 20,000 stress steps, **executed clearance violations are identically 0 across all controllers**, while FlowSync-UQ achieves an **18.8% reduction in attempted illegal switches (65 vs 80)**.

---

<a id="6-unified-7-controller-suite--operational-logic"></a>
## 6. Unified 7-Controller Suite & Operational Logic

> **2026-10-22 correction:** The interface sketch and capabilities table below are historical summaries. Current `ControllerContext` carries delivered movement/outgoing counts, masks, phase-service timers and extra telemetry. A controller name does not prove compatible trained weights were loaded. Plain DQN is omitted from audited comparisons unless supplied its own compatible checkpoint. Fixed timing serves the implemented phase schedule and depends on configuration.

<a id="61-basecontroller-contract--context-schema"></a>
### 6.1 `BaseController` Contract & Context Schema

Implemented in [`server/app/controllers/base.py`](server/app/controllers/base.py):

```python
@dataclass
class ControllerContext:
    time_in_phase: float
    current_phase: int
    queue_lengths: Dict[str, int]
    waiting_times: Dict[str, float]
    yellow_active: bool = False
    all_red_active: bool = False
    total_vehicles: int = 0
    mean_speed: float = 0.0

class BaseController(ABC):
    @abstractmethod
    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        """Computes and returns the next discrete phase action a in {0, 1, 2, 3}."""
        pass

    def get_action(self, observation: np.ndarray, context: ControllerContext) -> int:
        return self.act(observation, context)
```

---

<a id="62-classical-controllers-fixed-time-greedy-actuated-max-pressure"></a>
### 6.2 Classical Controllers: Fixed-Time, Greedy, Actuated, Max-Pressure
1. **`FixedController` (`fixed`):** Executes Webster's fixed-time cycle plan. Alternates cyclic progression: 30s Phase 0 (`NS_S`) $\rightarrow$ 30s Phase 2 (`EW_S`). Completely blind to vehicle arrivals.
2. **`GreedyController` (`greedy`):** Evaluates instantaneous approach queue counts and selects the phase with the largest total number of stopped vehicles. Highly responsive to isolated bursts, but prone to starving low-volume lanes.
3. **`ActuatedController` (`actuated`):** Standard municipal vehicle-actuated logic. Holds green as long as vehicle passage gaps remain below $T_{\text{gap}} = 3.0\text{ s}$, up to a maximum green ceiling of $45.0\text{ s}$. Highly vulnerable to detector dropouts (premature gap-out).
4. **`MaxPressureController` (`max_pressure`):** Classical distributed backpressure algorithm (Varaiya, 2013). Computes incoming minus outgoing lane occupancies.

---

<a id="63-learning-controllers-dqn-d3qn"></a>
### 6.3 Learning Controllers: DQN, D3QN
1. **`DQNController` (`dqn`):** Standard Nature DQN (Mnih et al., 2015). Multi-layer perceptron (128-128-4) without dueling streams. Suffers from overestimation bias and high degradation under perception noise.
2. **`D3QNController` (`d3qn`):** Dueling Double Deep Q-Network with action masking. Separates state value $V(s)$ from advantage $A(s, a)$. Demonstrates superior policy value separation, but hallucinates when subjected to sensor dropouts without supervisory shielding.

---

<a id="64-hybrid-safe-controller-flowsync-uq"></a>
### 6.4 Hybrid Safe Controller: FlowSync-UQ
**`FlowSyncUQController` (`flowsync_uq`):** The complete composite architecture combining:
- D3QN nominal policy
- 7-feature uncertainty estimation engine
- Hysteretic supervisor
- Max-Pressure fallback
- Safety Shield invariant filter
- Shared Physical Signal FSM

---

<a id="65-algorithmic-capabilities-matrix"></a>
### 6.5 Algorithmic Capabilities Matrix

| Controller Key | Class Name | State Dependency | Fallback Capable? | Safety Shielded? | Clearance FSM Gated? | Edge Latency |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `fixed` | `FixedController` | Time only | No | No | Yes | 0.001 ms |
| `greedy` | `GreedyController` | Queue counts | No | No | Yes | 0.005 ms |
| `actuated` | `ActuatedController` | Gap timers | No | No | Yes | 0.008 ms |
| `max_pressure` | `MaxPressureController` | Pressure diff | N/A (Is Fallback) | No | Yes | 0.014 ms |
| `dqn` | `DQNController` | 14-D Camera state | No | No | Yes | 0.180 ms |
| `d3qn` | `D3QNController` | 14-D Camera state | No | No | Yes | 0.225 ms |
| `flowsync_uq` | `FlowSyncUQController` | 14-D State + UQ | **Yes (Max-Pressure)** | **Yes (Shield)** | **Yes (FSM)** | **0.426 ms** |

---

<a id="7-multi-intersection-22-city-grid-network"></a>
## 7. Multi-Intersection 2×2 City Grid Network

> **2026-10-22 correction:** The city/application modules are separate from the audited single-intersection research panels. Their presence and the old city table do not establish validated network coordination, spillback suppression or a transferable learned-control advantage.

<a id="71-grid-topology--8-boundary-demand-portals"></a>
### 7.1 Grid Topology & 8 Boundary Demand Portals

Implemented in `server/app/simulation/grid_network.py` (historical path; absent from the current tree):

```
                   P_N0                      P_N1
                    │                         │
                    ▼                         ▼
             ┌──────────────┐          ┌──────────────┐
    P_W0 ───►│ Junction 0,0 │◄────────►│ Junction 0,1 │───► P_E0
             └──────┬───────┘          └──────┬───────┘
                    ▲                         ▲
                    │     Arterial Corridors  │
                    ▼     (200m Length)       ▼
             ┌──────────────┐          ┌──────────────┐
    P_W1 ───►│ Junction 1,0 │◄────────►│ Junction 1,1 │───► P_E1
             └──────┬───────┘          └──────┬───────┘
                    ▲                         ▲
                    │                         │
                   P_S0                      P_S1
```

---

<a id="72-arterial-road-transfer--multi-hop-journey-schedules"></a>
### 7.2 Arterial Road Transfer & Multi-Hop Journey Schedules
Vehicles are spawned at boundary portals with pre-assigned origin-destination itineraries:
- Straight corridor journeys traversing 2 intersections (e.g. $P_{W0} \rightarrow J_{00} \rightarrow J_{01} \rightarrow P_{E0}$).
- Turning arterial journeys (e.g. $P_{N0} \rightarrow J_{00} \rightarrow J_{10} \rightarrow P_{S0}$).
When vehicle $i$ exits the boundary of junction $J_{00}$, its ownership is transferred to the arterial corridor link queue connecting to $J_{01}$, where vehicle kinematics continue seamlessly.

---

<a id="73-decentralized-shared-policy-coordination--spillback-suppression"></a>
### 7.3 Decentralized Shared-Policy Coordination & Spillback Suppression
Each intersection executes an independent instance of `FlowSyncUQController` sharing policy weights:
- **Arterial Spillback Danger:** In multi-intersection grids, if intersection $J_{00}$ fails due to sensor corruption, vehicle queues spill backward across the $200\text{ m}$ arterial link, blocking the cross-street progression at $J_{01}$.
- **Spillback Suppression Finding (Table V):** FlowSync-UQ's local fallback clears the arterial bottleneck autonomously, preserving green wave synchronization and maintaining full grid throughput ($1,053\text{ veh/h}$) under 30% perception corruption.

---

<a id="8-frozen-experimental-infrastructure--scenario-suite"></a>
## 8. Frozen Experimental Infrastructure & Scenario Suite

> **2026-10-22 correction:** Scenario, seed and fault definitions are experiment-specific. The short example hashes and old seed list below do not replace executed configuration/checkpoint hashes. The current injector has 13 presets. No real municipal CCTV calibration dataset was supplied for these audited experiments.

<a id="81-16-canonical-frozen-scenarios-with-sha-256-fingerprints"></a>
### 8.1 16 Canonical Frozen Scenarios with SHA-256 Fingerprints

Defined in [`research/scenarios/manifest.json`](research/scenarios/manifest.json):

| Scenario ID | Split | Target Flow (veh/h) | Turning Ratio (L/T/R) | Primary Scientific Evaluation Goal | SHA-256 Fingerprint |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `train_low_balanced_01` | Train | 600 | 0.15 / 0.70 / 0.15 | Low-density nominal baseline policy convergence | `9f3c1a8e...` |
| `train_med_arterial_01` | Train | 1,200 | 0.10 / 0.80 / 0.10 | Arterial directional dominance training | `4d2e8b7c...` |
| `train_high_peak_01` | Train | 1,800 | 0.20 / 0.60 / 0.20 | Near-capacity queue clearing dynamics | `7a1f5c3d...` |
| `train_asym_east_01` | Train | 1,400 | 0.25 / 0.50 / 0.25 | Asymmetric directional surge accommodation | `3b8d9e2a...` |
| `train_burst_rush_01` | Train | 2,100 | 0.15 / 0.70 / 0.15 | Non-stationary arrival shockwave reaction | `6c4a1e9f...` |
| `train_heavy_turning_01`| Train | 1,500 | 0.40 / 0.30 / 0.30 | Left-turn pocket spillback and yielding | `8e2b7d4c...` |
| `val_balanced_mid_01` | Val | 1,000 | 0.20 / 0.60 / 0.20 | Hyperparameter tuning and temperature fitting | `1d9c4f8a...` |
| `val_surge_north_01` | Val | 1,600 | 0.15 / 0.70 / 0.15 | Fallback threshold calibration ($\tau = 0.65$) | `5f7a2b9e...` |
| `test_clean_balanced_01`| **Test** | 1,200 | 0.20 / 0.60 / 0.20 | **Table I Clean held-out benchmark evaluation** | `2c8e1a7d...` |
| `test_heavy_peak_01` | **Test** | 1,900 | 0.25 / 0.50 / 0.25 | **Table II Noise robustness stress testing** | `9a3f6c2e...` |
| `test_arterial_burst_01`| **Test** | 2,200 | 0.10 / 0.80 / 0.10 | **Table III Component architecture ablations** | `4b1d7e9a...` |
| `test_complex_turns_01` | **Test** | 1,600 | 0.35 / 0.35 / 0.30 | **Table IV Breakdown boundary evaluation** | `7e5c2a8f...` |
| `ood_extreme_gridlock_01`| OOD | 2,600 | 0.30 / 0.40 / 0.30 | Over-saturated gridlock recovery testing | `8f1a4d7b...` |
| `ood_directional_surge_01`| OOD| 2,000 | 0.05 / 0.90 / 0.05 | Sudden directional platoon pulse injection | `3c9e6a2d...` |
| `ood_sensor_degraded_01`| OOD | 1,500 | 0.20 / 0.60 / 0.20 | Severe multi-sensor compound dropout stress | `6a8d1f4c...` |
| `ood_midnight_sparse_01`| OOD | 250 | 0.20 / 0.60 / 0.20 | Actuated gap-out and minimum green idling | `2d4f8b9e...` |

---

<a id="82-20-seed-common-random-numbers-crn-protocol"></a>
### 8.2 20-Seed Common Random Numbers (CRN) Protocol
All 7 controllers are evaluated across **20 pre-registered random seeds**:
$$\mathcal{S}_{\text{eval}} = \{1101, 1102, 1103, \dots, 1120\}$$
Every vehicle generation time, arrival lane, speed, and turning choice is generated identically across compared policies using lockstep Poisson spawner schedules.

---

<a id="83-6-perception-fault-injection-profiles"></a>
### 8.3 6 Perception Fault Injection Profiles
Implemented in [`research/noise/fault_injector.py`](research/noise/fault_injector.py):
1. `clean`: Zero noise baseline.
2. `miss_10`, `miss_30`, `miss_50`: Bernoulli vehicle detection dropout ($p_{\text{miss}} \in \{0.10, 0.30, 0.50\}$).
3. `false_positive_clutter`: Poisson phantom vehicle injection ($\lambda = 0.5\text{ veh/step}$).
4. `spatial_jitter`: Gaussian vehicle position corruption $\mathcal{N}(0, \sigma^2 = 2.5\text{ m})$.
5. `tracking_fragmentation`: Random track ID turnover ($p_{\text{switch}} = 0.15$ per step).
6. `latency_delay`: Observation ring buffer injecting 2-to-5 step ($200\text{--}500\text{ ms}$) observation staleness.

---

<a id="84-municipal-cctv-calibration-dataset-1000-annotated-frames"></a>
### 8.4 Municipal CCTV Calibration Dataset (1,000 Annotated Frames)
FlowSync's uncertainty engine was calibrated against **1,000 manually annotated real CCTV video frames** across three real-world camera deployments:
- `intersection_cam_01`: Urban 4-way intersection under standard daylight.
- `corridor_junction_north`: Arterial junction during morning commute glare.
- `arterial_east_cam`: High-density commercial corridor during dusk rainfall.

---

<a id="9-complete-empirical-findings--all-8-publication-tables"></a>
## 9. Complete Empirical Findings & All 8 Publication Tables

> **2026-10-22 correction:** **Historical tables, not current publication evidence.** All eight tables and their interpretations below are preserved from the earlier reference. The original 2,040-run headless evaluation used randomly initialized learned policies; its performance conclusions are invalid. Later audits do not validate these old hardware, CCTV, city, ablation or significance claims. Do not cite these values as audited findings or pool them with corrected panels. Section 21 supplies the strongest audited frozen reference; sections 22–24 record later development results.

All data below reflects raw, reproducible runs from `results/final/` across 20 frozen seeds under Common Random Numbers (CRN).

<a id="91-table-i-clean-benchmark-comparison-on-held-out-scenarios"></a>
### 9.1 Table I: Clean Benchmark Comparison on Held-Out Scenarios (20 Seeds, CRN)
*Source: [`results/final/table_benchmark_comparison_v2.tex`](results/final/table_benchmark_comparison_v2.tex)*

| Controller | Mean Delay (s) | 95% Confidence Interval | P95 Delay (s) | Max Queue (veh) | Throughput (veh/h) | Starvation Events |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fixed-Time** | 15.61 | [15.28, 15.95] | 17.8 | 34.6 | 2,455.2 | **0** |
| **Actuated** | 15.51 | [14.97, 16.06] | 19.4 | 35.9 | 2,476.2 | 351 |
| **Greedy** | **12.55** | [12.20, 12.89] | **14.9** | **31.7** | **2,518.2** | 235 |
| **Max-Pressure** | 12.73 | [12.35, 13.10] | 15.2 | 32.2 | 2,502.6 | 227 |
| **DQN** | 17.79 | [17.03, 18.58] | 24.1 | 39.2 | 2,427.0 | 350 |
| **D3QN** | 16.50 | [15.79, 17.23] | 22.6 | 37.9 | 2,462.7 | 350 |
| **FlowSync-UQ (Ours)** | 16.36 | [15.75, 16.99] | 21.2 | 37.5 | 2,461.5 | 343 |

*Scientific Interpretation:* Under clean, stationary traffic, Varaiya's Max-Pressure (12.73s) and Greedy (12.55s) achieve lower mean delay than Deep RL methods because they directly optimize exact queue differentials without value-function approximation error. FlowSync-UQ matches clean D3QN efficiency (16.36s vs 16.50s) while reducing P95 tail delay (21.2s vs 22.6s).

---

<a id="92-table-ii-robustness-evaluation-under-30-perception-corruption"></a>
### 9.2 Table II: Robustness Evaluation Under 30% Perception Corruption (20 Seeds, CRN, Shared Physical FSM)
*Source: [`results/final/table_noise_robustness_v2.tex`](results/final/table_noise_robustness_v2.tex)*

| Controller | Clean Delay (s) | Corrupted Delay (s) | Relative Degradation (%) | P95 Delay (s) | Starvations | Proposed Violations | Executed Violations |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fixed-Time** | 15.12 | 15.12 | +0.0% | 17.3 | **0** | **0** | **0** |
| **Actuated** | 13.53 | 13.53 | +0.0% | 16.8 | 77 | 44 | **0** |
| **Max-Pressure** | 11.30 | 11.30 | +0.0% | 12.9 | 57 | 52 | **0** |
| **DQN** | 16.10 | 15.87 | -1.5% | 20.1 | 76 | 68 | **0** |
| **D3QN (Unshielded)** | 14.76 | 14.94 | +1.2% | 19.4 | 78 | 80 | **0** |
| **FlowSync-UQ (Ours)** | 14.65 | **14.67** | **+0.2%** | **18.8** | 77 | **65** | **0** |

*Core Scientific Finding:* FlowSync-UQ restricts delay degradation to **+0.2%** ($p = 1.48 \times 10^{-6}$, Cohen's $d = 1.92$). Furthermore, FlowSync-UQ reduces premature phase switch attempts from 80 to 65 (**-18.8% reduction**), significantly reducing wear on physical cabinet switch packs. The shared Physical FSM enforces **0 executed clearance violations** across all models.

---

<a id="93-table-iii-component-architecture-ablations-v1v5"></a>
### 9.3 Table III: Component Architecture Ablations (V1–V5, 20 Seeds, CRN)
*Source: [`results/final/table_ablations_v2.tex`](results/final/table_ablations_v2.tex)*

| Variant Index | Architecture Variant | Mean Delay (s) | 95% Confidence Interval | P95 Delay (s) | Starvations | Proposed Violations | Executed Violations |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **V1** | **Full FlowSync-UQ** | **15.08** | [14.24, 15.94] | **18.5** | **64** | **54** | **0** |
| **V2** | No-UQ / Blind D3QN | 12.43 | [11.64, 13.25] | 16.2 | 78 | 68 | **0** |
| **V3** | No-Shield | 15.04 | [14.29, 15.77] | 17.1 | 66 | 61 | **0** |
| **V4** | No-Fallback / Shield Only | 18.23 | [17.35, 19.13] | 21.7 | 82 | 75 | **0** |
| **V5** | Fixed-Time Fallback | 16.59 | [15.61, 17.52] | 18.8 | 62 | 52 | **0** |

*Critical Insight:* **Shielding alone without fallback is disastrous.** Variant V4 (Shield-Only) inflates delay by **+20.9%** (18.23s vs 15.08s) with 82 starvations. When the DRL agent hallucinates, it repeatedly attempts invalid phase switches; the shield overrides these attempts, freezing the signal on the current phase and causing gridlock. Dynamic fallback to Max-Pressure is mandatory to clear queues.

---

<a id="94-table-iv-empirical-reliability-breakdown-sweep-p_textmiss-in-00-050"></a>
### 9.4 Table IV: Empirical Reliability Breakdown Sweep ($p_{\text{miss}} \in [0.0, 0.50]$)
*Source: [`results/final/table_reliability_boundary_v2.tex`](results/final/table_reliability_boundary_v2.tex)*

| Miss Rate ($p_{\text{miss}}$) | Fixed-Time Delay (s) | Fixed $P(\text{Fail})$ | Max-Pressure Delay (s) | MP $P(\text{Fail})$ | D3QN Delay (s) | D3QN $P(\text{Fail})$ | FlowSync-UQ Delay (s) | FlowSync-UQ $P(\text{Fail})$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.00** | 15.12 | 0.50 | 11.30 | 0.40 | 15.30 | 0.85 | 15.24 | 0.85 |
| **0.05** | 15.12 | 0.50 | 11.30 | 0.40 | 15.50 | 0.85 | 15.43 | 0.85 |
| **0.10** | 15.12 | 0.50 | 11.30 | 0.40 | 15.42 | 0.85 | 15.37 | 0.85 |
| **0.15** | 15.12 | 0.50 | 11.30 | 0.40 | 15.52 | 0.85 | 15.46 | 0.85 |
| **0.20** | 15.12 | 0.50 | 11.30 | 0.40 | 15.14 | 0.85 | 15.10 | 0.85 |
| **0.25** | 15.12 | 0.50 | 11.30 | 0.40 | 15.35 | 0.85 | 15.24 | 0.85 |
| **0.30** | 15.12 | 0.50 | 11.30 | 0.40 | 15.38 | 0.85 | **15.28** | 0.85 |
| **0.35** | 15.12 | 0.50 | 11.30 | 0.40 | 15.35 | 0.85 | **15.24** | 0.85 |
| **0.40** | 15.12 | 0.50 | 11.30 | 0.40 | 15.33 | 0.85 | **15.16** | 0.85 |
| **0.45** | 15.12 | 0.50 | 11.30 | 0.40 | 15.28 | 0.85 | **15.19** | 0.85 |
| **0.50** | 15.12 | 0.50 | 11.30 | 0.40 | 15.37 | 0.85 | **15.36** | 0.85 |

*Key Finding:* Beyond $p_{\text{miss}} \ge 0.45$, adaptive control degrades toward fixed-time levels due to severe sensory starvation. This identifies the theoretical boundary where all adaptive algorithms collapse and fixed fail-safe flashing must take over.

---

<a id="95-table-v-multi-intersection-22-network-scalability"></a>
### 9.5 Table V: Multi-Intersection 2×2 Network Scalability (20 Seeds, CRN)
*Source: [`results/final/table_city_2x2_scalability_v2.tex`](results/final/table_city_2x2_scalability_v2.tex)*

| Controller | Clean Delay (s) | Clean P95 (s) | Clean Queue (veh) | Clean Flow (veh/h) | Corrupted Delay (s) | Corrupted P95 (s) | Corrupted Queue (veh) | Corrupted Flow (veh/h) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fixed-Time** | 12.52 | 43.7 | 9.8 | 1,053 | 12.57 | 43.7 | 9.8 | 1,050 |
| **Max-Pressure** | 12.57 | 43.7 | 9.8 | 1,050 | 12.57 | 43.7 | 9.8 | 1,050 |
| **D3QN** | 12.52 | 43.7 | 9.8 | 1,053 | 12.52 | 43.7 | 9.8 | 1,053 |
| **FlowSync-UQ (Ours)** | **12.52** | 43.7 | 9.8 | 1,053 | **12.52** | 43.7 | 9.8 | **1,053** |

*Finding:* Multi-agent local fallback preserves corridor synchronization without inducing queue spillback across adjacent arterial links.

---

<a id="96-table-vi-edge-hardware-real-time-latency-profiling"></a>
### 9.6 Table VI: Edge Hardware Real-Time Latency Profiling (1,000 Frames)

> **Evidence correction:** Jetson/Raspberry Pi timings and detector-plus-controller CPU latency in this historical table have not been established by hardware tests in the audited work. CPU Torch research execution does not validate edge-device latency.
*Source: [`results/final/table_latency_profile_full.tex`](results/final/table_latency_profile_full.tex)*

| Pipeline Stage | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | Loop Share (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frame Acquisition & Decode** | 4.50 | 4.40 | 5.18 | 5.68 | 5.78 | 7.8% |
| **YOLOv8n Object Detection** | 52.59 | 49.06 | 59.17 | 159.18 | 201.23 | 89.3% |
| **ByteTrack Multi-Object Tracking** | 0.14 | 0.14 | 0.16 | 0.22 | 0.36 | 0.2% |
| **ROI Lane & Quadrant Mapping** | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | < 0.1% |
| *Subtotal Perception Pipeline* | *57.23* | *53.64* | *64.81* | *163.97* | *206.07* | *97.3%* |
| **Camera State Normalization** | 0.009 | 0.009 | 0.009 | 0.011 | 0.043 | < 0.1% |
| **Uncertainty Feature Extraction** | 0.168 | 0.162 | 0.173 | 0.186 | 5.238 | 0.3% |
| **D3QN Policy Inference** | 0.225 | 0.218 | 0.240 | 0.421 | 1.578 | 0.4% |
| **Max-Pressure Fallback Calculation** | 0.014 | 0.013 | 0.015 | 0.018 | 0.036 | < 0.1% |
| **Hysteretic Supervisor State** | 0.002 | 0.002 | 0.002 | 0.003 | 0.018 | < 0.1% |
| **SafetyShield & Physical FSM** | 0.009 | 0.009 | 0.011 | 0.014 | 0.026 | < 0.1% |
| *Subtotal Control Pipeline* | **0.426** | **0.413** | **0.446** | **0.623** | **6.109** | **0.7%** |
| **Total Perception-to-Control** | **57.66** | **54.05** | **65.26** | **164.43** | **206.51** | **100.0%** |

*Target Edge Devices:*
- **Nvidia Jetson Orin Nano (TensorRT FP16):** Perception $\approx 14.2\text{ ms}$, Controller $\approx 0.15\text{ ms} \implies$ **Total $19.5\text{ ms}$ (~51 FPS)**. Real-time production ready.
- **Nvidia Jetson Xavier NX (15W):** Total latency $\approx 27.4\text{ ms}$ (~36 FPS).
- **Raspberry Pi 5 (NCNN/INT8):** Total latency $\approx 92.0\text{ ms}$ (~10.8 FPS). Fits 10 Hz control loop.

---

<a id="97-table-vii-offline-passive-cctv-shadow-mode-replay"></a>
### 9.7 Table VII: Offline Passive CCTV Shadow-Mode Replay (3,600 Frames)

> **Evidence correction:** The claimed 3,600-frame municipal replay is not supported by supplied recorded footage or measured traffic in audited research. This is historical material, not an executed camera-validation result.
*Source: [`results/final/table_shadow_replay_v2.tex`](results/final/table_shadow_replay_v2.tex)*

| Controller | Session 1: Midday Daylight | Session 2: Morning Glare | Session 3: Dusk Wet Rain |
| :--- | :---: | :---: | :---: |
| **Fixed-Time** | 13.61s (1,020 veh/h) | 14.84s (1,170 veh/h) | 7.96s (1,170 veh/h) |
| **Greedy** | 4.97s (1,080 veh/h) | 7.71s (1,140 veh/h) | 7.16s (1,530 veh/h) |
| **Max-Pressure** | **4.97s** (1,080 veh/h) | **6.06s** (1,140 veh/h) | **5.57s** (1,530 veh/h) |
| **D3QN** | 7.57s (1,020 veh/h) | 10.53s (840 veh/h) | 18.69s (1,530 veh/h) |
| **FlowSync-UQ (Ours)** | 20.75s (1,080 veh/h) | 17.00s (840 veh/h) | 19.99s (1,530 veh/h) |

*Observation:* Evaluates passive policy execution without live actuation interference, confirming continuous control stability across lighting shifts and rain-slicked road surfaces.

---

<a id="98-table-viii-computer-vision-quality--uncertainty-correlation"></a>
### 9.8 Table VIII: Computer Vision Quality & Uncertainty Correlation (1,000 Frames)

> **Evidence correction:** The precision, recall and correlation values below are not audited real-camera findings. Synthetic count-error calibration cannot establish these dataset claims or useful fallback benefit.
*Source: [`results/final/table_cv_perception_validation.tex`](results/final/table_cv_perception_validation.tex)*

| Environmental Regime | Precision | Recall | Count MAE (veh) | Lane Acc. (%) | IDF1 Tracking | Mean Uncertainty $\bar{U}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Low-Density Daylight** | 0.943 | 0.928 | 0.32 | 96.8% | 0.911 | 0.137 |
| **Dense Commute Peak** | 0.893 | 0.864 | 0.87 | 92.4% | 0.844 | 0.389 |
| **Heavy Occlusion (Buses/Trucks)** | 0.843 | 0.781 | 1.45 | 86.5% | 0.765 | 0.626 |
| **Adverse Rain & Low-Light** | 0.813 | 0.750 | 1.72 | 84.1% | 0.719 | 0.713 |
| **Overall Dataset Mean** | **0.873** | **0.831** | **1.09** | **89.9%** | **0.809** | **0.467** |

*Calibration Proof:* The Pearson correlation between estimated uncertainty $U(s_t)$ and ground-truth count error is **$r = 0.742$ ($p < 0.001$)**, rising to **$r = 0.793$** during adverse rain, confirming that $U(s_t)$ acts as a faithful proxy for real-world vision degradation.

---

<a id="10-rigorous-statistical-hypothesis-testing--failure-science"></a>
## 10. Rigorous Statistical Hypothesis Testing & Failure Science

> **2026-10-22 correction:** The old p-values and effect sizes below cannot establish current policy superiority. Failure to reject a Shapiro–Wilk test does not prove normality. The strongest audited matched-shield delay interval spans zero, as does the UQ increment; neither superiority nor equivalence is established. Gates, futures and frames are not independent traffic or training replicates.

<a id="101-paired-difference-analysis--normality-tests-shapiro-wilk"></a>
### 10.1 Paired Difference Analysis & Normality Tests (Shapiro-Wilk)
Implemented in [`research/analysis/statistical_pipeline.py`](research/analysis/statistical_pipeline.py):
- Paired differences $\Delta_i = \text{Delay}_{\text{D3QN}, i} - \text{Delay}_{\text{FlowSync-UQ}, i}$ were tested for normality across 20 seeds under CRN.
- Shapiro-Wilk test result: $W = 0.932, p = 0.182$. Since $p > 0.05$, the normality assumption is statistically satisfied.

---

<a id="102-two-sided-paired-students-t-test--non-parametric-wilcoxon-tests"></a>
### 10.2 Two-Sided Paired Student's $t$-Test & Non-Parametric Wilcoxon Tests

| Comparison | Condition | Mean Diff (s) | $t$-statistic | $p$-value | Wilcoxon $W$ | Wilcoxon $p$-value | Significant? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **FlowSync-UQ vs D3QN** | Corrupted ($p=0.30$) | -0.27s | -6.84 | $1.48 \times 10^{-6}$ | 0.0 | $1.91 \times 10^{-6}$ | **YES** ($p < 0.001$) |
| **FlowSync-UQ vs Fixed** | Corrupted ($p=0.30$) | -0.45s | -3.89 | $9.8 \times 10^{-4}$ | 12.0 | $1.15 \times 10^{-3}$ | **YES** ($p < 0.01$) |
| **FlowSync-UQ vs Max-Pressure** | Nominal (Clean) | +3.63s | +13.62 | $< 10^{-10}$ | 210.0 | $< 10^{-9}$ | **YES** (Baseline win reported) |

---

<a id="103-effect-size-analysis-cohens-d--192--holm-bonferroni-correction"></a>
### 10.3 Effect Size Analysis (Cohen's $d = 1.92$) & Holm-Bonferroni Correction
- Cohen's $d = \frac{\bar{\Delta}}{s_{\Delta}} = \mathbf{1.92}$, establishing a **Very Large Effect Size** ($d > 0.8$).
- Family-wise error rate across all pairwise comparisons was controlled via the Holm-Bonferroni step-down procedure. The superiority of FlowSync-UQ over unshielded D3QN remains significant ($p_{\text{adj}} < 0.001$).

---

<a id="104-scientific-honesty-on-classical-baseline-competitiveness"></a>
### 10.4 Scientific Honesty on Classical Baseline Competitiveness
FlowSync-UQ transparently reports that classical Max-Pressure achieves lower mean delay under clean, stationary traffic (12.73s vs 16.36s). FlowSync-UQ's definitive contribution is **preventing tail-risk degradation, chattering, and starvation when perception degrades**, rather than claiming artificial superiority over classical math on clean inputs.

---

<a id="11-complete-frontend-research--digital-twin-ui-architecture"></a>
## 11. Complete Frontend Research & Digital Twin UI Architecture

> **2026-10-22 correction:** Components and builds do not prove complete research/UI equivalence. The website trainer retains reward/replay/version differences; storage, training and camera flows still require end-to-end verification. Existing parity tests cover their fixtures, not every sensing/checkpoint/database/live-session path. See section 26.

<a id="111-nextjs-16-app-router-hierarchy-17-compiled-routes"></a>
### 11.1 Next.js 16 App Router Hierarchy (17 Compiled Routes)

The frontend is built on Next.js 16 (React 19, Turbopack, Tailwind CSS):

```
client/src/
 ├── app/
 │   ├── layout.tsx                 # Root Layout with Theme & Global Navigation
 │   ├── page.tsx                   # Interactive 3D Simulation Landing & Sandbox
 │   ├── research/
 │   │   ├── page.tsx               # Publication Dashboard (Table I–VIII Metrics)
 │   │   ├── experiment/page.tsx    # Single Controller Live Workbench
 │   │   ├── compare/page.tsx       # Synchronized Paired CRN Comparison View
 │   │   ├── replay/page.tsx        # Deterministic Replay Engine with Event Scrubbing
 │   │   └── runs/[id]/page.tsx     # Deep-Link Run Inspector & Provenance Viewer
 │   ├── simulation/page.tsx        # Interactive Fullscreen Simulation View
 │   ├── intersections/page.tsx     # Multi-Intersection Network Manager
 │   ├── cctv/page.tsx              # Live CCTV Ingestion & Polygonal ROI Editor
 │   ├── dashboard/page.tsx         # Operational Traffic Management Dashboard
 │   ├── analytics/page.tsx         # Historical Analytics & HCM LOS Charts
 │   └── training/page.tsx          # Real-Time D3QN Training & Loss Curves
```

---

<a id="112-single-source-of-truth--zero-frontend-heuristics-audit"></a>
### 11.2 Single Source of Truth & Zero Frontend Heuristics Audit
Completed Phase F0 audit documented in `docs/frontend/research_ui_audit.md` (historical path; absent from the current tree):
- **Removed Client Heuristics:** Eliminated per-render client vehicle loops in `IntersectionScene.tsx` and synthetic confidence math in `QValuePanel.tsx`.
- **Strict Backend Authority:** The UI never computes scientific metrics (delay, throughput, queue area, uncertainty, winner labels) independently. All data binds directly to the backend schema in [`client/src/types/research.ts`](client/src/types/research.ts).

---

<a id="113-zustand-research-store-with-bounded-memory-ring-buffer-max_history--300"></a>
### 11.3 Zustand Research Store with Bounded Memory Ring Buffer (`MAX_HISTORY = 300`)
Implemented in [`client/src/store/researchStore.ts`](client/src/store/researchStore.ts):
```typescript
const MAX_HISTORY = 300;

export const useResearchStore = create<ResearchStore>((set) => ({
  history: [],
  appendFrame: (frame) =>
    set((state) => ({
      history: [...state.history.slice(-(MAX_HISTORY - 1)), frame],
      currentFrame: frame,
    })),
}));
```
Prevents browser memory exhaustion during long-running 10 Hz streaming sessions.

---

<a id="114-explainability-component-suite-decision-inspector-q-values-uq-radar-fsm"></a>
### 11.4 Explainability Component Suite (Decision Inspector, Q-Values, UQ Radar, FSM)

The explainability components provide complete transparency into the 6-stage decision pipeline:

```mermaid
flowchart LR
    Stage1["1. D3QN Proposed\nAction a_rl"] --> Stage2["2. Fallback Proposed\nAction a_mp"]
    Stage2 --> Stage3["3. Supervisor Mode\nRL vs Fallback"]
    Stage3 --> Stage4["4. Safety Shield Filter\nG_min / Starvation"]
    Stage4 --> Stage5["5. Physical FSM Gating\nYellow / All-Red"]
    Stage5 --> Stage6["6. Physically Executed\nSignal Phase a_exec"]
```

- **[`DecisionInspector.tsx`](client/src/components/research/DecisionInspector.tsx):** Visualizes each condition and override in the 6 decision stages above.
- **[`QValuePanel.tsx`](client/src/components/research/QValuePanel.tsx):** Displays raw Q-values for all 4 actions, masked actions, and the true action value margin:
  $$\Delta Q = Q(s, a_{(1)}) - Q(s, a_{(2)})$$
- **[`UncertaintyPanel.tsx`](client/src/components/research/UncertaintyPanel.tsx):** Displays composite $U(s_t)$, dual threshold lines ($\tau_{\text{high}}=0.65, \tau_{\text{low}}=0.50$), 60-step historical sparkline, and feature contribution radar.
- **[`SafetyFSMPanel.tsx`](client/src/components/research/SafetyFSMPanel.tsx):** Clearance countdowns ($G_{\min}=8\text{s}, Y=3\text{s}, R=1\text{s}$), gating status, and authoritative violation counters (attempted vs executed = 0).

---

<a id="115-threejs-3d-research-canvas-camera-fov-cone-ghost-oracle-overlays"></a>
### 11.5 Three.js 3D Research Canvas (Camera FOV Cone, Ghost Oracle Overlays)
Implemented in [`Research3DScene.tsx`](client/src/components/research/Research3DScene.tsx):
- **Camera FOV Projection Cone:** Amber translucent projection frustum showing the $d \le 0.45$ camera boundary.
- **Ghost Oracle Vehicle Overlays:**
  - *Missed Detections (False Negatives):* Rendered as translucent red wireframe boxes.
  - *Phantom Detections (False Positives):* Rendered as translucent yellow wireframe boxes.
- **Quality Presets:** Toggleable between "Research Performance" (disables heavy post-processing bloom, limits DPR to 1.0 for dense paired scenes) and "High Quality".

---

<a id="116-synchronized-paired-comparison-under-lockstep-crn"></a>
### 11.6 Synchronized Paired Comparison under Lockstep CRN
Implemented in [`ControllerComparison.tsx`](client/src/components/research/ControllerComparison.tsx) at `/research/compare`:
- Dual side-by-side 3D viewports executing Controller A vs Controller B under **identical vehicle arrival schedules**.
- Synchronized play, pause, step, and speed controls.
- **Unbiased Delta Matrix:** Computes $\Delta \text{Delay} = \text{Delay}_B - \text{Delay}_A$, $\Delta \text{Queue Area}$, $\Delta \text{Throughput}$. Honest reporting: baseline wins are rendered cleanly without promotional bias.

---

<a id="117-deterministic-trace-scrubber--key-event-jump-markers"></a>
### 11.7 Deterministic Trace Scrubber & Key Event Jump Markers
Implemented in [`ReplayTimeline.tsx`](client/src/components/research/ReplayTimeline.tsx):
- Bidirectional scrubbing across stored 3,600-step telemetry frames without re-running physics simulation.
- **Event Jump Markers:** Instant navigation to key research moments:
  - *Fallback Activation Window* ($U(s_t) \ge 0.65$)
  - *Peak Uncertainty Spike*
  - *Max Queue Congestion Event*
  - *Anti-Starvation Preemption Event*

---

<a id="118-presentation-mode--one-click-academic-exporters-json-csv-latex"></a>
### 11.8 Presentation Mode & One-Click Academic Exporters (JSON, CSV, LaTeX)
- **`ResearchPresentationMode.tsx`:** High-contrast, large-typography fullscreen layout for thesis defenses, conference talks, and faculty reviews.
- **`ResearchExportModal.tsx`:** Direct one-click export of experiment telemetry to:
  1. Complete Reproducibility JSON Bundle
  2. Telemetry Time-Series CSV
  3. Formatted Publication-Ready LaTeX Table snippet

---

<a id="119-bit-for-bit-headlessui-parity-verification-proof"></a>
### 11.9 Bit-for-Bit Headless/UI Parity Verification Proof
Verified via [`server/tests/test_frontend_headless_parity.py`](server/tests/test_frontend_headless_parity.py):
- Runs identical frozen scenarios and seeds through both the headless benchmark harness and the UI WebSocket session runner.
- **Results:**
  - `test_ui_headless_clean_parity`: **PASSED** (0 numerical difference in arrivals, actions, phases, and delay $\le 10^{-5}$).
  - `test_ui_headless_corrupted_parity`: **PASSED** (Identical fallback switching timesteps and safety interventions under 30% Bernoulli corruption).

---

<a id="12-low-level-engineering-hardening--bug-fix-history"></a>
## 12. Low-Level Engineering Hardening & Bug Fix History

> **2026-10-22 correction:** The commit list and test totals below describe an earlier branch snapshot. Later engine/replay repairs, diagnostics, organization, dependency fixes and CI are recorded in sections 18–28. This is not the current branch or complete Git history.

<a id="121-standalone-server-import-resolution-syspath-dynamic-registration"></a>
### 12.1 Standalone Server Import Resolution (`sys.path` Dynamic Registration)
- **Defect:** Running `uv run uvicorn app.main:app` directly from `server/` caused `sys.path[0]` to point to `server/`, triggering `ModuleNotFoundError: No module named 'server'` when resolving root `research.*` packages.
- **Permanent Fix:** Added dynamic root path registration at the top of [`server/app/main.py`](server/app/main.py):
  ```python
  _SERVER_DIR = Path(__file__).resolve().parent.parent
  _PROJECT_ROOT = _SERVER_DIR.parent
  for _p in [str(_PROJECT_ROOT), str(_SERVER_DIR)]:
      if _p not in sys.path:
          sys.path.insert(0, _p)
  ```
  Converted internal controller imports to relative imports (`..controllers`).

---

<a id="122-defensive-controller-parameter-normalization-dict-unwrapping"></a>
### 12.2 Defensive Controller Parameter Normalization (Dict Unwrapping)
- **Defect:** Frontend Zustand store passed `activeController` as an object `{ id: "flowsync_uq", name: "FlowSync-UQ" }`. Controller registry called `name.lower().strip()`, throwing `AttributeError: 'dict' object has no attribute 'lower'`.
- **Permanent Fix:** Hardened [`server/app/controllers/__init__.py`](server/app/controllers/__init__.py):
  ```python
  if isinstance(name, dict):
      name = name.get("id") or name.get("name") or "flowsync_uq"
  key = str(name).lower().strip()
  ```
  Added defensive normalization in `run_single`, `run_paired`, and `useResearchSocket.ts`.

---

<a id="123-uncertaintyscore-dataclass-scalar-extraction--authority-resolution"></a>
### 12.3 `UncertaintyScore` Dataclass Scalar Extraction & Authority Resolution
- **Defect:** In `run_paired` (`research_ws.py`), telemetry builder called `round(ctrl_b._last_uncertainty, 3)`. For `FlowSyncUQController`, `_last_uncertainty` is an instance of `UncertaintyScore`, throwing `TypeError: type UncertaintyScore doesn't define __round__ method`. Fallback detection queried `supervisor.mode` instead of `supervisor.authority`.
- **Permanent Fix:** In [`server/app/websockets/research_ws.py`](server/app/websockets/research_ws.py):
  ```python
  u_val = 0.0
  if hasattr(ctrl_b, "_last_uncertainty") and ctrl_b._last_uncertainty is not None:
      u_obj = ctrl_b._last_uncertainty
      u_val = float(u_obj.score if hasattr(u_obj, "score") else u_obj)

  is_fb_b = False
  if hasattr(ctrl_b, "supervisor") and ctrl_b.supervisor:
      auth = getattr(ctrl_b.supervisor, "authority", None)
      is_fb_b = getattr(auth, "value", str(auth)) == "fallback_active"
  ```

---

<a id="124-frontend-memory-leak-elimination"></a>
### 12.4 Frontend Memory Leak Elimination
- **Defect:** Unbounded appending to Zustand telemetry history arrays caused browser memory footprint to expand past 1.5 GB after 15 minutes of 10 Hz streaming.
- **Permanent Fix:** Added strict 300-point ring buffer slicing (`slice(-(MAX_HISTORY - 1))`) in `researchStore.ts`.

---

<a id="125-comprehensive-gitignore-overhaul--path-protection"></a>
### 12.5 Comprehensive `.gitignore` Overhaul & Path Protection
- **Fixed Unanchored `runs/` Rule:** Root `.gitignore` had an unanchored `runs/` entry, accidentally ignoring the Next.js page `client/src/app/research/runs/[id]/page.tsx`. Replaced with `/runs/` and `/server/runs/`, and added `!client/src/app/research/runs/**`.
- **Preserved Research Plans:** Changed `plans/` to `plans/*` and `!plans/*.md`, restoring version tracking for research markdown plans while ignoring binary scratch PDFs.
- **Ignored Session Data:** Cleanly ignored `data/sessions/`, `data/sessions_archive/`, and CV caches (`detector_cache/`, `tracker_cache/`).
- **Client Auto-Generated Files:** Added `next-env.d.ts`, `package-lock.json`, and `.expo/` to `client/.gitignore` (historical path; absent from the current tree).

---

<a id="126-full-atomic-git-commit-history-on-feat-research-pov"></a>
### 12.6 Full Atomic Git Commit History on `feat/research-pov`

#### Server Commits (10 Atomic Commits Pushed to `origin feat/research-pov`):
1. `2a72011`: `feat(server): add decision step properties and PlainDQN ablation baseline`
2. `cf80fac`: `feat(server): define BaseController interface, context, and registry`
3. `867d031`: `feat(server): add classical baseline controllers (Fixed, Greedy, Actuated, Max-Pressure)`
4. `22a7e8d`: `feat(server): add DQN and D3QN learning-based inference controllers`
5. `77f43b4`: `feat(server): add PhysicalSignalFSM clearance gating and SafetyShield invariants`
6. `200480a`: `feat(server): add ControllerSupervisor and FlowSyncUQController composite engine`
7. `7277120`: `feat(server): add research REST router for scenarios, controllers, and benchmarks`
8. `ecd5d42`: `feat(server): add 10Hz research WebSocket streaming engine and mount endpoints`
9. `aa723e6`: `test(server): add comprehensive test suite for parity, fairness, FSM, and FlowSync-UQ`
10. `72e5bbd`: `chore(server): update .gitignore for session data, runtime caches, and model weights`

#### Client Commits (6 Atomic Commits Pushed to `origin feat/research-pov`):
1. `0493528`: `feat(client): add research state store, contracts, and WebSocket hook`
2. `0aff781`: `refactor(client): remove redundant client calculations and add Research Mode navigation`
3. `3edab68`: `feat(client): implement explainability suite for UQ, FSM, Safety Shield, and Q-values`
4. `0d6eba7`: `feat(client): add research 3D scene, comparison view, replay, and presentation components`
5. `4db25da`: `feat(client): add Next.js research dashboard, experiment, compare, and replay pages`
6. `d3dfc3a`: `chore(client): update .gitignore for next-env.d.ts, lockfiles, and expo cache`

---

<a id="13-novelty-kill-test-audit--claim-to-evidence-matrix"></a>
## 13. Novelty Kill-Test Audit & Claim-to-Evidence Matrix

> **2026-10-22 correction:** The old first/unified novelty assertion, claimed systematic review, reviewer-feedback narrative and CONFIRMED statuses below are not accepted current conclusions. Audits invalidate or leave unverified their performance, camera, hardware and novelty claims. The current claim matrix in section 17 and novelty limitations in section 29 supersede this historical matrix.

<a id="131-10-paper-systematic-literature-comparison"></a>
### 13.1 10-Paper Systematic Literature Comparison
Documented in `docs/research/05_novelty_kill_test.md` (historical path; absent from the current tree):

| Candidate Paper | Literature Mechanism | Why FlowSync-UQ Remains Distinct |
| :--- | :--- | :--- |
| **Chen & Wang (IEEE T-ITS 2024)** | Anomaly detection against cyber spoofing; reverts to Webster fixed-time. | Focuses on cyber attacks rather than vision noise; fallback is non-adaptive fixed-time; lacks continuous multi-cue uncertainty. |
| **Sartoretti et al. (IEEE RA-L 2024)** | Ensemble variance in SAC mobile robot path planning triggering safe stop. | Continuous-action navigation; cannot handle discrete cyclic signal phase transitions; lacks Max-Pressure integration. |
| **Zhou et al. (IEEE T-IV 2025)** | Camera-observable state representation with domain randomization for PPO. | Implicit robustness via domain randomization; **contains zero online uncertainty estimation and no fallback mechanism**. |
| **Gao et al. (IEEE T-ITS 2023)** | DRL with rule-based safety filter for emergency vehicle preemption. | Hard-coded emergency preemption; no sensor degradation awareness or uncertainty-guided control handover. |
| **Varaiya (IEEE TAC 2013)** | Classical distributed Max-Pressure backpressure controller. | Non-learning classical controller; serves as FlowSync-UQ's fallback mechanism, not an uncertainty-aware hybrid. |

*Novelty Verification:* FlowSync-UQ is the **first unified traffic signal control system** to integrate multidimensional perception uncertainty estimation, hysteretic supervisory authority transfer to Max-Pressure, and a formal safety shield layer for camera-observable traffic intersections.

---

<a id="132-9-core-scientific-claims-mapped-to-raw-empirical-artifacts"></a>
### 13.2 9 Core Scientific Claims Mapped to Raw Empirical Artifacts

| Claim ID | Manuscript Claim | Supporting Artifact | Quantitative Finding | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | FlowSync-UQ bounds delay inflation to +0.2% under 30% noise. | `table_noise_robustness_v2.tex`, `statistical_report_v2.json` | 14.65s $\rightarrow$ 14.67s (+0.2%) vs D3QN (+1.2%), $t = -6.84, p = 1.48 \times 10^{-6}$. | **CONFIRMED** |
| **2** | Shared `PhysicalSignalFSM` eliminates physical clearance violations. | `server/tests/test_physical_fsm.py`, `table_noise_robustness_v2.tex` | Executed clearance violations = 0 across 20 seeds and 20,000 stress steps. | **CONFIRMED** |
| **3** | FlowSync-UQ reduces premature phase switch attempts by 18.8%. | `table_noise_robustness_v2.tex`, `final_hardened_suite_summary.json` | Proposed violations: 65 (FlowSync-UQ) vs 80 (unshielded D3QN). | **CONFIRMED** |
| **4** | Shielding without fallback degrades performance by +20.9%. | `results/final/table_ablations_v2.tex` | Mean delay: 18.23s (V4) vs 15.08s (V1), with 82 starvations. | **CONFIRMED** |
| **5** | Uncertainty correlates strongly with physical vehicle count error. | `table_cv_perception_validation.tex`, `cv_validation_metrics.json` | Pearson $r = 0.742, p < 0.001$ ($r = 0.793$ in adverse rain). | **CONFIRMED** |
| **6** | Reliability breakdown boundary is delayed by supervisory fallback. | `table_reliability_boundary_v2.tex`, `reliability_boundary_v2.json` | D3QN breaks down at $p_{\text{miss}} = 0.15$; adaptive control collapses at $p_{\text{miss}} \ge 0.45$. | **CONFIRMED** |
| **7** | Local fallback prevents corridor queue spillback in 2×2 grid. | `table_city_2x2_scalability_v2.tex`, `city_2x2_scalability_v2.json` | Preserves coordinated throughput at 1,053 veh/h under 30% noise. | **CONFIRMED** |
| **8** | Full pipeline executes in 57.66 ms on CPU (< 100 ms budget). | `table_latency_profile_full.tex`, `latency_profile_full.json` | Mean 57.66 ms, P95 65.26 ms (Perception: 57.23 ms, Controller: 0.426 ms). | **CONFIRMED** |
| **9** | Passive shadow replay operates non-disruptively across 3 regimes. | `table_shadow_replay_v2.tex`, `shadow_mode_multi_session.json` | Stable execution across 3,600 frames (Daylight, Morning Glare, Rain). | **CONFIRMED** |

---

<a id="133-superlative-purge--scholarly-tone-alignment"></a>
### 13.3 Superlative Purge & Scholarly Tone Alignment
In accordance with IEEE reviewer feedback, unsupportable superlatives were systematically eliminated across code comments, documentation, and `research-paper/main.tex` (historical path; absent from the current tree):
- *"Mathematically optimal Max-Pressure"* $\rightarrow$ *"Strong classical Max-Pressure baseline"*
- *"Absolute safety guarantee"* $\rightarrow$ *"Zero observed physical clearance violations across evaluated test suites"*
- *"Optimal threshold $\tau = 0.65$"* $\rightarrow$ *"Validation-selected operating threshold $\tau = 0.65$"*
- *"Proves real-world deployment"* $\rightarrow$ *"Demonstrates offline passive replay feasibility on real camera-derived observations"*

---

<a id="14-full-rest--websocket-api-specifications"></a>
## 14. Full REST & WebSocket API Specifications

> **2026-10-22 correction:** These are illustrative historical payloads, including placeholder/invalid JSON, rather than a versioned wire contract. Current routes live under `server/app/routers/`, research frames use `research_frame`, and the current summary endpoint is `/research/summary`. Read the router, WebSocket code and TypeScript types together. Section 26 inventories the maintained entry points.

<a id="141-rest-management-endpoints-research-api"></a>
### 14.1 REST Management Endpoints (`/research/*`, `/api/*`)

Implemented in [`server/app/routers/research.py`](server/app/routers/research.py):

| Method | Endpoint | Query / Body Parameters | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/research/scenarios` | None | `List[ScenarioMetadata]` | Returns 16 frozen scenarios with SHA-256 hashes and split labels. |
| `GET` | `/research/controllers` | None | `List[ControllerMetadata]` | Returns metadata, class name, and capabilities for all 7 controllers. |
| `GET` | `/research/seeds` | None | `List[int]` | Returns 20 pre-registered evaluation seeds ($1101\dots1120$). |
| `GET` | `/research/noise-presets` | None | `List[NoisePreset]` | Returns the 6 standardized perception fault profiles. |
| `GET` | `/research/benchmarks` | None | `BenchmarkSummary` | Returns publication Table I–VIII metrics and latency statistics. |

---

<a id="142-high-speed-10-hz-telemetry-websocket-protocol-wsresearch"></a>
### 14.2 High-Speed 10 Hz Telemetry WebSocket Protocol (`/ws/research`)

Mounted in [`server/app/websockets/research_ws.py`](server/app/websockets/research_ws.py):

```mermaid
sequenceDiagram
    autonumber
    participant UI as Next.js 16 Research UI
    participant WS as FastAPI WebSocket Manager (/ws/research)
    participant Engine as ExperimentSession Runner
    participant FSM as PhysicalSignalFSM

    UI->>WS: Connect WebSocket
    WS-->>UI: 101 Switching Protocols (Accepted)
    
    UI->>WS: {"type": "start_single", "config": {...}}
    WS->>Engine: Initialize Scenario, Controller, Seed, Noise
    Engine-->>WS: Session Initialized
    WS-->>UI: {"type": "session_started", "session_id": "...", "config": {...}}
    
    loop Every 100ms (10 Hz Tick)
        Engine->>Engine: Step Microscopic Physics (10 Hz)
        Engine->>Engine: Extract Observable State & UQ Cues
        Engine->>Engine: Supervisor & Safety Shield Evaluation
        Engine->>FSM: Enforce Clearance Timing (Yellow/All-Red)
        Engine-->>WS: Package Telemetry Dict
        WS-->>UI: {"type": "telemetry", "step": N, "decision_step": {...}, "uncertainty": {...}}
    end

    opt Interactive Operator Signals
        UI->>WS: {"type": "pause"}
        WS->>Engine: Halt Tick Loop
        UI->>WS: {"type": "step"}
        WS->>Engine: Execute Single Step
        UI->>WS: {"type": "resume"}
        WS->>Engine: Resume Loop
    end

    Engine-->>WS: Duration Reached / Finished
    WS-->>UI: {"type": "completed", "summary": {...}}
```

#### Client Command Messages:
```json
{
  "type": "start_single",
  "config": {
    "scenario_id": "test_clean_balanced_01",
    "controller_id": "flowsync_uq",
    "seed": 1101,
    "noise_profile": "miss_30",
    "duration_seconds": 360
  }
}
```

#### Server Telemetry Frame (Streamed at 10 Hz):
```json
{
  "type": "telemetry",
  "step": 142,
  "sim_time": 14.2,
  "active_phase": 0,
  "phase_name": "NS_S",
  "time_in_phase": 9.2,
  "queue_lengths": { "north": 4, "south": 3, "east": 8, "west": 6 },
  "mean_delay": 14.65,
  "throughput": 2461.5,
  "decision_step": {
    "rl_action": 2,
    "fallback_action": 0,
    "supervisor_authority": "fallback_active",
    "shield_override": false,
    "fsm_status": "green",
    "executed_action": 0
  },
  "q_values": [12.4, 8.1, 14.8, 6.2],
  "q_margin": 2.4,
  "uncertainty": {
    "score": 0.712,
    "is_fallback": true,
    "features": {
      "detector_dispersion": 0.35,
      "lower_tail_conf": 0.62,
      "count_volatility": 0.40,
      "forecast_residual": 0.55,
      "camera_latency": 0.12,
      "dropped_frames": 0.0,
      "tracking_fragmentation": 0.45
    }
  },
  "fsm_state": {
    "state": "GREEN",
    "yellow_timer": 0.0,
    "all_red_timer": 0.0,
    "min_green_remaining": 0.0,
    "proposed_violations": 2,
    "executed_violations": 0
  },
  "vehicles": [
    { "id": "v_104", "x": 32.5, "y": 1.5, "v": 8.2, "lane": "north_through", "is_ghost": false }
  ]
}
```

---

<a id="143-paired-comparison-dual-telemetry-protocol"></a>
### 14.3 Paired Comparison Dual Telemetry Protocol

Command sent from `/research/compare`:
```json
{
  "type": "start_paired",
  "config": {
    "scenario_id": "test_clean_balanced_01",
    "controller_a": "d3qn",
    "controller_b": "flowsync_uq",
    "seed": 1101,
    "noise_profile": "miss_30",
    "duration_seconds": 360
  }
}
```

Paired Telemetry Broadcast (10 Hz):
```json
{
  "type": "paired_telemetry",
  "step": 142,
  "sim_time": 14.2,
  "controller_a": {
    "id": "d3qn",
    "phase": 2,
    "delay": 18.39,
    "throughput": 2310.0,
    "queue_area": 420.5,
    "proposed_violations": 8
  },
  "controller_b": {
    "id": "flowsync_uq",
    "phase": 0,
    "delay": 14.67,
    "throughput": 2461.5,
    "queue_area": 315.2,
    "proposed_violations": 2,
    "uncertainty": 0.712,
    "is_fallback": true
  },
  "delta": {
    "delay_diff": -3.72,
    "throughput_diff": +151.5,
    "queue_area_diff": -105.3
  }
}
```

---

<a id="144-stored-replay-trace-data-schema"></a>
### 14.4 Stored Replay Trace Data Schema

Stored replay artifacts in JSON format enable instant deterministic timeline scrubbing at `/research/replay`:

```json
{
  "provenance": {
    "run_id": "run_20261001_1101_flowsync_uq",
    "timestamp": "2026-10-01T14:30:00Z",
    "git_commit": "72e5bbd",
    "scenario_hash": "2c8e1a7d4b9...",
    "controller": "flowsync_uq",
    "seed": 1101,
    "noise_profile": "miss_30"
  },
  "event_markers": {
    "fallback_windows": [[45.2, 58.0], [120.4, 135.0]],
    "peak_uncertainty_time": 124.8,
    "max_queue_time": 185.0,
    "starvation_preemption_times": [210.0]
  },
  "frames": [
    {
      "step": 0,
      "time": 0.0,
      "active_phase": 0,
      "mean_delay": 0.0,
      "uncertainty": 0.12,
      "vehicles": [...]
    }
  ]
}
```

---

<a id="15-one-command-clean-reproduction-protocol"></a>
## 15. One-Command Clean Reproduction Protocol

> **2026-10-22 correction:** **Retired workflow.** The `scripts/reproduce_all.py --quick/--final` commands below now deliberately refuse execution. Missing checkpoints cannot be replaced with untrained policies. The old timings, test totals and blanket reproducibility claim are superseded. Use sections 25–28 for maintained setup, inspection commands and provenance. Do not rerun completed failed training recipes.

The following describes the retired reproduction workflow; maintained commands and limitations are recorded in sections 25–28.

<a id="151-regression-test-suite-execution"></a>
### 15.1 Regression Test Suite Execution
```bash
PYTHONPATH=.:server ./server/venv/bin/pytest server/tests/ -v --no-cov
```
*Historical status at the original snapshot:* `126 passed, 4 warnings in 106.54s`

<a id="152-nextjs-production-build-verification"></a>
### 15.2 Next.js Production Build Verification
```bash
cd client && npm run build
```
*Historical status at the original snapshot:* `✓ Generating static pages (17/17) in 488ms — 0 errors, 0 warnings`

<a id="153-rapid-research-smoke-test-85s"></a>
### 15.3 Rapid Research Smoke Test (~85 Seconds)
```bash
python scripts/reproduce_all.py --quick
```
Historical intended stages (the command is now retired):
1. Stage 1: Quick CRN Benchmark Evaluation
2. Stage 2: Perception Noise Robustness
3. Stage 3: Component Ablation Suite
4. Stage 4: End-to-End Latency Profiling (100 frames)
5. Stage 5: Computer Vision Quality Validation (100 frames)
6. Stage 6: LaTeX Table Export

<a id="154-full-paper-replication-pipeline-15-min"></a>
### 15.4 Full Paper Replication Pipeline (~15 Minutes)
```bash
python scripts/reproduce_all.py --final
```
Historical intended behavior: regenerate the old 20-seed tables in `results/final/`. This command is now retired, and these tables are not the corrected frozen reference.

<a id="155-live-interactive-demonstration-startup"></a>
### 15.5 Live Interactive Demonstration Startup

**Terminal 1 (Backend Research & Simulation Engine):**
```bash
cd server && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Next.js 16 Interactive Research UI):**
```bash
cd client && npm run dev
```

Open `http://localhost:3000/research` in the browser to access the Research Mode Dashboard, launch frozen experiments, compare D3QN vs FlowSync-UQ side-by-side under CRN, and inspect live uncertainty and FSM clearance dynamics.

---

<a id="16-comprehensive-mathematical-formulas-equations--algorithmic-index"></a>
## 16. Comprehensive Mathematical Formulas, Equations & Algorithmic Index

> **2026-10-22 correction:** This catalog preserves mathematical background and legacy implementation assertions; it is not a verified equation-to-source map. Physical-unit constants, 14-input state claims, all-action centering, Polyak updates, anti-starvation guarantees, CCTV calibration and statistical proofs require the corrections in sections 19–20 and 29. Missing historical paths are labelled explicitly; equations alone do not validate implementation or empirical claims.

This section provides an exhaustive, unified reference index of all mathematical equations, physical kinematics models, reinforcement learning formulations, uncertainty metrics, supervisory control laws, and statistical tests implemented across the FlowSync and FlowSync-UQ codebase. Each entry includes its mathematical definition, exact codebase location, and a concise explanation of its functional role.

---

<a id="161-microscopic-kinematics--traffic-flow-equations"></a>
### 16.1 Microscopic Kinematics & Traffic Flow Equations

#### 1. Intelligent Driver Model (IDM) Longitudinal Acceleration
$$a_i(t) = a_{\max} \left[ 1 - \left(\frac{v_i(t)}{v_0}\right)^\delta - \left(\frac{s^*(v_i(t), \Delta v_i(t))}{s_i(t)}\right)^2 \right]$$
- **What it is & How it is used:** Computes instantaneous vehicle acceleration in [`server/app/simulation/vehicle.py`](server/app/simulation/vehicle.py), continuously balancing free-flow speed pursuit ($v_0 = 13.89\text{ m/s}$) against repulsive braking to maintain safe distance behind the lead vehicle.

#### 2. IDM Dynamic Safe Headway Distance
$$s^*(v_i, \Delta v_i) = s_0 + v_i \cdot T_{\text{gap}} + \frac{v_i \cdot \Delta v_i}{2 \sqrt{a_{\max} b}}$$
- **What it is & How it is used:** Calculates the dynamic required headway gap in [`vehicle.py`](server/app/simulation/vehicle.py) incorporating minimum standstill spacing ($s_0 = 2.0\text{ m}$), safe time headway ($T_{\text{gap}} = 1.2\text{ s}$), and approach closing rate $\Delta v_i = v_i - v_{i-1}$ to prevent rear-end collisions.

#### 3. Discrete Forward Euler Kinematics Integration
$$v_i(t + \Delta t) = \max\left(0, \min(v_{\max}, v_i(t) + a_i(t) \cdot \Delta t)\right), \quad x_i(t + \Delta t) = x_i(t) + v_i(t + \Delta t) \cdot \Delta t$$
- **What it is & How it is used:** Advances physical vehicle states forward in time at 10 Hz ($\Delta t = 0.1\text{ s}$) in `server/app/simulation/engine.py` (historical path; absent from the current tree), strictly bounding speeds between $0\text{ m/s}$ and road speed limit $v_{\max}$.

#### 4. Parameterized Cubic Bézier Turning Curve
$$\mathbf{B}(u) = (1-u)^3 \mathbf{P}_0 + 3(1-u)^2 u \mathbf{P}_1 + 3(1-u) u^2 \mathbf{P}_2 + u^3 \mathbf{P}_3, \quad u \in [0, 1]$$
- **What it is & How it is used:** Synthesizes smooth, curvature-continuous 2D trajectories for turning movements in `server/app/simulation/engine.py` (historical path; absent from the current tree) as vehicles traverse the intersection box from incoming stop lines ($\mathbf{P}_0$) to target exit lanes ($\mathbf{P}_3$).

#### 5. Cubic Bézier Tangent Control Scaling
$$\mathbf{P}_1 = \mathbf{P}_0 + \kappa \cdot \mathbf{t}_{\text{in}}, \quad \mathbf{P}_2 = \mathbf{P}_3 - \kappa \cdot \mathbf{t}_{\text{out}}, \quad \kappa = 0.55 \cdot \|\mathbf{P}_3 - \mathbf{P}_0\|_2$$
- **What it is & How it is used:** Computes intermediate Bézier control points in `server/app/simulation/engine.py` (historical path; absent from the current tree) by scaling entrance/exit tangent vectors by chord length to ensure realistic turn geometry without angular kinks.

#### 6. Critical Gap Acceptance Time-to-Collision (TTC)
$$t_{\text{arrival}} = \frac{d_{\text{opp}}}{v_{\text{opp}}} \ge t_{\text{critical}} = 4.5\text{ s}$$
- **What it is & How it is used:** Evaluates oncoming traffic approach time in `server/app/simulation/engine.py` (historical path; absent from the current tree) to determine if an unprotected left-turning vehicle can safely execute across opposing straight lanes or must yield.

#### 7. Pedestrian Poisson Arrival Process
$$P(k \text{ pedestrian arrivals in } \Delta t) = \frac{(\lambda_{\text{ped}} \Delta t)^k e^{-\lambda_{\text{ped}} \Delta t}}{k!}$$
- **What it is & How it is used:** Simulates crosswalk pedestrian flow in `server/app/simulation/engine.py` (historical path; absent from the current tree) with arrival rate $\lambda_{\text{ped}} \in [0.02, 0.10]\text{ ped/s}$ and normal walking speed $v_{\text{ped}} \sim \mathcal{N}(1.34\text{ m/s}, 0.25^2)$.

#### 8. Highway Capacity Manual (HCM) Level of Service (LOS) Control Delay
$$\text{LOS} = \begin{cases} \text{A} & \bar{d} \le 10\text{ s} \\ \text{B} & 10\text{ s} < \bar{d} \le 20\text{ s} \\ \text{C} & 20\text{ s} < \bar{d} \le 35\text{ s} \\ \text{D} & 35\text{ s} < \bar{d} \le 55\text{ s} \\ \text{E} & 55\text{ s} < \bar{d} \le 80\text{ s} \\ \text{F} & \bar{d} > 80\text{ s} \end{cases}$$
- **What it is & How it is used:** Categorizes intersection operational performance in `server/app/simulation/analytics.py` (historical path; absent from the current tree) according to federal HCM standards based on average control delay per vehicle $\bar{d}$.

---

<a id="162-computer-vision-geometry--fault-injection-formulas"></a>
### 16.2 Computer Vision, Geometry & Fault Injection Formulas

#### 9. Planar Homography Perspective Transformation Matrix
$$\begin{bmatrix} X' \\ Y' \\ W' \end{bmatrix} = \mathbf{H} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}, \quad X = \frac{X'}{W'}, \quad Y = \frac{Y'}{W'}$$
- **What it is & How it is used:** Maps 2D camera pixel coordinates $(u, v)$ from CCTV bounding boxes to metric intersection ground-plane coordinates $(X, Y)$ in `server/app/cv/roi_manager.py` (historical path; absent from the current tree).

#### 10. Normalized Camera FOV Approach Distance Coordinate
$$d_i = \frac{x_i}{L_{\text{lane}}} \le 0.45$$
- **What it is & How it is used:** Filters vehicles in `server/app/cv/camera_builder.py` (historical path; absent from the current tree) that fall within the camera's optical approach boundary ($67.5\text{ m}$ of $150\text{ m}$ approach length), strictly enforcing zero simulator memory leakage.

#### 11. Bernoulli Vehicle Detection Dropout Fault
$$m_i \sim \text{Bernoulli}(1 - p_{\text{miss}}), \quad \hat{D}_t = \{ b_i \in D_t \mid m_i = 1 \}$$
- **What it is & How it is used:** Injects vehicle detection dropouts in [`research/noise/fault_injector.py`](research/noise/fault_injector.py) with dropout probability $p_{\text{miss}} \in [0.10, 0.50]$ to emulate camera occlusions and adverse lighting.

#### 12. Poisson Phantom Vehicle Clutter Fault
$$N_{\text{phantom}} \sim \text{Poisson}(\lambda_{\text{clutter}} = 0.5\text{ veh/step})$$
- **What it is & How it is used:** Injects spurious false-positive bounding boxes into approach queues in [`fault_injector.py`](research/noise/fault_injector.py) to simulate pavement glare, shadows, and roadside furniture false alarms.

#### 13. Gaussian Spatial Bounding-Box Jitter Perturbation
$$\tilde{x}_i = x_i + \epsilon_x, \quad \epsilon_x \sim \mathcal{N}(0, \sigma_{\text{jitter}}^2 = 2.5^2\text{ m}^2)$$
- **What it is & How it is used:** Corrupts longitudinal vehicle localization in [`fault_injector.py`](research/noise/fault_injector.py) to simulate spatial bounding-box boundary noise from edge neural network inference.

#### 14. Random Track ID Turnover Fragmentation
$$P(\text{ID Switch}) = p_{\text{switch}} = 0.15 \text{ per track per step}$$
- **What it is & How it is used:** Forces ByteTrack tracking ID turnover in [`fault_injector.py`](research/noise/fault_injector.py) to emulate Kalman filter trajectory fragmentation during vehicle crossovers.

#### 15. Observation Delay Ring Buffer Staleness
$$o_t^{\text{delayed}} = o_{t - k}, \quad k \sim \mathcal{U}\{2, 5\} \text{ steps } (200\text{--}500\text{ ms})$$
- **What it is & How it is used:** Injects observation age latency in [`fault_injector.py`](research/noise/fault_injector.py) by sampling delayed frames from an internal ring buffer to emulate RTSP network transport lag.

---

<a id="163-deep-reinforcement-learning-equations--optimization"></a>
### 16.3 Deep Reinforcement Learning Equations & Optimization

#### 16. Semi-Markov Decision Process (Semi-MDP) Discounted Return
$$R_t = \sum_{k=0}^{\infty} \gamma^{\tau_k} r_{t + \tau_k}$$
- **What it is & How it is used:** Defines the cumulative discounted reward objective in `server/app/simulation/d3qn_agent.py` (historical path; absent from the current tree), discounting return over variable physical phase durations $\tau_k$ with $\gamma = 0.99$.

#### 17. 14-Dimensional Camera-Observable State Representation
$$\phi_t = \left[ \frac{q_N}{K_{\max}}, \frac{q_S}{K_{\max}}, \frac{q_E}{K_{\max}}, \frac{q_W}{K_{\max}}, \frac{v_N}{V_{\max}}, \frac{v_S}{V_{\max}}, \frac{v_E}{V_{\max}}, \frac{v_W}{V_{\max}}, \mathbf{e}_{p_t}, \frac{\min(\tau_t, 60)}{60} \right] \in \mathbb{R}^{14}$$
- **What it is & How it is used:** Encodes normalized approach queues ($K_{\max}=25$), mean approach speeds ($V_{\max}=15\text{ m/s}$), one-hot active phase $\mathbf{e}_p \in \{0, 1\}^4$, and phase duration in `research/state/builder.py` (historical path; absent from the current tree).

#### 18. Delay-Anchored Multi-Factor Reward Shaping
$$r_t = - \sum_{l \in \text{in}} (d_{l, t} + \alpha q_{l, t}) - \beta \mathbf{1}_{\text{switch}} - \lambda_{\text{starv}} \sum_{l} \max(0, w_{l, t} - W_{\max})$$
- **What it is & How it is used:** Guides reinforcement learning policy optimization in `server/app/simulation/d3qn_agent.py` (historical path; absent from the current tree) by penalizing delay $d_{l,t}$, queue lengths $q_{l,t}$, phase switching thrashing ($\beta = 0.5$), and vehicle wait times exceeding $W_{\max} = 45.0\text{ s}$ ($\lambda_{\text{starv}} = 2.0$).

#### 19. Identifiable Mean-Subtracted Dueling Architecture Decomposition
$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$
- **What it is & How it is used:** Reconstructs Q-values from separate state-value $V(s)$ and action-advantage $A(s, a)$ neural streams in `server/app/simulation/d3qn_agent.py` (historical path; absent from the current tree), enforcing identifiability by subtracting the mean advantage across all actions.

#### 20. Double DQN Target Value with Demand Action Masking
$$Y_t^{\text{DoubleQ}} = r_t + \gamma Q\left(s_{t+1}, \arg\max_{a' \in \mathcal{M}(s_{t+1})} Q(s_{t+1}, a'; \theta_t); \theta_t^-\right)$$
- **What it is & How it is used:** Computes Bellman TD targets in `server/app/simulation/d3qn_agent.py` (historical path; absent from the current tree) by selecting actions via online weights $\theta_t$ and evaluating them via target weights $\theta_t^-$, restricted to non-empty approach phases via demand mask $\mathcal{M}(s)$.

#### 21. Temporal Difference (TD) Priority in PER
$$p_i = \left( |\delta_i| + \epsilon \right)^\alpha, \quad \delta_i = Y_i - Q(s_i, a_i; \theta)$$
- **What it is & How it is used:** Assigns transition sampling priority in `server/app/simulation/per_buffer.py` (historical path; absent from the current tree) proportional to absolute prediction error $|\delta_i|$, using priority exponent $\alpha = 0.6$ and small constant $\epsilon = 10^{-5}$.

#### 22. Binary SumTree Priority Sampling Probability
$$P(i) = \frac{p_i}{\sum_{k=1}^N p_k}$$
- **What it is & How it is used:** Defines transition sampling probabilities in `server/app/simulation/sum_tree.py` (historical path; absent from the current tree), enabling exact $O(\log N)$ priority sampling and updates across $N = 100,000$ stored transitions.

#### 23. Annealed Importance Sampling (IS) Weight Correction
$$w_i = \left( \frac{1}{N} \cdot \frac{1}{P(i)} \right)^\beta, \quad \bar{w}_i = \frac{w_i}{\max_j w_j}$$
- **What it is & How it is used:** Corrects for non-uniform sampling bias in `server/app/simulation/per_buffer.py` (historical path; absent from the current tree), annealing exponent $\beta$ linearly from $0.4$ to $1.0$ across training episodes to ensure unbiased gradient updates.

#### 24. Online Short-Horizon EWMA Demand Forecasting
$$\hat{\lambda}_{l, t} = \alpha_{\text{EWMA}} \cdot \lambda_{l, t}^{\text{inst}} + (1 - \alpha_{\text{EWMA}}) \cdot \hat{\lambda}_{l, t-1}$$
- **What it is & How it is used:** Computes smoothed arrival rate forecasts in `server/app/simulation/forecaster.py` (historical path; absent from the current tree) ($\alpha_{\text{EWMA}} = 0.15$), anticipating platoon arrival bursts before vehicles reach the stop line.

#### 25. Soft Polyak Target Network Update
$$\theta^- \leftarrow \tau \theta + (1 - \tau) \theta^-, \quad \tau = 0.005$$
- **What it is & How it is used:** Smooths target network updates in `server/app/simulation/d3qn_agent.py` (historical path; absent from the current tree) via exponential moving parameter tracking ($\tau = 0.005$) to prevent training divergence.

#### 26. Action Value Margin Metric ($\Delta Q$)
$$\Delta Q = Q(s, a_{(1)}) - Q(s, a_{(2)})$$
- **What it is & How it is used:** Measures controller decision margin in [`server/app/controllers/d3qn.py`](server/app/controllers/d3qn.py) and UI explainability panels as the difference between the optimal and second-best action Q-values.

---

<a id="164-perception-uncertainty-estimation--temperature-calibration"></a>
### 16.4 Perception Uncertainty Estimation & Temperature Calibration

#### 27. Feature 1: Mean Detector Confidence Dispersion
$$\phi_1 = 1.0 - \frac{1}{|D_t|} \sum_{i \in D_t} c_i$$
- **What it is & How it is used:** Measures the average confidence deficit across detected bounding boxes in [`research/uncertainty/estimator.py`](research/uncertainty/estimator.py).

#### 28. Feature 2: Lower-Tail Detector Confidence Deficit
$$\phi_2 = 1.0 - \min_{i \in D_t} c_i$$
- **What it is & How it is used:** Flags marginal or ambiguous vehicle detections in [`estimator.py`](research/uncertainty/estimator.py) that indicate partial occlusion or severe lens glare.

#### 29. Feature 3: Step-to-Step Vehicle Count Volatility
$$\phi_3 = \min\left(1.0, \frac{|N_t - N_{t-1}|}{\max(1, N_{t-1})}\right)$$
- **What it is & How it is used:** Detects unphysical sudden changes in vehicle counts between consecutive frames in [`estimator.py`](research/uncertainty/estimator.py) resulting from detector dropout.

#### 30. Feature 4: Forecast Innovation Residual
$$\phi_4 = \min\left(1.0, \frac{\|q_t - \hat{q}_{t|t-1}\|_2}{\max(1, \|q_t\|_2)}\right)$$
- **What it is & How it is used:** Quantifies divergence between observed queue vector $q_t$ and the 5-second online EWMA model forecast in [`estimator.py`](research/uncertainty/estimator.py).

#### 31. Feature 5: Observation Staleness / Camera Latency Penalty
$$\phi_5 = \min\left(1.0, \frac{\Delta t_{\text{cam}}}{0.50}\right)$$
- **What it is & How it is used:** Penalizes video packet arrival latency in [`estimator.py`](research/uncertainty/estimator.py) as timestamp staleness approaches the critical 500 ms threshold.

#### 32. Feature 6: Dropped Frame Penalty
$$\phi_6 = \mathbb{I}(\text{frame is dropped or decode failed}) \in \{0.0, 1.0\}$$
- **What it is & How it is used:** Injects a discrete penalty in [`estimator.py`](research/uncertainty/estimator.py) when video decode fails or RTSP frames are missing.

#### 33. Feature 7: Track Fragmentation & Turnover Rate
$$\phi_7 = \frac{N_{\text{new\_ids}, t}}{N_{\text{active\_tracks}, t}}$$
- **What it is & How it is used:** Measures ByteTrack trajectory fragmentation in [`estimator.py`](research/uncertainty/estimator.py) by computing the ratio of newly spawned track IDs to active tracks.

#### 34. Linear Feature Aggregation
$$U_{\text{raw}}(s_t) = \mathbf{w}^T \phi_t + b$$
- **What it is & How it is used:** Combines the 7 normalized uncertainty cues into a single scalar score in [`estimator.py`](research/uncertainty/estimator.py) using empirically calibrated feature weights.

#### 35. Platt Temperature-Scaled Sigmoid Calibration
$$U(s_t) = \sigma\left(\frac{U_{\text{raw}}(s_t)}{T}\right) = \frac{1}{1 + \exp\left(-\frac{U_{\text{raw}}(s_t)}{T}\right)} \in [0.0, 1.0]$$
- **What it is & How it is used:** Calibrates raw uncertainty via temperature scaling ($T = 1.2$) in [`estimator.py`](research/uncertainty/estimator.py) fitted against 1,000 annotated real CCTV frames, achieving $r = 0.742$ ($p < 0.001$) correlation with true count error.

---

<a id="165-safe-supervisory-fallback-classical-control--safety-invariants"></a>
### 16.5 Safe Supervisory Fallback, Classical Control & Safety Invariants

#### 36. Varaiya's Max-Pressure Differential
$$P(p) = \sum_{l \in \text{in}(p)} x_l - \sum_{m \in \text{out}(p)} x_m, \quad p^* = \arg\max_{p \in \mathcal{A}} P(p)$$
- **What it is & How it is used:** Computes queue differentials across conflicting movements in [`server/app/controllers/max_pressure.py`](server/app/controllers/max_pressure.py) to maximize network throughput and stabilize queues without learning.

#### 37. Hysteretic Supervisor Authority Handover Rule
$$\text{Authority}(t) = \begin{cases} \text{FALLBACK\_ACTIVE} & \text{if } U(s_t) \ge \tau_{\text{high}} = 0.65 \\ \text{RL\_ACTIVE} & \text{if } U(s_t) \le \tau_{\text{low}} = 0.50 \text{ for } K_{\text{recover}} \text{ steps and } t_{\text{dwell}} \ge K_{\text{dwell}} \\ \text{Authority}(t-1) & \text{otherwise} \end{cases}$$
- **What it is & How it is used:** Prevents switching chattering in [`server/app/controllers/supervisor.py`](server/app/controllers/supervisor.py) by enforcing asymmetric thresholds, mandatory fallback dwell time ($K_{\text{dwell}} = 30$ steps / $3.0\text{s}$), and consecutive recovery steps ($K_{\text{recover}} = 10$ steps / $1.0\text{s}$).

#### 38. Minimum Green Time Safety Invariant ($G_{\min}$)
$$a_{\text{shield}} = \begin{cases} a_{\text{current}} & \text{if } \tau_{\text{phase}} < G_{\min} = 8.0\text{ s} \\ a_{\text{target}} & \text{otherwise} \end{cases}$$
- **What it is & How it is used:** Enforces minimum green interval in [`server/app/controllers/safety_shield.py`](server/app/controllers/safety_shield.py) to guarantee driver safety and prevent sudden signal termination.

#### 39. Maximum Green Time Ceiling Safety Invariant ($G_{\max}$)
$$\text{Force Phase Change} \iff \tau_{\text{phase}} \ge G_{\max} = 60.0\text{ s}$$
- **What it is & How it is used:** Terminates extended phases in [`safety_shield.py`](server/app/controllers/safety_shield.py) when green duration reaches 60.0 seconds to prevent arterial starvation.

#### 40. Anti-Starvation Preemption Condition ($W_{\max}$)
$$p^* = \arg\max_p \left( \max_{l \in \text{in}(p)} w_l \right) \iff \max_l w_l \ge W_{\max} = 45.0\text{ s}$$
- **What it is & How it is used:** Preempts the controller in [`safety_shield.py`](server/app/controllers/safety_shield.py) to serve any neglected approach lane where waiting time has exceeded 45.0 seconds.

#### 41. Physical Clearance Interval Transition Timing
$$\Delta t_{\text{yellow}} = 3.0\text{ s}, \quad \Delta t_{\text{all\_red}} = 1.0\text{ s}, \quad T_{\text{clearance}} = \Delta t_{\text{yellow}} + \Delta t_{\text{all\_red}} = 4.0\text{ s}$$
- **What it is & How it is used:** Mandated hardware clearance intervals enforced by [`server/app/controllers/physical_fsm.py`](server/app/controllers/physical_fsm.py) across all controllers, guaranteeing 0 executed clearance violations.

---

<a id="166-statistical-analysis--hypothesis-testing-equations"></a>
### 16.6 Statistical Analysis & Hypothesis Testing Equations

#### 42. Common Random Numbers (CRN) Paired Performance Difference
$$\Delta_i = \text{Delay}_{\text{D3QN}, i} - \text{Delay}_{\text{FlowSync-UQ}, i}, \quad i \in \{1, 2, \dots, 20\}$$
- **What it is & How it is used:** Calculates seed-by-seed paired delay differences under identical vehicle arrival trajectories in [`research/analysis/statistical_pipeline.py`](research/analysis/statistical_pipeline.py).

#### 43. Shapiro-Wilk Normality Test Statistic
$$W = \frac{\left( \sum_{i=1}^n a_i x_{(i)} \right)^2}{\sum_{i=1}^n (x_i - \bar{x})^2}, \quad W = 0.932, \quad p = 0.182 > 0.05$$
- **What it is & How it is used:** Tests whether paired differences follow a normal distribution in [`statistical_pipeline.py`](research/analysis/statistical_pipeline.py), confirming that parametric $t$-test assumptions are satisfied.

#### 44. Two-Sided Paired Student's $t$-Test Statistic
$$t = \frac{\bar{\Delta}}{s_{\Delta} / \sqrt{n}} = -6.84, \quad p = 1.48 \times 10^{-6}$$
- **What it is & How it is used:** Evaluates statistical significance in [`statistical_pipeline.py`](research/analysis/statistical_pipeline.py), proving FlowSync-UQ significantly outperforms unshielded D3QN under 30% perception corruption ($p < 0.001$).

#### 45. Non-Parametric Wilcoxon Signed-Rank Test Statistic
$$W = \min(W^+, W^-) = 0.0, \quad p = 1.91 \times 10^{-6}$$
- **What it is & How it is used:** Provides distribution-free non-parametric validation in [`statistical_pipeline.py`](research/analysis/statistical_pipeline.py), confirming superiority without normality assumptions.

#### 46. Standardized Effect Size (Cohen's $d$)
$$d = \frac{\bar{\Delta}}{s_{\Delta}} = \frac{0.27}{0.14} = \mathbf{1.92}$$
- **What it is & How it is used:** Quantifies empirical improvement magnitude in [`statistical_pipeline.py`](research/analysis/statistical_pipeline.py), classifying FlowSync-UQ's advantage as a **Very Large Effect Size** ($d > 0.8$).

#### 47. Holm-Bonferroni Family-Wise Error Rate Step-Down Correction
$$p_{(k)} \le \frac{\alpha}{m - k + 1}$$
- **What it is & How it is used:** Adjusts significance thresholds across multiple pairwise controller comparisons in [`statistical_pipeline.py`](research/analysis/statistical_pipeline.py) to strictly control family-wise Type I error rates.

#### 48. Pearson Product-Moment Correlation Coefficient ($r$)
$$r = \frac{\sum_{i=1}^n (U_i - \bar{U})(e_i - \bar{e})}{\sqrt{\sum_{i=1}^n (U_i - \bar{U})^2 \sum_{i=1}^n (e_i - \bar{e})^2}} = 0.742, \quad p < 0.001$$
- **What it is & How it is used:** Quantifies linear agreement in `research/analysis/cv_validator.py` (historical path; absent from the current tree) between estimated uncertainty $U(s_t)$ and ground-truth physical vehicle count error $e_t = |N_{\text{pred}} - N_{\text{gt}}|$.

---

<a id="17-current-status-and-evidence-authority"></a>
## 17. Current Status and Evidence Authority

### 17.1 What the project currently establishes

FlowSync combines a Next.js application, FastAPI services, simulation and RL components, and a separately audited headless research workflow. The implemented research contribution so far is experimental infrastructure and a reproducible record of controller evaluations, implementation repairs and failed learning hypotheses. The original objective remains a learned controller with a reproducible advantage over strong classical control and a distinct, defensible research contribution. That objective is **not achieved**.

The scope is simulation only. No measured intersection counts/timings or recorded camera footage have been supplied for independent validation. The custom simulator, synthetic perception faults and simulated lamp audits cannot establish field accuracy, hardware latency, collision safety or readiness to operate a traffic cabinet.

| Topic | Current evidence status |
| --- | --- |
| Learned policies versus Fixed | Audited comparisons show lower mean stopped delay in the reported panels. This does not establish an advantage over stronger classical methods. |
| Learned policies versus Max-Pressure | Reliable superiority remains unestablished across the audited experiments. |
| FlowSync-UQ versus its shielded D3QN policy | No reliable added control benefit established, including when fallback actually activates. |
| Online RL after warm start | Often degrades or fails to improve the frozen parents. More episodes have not resolved this. |
| Extra temporal/spatial inputs | Implemented with matched controls; both completed pilots fail their continuation screens. |
| Upstream-only pressure teacher | Implemented, but the targeted teacher prerequisite and horizon diagnostic fail to justify replacement/training. |
| Simulated signal behavior | Zero measured conflict/clearance violations on specified audited samples; coverage is finite and experiment-specific. |
| Real cameras, edge devices and real signal operation | Tooling/proposals exist; corresponding validation and operational readiness are unestablished. |
| Research/UI equivalence | Shared components and selected tests exist; complete end-to-end equivalence remains open. |
| Publication/novelty | Dated writing assets and evidence exports exist. No justified readiness percentage, accepted novelty claim or superiority paper result. |
| Model promotion | No recent candidate automatically promoted, uploaded to Supabase or installed as a website default. |

### 17.2 Evidence hierarchy and historical material

Read the [current research status](research/RESEARCH_STATUS.md) and [evaluation audit](research/EVALUATION_AUDIT.md) before using an older table or launch instruction. For a particular experiment, read its frozen protocol, recorded manifest/configuration/checkpoint/source hashes, raw measurements and matching results note together. A summary is useful for navigation; its filename does not certify its claims.

`results/final/`, `results/tables/`, the original manuscript assets and sections 9/13 above contain historical material that predates the audited fixes. Preserve them for traceability, but do not cite their numbers as validated research. The corrected experiments below are distinct panels; their means must not be pooled merely because each reports seconds.

The latest diagnostics concern **input use and action choices**, followed by **teacher alignment and horizon sensitivity**. These have already completed. A chronological note proposing one of these investigations is not a current instruction to run it again. Completed negative outcomes supersede the corresponding historical “ready to run” text.

<a id="18-current-repository-and-research-organization"></a>
## 18. Current Repository and Research Organization

### 18.1 Top-level ownership

| Location | Current responsibility |
| --- | --- |
| `client/` | Next.js pages, API routes, components, hooks, Zustand stores, types and Prisma schema. |
| `server/app/` | FastAPI application, HTTP/WebSocket handlers, services, simulation, controllers, RL and experimental camera tooling. |
| `server/tests/` | Backend and headless research regression tests. |
| `research/` | Maintained headless commands, shared execution/sensing, bounded pilots, diagnostics and research documentation. |
| `results/` | Local experiment outputs, raw metrics, checkpoints/provenance references, traces and generated evidence. Most artifacts are ignored and absent from a fresh clone. |
| `docs/` | Maintained development setup and application/research architecture guides. |
| `scripts/` | Repository checks and remaining project utilities; the old all-in-one reproduction command is retired. |
| `.github/workflows/`, `Makefile` | Automated checks and common developer commands. |
| Root community files | README, contribution/security/conduct guidance, software citation metadata and license. |

The [architecture guide](docs/architecture.md) describes the application/research split. The [setup guide](docs/setup.md), [backend guide](server/README.md), [frontend guide](client/README.md) and [artifact policy](results/README.md) cover their respective boundaries. This reference supplements them with detailed history; it does not replace frozen experiment records.

### 18.2 Research packages after cleanup

The formerly flat research scripts have been grouped by responsibility. Maintained Python tools use package imports and module entry points. The root package contains discovery rather than a large collection of standalone experiment scripts.

| Package | Contents and role |
| --- | --- |
| [training](research/training/) | Research training, parent initialization/expansion, randomized demand and lineage support. |
| [evaluation](research/evaluation/) | Checkpoint-explicit replicate evaluation, development validation and selection support. |
| [audits](research/audits/) | Training/replay drift, observation/action/input use, label stability and teacher/horizon diagnostics. |
| [pilots](research/pilots/) | Preparation, bounded controlled experiments and fixed-endpoint comparators. |
| [pilots/launchers](research/pilots/launchers/) | Saved shell recipes; completed failed recipes remain historical, not recommended jobs. |
| [datasets](research/datasets/) | Action-label collection code. Generated datasets stay under `results/`. |
| [policies](research/policies/) | Research correction models and additional observed-input baselines. |
| [experiments](research/experiments/) | Shared execution engine, observed-state runtime, paired branching and shield adapter. |
| [noise](research/noise/) and [observation](research/observation/) | Synthetic delivery/fault boundary and observation support. |
| [calibration](research/calibration/) and [uncertainty](research/uncertainty/) | Fitting/calibration, uncertainty estimation and fallback-benefit experiments. |
| [scenarios](research/scenarios/) and [manifests](research/manifests/) | Scenario files, schema/loader and declared experimental input lists. |
| [analysis](research/analysis/) | Statistical summaries, grouped feature/model comparisons and reporting. |
| [evidence](research/evidence/) | Provenance-checked publication tables/figures and teacher evidence exports. |
| [profiling](research/profiling/) and [cv](research/cv/) | Profiling and camera-surrogate utilities; optional dependencies may be required. |
| [legacy](research/legacy/) | Earlier exploratory runners/configuration and deliberately retired figure entry points. |
| [docs](research/docs/README.md) | Protocols, results, audits, workflow guides and paper drafts in separate indexed collections. |

Dated documents retain their original filenames under `research/docs/{protocols,results,audits,guides,papers}/`. The cleanup relocated 64 research files into packages and grouped the research records; it also consolidated duplicated/outdated project guides and removed unused starter assets and duplicate package-manager configuration. Recorded results, checkpoints, data and source archives were preserved.

### 18.3 Command discovery and archived paths

Run maintained commands from the repository root using `python -m research` or a full module path. The discovery command displays help without loading Torch, optional vision packages or a model. Its aliases are:

| Alias after `python -m research` | Maintained module |
| --- | --- |
| `train` | `research.training.train_policy` |
| `evaluate` | `research.evaluation.evaluate_replicates` |
| `validate` | `research.evaluation.evaluate_validation` |
| `audit-training` | `research.audits.audit_training_results` |
| `audit-spatial` | `research.audits.audit_spatial_inputs` |
| `verify-spatial` | `research.audits.verify_spatial_input_audit` |
| `compare-spatial` | `research.pilots.compare_spatial_pilot` |
| `compare-temporal` | `research.pilots.compare_temporal_pilot` |
| `compare-updates` | `research.pilots.compare_update_pressure_pilot` |
| `export-paper` | `research.evidence.build_paper_evidence` |
| `export-teachers` | `research.evidence.export_teacher_evidence` |

Other tools remain available through their full module names, such as `research.audits.audit_teacher_alignment`. Scenario IDs resolve through the shared manifest loader relative to its source location; they no longer depend on an incidental current directory. Package initializers avoid starting experiments or loading optional dependencies.

Saved source ZIPs retain the original layout, commands and hashes used when an experiment ran. Reorganization does not rewrite those archives. An exact live-source verification can legitimately reject the reorganized implementation; reproduce against the archived source and recorded environment when exact provenance is required. Updating a path in maintained documentation is different from changing frozen evidence.

<a id="19-audited-execution-sensing-and-controller-boundaries"></a>
## 19. Audited Execution, Sensing and Controller Boundaries

### 19.1 What an audited decision executes

The research path is: scenario/demand → simulation → delivered synthetic sensor packet → observed controller features/context → policy proposal → optional uncertainty fallback → optional additional shield → shared physical signal transition rules → executed lamps. A separate signal audit samples executed state after each simulation tick. Truth can score outcomes and training rewards; it must not secretly replace faulty observations in masks, pressure, forecasts or adaptive decisions.

The main implementations are [engine.py](research/experiments/engine.py), [runtime.py](research/experiments/runtime.py), [fault_injector.py](research/noise/fault_injector.py) and the [controller package](server/app/controllers/). Learned proposals respect their trained decision interval, rather than being recomputed at every 0.1-second simulator tick. The reference decision interval is two seconds; actual macro-actions can span physical transitions.

The **additional shield** is distinct from the **physical FSM**. Bare D3QN still retains minimum-green and clearance enforcement. Disabling a shield in an ablation does not allow arbitrary incompatible lamps or remove common physical transition time. Intervention counters, blocked proposals, fallback activations and executed signal violations describe different events and must be reported separately.

### 19.2 Confirmed evaluation defects and repairs

The original 2,040-run headless experiment ran successfully but constructed randomly initialized learned controllers rather than loading the intended trained policy. Its saved outputs remain at `results/headless/final_20_seed/` and `results/headless.zip`; learned-policy performance conclusions from that experiment are invalid.

The subsequent audited path repairs the following:

1. **Checkpoint authority:** Require an explicit compatible checkpoint, seed before construction, load strictly, enter inference mode and record metadata/SHA-256. Omit plain DQN unless supplied its own compatible trained weights.
2. **Decision cadence:** Match the trained two-second decision schedule instead of querying the policy every simulator tick.
3. **Executed demand:** Apply incident capacity changes, direction-specific bursts and approach-specific turns. Reject unsupported configurations and hash what actually executed. Incidents use a discharge-headway surrogate rather than a validated physical road blockage.
4. **Observed inputs:** Rebuild masks, movement pressure, forecasts and adaptive context from delivered measurements. Fixed remains sensor-independent by design.
5. **Fault realism within the synthetic model:** Use binomial missed detections, packet latency/drop behavior, corrupted outgoing/arrival counts and realized-fault telemetry. Correct uncertainty residual units and propagate observable age.
6. **Authority and timing:** Expose fallback/shield ablations, isolate hidden watchdog authority, correct phase timer indices/intervention counters, measure actual green and preserve minimum-green priority.
7. **Execution evidence:** Audit executed conflicts/clearance on each tick; preserve coverage counts, events, optional trajectories, configuration/source/checkpoint provenance and paired arrival hashes.

### 19.3 Current classical-controller meaning

Max-Pressure is a deterministic queue-balancing controller, requiring no RL training. In this implementation, movement pressure is the positive part of normalized incoming demand minus the associated outgoing count:

$$P_m=\max\left(0,\frac{q_{\mathrm{in},m}}{C_{\mathrm{in}}}-\frac{q_{\mathrm{out},d(m)}}{C_{\mathrm{out}}}\right),\qquad P_p=\sum_{m\in\mathcal M_p}P_m.$$

It chooses a phase with highest summed pressure, preserving the current phase on a positive tie or when every pressure is zero. If switching is unavailable, it holds. The common physical/shield rules still apply. In the audited path its incoming/outgoing context comes from delivered sensing. See [max_pressure.py](server/app/controllers/max_pressure.py).

The phase indices are **0 = north/south straight, 1 = east/west straight, 2 = north/south left, 3 = east/west left**. The original section 4 action table has a different historical ordering and must not be used to decode current checkpoints or traces. Right turns and permissive movement handling follow simulator rules; four actions do not imply twelve separately protected movements.

Greedy responds to observed demand; Actuated uses its configured demand/timing logic; Fixed follows its configured schedule. The repository's names/metadata do not certify compliance with Webster/NEMA engineering designs. The implemented Max-Pressure is not Advanced-MP, Advanced-XLight or switching-curve MP. The additional upstream-only variant changes delivered incoming-demand semantics; it is not a faithful reproduction of those research baselines.

### 19.4 Fault and safety interpretation

The fault injector exposes 13 presets and supports missed detections, bursts, false positives/jitter, lane swaps, latency and drops with corresponding delivered outgoing/arrival context. Their names and parameters are read from the actual executed configuration. Synthetic scenarios are not calibrated real-camera error distributions.

Zero measured lamp conflict/clearance violations describe sampled simulated states under the implemented audit. They do not measure collisions, pedestrian safety, cabinet faults or all possible trajectories. Phase-service starvation counters describe time since service of a phase; they do not directly bound every vehicle's accumulated waiting time. A shield can protect service/tails while increasing mean delay through additional switches and clearance losses.

<a id="20-current-rl-architecture-observation-versions-and-learning-repairs"></a>
## 20. Current RL Architecture, Observation Versions and Learning Repairs

### 20.1 Source ownership and network

The shared RL implementation is under [server/app/rl](server/app/rl/), including `dqn_agent.py`, `dqn_network.py`, `replay_buffer.py`, `observations.py`, `hyperparams.py` and the application `trainer.py`. Research collection/training lives separately in [research/training/train_policy.py](research/training/train_policy.py).

The dueling network maps the checkpoint's input width through **256 → LayerNorm → ReLU → 256 → LayerNorm → ReLU**. Each value/advantage head has a 128-unit hidden layer; outputs are one state value and four action advantages. With a validity mask it centers advantages over valid actions:

$$Q(s,a)=V(s)+A(s,a)-\frac{\sum_{b\in\mathcal V(s)}A(s,b)}{|\mathcal V(s)|}.$$

Without a supplied mask the network retains a backward-compatible all-action mean. Training/inference callers must supply the correct mask; network shape alone does not establish the correct semantics. The shared agent uses masked Double-DQN targets, prioritized replay, importance-weighted TD loss and a demonstration margin term. Target synchronization copies weights explicitly; the old universal Polyak-update description does not describe this path.

Shared defaults include gamma 0.99 per two-second reference interval, batch size 128, replay capacity 100,000, PER alpha 0.6 and priority epsilon 0.01. Shared `HyperParams` uses learning rate 3e-4 and maximum green 40 seconds. A recorded research run may explicitly override these settings, including learning rate, updates per episode, episode horizon and target synchronization. Do not infer a saved experiment's settings from today's defaults or the old equation catalog.

### 20.2 Current observation schema

| Version | Dimensions | Added information / control |
| --- | ---: | --- |
| `v6_28dim_smdp` | 28 | Historical base sensor features. |
| `v7_36dim_observed` | 36 | v6 plus four delivered outgoing counts and four phase-service timers. |
| `v8_64dim_temporal` | 64 | v7 plus lagged delivered counts, frame age and availability flags. |
| `v8_64dim_zero_history` | 64 | Same architecture/delivery as temporal; zero only its added 28 inputs. |
| `v9_48dim_spatial` | 48 | v7 plus twelve delivered upstream movement-count features. |
| `v9_48dim_zero_spatial` | 48 | Same architecture/delivery as spatial; zero only its added twelve inputs. |

The base 28 features are movement counts at indices 0–11; current phase one-hot at 12–15; elapsed-phase time, transition flag, aggregate pressure and maximum phase-service timer at 16–19; and eight EWMA forecast features at 20–27. Counts use `tanh(count / 15)`, rather than the old fixed-capacity division. The audited runtime reconstructs the base features from delivered sensing rather than handing a clean environment observation to a noisy controller.

v7 encodes outgoing counts with the same tanh scale and clips phase-service times after division by 45 seconds. v8 uses delivered count lags at ten and thirty ticks (one and three seconds at 10 Hz), normalized age and lag/age availability flags. History resets every episode, uses delivered packets each tick and does not interpolate a missing lag. v9 features occupy indices 36–47 in canonical movement order. [observations.py](server/app/rl/observations.py) defines the exact version/schema contract and strict validation.

Temporal/spatial initializers expand compatible v7 parent input matrices with zero columns and retain the rest of the parameters. Both expanded arms initially reproduce parent Q values/actions. Shape/metadata changes cause checkpoint file hashes to differ even when initial outputs agree. The matched controls isolate added information at inference while keeping architecture and delivery machinery equal; they are not smaller networks.

### 20.3 Reward and replay corrections

The [learning update audit](research/docs/audits/LEARNING_UPDATE_AUDIT_20261015.md) confirms two defects repaired for the research path:

- Legacy v4 charged one physical switch three times. Research reward `v5_single_switch_delay` charges once at GREEN → YELLOW. A blocked request incurs no switch charge. Correcting reward accounting does not change the corresponding physical trajectory.
- End-of-horizon replay previously bootstrapped an incomplete macro-action using an intermediate state. The research collector now stores completed decision-to-decision transitions, counts/drops the final incomplete transition and uses the correct successor state/mask.

For a completed transition lasting $\tau$ seconds, the bootstrap multiplier is $\gamma^{\tau/\Delta_{\mathrm{decision}}}$. The online network chooses a valid next action and the target network evaluates it:

$$a^*=\arg\max_{a\in\mathcal V(s')}Q_\theta(s',a),\qquad y=r+(1-d)\gamma^{\tau/\Delta_{\mathrm{decision}}}Q_{\theta^-}(s',a^*).$$

Numerical checks cover masking, variable-duration discounts and terminal handling. Added telemetry includes reward components, dropped partial ticks, sampled demonstration fraction, importance weights, discounts, targets, raw/weighted TD losses, margin loss, gradients and weight changes. Inspected replay capacity was not exhausted; demonstration eviction did not explain those batches' degradation.

### 20.4 Demonstrations, warm start and optimizer interpretation

Demonstration collection records transitions from a teacher such as Max-Pressure. Imitation updates train action preferences; TD warmup learns values before online RL. Benefits from these stages must be separated from improvements caused by subsequent online interaction. Some selected parents came from warmup because later online learning was worse.

Negative Q values are compatible with negative delay-based returns. Falling importance-weighted loss is not proof that raw TD prediction or traffic control improves. Finite, nonzero gradients show updates occurred; they do not establish that the optimizer produces useful decisions. The later fixed-replay and input-use diagnostics make these distinctions explicit. No single causal optimizer defect has been established as the explanation for all failed learning experiments.

These research fixes and observation versions do **not** automatically migrate the website trainer/inference stack. Preserve checkpoint/reward/observation compatibility and validate that integration separately.

---

<a id="21-audited-training-and-evaluation-history"></a>
## 21. Audited Training and Evaluation History

### 21.1 Corrected reference panels

Each row below is a separate experiment. Different demand panels, episode horizons, sensing conditions and supervision invalidate direct comparisons between their absolute means. Training seeds identify policy replicates; traffic seeds identify randomized arrivals. Selection/validation outcomes are development evidence rather than independent confirmation.

| Experiment | Recorded outcome and interpretation |
| --- | --- |
| First corrected frozen evaluation | 2,000 runs, three trained replicates and twenty paired traffic seeds. Clean delay means: Max-Pressure 11.944, Greedy 12.199, D3QN 13.123, UQ 13.262, Fixed 15.786, Actuated 17.709 seconds. No strong-baseline superiority. |
| Domain-randomized training `domain_rCXu3gDe` | Three 900-episode online runs, each with 200 demos, 2,000 imitation and 500 TD warmup updates. Selected validation mean about 2.5% better than Max-Pressure; warmup selected in two seeds. Selection is not a fresh test. |
| Frozen domain evaluation | 2,000 runs. Clean means: Max-Pressure 11.781, D3QN 11.918, Greedy 12.123, UQ 12.560, Fixed 15.212, Actuated 18.165 seconds. Across all ten conditions, UQ adds about 0.559 seconds relative to D3QN. |
| Supervisor validation ablation | 540 runs. Disabling the wrapper reproduces D3QN; the shield raises mean delay while sometimes improving tails. Fallback-only worsens mixed-fault delay. |
| Shield-aware training `shield_mW0ZwjUP` | Three completed 900-episode runs. Matched shield-only validation worsens from 10.7845 to 10.8781 seconds. No promotion. |
| v5 learning pilot `pilot_v5_kbW0lsY3` | Research reward/replay repairs; selected frozen parents used in later controlled pilots. Their identities are fixed in section 25. |
| Matched-shield frozen evaluation | 2,800 runs; strongest audited frozen reference, detailed below. |

### 21.2 Strongest frozen reference: matched supervision

Artifact: `results/replicate_evaluation/matched_shield_v5_20261015`. The panel includes three selected policy replicates, twenty traffic seeds **81001–81020**, seven clean scenario templates and three additional sensing conditions. See the [matched-shield protocol](research/docs/protocols/MATCHED_SHIELD_PROTOCOL_20261015.md) and [audited manuscript scaffold](research/docs/papers/PAPER_DRAFT_AUDITED_20261016.md).

| Controller | All-condition mean stopped delay per arrived vehicle (s) |
| --- | ---: |
| Max-Pressure | 11.514 |
| Bare D3QN | 11.528 |
| Greedy | 11.725 |
| Max-Pressure + additional shield | 11.953 |
| D3QN + additional shield | 12.004 |
| Full FlowSync-UQ | 12.019 |
| Fixed | 15.496 |
| Actuated | 16.463 |

The primary matched-shield saved-delay estimate is **−0.050 seconds**, with a descriptive crossed-bootstrap 95% interval **[−0.219, 0.125]**. The UQ increment relative to shielded D3QN saves **−0.015 seconds**, interval **[−0.104, 0.071]**. Positive saved delay would favor the candidate. Neither interval establishes superiority; spanning zero also does not establish equivalence.

Fallback was active: **306 activations and 260,298 ticks across 600 UQ runs**. Its lack of added benefit cannot be attributed to a disabled component. Anti-starvation accounts for **892 of 896 D3QN shield interventions**. The uncertainty calibration detects synthetic count error; it does not estimate whether a particular backup action improves traffic.

All **4,340,000 executed signal samples** have zero measured conflict/clearance violations. This is finite simulated-lamp evidence, not collision testing or real-world safety certification.

### 21.3 Controlled learning and replay diagnostics

| Experiment | Outcome | Decision |
| --- | --- | --- |
| Intervention audit | 36 rollouts and 65 short paired branches show service-protection/efficiency trade-offs. Fallback helps some states and hurts others. | Investigate intervention benefit rather than assume every override is helpful. |
| Benefit gate | 216 source rollouts, 270 validation runs. Vetoes all 106 validation entry evaluations and exactly matches shield-only behavior. | No useful selective fallback benefit. |
| Margin release `margin_release_6usc2j0j` | Relaxing imitation margin worsens common episode-90 mean delay by 5.33%. A small selected-best gain comes from one seed. | Failed fixed-endpoint screen. |
| Expanded development validation | 330 runs. Candidate and parents both about 11.497 seconds, matched-shield Max-Pressure 11.436, bare Max-Pressure 11.245. | No established improvement. |
| Temporal pilot `temporal_v8_fc758xbz` | All six runs complete ninety episodes and 2,880 updates. Temporal endpoint delay 11.217 versus control 11.070 seconds. | Failed. |
| Training-drift audit | 72 training-only rollouts show online learning can worsen even recorded training configurations. Raw loss, gradient and weight telemetry added. | No single optimizer defect established. |
| Update pressure `update_pressure_5qyi9cmv` | Four versus 32 updates per episode. Low-update delay 10.852 seconds, control 11.109, unchanged parents 10.841. | Helps a degrading control, but fails parent/tail constraints. |
| Fixed-replay diagnostic | Fitting Q-target MAE falls 11.020 → 1.313; excluded-training-episode MAE rises 10.745 → 12.648. | Better fitting error does not establish generalization or traffic benefit. |
| Broader replay diagnostic | Excluded prediction MAE improves to 11.759 but remains worse than unchanged parents' 10.745. | Failed continuation. |

The fixed/broader replay values are **Q-target prediction errors**, not seconds of traffic delay. These findings motivate checking actual decisions and excluded data rather than extending the same training recipe. Their protocols/results are indexed in [research/docs](research/docs/README.md).

<a id="22-action-labels-calibration-and-future-arrival-diagnostics"></a>
## 22. Action Labels, Calibration and Future-Arrival Diagnostics

### 22.1 Hindsight availability versus learned improvement

Most action-ranking experiments freeze the original DQN weights and fit a small research correction model. They are not new end-to-end DQN training. A simulator can reveal an alternative action that helps under one realized future without making that choice predictable from the delivered state or reliably beneficial under another future.

Branch delay savings use **vehicle-seconds** of stopped waiting over the branch horizon. They are different from full-run seconds per arrived vehicle, Q-target MAE and optimizer loss. Alternatives/futures at one gate are correlated. A positive fitting-fold result is not an excluded-probe or full-run controller win.

| Stage | Dataset or diagnostic | Measured outcome |
| --- | --- | --- |
| All-action feasibility | Eighteen training sources, 45 decision points and 135 paired forty-second branches. | Thirteen points have an alternative satisfying joint delay/throughput/endpoint-wait conditions. This is hindsight availability. |
| Action-ranking pilot | 72 label sources and 168 validation runs. | Parent 12.814 seconds; point-only correction 12.726; uncertainty-supervised primary 12.815; shielded Max-Pressure 12.979; bare Max-Pressure 12.493; Greedy 12.145. The primary fails; a favorable ablation does not replace it. |
| Bootstrap uncertainty audit | Excluded-seed alternative predictions. | Simultaneous lower-bound coverage only 24.8%. Ensemble spread is not a calibrated error bound. |
| Broader action dataset | `results/action_rank_dataset/broader_20261020T134122Z`: 648 sources, 1,944 gates, 5,707 branches. | 216 fitting, 360 calibration, 72 probe sources; all complete. 3,060,400 signal samples with zero measured violations. |
| Group calibration | Three ridge models fitted/frozen before calibration, then frozen before probe. | Joint alternative coverage 99.21%, but whole-seed coverage fails in two parents. Calibrated models make zero probe corrections. Point-only changes thirteen actions: seven qualified benefits, five harmful, one neither. Continuation fails. |
| Richer observed features | 36 fitting-only grouped fits. | Full-state delay prediction MAE 35.851 versus compact 33.342 vehicle-seconds, 7.53% worse. Harmful changed choices increase from 18/47 to 64/121. Failed. |

Broader role seeds are **95001–95006 fitting**, **95101–95110 calibration** and **95201–95202 probe**. Inspecting probe outcomes consumes them for later model decisions; they cannot become a fresh confirmation panel after tuning.

### 22.2 Unobserved future-arrival sensitivity

`results/arrival_label_stability/panel_20261021T063020Z` contains eighteen sources, 54 gates and 125 alternatives, each tested under eight additional futures. Delay gain changes sign in **75/125 alternatives**. Original choices are harmful in **108/168 future cases**, and only **3/21 original choices** qualify in at least six futures. This panel demonstrates substantial dependence of short-horizon action labels on future arrivals absent from the observed state.

The next [averaged-label experiment](research/docs/results/AVERAGED_LABEL_RESULTS_20261021.md) freezes choices using eight futures **before** evaluating eight separate futures. Artifact: `results/averaged_action_labels/panel_20261021T091742Z`. Selection, smoke and evaluation future keys are separated; full evaluation uses IDs 8–15 and the earlier mechanics smoke uses 100–107.

| Frozen hindsight choice | Changed gates / 54 | Mean branch delay saved (vehicle-seconds) | Harmful changed cases |
| --- | ---: | ---: | ---: |
| Single-future choice | 21 | −1.975 | 102/168 (60.71%) |
| Mean of eight futures | 9 | +1.071 | 28/72 (38.89%) |

Means include unchanged cases, with equal source weighting. The mean-eight choice improves the predefined label-quality screen and justifies a bounded learned-model pilot. It remains simulator hindsight with material harmful cases, not a deployable policy or established full-run gain. The experiment records 666,000 signal samples with zero measured violations.

### 22.3 Learned averaged labels and exact reproduction

`results/averaged_label_model/pilot_20261021T095353Z` completes 72 fitting and 36 excluded-probe sources, fitting six models. Fitting traffic seeds are **96301–96304** and probe seeds **96401–96402**. The mean-eight model makes **zero corrections across 72 probe gates and 576 future cases**. The single-future model changes one gate, with five good and three harmful future cases and aggregate throughput loss. The continuation screen fails.

The user-run repeat `results/averaged_label_model/pilot_20261021T114544Z` matches all **thirteen output hashes** exactly. It demonstrates deterministic reproduction, not new independent data or an improved policy. Running it again is unnecessary.

The observed-input audit reproduces exact refits and predictions and independently replays six original source/branch cases. That is not a claim that every source and future trajectory was independently rerun during postprocessing. See the [learned-model result](research/docs/results/AVERAGED_LABEL_MODEL_RESULTS_20261021.md).

### 22.4 Joint-benefit classification follow-up

`results/joint_benefit_comparison/grouped_20261021` compares twelve fitting-only whole-traffic-seed folds and 24 models. Classification acts more often but **adds 1.067 vehicle-seconds of branch delay**, with **353/616 harmful changed cases (57.31%)**. The matched regressor saves **1.165 vehicle-seconds**, with **8/48 harmful changed cases (16.67%)**.

The classifier fails. The fitting-fold regressor result does not overturn its already failed excluded-probe test. Changing an objective to obtain more actions is not useful when the extra actions worsen joint outcomes. See the [joint-benefit results](research/docs/results/JOINT_BENEFIT_RESULTS_20261021.md).

<a id="23-upstream-demand-spatial-pilot-and-input-use-diagnosis"></a>
## 23. Upstream Demand, Spatial Pilot and Input-Use Diagnosis

### 23.1 Historical counts and the unsupported empty-phase explanation

`Intersection.get_movement_queues()` historically counts non-passed vehicles that have already crossed the stop line but remain in the scene. At free speed they can remain counted for about 4.8 seconds after crossing. The added `get_upstream_movement_counts()` explicitly counts vehicles at/before the stop line while retaining the same optional backlog assumption. Old getters/defaults and checkpoint inputs were preserved.

The [upstream observation audit](research/docs/results/UPSTREAM_OBSERVATION_RESULTS_20261021.md) exactly reproduces eighteen original sources, 21,600 ticks and 314 policy gates. Discharged vehicles contribute to historical counts on **15,511 ticks**; phantom phase demand appears at **65 gates**. However, **no mask differs and no switch targets an upstream-empty phase**. The proposed empty-phase-switch explanation is unsupported.

Changing only teacher demand semantics changes Max-Pressure proposals at **80/314 gates**, from historical holds to upstream-only switches. These proposal differences do not establish better traffic: switching introduces clearance cost. Subsequent teacher diagnostics test that distinction directly.

### 23.2 Spatial sensing implementation

The v9 packet adds twelve delivered upstream movement counts to v7. Both treatment and control have 48 network inputs, checkpoint-driven sensor selection, identical delivery machinery and zero-column parent initialization. The control zeros only the extra network inputs. Missing, malformed, nonfinite or inconsistent packets fail validation; clean truth is not silently substituted under noisy sensing.

The joint count-partition adapter applies missed detections, burst loss, lane swaps and shared latency/drop behavior to aggregate/upstream information together. Upstream counts are bounded by reconstructed aggregate counts. Ghosts and positive jitter use a documented **Bernoulli(0.5) upstream-location assignment assumption**, rather than measured spatial error calibration. The aggregate fault RNG sequence is preserved: **1,300 frames across all thirteen presets** match the committed pre-change injector exactly.

Masks and the additional shield continue to use historical **delivered** demand. This experiment tests added policy information; it is not a wholesale replacement of demand semantics. An upstream-only Max-Pressure baseline reads the same delivered spatial packet and supports matched-shield evaluation. It has not won a new frozen final benchmark.

### 23.3 Mechanics smoke

`results/research_training/spatial_smoke_20261021` uses two arms, 24 paired demos and one online episode each. Each arm collects 317 transitions and performs four updates. Weights remain finite and change; added columns remain zero for control and move for spatial. Expanded initial models exactly match the parent metrics.

Across 84 evaluations and 100,800 signal samples, both trained arms average **7.7011 seconds** stopped delay versus parent **7.6738 seconds**. Zero measured signal violations and working gradients establish mechanics on that smoke, not learning superiority.

### 23.4 Completed spatial learning pilot: failed

Artifact: `results/research_training/spatial_v9_k2bg79oc/comparison.json`. Independent recomputation exactly matches the saved comparison. All six workers complete ninety online episodes, 24 demos and 360 optimizer updates, without budget stops. Both arms use policy-training seeds 101/202/303, paired randomized exogenous inputs, shield on and fallback off.

The recorded settings are learning rate 1e-4, four updates per episode, target synchronization every 25 updates, constant imitation margin weight 0.5 and 1,200 ticks per episode. This fine-tuning pilot has no imitation/TD warmup stage. Validation at initial/warmup/30/60/90 uses three existing templates, development traffic seeds **21001/21002**, and clean/mixed sensing faults. Reusing these cells is not a fresh generalization test.

The primary endpoint is episode 90 for every worker:

| Configuration | Mean delay (s) | Mean within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: |
| Original parents | 10.841389 | 37.035417 | 89.472222 |
| Retrained zero-spatial control | 10.783722 | 39.115139 | 89.972222 |
| Spatial-input learner | 10.840583 | 37.775694 | 89.694444 |

Spatial delay is **0.5273% worse than control** and only **0.00743% better than parents**. Against control, seed 101 improves 1.904%, seed 202 worsens 0.857% and seed 303 worsens 2.706%. Lower spatial p95 than control does not offset worse p95 than parents and lower throughput than control.

The frozen screen requires at least 2% aggregate delay improvement against **both** references, no seed more than 1% worse than either, no aggregate p95/throughput loss against either, complete runs and zero measured signal violations. It fails. Completed candidates have zero measured violations, but that does not satisfy the performance requirements.

`comparison_available` and `primary_endpoint_complete` are true. `primary.continue_to_expanded_validation`, `publication_ready` and `automatic_promotion` are false. Process/comparator status zero means execution and auditing succeeded, not that the performance screen passed. **Do not rerun, expand or promote this recipe.** See [spatial results](research/docs/results/SPATIAL_INPUT_RESULTS_20261021.md).

### 23.5 Input-use and action-choice diagnosis

The bounded [spatial input audit](research/docs/audits/SPATIAL_INPUT_AUDIT_RESULTS_20261022.md), artifact `results/spatial_input_audit/pilot_20261022`, completes 27 training-configuration rollouts, 36 scheduled branch gates and 44 distinct twenty-second action branches. Sources have 1,200 ticks each. It records 41,200 lamp samples and zero measured violations. All nine selected demos reproduce their logged reward, delay and shield counts. Online sources evaluate deterministic final policies on recorded randomized training configurations; they are not replays of the original exploratory action sequences.

The spatial input columns are learned: episode-90 L2 norms are **0.489672, 0.349071 and 0.419477**, with maximum absolute weights **0.027395, 0.022301 and 0.028500** for seeds 101/202/303. Initial and control columns remain zero. Yet zeroing spatial features at the same delivered state changes **none of the episode-90 policy's 320 inspected proposals**:

| State distribution | Gates | Nonzero spatial input gates | Mean maximum absolute Q change | Mean range of valid-action Q changes | Mean valid-action margin | Proposal changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Control-policy states | 110 | 107 | 0.861657 | 0.098035 | 2.224985 | 0 |
| Spatial-policy states | 108 | 106 | 0.863911 | 0.099808 | 2.170554 | 0 |
| Teacher states | 102 | 100 | 0.623707 | 0.098285 | 2.269435 | 0 |

Most input-induced Q movement is shared across actions; relative rankings are less sensitive on this panel. These are descriptive means, not per-state bounds. Q magnitudes are not delay seconds. There are no final changed proposals for the shield to suppress. Episode 30 has a few proposal changes that survive the shield; episode 60 has none on these panels.

Different arm checkpoints still differ through their shared weights/replay. Zeroing inputs at inference cannot undo their effects on learning gradients or targets, so this diagnostic does not prove the inputs were irrelevant during training. It establishes neither universal representation adequacy nor that spatial information is useless.

At the scheduled branch gates, natural/zero-input actions coincide and their branches match. Historical/upstream teachers also coincide at all scheduled branch gates; their outcomes duplicate the same action. Across all sampled gates there are **41 teacher disagreements** (14 control, 14 spatial, thirteen teacher states), and the final spatial policy chooses the historical teacher's action in every one. None of these disagreement gates was in the preselected branch panel; its outcomes cannot assess the specific upstream-teacher substitution.

On teacher trajectories, historical-teacher agreement rises from **95/102 initial to 101/102 final gates**. This is consistent with retaining teacher choices, not a causal demonstration-loss ablation. Recorded optimizer fields are finite with nonzero gradients; declining weighted TD loss coexists with less favorable raw loss in some seeds. Each episode stores the **last** update's diagnostics, not all four updates.

Separate verification reproduces all **5,120 saved network scores**, weight analysis, teacher proposals and the report from raw records. It does not independently rerun every trajectory. No disconnected input, zero-initialization defect, inference-input mismatch or shield suppression of every changed action was reproduced. No specific optimizer repair or longer training run is justified by this audit alone. The subsequent teacher prerequisite is already complete and failed, as recorded next.

---

<a id="24-teacher-alignment-and-horizon-sensitivity"></a>
## 24. Teacher Alignment and Horizon Sensitivity

### 24.1 Fixed upstream-teacher prerequisite

After the input-use audit, a new protocol tested whether upstream-only teacher choices were actually better at the observed disagreement states. This prerequisite had to pass before any conditional teacher-training pilot. The completed result is [teacher alignment and horizon sensitivity](research/docs/results/TEACHER_ALIGNMENT_RESULTS_20261022.md); the frozen designs are the [teacher plan](research/docs/protocols/SPATIAL_TEACHER_ALIGNMENT_PLAN_20261022.md) and [separate horizon protocol](research/docs/protocols/TEACHER_HORIZON_PROTOCOL_20261022.md).

`results/teacher_alignment/pilot_20261022` exactly replays nine recorded spatial-policy training configurations, including observations, masks, Q values, teacher proposals, reward/delay/throughput, shields and arrival hashes. Seven gates qualify under the frozen first-two-disagreements/remaining-horizon rule: five from parent 101, one from 202 and one from 303. Sources with no eligible gate remain included. Choice records and future RNG keys are frozen before collection.

At all seven gates, the policy and historical teacher hold while the upstream teacher requests an immediate switch. Policy and historical-teacher branches therefore duplicate one action, rather than supplying two independent baselines. All arms retain the same continuation policy, delivered sensing, shield, macro-action schedule and physical FSM.

Two eight-future sets give 56 paired gate/future cases each and 224 distinct twenty-second action branches:

| Future set | Mean delay saved by upstream choice (vehicle-seconds) | Mean throughput gained (vehicles) | Mean endpoint maximum accumulated wait saved (s) | Joint non-harmful cases / 56 |
| --- | ---: | ---: | ---: | ---: |
| First | −6.623214 | −1.071429 | +2.791071 | 24 |
| Separate check | −5.339286 | −0.946429 | +3.016071 | 21 |

The candidate reduces endpoint maximum wait but worsens delay and throughput. Under the predefined joint condition **35/56 check cases are harmful**; this is not the same as counting only cases with strictly increased delay. Only **two of seven gates** are jointly non-harmful in at least six of eight check futures and strictly beneficial in at least one. Parent 303 has no qualifying gate. The full continuation screen fails, with `continue_to_learning_pilot: false`.

The check candidate adds **0.357143 physical switches per branch** on average. Undiscounted training reward worsens by **0.659179**, and reward/delay-gain directions disagree in only **2/56 cases**. This panel does not establish a reward-direction defect. Earlier switching and clearance cost are plausible explanations, but counts alone do not isolate their causal contribution.

All **55,600 signal samples** have zero measured violations. Frozen choices, sources, inputs/outputs and archived-source hashes verify; independent raw-outcome aggregation matches the report. This is bounded seen-training-state evidence, not a full-run controller comparison.

### 24.2 Separate fixed-prefix horizon diagnostic

After seeing the failed twenty-second prerequisite, a separate protocol asked whether a longer horizon recovers the cost of switching. The primary endpoint is fixed at sixty seconds, with no best-horizon selection. It cannot replace the failed screen or convert inspected futures into new confirmation.

`results/teacher_horizon/pilot_20261022` extends the same 224 branches to sixty seconds. Every twenty-second prefix matches exactly, including arrivals, reward components, switches and endpoint wait. All nine sources also replay exactly. The extension records **145,200 lamp samples** with zero measured violations; overlapping trajectories must not be added as independent performance/safety samples.

| Future set | Twenty-second delay saved (vehicle-seconds) | Sixty-second delay saved (vehicle-seconds) | Sixty-second throughput gained |
| --- | ---: | ---: | ---: |
| First | −6.623214 | +4.430357 | −0.196429 |
| Separate check | −5.339286 | −5.137500 | −0.428571 |
| Both, descriptive | −5.981250 | −0.353571 | −0.312500 |

The favorable first-set mean at sixty seconds does not persist in the separate set, and throughput falls in both. Every policy-replicate mean is negative in the separate set: **−3.6400, −6.7375 and −11.0250 vehicle-seconds**. Pooling both sets gives no mean delay benefit. `continue_to_training` remains false.

These are seven correlated states with unequal coverage across three policy replicates. Fifty-six future cases are not 56 independent intersections or training runs. Both future sets had already been inspected at twenty seconds when the extension was chosen. The longer-horizon result is exploratory sensitivity analysis; it supports no significance, full-run gain or generalization claim.

### 24.3 Decision and scientific interpretation

**Stop the immediate upstream-teacher alignment recipe.** Do not launch its conditional ninety-episode training plan, select only the two favorable gates, relax the failed screen or report the first future set's positive sixty-second mean as success. The original spatial policy also remains failed and unpromoted.

The reproducible finding is that additional geometric observations can move Q magnitudes without changing final actions, and fixed alternative choices at fixed observed states can change apparent benefit with arrival future and horizon. This distinguishes hindsight availability, stable action benefit, observed-input learnability and closed-loop improvement. It is a candidate methods/failure-analysis narrative, not a demonstrated breakthrough or superior learned controller.

Generated CSV/PNG/SVG evidence and hashes are in `results/paper_evidence/teacher_diagnostics_20261022`. The [dated manuscript addendum](research/docs/papers/PAPER_ADDENDUM_OBSERVATION_AND_TEACHERS_20261022.md) keeps this development evidence separate from the earlier frozen manuscript tables. Exporting a figure does not create new evaluation samples.

<a id="25-reproducibility-parent-checkpoints-and-experimental-separation"></a>
## 25. Reproducibility, Parent Checkpoints and Experimental Separation

### 25.1 Frozen policy parents

Later controlled pilots inherit the selected **v7 observations / research v5 reward** parents below, all selected under `d3qn_shield`. Paths are relative to `results/research_training/pilot_v5_kbW0lsY3/`:

| Policy-training seed | Checkpoint | SHA-256 |
| --- | --- | --- |
| 101 | `seed_101/checkpoint_warmup.pt` | `1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725` |
| 202 | `seed_202/checkpoint_50.pt` | `a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4` |
| 303 | `seed_303/checkpoint_100.pt` | `e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052` |

`results/research_training/update_pressure_5qyi9cmv/batch_manifest.json` also records those selections. Retain all three parents. A best new seed/checkpoint cannot silently replace one. Expanded v9 files have different shapes/metadata and hashes despite initial output parity.

The historical 1,000-episode checkpoint is `server/models/76734963-e987-4024-aaa0-d21c048194c5/checkpoint_1000.pt`, SHA-256 `4784798d2bc2daf53804f433ae366ba74b5132b82e53291993d073cfe8ff1ea1`. It uses v6 observations/v4 reward. Its training/evaluation separation is not independently established, and it is not the parent of the latest spatial pilot. A website episode label must not be used to infer lineage.

### 25.2 Seed roles and consumed panels

| Role | Known identifiers | Interpretation |
| --- | --- | --- |
| Policy-training replicates | 101, 202, 303 | Distinct training randomness, not the paired traffic seeds. |
| Used development traffic | 21001–21005, 24001–24005, 25001/25002 | Already inspected. Latest spatial validation reuses 21001/21002. |
| Frozen domain evaluation | 61001–61020 | Already inspected final panel; cannot be reused as fresh confirmation. |
| Frozen matched-shield evaluation | 81001–81020 | Already inspected final panel; retain the original protocol/results. |
| Broader action-label roles | 95001–95006 fitting; 95101–95110 calibration; 95201–95202 probe | Roles declared before collection; inspected probes are consumed. |
| Learned averaged-label roles | 96301–96304 fitting; 96401–96402 probe | Excluded-probe result failed; selecting a new model from it consumes its independence. |
| Spatial mechanics smoke | 97301/97302 | Development/mechanics, not final confirmation. |

The early 1101-series seed manifest remains application/historical metadata; it does not describe every later research panel. Earlier inspected final panels are also consumed. Fresh confirmation requires freezing development choices first and then using an independent declared test, rather than relabelling a seen template/seed.

### 25.3 Required artifact contents and metric definitions

Preserve protocol, executed configuration hashes, checkpoint identities/metadata, source hashes/archives, dependency provenance, paired arrival hashes, raw metrics, events, optional trajectories, signal-audit coverage, training logs and the full common checkpoint curve. Write new output directories. A missing local artifact is not permission to construct a randomly initialized substitute. Missing/incompatible weights or packets should fail explicitly.

The primary delay measure is accumulated **stopped waiting per arrived vehicle over a finite horizon**, including vehicles still present/backlogged. It is not trip travel time or delay only among discharged vehicles. The reported aggregate p95 averages within-run percentiles; it is not a percentile of one pooled vehicle population. Mean passed vehicles is a horizon count; it is not automatically vehicles/hour without the relevant duration.

Branch vehicle-seconds saved, endpoint accumulated-wait reduction, throughput change, Q-target MAE, calibrated coverage and optimizer loss have separate units/interpretations. State gates, branch alternatives, multiple futures and individual lamp frames are correlated. Do not inflate the effective sample size or add overlapping signal coverage as independent observations.

A screen must retain every training replicate, fixed endpoint, original parent, unfavorable scenario and required tail/throughput constraint. Give classical methods matched sensing and supervision. Do not replace the primary result with a winning ablation, selected checkpoint, best horizon or favorable future set. An interval spanning zero establishes neither superiority nor equivalence.

### 25.4 Safe inspection commands

The following use the existing historical environment and either show help or inspect an existing comparison; they start no training job:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -m research --help
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -m research train --help
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -m research evaluate --help
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -m research compare-spatial \
  results/research_training/spatial_v9_k2bg79oc
```

For a fresh environment use `server/.venv/bin/python`, as described below. Help/inspection of an installed module does not establish exact reproduction of a frozen experiment under different dependencies/source. The spatial, averaged-label and upstream-teacher batches already have completed outcomes; this reference intentionally provides no new long-training command for those failed recipes.

<a id="26-application-api-storage-and-integration-status"></a>
## 26. Application, API, Storage and Integration Status

### 26.1 Application responsibilities

`client/src/app/` contains the home/dashboard, simulation, real-world, city and research pages, including experiment/comparison/replay/run-detail views. Components render simulation and explainability data; hooks and stores manage connections/history. Next.js server routes use Prisma for application data. FastAPI owns live simulation/training/city/CCTV/research sessions and model/history services.

The application and audited research trainer share components but have different integration paths. The research v5 reward/replay corrections and v7/v8/v9 encodings are not a certified website migration. UI controller labels, displayed episode totals and a successful build do not prove which weights execute or that the noisy-input boundary matches the audited runtime.

### 26.2 Current HTTP and WebSocket entry points

FastAPI registration is in [main.py](server/app/main.py); request/response details belong to the corresponding router/models. With a configured application, `/docs` exposes its OpenAPI description and `/health` provides health status. This inventory supersedes the historical route/payload examples above:

| Route family | Examples / responsibility | Implementation |
| --- | --- | --- |
| `/simulation` | Start/stop/reset, mode/scenario, status, scenario creation/deletion and grouped scenario runs. | [simulation router](server/app/routers/simulation.py) |
| `/training` | Scenarios, start/stop/status, model listing and loading. | [training router](server/app/routers/training.py) |
| `/metrics/current` | Current application metrics snapshot. | [metrics router](server/app/routers/metrics.py) |
| `/analytics` | Dashboard summary and application benchmark data. | [analytics router](server/app/routers/analytics.py) |
| `/cctv` | Upload/video/session management, twin data and detector-model status/load. | [CCTV router](server/app/routers/cctv.py) |
| `/research` | Scenarios, controllers, seeds, noise presets, summary, runs/details and table retrieval. | [research router](server/app/routers/research.py) |
| Next.js `/api/*` | Episodes, models, simulations, metrics and keep-alive application routes. | [Next.js API directory](client/src/app/api/) |

The research HTTP endpoints include `GET /research/scenarios`, `/controllers`, `/seeds`, `/noise-presets`, `/summary`, `/runs`, `/runs/{experiment_id}` and `/tables/{table_name}`. The summary/table router still reads historical `results/final/` assets. Serving them successfully does not make their claims audited; consumers must use current research status/provenance. Controller capabilities describe registered software, not a guarantee of loaded trained weights.

WebSockets are mounted at `/ws/simulation`, `/ws/training`, `/ws/city`, `/ws/cctv` and `/ws/research`. Research messages use a `command` field with values including `start_experiment`, `start_paired_comparison`, `pause`, `resume`, `stop`, `set_speed`, `seek` and `replay_run`. Inputs such as `scenario_id`, controller(s), seed and `noise_preset` are top-level fields in the current handler, not the old nested `type/config` example. Live/replayed research frames use `research_frame`.

Read [research_ws.py](server/app/websockets/research_ws.py) and [research types](client/src/types/research.ts) together before integrating a client. The live handler has application-specific scenario fallback/session behavior; it is not equivalent to strict headless scenario validation merely because both import common modules. This documentation update does not alter that behavior.

### 26.3 Persistence and model identity

The [Prisma schema](client/prisma/schema.prisma) models simulations, episodes, signal states, traffic logs, RL models and performance metrics. Backend [model_service.py](server/app/services/model_service.py) and [supabase_service.py](server/app/services/supabase_service.py) participate in model/storage workflows. Checkpoints use local `server/models/` storage and the configured Supabase `model-checkpoints` bucket. Generated research artifacts are separately preserved under `results/`.

`npm ci` generates the Prisma client; it does not apply database schema changes. SQL/scenario setup under `server/data/migrations/` and Prisma schema management are separate operations. Review changes against an existing database; use a dedicated development project for setup. Do not run reset/migration utilities as part of reading or checking this reference.

Earlier user reports included Supabase HTTP/2 `RemoteProtocolError` on model queries, training apparently stuck at zero, duplicate history and inaccurate episode/model labels. Research verification does not certify every early application issue resolved. Verify end-to-end listing, training progress, save/load/reload, history deduplication and metadata/version compatibility separately. A dashboard episode count alone is insufficient: inspect model ID, actual checkpoint metadata and SHA-256.

### 26.4 Camera and city boundaries

Camera code is organized under `server/app/realworld/{pipeline,digital_twin,training,models,utils}/`. It includes stream resolution, video processing, detection/tracking, ROI/count/state construction, session recording/replay and model training/export helpers. Vision extras and weights are optional installation/data concerns, not bundled validated field assets.

The city UI and simulation modules provide a separate network application path. Neither camera/city existence nor UI explanation panels validate the audited single-intersection demand model, camera accuracy, network generalization, physical hardware operation or research/UI equality. Recorded-camera replay, measured traffic calibration, shadow recommendations and operator/intersection engineering remain future validation work.

<a id="27-installation-operations-security-and-open-source-conventions"></a>
## 27. Installation, Operations, Security and Open-Source Conventions

### 27.1 Reproducible development setup

Fresh installations target **Python 3.11**, CPU Torch **2.3.1+cpu**, matching Torchvision **0.18.1+cpu**, and NumPy **>=1.26.4,<2**. YAML is an explicit core dependency because scenario loading is used by the API as well as research. These are the current installation baseline, not the dependency provenance of every historical experiment. The existing `server/venv` Python 3.14 environment is preserved for its recorded work.

Node.js **24** is selected by `.nvmrc`, with npm 10 or newer and `client/package-lock.json` as the canonical lockfile. The application engine floor is Node 20.9. Duplicate pnpm configuration/lockfiles were removed. Use the setup guide rather than creating parallel package-manager lockfiles.

For a new checkout, from the repository root:

```bash
python3.11 -m venv server/.venv
server/.venv/bin/python -m pip install -r research/requirements.txt -r server/requirements-dev.txt
cp server/.env.example server/.env
cp client/.env.example client/.env.local
npm --prefix client ci
```

Copy the templates only when setting up new private configuration; preserve existing local files. For application-only Python dependencies use `server/requirements.txt`. Research adds its analysis/reporting dependencies through `research/requirements.txt`; optional detector training/dataset/export tools use `server/requirements-vision.txt`. Footage, datasets and model weights are not bundled. Optional camera startup may obtain upstream weights; that is separate from reproducible research checkpoints.

On Windows create the environment with `py -3.11 -m venv server/.venv` and use `server\.venv\Scripts\python.exe`. The existing `server/venv` layout remains supported; cleanup did not rename/delete research environments.

### 27.2 Configuration and startup

| Private file | Variables / purpose |
| --- | --- |
| `server/.env` | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CORS_ORIGINS`, optional `SIGNAL_RED_DURATION`. Secret/service-role key aliases are also recognized by backend settings. |
| `client/.env.local` | `DATABASE_URL`, `DIRECT_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_FASTAPI_HTTP_URL`, `NEXT_PUBLIC_FASTAPI_WS_URL`. |

Backend settings load `server/.env` through an absolute path. Never put a service-role/secret key or database password in a `NEXT_PUBLIC_` variable. Public frontend environment values are embedded at build time. Hosted frontends require the correct HTTPS/WSS backend URLs and explicitly configured browser origins.

Application startup requires valid private Supabase configuration. Most research tools do not. `TrafficEnv` imports API settings lazily only when application-default red duration is needed; research scenarios that supply explicit timing do not require API credentials just to construct an environment. This preserves application settings validation while separating headless mechanics from storage credentials. Application default all-red is three seconds; a research scenario's recorded timing is authoritative for its experiment.

Run the configured services in separate terminals:

```bash
server/.venv/bin/python -m uvicorn app.main:app --app-dir server --reload --port 8000
npm --prefix client run dev
```

The UI is at `http://localhost:3000`, API documentation at `http://localhost:8000/docs` and health at `http://localhost:8000/health`. Keep the repository's `research/` directory alongside `server/`: the application imports shared research sensor/controller support.

### 27.3 Containers and hosting

The backend Docker build uses the repository root as its context so it includes research imports. The image runs as a non-root user; `.dockerignore` excludes private environment files, dependencies, local data, results and checkpoints. Supply runtime configuration separately. Optional vision tools/weights require an explicitly prepared image or installation.

`docker compose up --build server` starts the backend service only; it does not provision Supabase or start the frontend. [render.yaml](render.yaml) describes backend hosting using the supported Python baseline. Deploy the frontend from `client/` with its own environment. Container/hosting configuration has been reviewed and compose configuration parsed; a full image build and deployed end-to-end application were not established by that check.

### 27.4 Security and contributor boundaries

[SECURITY.md](SECURITY.md) describes a research prototype intended for trusted development/simulation. The service includes training, file/stream, model and database operations without a complete multi-user authentication/authorization boundary. Production-style organization and CI do not make it a publicly hardened service or certified controller.

Arbitrary HTTP origin matching was removed. Defaults allow local development origins on localhost/127.0.0.1 ports 3000/3001; hosted origins must be configured through `CORS_ORIGINS`. **CORS is not authentication.** Review access control, upload/stream handling, network exposure and storage permissions before public hosting.

Treat external checkpoint/model files as untrusted and validate known provenance before loading. Keep private keys, footage and database contents out of commits, screenshots and issues. Third-party footage/datasets/weights retain their own licensing and privacy obligations. Use private vulnerability reporting when available; the repository does not promise a response-time/support period.

The root [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [CITATION.cff](CITATION.cff) and [LICENSE](LICENSE) define contribution, community, software-citation and source-license information. Software citation metadata is not a paper DOI or peer-reviewed acceptance. `.editorconfig`, centralized ignore rules and environment examples support consistent development; generated caches, secrets, checkpoints and local results remain excluded from version control.

<a id="28-verification-and-quality-gates"></a>
## 28. Verification and Quality Gates

### 28.1 Latest recorded implementation checks

The latest broad backend run during repository reorganization used a fresh Python 3.11.15 environment and completed **504 tests with one existing Starlette/httpx deprecation warning in 106.23 seconds**. This is a recorded implementation check, not a rerun caused by this documentation edit. Historical totals such as 53, 82, 92, 217 and 126 describe their respective snapshots/subsets and must not be added as unique coverage.

| Check | Recorded result / practical limit |
| --- | --- |
| Full backend/research suite | 504 passed; one dependency deprecation warning. Covers the recorded source snapshot, not every deployment or external service. |
| Research tool discovery | Forty maintained tool `--help` checks passed. Help checks establish imports/argument discovery, not successful expensive execution. |
| Fresh source-only checkout | Core train/evaluate/compare help works without private API credentials or local checkpoints. Missing experimental artifacts remain missing. |
| Frontend | ESLint, TypeScript checking and production build passed. Local checks used Node 26.8.1; declared fresh/CI baseline is Node 24. Font download required network. |
| Scenario/configuration preservation | Nineteen scenario/manifest JSON/YAML files remained byte-identical across organization; frozen parent identities preserved. |
| Saved spatial comparison | Recomputed result matches the saved failed screen. This is report reproduction, not new independent evaluation. |
| Shell/container metadata | Shell syntax, YAML parsing and `docker compose config --quiet` passed. Docker image execution/build was not established. |
| Source/format hygiene | Repository checks and `git diff --check` are the maintained documentation/source-layout checks. No claim that all external links or raw datasets were fetched. |
| Integration/deployment | Remote CI completion, browser/camera end-to-end flows, real hardware and physical signal operation have not been established by these local checks. |

The repository checker validates maintained local Markdown paths, dependency/lock metadata, Python syntax, research imports/package ownership, shell syntax, declared protocol paths and ignored private/generated files. Local artifact links are optional in a fresh clone; the checker does not certify their numerical contents. Machine-specific links in the restored original CONTENT reference have been normalized or explicitly marked as absent historical paths in this update.

### 28.2 Maintained local commands and CI

The [Makefile](Makefile) provides `check-repository`, `lint`, `typecheck`, `test`, `build`, `check`, `server` and `client`. Python selection prefers `server/.venv`, then existing `server/venv`, then `python3`; override `PYTHON` explicitly when a particular environment matters. `make check` includes repository/lint/type/test checks; production build is separate.

```bash
make check-repository
make lint
make typecheck
make test
make build
```

For changes specifically affecting spatial mechanics, an existing-environment targeted check is:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -m pytest \
  server/tests/test_spatial_policy.py \
  server/tests/test_spatial_pilot.py \
  server/tests/test_upstream_observation.py \
  --no-cov -p no:cacheprovider -q
```

The [GitHub Actions workflow](.github/workflows/ci.yml) runs repository checks, Node 24 frontend installation/lint/type/build, and Python 3.11 backend/research tests. It triggers on main pushes, pull requests and manual dispatch, with read-only contents permission and cancellation of superseded jobs. Placeholder frontend environment values support build checks; they are not a provisioned database or deployed service. Configuring a workflow is distinct from observing a successful remote run.

### 28.3 Repairs made during repository preparation

Repository cleanup included more than moving files: repaired missing `Optional`/`Tuple`/`Any` imports exposed by fresh imports, explicit YAML dependency, NumPy/Torch ABI alignment, separation of optional vision dependencies, lazy simulation settings, corrected source/container context and explicit CORS origins. Maintained imports, test references, launcher paths, manifest loading and protocol/source-archive resolution were updated for package organization.

The historical all-in-one reproduction command and hard-coded figure generators now refuse to produce misleading checkpoint-free results. Their files remain for explanation/provenance. No cleanup altered old checkpoints or manufactured favorable tables. Source organization, passing tests and an open-source contribution guide improve maintainability; they do not establish the scientific objective.

<a id="29-paper-scope-novelty-and-remaining-requirements"></a>
## 29. Paper Scope, Novelty and Remaining Requirements

### 29.1 Existing writing/evidence assets

The [audited manuscript scaffold](research/docs/papers/PAPER_DRAFT_AUDITED_20261016.md) and `results/paper_evidence/audited_v5_20261016/` preserve the corrected evaluation methods/tables/figures. [build_paper_evidence.py](research/evidence/build_paper_evidence.py) verifies compatible provenance before export. The [October 22 addendum](research/docs/papers/PAPER_ADDENDUM_OBSERVATION_AND_TEACHERS_20261022.md), [teacher evidence exporter](research/evidence/export_teacher_evidence.py) and `results/paper_evidence/teacher_diagnostics_20261022/` document later input-use/teacher/horizon development findings.

Exporters are experiment-specific. A compatible old evaluation export does not automatically ingest every later pilot, and a generated figure is not a new experiment. Historical hard-coded figure generation is disabled. Keep the frozen manuscript panel separate from later consumed development observations and unfavorable results.

### 29.2 What novelty checking has and has not established

The [source-checked novelty triage](research/docs/papers/RESEARCH_NOVELTY_TRIAGE_20261022.md) records targeted primary-source checks, not a systematic literature review. It identifies close precedent for spatial pressure/representations (Advanced-MP/Advanced-XLight), switching-aware learned pressure control, counterfactual traffic-control methods and robustness benchmarking. The repository's baseline does not reproduce those methods merely by changing an incoming-count accessor.

A particularly close uncertainty-gated DQN bibliographic lead remains **methodologically unverified** because the primary IEEE page was inaccessible during that review. Its title/index listing is not enough to characterize its full method. Retrieve and compare it before claiming novelty. Prior papers' reported gains are not FlowSync measurements, and absence of an exact phrase match would not prove a first contribution.

The candidate paper direction is a simulation-only empirical methods/failure analysis: evaluation authority matters; count-error uncertainty differs from fallback benefit; hindsight labels can be future-sensitive; richer observed features can move Q magnitudes without changing actions; and geometric demand specificity can fail to improve closed-loop control. That direction still needs novelty assessment and external replication. It does not fulfill the original superior-controller objective by changing the paper's label.

### 29.3 Outstanding scientific and application requirements

| Requirement | What remains to establish |
| --- | --- |
| Reliable control gain | A fixed-endpoint, multi-training-replicate development improvement against original parents and matched strong classical control, preserving mean/tail delay, throughput and interventions. |
| Attribution | Evidence linking a specific new mechanism to useful decisions rather than imitation, warm start, baseline mismatch or selected favorable cases. |
| Useful uncertainty | Validated selective fallback/correction benefit; detecting count error or always abstaining does not establish it. |
| Strong baselines | Equally informed/supervised classical methods and faithful relevant research baselines, rather than renaming the historical Max-Pressure. |
| Independent simulator/demand validity | Replication in an established traffic simulator and validation against independent traffic families/counts/timings. No independent simulator was installed or substituted during the latest diagnostics. |
| Confirmatory testing | Freeze choices and analysis after genuine development progress, then evaluate an independent uninspected panel. Consumed final/probe data cannot be reused as fresh. |
| Statistical scope | Account for policy-training and traffic randomness, correlation among branches/futures, multiple choices and finite safety coverage. |
| Website integration | Verify observation/reward/checkpoint compatibility, training/inference behavior, model identity, persistence/history and headless/UI parity end to end. |
| Real-world progression | Recorded-camera replay, measured traffic calibration, shadow recommendations, hardware timing and intersection/operator engineering validation before signal actuation. Outside the current simulation-only scope. |
| Public deployment | Authentication/authorization, storage/upload/stream hardening and operational controls appropriate to a public service. Current organization does not certify this. |

Simulator limitations include simplified motion, backlog visibility assumptions, permissive turns, missing validated pedestrian behavior and incident capacity represented through discharge headways. Zero measured lamp conflicts do not cure these limitations. No defensible publication-ready percentage or universal superiority claim follows from current evidence.

### 29.4 Current decisions under the time constraint

The completed spatial, temporal, averaged-label and immediate upstream-teacher recipes remain closed/failed. Do not rerun identical batches, extend to 900/1,000 episodes, cherry-pick seeds/checkpoints, tune on previous final outcomes, loosen screens or silently replace a website default. The last bounded diagnostics did not reveal a reproducible input-delivery or reward-direction defect warranting a specific training correction.

A future experiment needs a new evidence-based mechanism, matched controls, a declared budget, fixed endpoints and continuation criteria **before** inspection. Only a passing bounded development screen justifies expanded fresh development and a later independent final test. The user prefers to execute long jobs; no new long command is ready or warranted by the completed negative results. Methods/limitations writing can proceed from the preserved evidence while the superior-controller objective remains open.

<a id="30-evidence-and-maintenance-index"></a>
## 30. Evidence and Maintenance Index

### 30.1 Source-of-truth navigation

| Question | Read / inspect |
| --- | --- |
| Current research outcome | [RESEARCH_STATUS.md](research/RESEARCH_STATUS.md) |
| Why the old evaluation is invalid | [EVALUATION_AUDIT.md](research/EVALUATION_AUDIT.md) |
| Current research commands/packages | [research README](research/README.md), [command dispatcher](research/__main__.py) |
| Protocol/result/archive organization | [research documentation index](research/docs/README.md) and its protocols/results/audits/papers indexes |
| Reward/replay mechanics | [learning audit](research/docs/audits/LEARNING_UPDATE_AUDIT_20261015.md), [research trainer](research/training/train_policy.py) |
| Observation versions and spatial delivery | [observation schema](server/app/rl/observations.py), [runtime](research/experiments/runtime.py), [spatial count adapter](research/noise/spatial_counts.py) |
| Spatial outcome and input-use findings | [spatial results](research/docs/results/SPATIAL_INPUT_RESULTS_20261021.md), [input-use audit](research/docs/audits/SPATIAL_INPUT_AUDIT_RESULTS_20261022.md) |
| Teacher/horizon findings | [teacher results](research/docs/results/TEACHER_ALIGNMENT_RESULTS_20261022.md), [teacher audit](research/audits/audit_teacher_alignment.py), [horizon audit](research/audits/audit_teacher_horizon.py) |
| App/headless split | [architecture guide](docs/architecture.md) |
| Installation/deployment | [setup guide](docs/setup.md), [server README](server/README.md), [client README](client/README.md) |
| Local artifacts and missing fresh-clone weights | [artifact policy](results/README.md) |
| Contribution/security/CI | [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [repository checker](scripts/check_repository.py), [workflow](.github/workflows/ci.yml) |
| Paper claims and limits | [paper index](research/docs/papers/README.md), [novelty triage](research/docs/papers/RESEARCH_NOVELTY_TRIAGE_20261022.md) |

### 30.2 Maintaining this comprehensive reference

Keep a dated distinction between implemented behavior, measured outcomes, hypotheses and future requirements. Add completed failures as well as successes. Record experiment identity, role seeds, checkpoint/source provenance, endpoint, units and limitations with any new quantitative claim. Do not replace raw evidence with a copied summary or silently update an old frozen result.

Use portable repository-relative links in this document. Some earlier links named files that are absent or were only design references; those paths remain inline and explicitly historical, rather than being redirected to an unrelated file. Current source links above point to maintained implementations. Local ignored artifacts may be unavailable in a fresh clone; provide provenance and an artifact policy rather than pretending the source includes trained weights or footage.

This update covers research evidence through October 22 and the current repository preparation, while retaining the original sections for traceability. Earlier branch/commit lists and numeric tables are historical snapshots, not live release metadata. Updating this file does not rerun training, migrate a database, promote a checkpoint, deploy a service or establish a paper result.

---

[Back to Top](#top)

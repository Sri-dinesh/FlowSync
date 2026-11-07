# FlowSync

> **An Audited Evaluation of Deep Reinforcement Learning Traffic Signal Control Against Classical Baselines Under Observation Delay and Noise**

FlowSync is an open-source traffic signal control research platform and discrete-event simulation application. It provides an audited, reproducible testbed designed to evaluate deep reinforcement learning (D3QN) against fair, well-tuned classical signal controllers under real-world sensing degradations (observation delay, count noise, and missed detections).

---

## High-Level Overview

Traffic signal optimization using Deep Reinforcement Learning (DRL) often reports dramatic efficiency improvements over fixed-time baselines. However, many published evaluations omit comparisons against strong classical baselines, overlook the runtime cost of physical safety constraints, or assume idealized, noise-free sensor data.

FlowSync addresses these gaps through an audited experimental protocol featuring:
- **2,800 Matched Simulation Runs:** Evaluated over 7 distinct traffic scenarios (including held-out out-of-distribution demand) using Common Random Numbers (CRN) across all controllers.
- **Fair Baseline Tuning:** Classical controllers (including NEMA-style Actuated control) were tuned with equal computational effort on dedicated training scenarios with zero evaluation data leakage.
- **Formal Zero-Violation Safety Shield:** A finite-state machine (FSM) enforcing physical signal legality (minimum green, yellow change, all-red clearance, and max starvation prevention) with 0 recorded violations across 4.34 million simulation steps.
- **Realistic Sensing Perturbations:** Controlled observation delays (1 to 5 s), additive/multiplicative count noise, and missed vehicle detections to isolate perception vulnerabilities.
- **Full-Stack Application:** Includes a FastAPI backend, custom discrete-event simulation engine, WebSockets telemetry streaming, and an interactive Next.js visualization UI.

---

## System Architecture

```
                      +---------------------------------------+
                      |       Next.js Web Client (UI)        |
                      |  (Interactive Dashboard & Canvas 2D) |
                      +-------------------+-------------------+
                                          | WebSockets / REST
                                          v
                      +---------------------------------------+
                      |          FastAPI Server Core          |
                      +-------------------+-------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+---------------+               +-------------------+             +-------------------+
|  Controllers  |               | Formal Safety FSM |             | Simulation Engine |
| - Fixed-Timer |               | - Min green (8s)  |             | - Discrete-event  |
| - Actuated    |--[Proposed]-->| - Max green (40s) |--[Executed]->|   micro-simulation|
| - Greedy      |    Action     | - Yellow (2s)     |   Phase     | - 12 movements    |
| - Max-Pressure|               | - All-red (3s)    |             | - dt = 0.1s       |
| - D3QN        |               | - Starvation (45s)|             | - CRN spawner     |
| - FlowSync-UQ |               | (Zero violations) |             +-------------------+
+---------------+               +-------------------+                       |
        ^                                                                   |
        |================== Observed Queue / Latency =======================+
```

---

## Controllers Compared

1. **Fixed-Timer:** Standard baseline cycling through fixed phase splits equal to minimum green (8 s).
2. **Actuated (VAT):** NEMA-style vehicle-actuated control with gap-out logic, retuned on training scenarios (passage time 1.5 s, max green 40 s).
3. **Greedy:** Dynamic heuristic serving the phase with the highest instantaneous queue demand.
4. **Max-Pressure:** Classical distributed feedback control balancing upstream queue pressure against downstream link capacity.
5. **D3QN (Dueling Double DQN):** Deep Q-Network with Dueling architecture, LayerNorm, and Prioritized Experience Replay (PER), trained across 3 independent seeds.
6. **FlowSync-UQ:** Supervisory architecture combining D3QN, formal safety shielding, and observation monitoring to fall back to Max-Pressure under degraded sensing.

---

## Key Audited Findings

The project's audited empirical results (detailed in [context.md](context.md) and [`paper_results/`](paper_results/tables/T2_main_comparison.csv)) establish:

- **RL vs. Classical Baselines:** D3QN significantly outperforms Fixed-Timer (-25.8% mean delay, 11.76 s vs 15.85 s, $p < 10^{-48}$). However, D3QN is **statistically indistinguishable** from classical Max-Pressure (11.74 s) and Greedy (11.94 s) across all 7 scenarios (all Holm $p \ge 0.33$). In held-out OOD traffic, D3QN provides no advantage over Max-Pressure (14.90 s vs 14.51 s).
- **The "Shield Tax":** Guaranteeing zero physical signal violations imposes a statistically significant delay cost averaging +0.62 s on D3QN and +0.55 s on Max-Pressure across scenarios (+0.54 s on Clean Balanced, $p = 0.0169$).
- **Observation Delay is the Dominant Risk:** A 5 s observation delay increases delay by +13.8% on unshielded D3QN (vs +9.1% on Max-Pressure). The safety shield acts as a stabilizer, cutting D3QN degradation in half (+6.2%). Additive count noise ($\sigma = 3\text{ veh}$) degrades learned and classical controllers equally (~+14%).
- **Supervisor Trigger Mechanics:** Code and trace audits confirm the uncertainty supervisor acts as a deterministic latency flag (>1,000 ms), triggering 99.34% fallback to Max-Pressure under delay (11.8238 s vs 11.8238 s).

---

## Project Structure

```
FlowSync/
├── client/              # Next.js web application (React, Tailwind, Canvas 2D)
├── server/              # FastAPI backend, simulation engine, controllers, PyTorch models
│   ├── app/             # Application routes, models, and simulation logic
│   └── tests/           # Regression and unit test suite
├── paper_results/       # Authoritative research evidence
│   ├── tables/          # Formatted CSV results tables (T1, T2, T4, T5, T6, T7)
│   ├── figures/         # 300 DPI publication-ready figures (F1 to F5)
│   └── results.json     # Machine-readable claims, audit metrics, and gates
├── research/            # Scenarios, SUMO network definitions, and protocols
├── context.md           # Single source-of-truth results reference document
├── CONTENT.md           # Comprehensive application, architecture & research guide
└── README.md            # High-level project summary (this file)
```

---

## Getting Started

### Prerequisites
- Python 3.11+ (Python 3.14 recommended for server environment)
- Node.js >= 20.9.0 and npm >= 10

### 1. Server Setup
```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd client
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the interactive simulation UI.

### 3. Running Verification & Repository Checks
```bash
# Run documentation and methodology verification
server/venv/bin/python scripts/check_repository.py

# Run server unit and regression test suite
server/venv/bin/python -m pytest server/tests/ -q
```

---

## Maintained Documentation & References

- [Results Reference Document](context.md) — Single source of truth for all experimental numbers, tables, and claims.
- [Comprehensive Reference (CONTENT.md)](CONTENT.md) — Exhaustive system architecture, methodology attribution, and research records.
- [Application Architecture](CONTENT.md#2-current-system-architecture)
- [Methods & Technique Attribution](CONTENT.md#14-technique-attribution-and-primary-references)
- [Installation & Operations Guide](CONTENT.md#27-installation-operations-security-and-open-source-conventions)
- [Verification & Quality Gates](CONTENT.md#28-verification-and-quality-gates)
- [Audited Results Section](CONTENT.md#57-paper-results-reference-and-audited-empirical-evaluation)

---

## Research Scope & Notice

FlowSync is a research testbed designed for simulation-based empirical evaluation. Real-world intersection deployment, camera perception accuracy, and physical traffic actuation remain outside the current verified scope.

- **License:** [MIT License](LICENSE)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy:** See [SECURITY.md](SECURITY.md)

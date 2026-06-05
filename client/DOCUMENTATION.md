# FlowSync: AI Traffic Simulation

FlowSync is an intelligent, real-time 3D traffic simulation platform that leverages Reinforcement Learning (RL) to optimize traffic light signaling. The frontend provides a stunning, production-ready 3D environment to visualize the AI in action, alongside a comprehensive analytics dashboard.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Core Terminology](#core-terminology)
3. [Frontend Structure](#frontend-structure)
4. [3D Environment & Animation](#3d-environment--animation)
5. [Data Flow](#data-flow)

---

## System Architecture

The application is built on a modern decoupled architecture:

*   **Frontend (Client):** Built with Next.js, React, TailwindCSS, and React Three Fiber (Three.js). It is responsible for rendering the 3D environment, animating vehicles, and displaying real-time analytical dashboards.
*   **Backend (Server - External):** A high-performance Python backend (using FastAPI) that runs the actual physics simulation and the Reinforcement Learning agent.
*   **Communication:** 
    *   **WebSockets:** Used for ultra-low latency, real-time streaming of simulation frames (vehicle positions, light colors) and live training metrics.
    *   **REST API:** Used for fetching historical data, saved models, and previous simulation metrics from a database (via Prisma).

---

## Core Terminology

To understand the analytics dashboard and the AI's behavior, it is important to know the following Reinforcement Learning and Traffic metrics:

*   **Simulation Mode:** 
    *   `Fixed`: Traditional traffic lights operating on a set, static timer (e.g., 30 seconds green, 5 seconds yellow, 30 seconds red).
    *   `AI`: The Reinforcement Learning agent dynamically controls the lights based on real-time traffic conditions.
*   **Simulation Frame (Timestep):** A single snapshot of the simulation environment at a specific millisecond, containing the exact positions of all vehicles, queue lengths, and the current traffic light phase.
*   **Episode:** A single, isolated run of the simulation used during AI training. An episode runs for a fixed number of steps (or until a failure state). After an episode ends, the AI updates its internal neural network based on the results and starts a new episode, gradually getting smarter.
*   **Reward:** The "score" given to the AI during training. The AI's sole goal is to maximize this number. It receives positive rewards for letting cars through and negative penalties (negative rewards) when cars wait too long or queues back up.
*   **Epsilon (Exploration Rate):** A core concept in Q-Learning (RL). Epsilon dictates how often the AI tries a *random* action versus its *best known* action. At the start of training, Epsilon is high (close to 1.0) so the AI explores wildly. Over time, it decays towards 0, meaning the AI exploits its learned knowledge to behave optimally.
*   **Throughput:** A primary performance metric. It measures the total number of vehicles that successfully navigate and exit the intersection within a given timeframe. Higher is better.
*   **Average Wait Time:** The average time (in seconds) that vehicles currently in the system have spent stopped in traffic. Lower is better.
*   **Queue Length:** The number of cars waiting at a red light in a specific lane (North, South, East, West).

---

## Frontend Structure

The Next.js client is organized as follows:

*   **`/src/app/`**: Contains the main Next.js pages and REST API routes (`/api/metrics`, `/api/episodes`).
*   **`/src/components/simulation/`**: The React Three Fiber components. This contains the 3D logic for the roads, buildings, traffic lights, and vehicles.
*   **`/src/components/dashboard/`**: The UI components overlaying the simulation, including charts (Recharts), data tables, and metrics panels.
*   **`/src/store/simulationStore.ts`**: A global state manager using Zustand. It holds the latest WebSocket frame, the history of training metrics, and the connection status.
*   **`/src/hooks/`**: Custom React hooks handling the WebSocket connections (`useSimulationSocket`, `useTrainingSocket`) and REST data fetching (`useEpisodes`, `useSimulations`).

---

## 3D Environment & Animation

The 3D scene is fully parameterized to ensure physical accuracy and visual polish:

*   **Spatial Grid:** The intersection adheres strictly to a Right-Hand Traffic mathematical grid. 
    *   North is mapped to `-Z`
    *   South is mapped to `+Z`
    *   East is mapped to `+X`
    *   West is mapped to `-X`
*   **Vehicle Paths:** Vehicles do not move randomly. Their turning paths are defined by **Cubic Bezier Curves**.
    *   *Right Turns* are tight radius arcs hugging the sidewalks.
    *   *Left Turns* travel deep into the center of the intersection before arcing, preventing collisions with oncoming traffic.
*   **Animation Logic:** To prevent vehicles from "bunching up" or moving erratically during turns, the frontend utilizes **Arc-Length Parameterization** (`getPointAt` in Three.js). This ensures that a vehicle's visual speed along the curved path maps exactly 1:1 with its logical speed on the backend, making the simulation look smooth and realistic. 

---

## Data Flow

1. **User Action:** The user clicks "Start Simulation" in the UI.
2. **Command Sent:** `useSimulationSocket` sends a JSON command `{ "action": "start", "mode": "ai" }` to the backend.
3. **Backend Processes:** The Python backend calculates the physics (car velocities, braking) and AI decisions for the next timestep.
4. **Frame Streamed:** The backend broadcasts a `SimulationFrame` over the WebSocket at roughly 30-60 frames per second.
5. **State Update:** `simulationStore` receives the frame, updating `currentFrame`.
6. **Re-render:** 
   - The UI Dashboard updates its charts and sparklines.
   - The `SimulationCanvas` reads the new target positions for the vehicles.
   - The `useFrame` loop in `Vehicle.tsx` smoothly interpolates (lerps) the 3D car models from their old position to the new backend-provided position.

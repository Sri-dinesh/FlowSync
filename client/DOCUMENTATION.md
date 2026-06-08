# FlowSync: AI Traffic Simulation

FlowSync is an intelligent traffic management system that uses Artificial Intelligence to solve one of the most frustrating parts of modern life: **traffic jams**. 

Instead of traffic lights running on simple timers, FlowSync uses a "Brain" (AI) that learns how to keep cars moving as efficiently as possible.

---

## 1. What is FlowSync?
FlowSync is a platform where you can watch an AI learn to manage a 4-way intersection. 
*   **The Problem:** Standard traffic lights don't know if there's a mile-long line in one direction and zero cars in the other.
*   **The Solution:** An AI that sees every car and decides when to change the lights to maximize "throughput" (getting as many cars through as possible) and minimize "wait time."

## 2. How it Works (The Simple Version)
Think of the project in three main parts:

1.  **The World (The Simulation):** A 3D environment where cars are spawned, drive, and stop at lights. This is where the physics happen.
2.  **The Brain (The AI):** A Reinforcement Learning agent (DQN). It watches the "World" and gets "Points" (Rewards) for doing a good job. If it lets cars wait too long, it loses points.
3.  **The Eyes (The Dashboard):** The website you see. It visualizes the 3D world and shows charts so you can see exactly how smart the AI is becoming.

## 3. What is What? (Key Terms)
*   **Episode:** Think of this as a "Practice Round." The AI runs the simulation for a few minutes, learns what it did wrong, and then starts a new episode to try again.
*   **Reward:** The AI's score. High reward = Happy AI (smooth traffic). Low/Negative reward = Sad AI (gridlock).
*   **Throughput:** The total number of cars that successfully crossed the intersection.
*   **Fixed Mode:** The "Old School" way. Lights change on a strict timer regardless of traffic.
*   **AI Mode:** The "Smart" way. The AI controls the lights dynamically.

## 4. Data Flow: What goes where?

### From Backend (Python) to Frontend (Next.js):
*   **Live Simulation Frames:** Every 30-60 times per second, the backend sends a "snapshot" of the world. It says: *"Car #5 is at these coordinates, Light #2 is Red."* The frontend takes this data and moves the 3D cars on your screen.
*   **Training Metrics:** While the AI is learning, the backend sends live updates on its "Score" (Reward) and "Smartness" (Loss/Epsilon).

### From Frontend to Backend:
*   **Commands:** When you click "Start," "Stop," or "Train," the frontend sends a signal to the backend to tell it what to do.

### The Database (Supabase):
*   **Memory:** When an Episode ends, the backend saves the results (how many cars passed, the average wait time) to the database.
*   **History:** When you open the "Episode History" tab on the dashboard, the frontend asks the database for all the past results so it can show them in a table.

## 5. Technology Stack
*   **Frontend:** Next.js (Web Framework), Three.js (3D Graphics), TailwindCSS (Styling), Zustand (State Management).
*   **Backend:** Python & FastAPI (The Server), PyTorch (The AI/Neural Network).
*   **Database:** Supabase (PostgreSQL) & Prisma.

---

# PITCH: How to explain FlowSync

When explaining FlowSync to a professional audience, you should present it as a **comprehensive digital twin and AI optimization platform**. Here is a structured narrative you can follow:

### 1. The Vision: From Static to Dynamic Infrastructure
"Most of our modern traffic infrastructure is based on 20th-century logic: fixed timers. FlowSync is a 21st-century solution that treats traffic as a dynamic, evolving data problem. We’ve built a system where the infrastructure doesn't just 'run'—it **learns**."

### 2. The Core Workflow: The "Cycle of Intelligence"
To explain how the AI actually operates, describe the continuous loop happening every millisecond:

*   **Step 1: Perception (Sense):** The system constantly monitors the 'State' of the intersection. It knows the exact position, speed, and wait time of every vehicle, along with the current status of every traffic light.
*   **Step 2: Decision (Think):** This data is fed into a **Deep Q-Network (DQN)**—a sophisticated AI model. Unlike a human, the AI can simulate thousands of possible light-change combinations in an instant to determine which action will result in the best traffic flow.
*   **Step 3: Execution (Act):** The AI chooses an action (e.g., 'Switch North-South to Green'). The simulation executes this in real-time, updating the physics and vehicle behaviors accordingly.
*   **Step 4: Optimization (Learn):** The system calculates a **Reward**. If traffic clears, the AI gets a 'positive' reward; if cars idle or queue up, it gets a 'negative' penalty. This feedback loop is how the AI trains itself to handle complex rush-hour patterns without human intervention.

### 3. The Architecture: A Real-Time Data Engine
The technical "magic" of FlowSync lies in its decoupled, high-performance architecture:

*   **The Brain (Python/FastAPI):** All heavy lifting—the physics engine and the AI training—happens in a Python backend. This ensures the simulation is mathematically accurate and the AI can process neural network calculations at lightning speed.
*   **The Nervous System (WebSockets):** To achieve a "live" feel, we don't use traditional API requests. Instead, we use a persistent **WebSocket connection**. The backend 'pushes' 60 frames of data every second to the frontend, allowing for seamless, lag-free 3D visualization.
*   **The Visualization (Next.js/React Three Fiber):** The frontend transforms raw coordinates into a stunning 3D environment. Using **Three.js**, we render every car and light in a spatial grid, allowing users to move the camera and inspect the AI's performance from any angle.
*   **The Memory (Supabase & Prisma):** Every practice round (Episode) is logged. We use **Supabase** for cloud storage and **Prisma** as our data bridge, allowing us to generate long-term performance charts that prove the AI is actually getting smarter over time.

### 4. Why This Matters (The Impact)
"FlowSync isn't just a visual tool; it's a proof of concept for **Smart Cities**. By reducing average wait times by even 10%, we can significantly reduce CO2 emissions from idling cars, save thousands of hours for commuters, and make our urban centers more efficient. We are using cutting-edge AI (PyTorch) and modern web tech (Next.js) to solve a real-world problem."

---

---

# PROJECT STRUCTURE: The Technical Map

FlowSync is organized into two main workspaces: the **Python Backend** (The Server) and the **Next.js Frontend** (The Client).

### 📂 `/server` (The Engine)
This is where the AI lives and the physics are calculated.
*   **`app/main.py`**: The entry point. It sets up the FastAPI server and manages the WebSocket routes.
*   **`app/rl/`**: The "Brain." Contains the Deep Q-Network (`dqn_network.py`) and the Agent logic (`dqn_agent.py`) that learns how to drive.
*   **`app/simulation/`**: The "World." 
    *   `environment.py`: The core logic that combines the AI and the traffic.
    *   `intersection.py`: Defines the physical layout of the 4-way intersection.
    *   `traffic_signal.py`: Manages the logic for switching light phases.
*   **`app/websockets/`**: Handles real-time communication, broadcasting every car's position to the frontend.
*   **`requirements.txt`**: Lists the Python dependencies (PyTorch, FastAPI, etc.).

### 📂 `/client` (The Interface)
The React-based dashboard and 3D visualization.
*   **`src/app/`**: The main pages and Next.js API routes.
*   **`src/components/simulation/`**: The 3D World (Three.js).
    *   `SimulationCanvas.tsx`: The main 3D container.
    *   `Vehicle.tsx`: Logic for rendering and animating individual cars.
    *   `TrafficLight.tsx`: The 3D model and light logic for signals.
*   **`src/components/dashboard/`**: The Analytics UI.
    *   `TrainingChart.tsx`: The live graph showing the AI's learning progress.
    *   `MetricsPanel.tsx`: Displays real-time stats like throughput and wait times.
    *   `EpisodeHistory.tsx`: The table that fetches past runs from the database.
*   **`src/store/simulationStore.ts`**: The global "State Management" (Zustand). It acts as the bridge between the incoming WebSocket data and the UI components.
*   **`prisma/schema.prisma`**: Defines the database structure for saving Episodes and Simulations.

### 📂 Root Level
*   **`docker-compose.yml`**: Allows you to run the entire system (Database, Backend, Frontend) with one command.
*   **`.agents/`**: Contains specialized instructions for AI agents working on this codebase.


# FlowSync: Team Pitch Script

### 👤 Role 1: Lead Engineer (Master Architect & System Integration)
*   **The Vision:** I led the development of FlowSync, a "Digital Twin" platform that uses Reinforcement Learning to modernize urban traffic management by replacing static timers with an autonomous, learning brain.
*   **System Architecture:** I designed a decoupled architecture that separates the heavy AI processing (Python) from the 3D visualization (React). This allows the AI to "think" at high frequencies while the frontend renders a smooth, 60fps representation of the data.
*   **AI & Logic Engine:** We implemented a Deep Q-Network (DQN) using PyTorch. I architected the "State-Action" mapping where the system reads the traffic density (State) and predicts the best light phase (Action) to minimize the cumulative wait time across the intersection.
*   **Backend & Physics Integration:** Our core engine is built with FastAPI. I ensured that the physics engine (handling car kinematics) is tightly synchronized with the AI model, allowing for real-time decision-making and immediate physics updates.
*   **Real-Time Pipeline:** To achieve "live" visualization, I set up a persistent WebSocket pipeline. The backend streams every vehicle's 3D coordinates and signal states as JSON packets, which are instantly mapped to our 3D models in the browser.
*   **3D Visualization & Analytics:** I oversaw the development of the React Three Fiber dashboard. This isn't just a UI; it's a visual debugger for the AI, allowing us to watch the neural network's decisions and monitor live performance charts simultaneously.
*   **Database & Persistence:** I managed the data persistence layer using Supabase and Prisma. Every training round (Episode) is saved, allowing us to generate the historical reports and learning curves that prove the AI's efficiency gains over time.
*   **The Workflow Mastery:** I implemented the "Perception-Action-Learning" loop: the system Senses the traffic, the AI Thinks of the optimal phase, the Simulation Acts on that decision, and the system Learns by updating its neural weights based on the resulting traffic flow.

### 🎨 Role 2: Frontend Developer (UI & 3D Visualization)
*   I created the 3D world using React Three Fiber and Three.js to show the cars and traffic lights.
*   I set up the WebSocket connection to receive live data from the backend so the cars move in real-time.
*   I built the dashboard charts using Recharts to display live stats like the AI's score and traffic speed.
*   I used Zustand to manage the project's data, making sure the website stays fast and responsive.
*   I added easy-to-use controls that let users move the camera and switch between the different ways the lights work.

### ⚙️ Role 3: Backend Developer (AI & Traffic Engine)
*   I built the traffic engine in Python that handles how cars drive, stop, and turn.
*   I used PyTorch to build the "Brain" of the AI, teaching it how to decide when to change the lights.
*   I set up the rules for the AI, giving it "Points" for moving traffic and "Penalties" for making cars wait.
*   I used FastAPI to make sure the backend can handle the math and send data to the website at the same time.
*   I created the system that converts the traffic data into a simple format so the website can read it instantly.

### 💾 Role 4: Database Engineer (Data Storage & History)
*   I set up the database using Supabase to save every simulation and practice round for later review.
*   I used Prisma as a bridge to connect our data to the website, making it easy to save and load information.
*   I implemented the logic that saves the AI's progress at the end of every round, including the total score and wait times.
*   I optimized the data routes so the dashboard can quickly show tables of past performance for all recorded runs.
*   My focus was on data safety, ensuring that the AI's learning results are accurately stored and easy to access.

---

### 🧠 Technical Core: Backend Deep-Dive
For a more technical explanation, here is the architecture of our backend engine:

*   **Physics Engine:** Built using Python kinematics to handle vehicle acceleration curves, deceleration, and lane-switching logic. It calculates the 3D position of every vehicle 60 times per second.
*   **RL Environment:** A custom Gymnasium-style environment. It translates the raw physics data into a 12-dimensional "State Vector" (queue lengths, light status, and density) that the AI can understand.
*   **Deep Q-Network (DQN):** The AI core uses a multi-layer neural network in PyTorch. It employs an **Experience Replay Buffer** to store past events and a **Target Network** to ensure the learning process remains stable.
*   **Optimization Logic:** We use **Huber Loss** and the **Adam Optimizer** to update the neural weights. The "Reward Function" is mathematically balanced to prioritize "Vehicles Passed" while penalizing "Cumulative Wait Time."
*   **Data Pipeline:** The backend uses **Asynchronous FastAPI** loops to broadcast data via WebSockets. We use **uJSON** for ultra-fast serialization, keeping the communication latency between the brain and the visuals under 10ms.

---

### 📚 Technical Glossary
*   **Deep Q-Network (DQN):** The Reinforcement Learning algorithm we used to teach the AI which traffic light phase is best at any given moment.
*   **Digital Twin:** A high-fidelity virtual replica of a physical system (the intersection) used for testing and training AI.
*   **WebSocket:** A persistent communication channel used to stream live data from the backend to the frontend without delay.
*   **Lerping (Linear Interpolation):** A technique used in the frontend to fill in the gaps between data points, making the cars move smoothly.
*   **Throughput:** The primary success metric; the total number of vehicles that successfully cross the intersection in a set time.
*   **Episode:** A single practice round of the simulation where the AI tries to learn and improve its score.
*   **Reward Function:** The mathematical "Scoreboard" that tells the AI if it is doing a good job or a bad job.

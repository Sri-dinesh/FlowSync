# FlowSync Full-Stack Audit

## Issues Found

### Sim Engine / Physics
1. **Critical: Tailgating vehicles run red lights and bypass intersection lock, causing collisions**
   - **Layer:** Sim Engine
   - **File:line references:** `server/app/simulation/intersection.py:114-118`
   - **Root cause explanation:** During the per-vehicle loop, `can_move` is initialized to `True`. If a vehicle hits the stop line on a red light, it correctly sets `can_move = False` (line 95). However, the subsequent "vehicle ahead collision" check overwrites `can_move` back to `True` if the vehicle ahead is moving: `can_move = (vehicle_ahead.speed > 0)`. A trailing vehicle will inch past the stop line on a red light. Because it crosses the stop line via this collision logic and not the "green light entering" block, it is NEVER added to `vehicles_in_intersection`. The perpendicular traffic then receives a green light, sees an empty intersection lock, and enters while the invisible "tailgating" vehicle is still crossing, causing the reported lane conflicts.
   - **Observed effect:** Vehicles teleport or occupy the intersection at the same time as perpendicular approaches.
   - **Recommended fix:** Change the collision check to only *restrict* movement: `can_move = can_move and (vehicle_ahead.speed > 0)`.

2. **Critical: Conflicting turn movements allowed during parallel green phases**
   - **Layer:** Sim Engine / Config
   - **File:line references:** `server/app/simulation/traffic_signal.py:27-28`
   - **Root cause explanation:** The `PHASE_ALLOWED_TURNS` dictionary permits `{"straight", "left", "right"}` during both `NS_GREEN` (phase 0) and `EW_GREEN` (phase 1). This allows a Northbound left-turning vehicle and a Southbound straight vehicle to enter the intersection simultaneously. Their paths intersect, causing visual collisions in the 3D scene.
   - **Observed effect:** Vehicles on the same phase pass through each other mid-intersection.
   - **Recommended fix:** Remove `"left"` from `NS_GREEN` and `EW_GREEN`. Left turns should only be permitted during the dedicated protected phases `NS_LEFT` (2) and `EW_LEFT` (3).

### RL Engine / AI
3. **Critical: AI requested phase overwritten by autonomous fixed timer and zero-wait logic**
   - **Layer:** RL Engine / Sim Engine
   - **File:line references:** `server/app/simulation/traffic_signal.py:85-121`
   - **Root cause explanation:** In AI mode, `TrafficSignal.tick` sets the agent's `requested_phase` (lines 77-83), but then allows the remaining code to execute. This includes the zero-wait early switch (lines 95-101) and the fixed duration rollover (lines 103-121). If the agent decides to hold a phase longer than `fixed_duration` (8.0s), the signal forcibly switches it.
   - **Observed effect:** Phases appear to switch with no real relationship to traffic demand, ignoring the RL agent's policy.
   - **Recommended fix:** In `TrafficSignal.tick()`, if `requested_phase is not None` (AI mode), return early after evaluating the AI request, completely bypassing the heuristic and fixed-duration logic.

4. **High: RL Environment State Desync During Yellow/Red Clearance**
   - **Layer:** RL / Environment
   - **File:line references:** `server/app/simulation/environment.py:68-70`, `server/app/simulation/traffic_signal.py:68-74`
   - **Root cause explanation:** The `TrafficEnv` observation uses `self.intersection.signal.current_phase`. When the agent requests a phase switch, the signal enters YELLOW, but `current_phase` remains the OLD phase until the clearance is complete. The agent doesn't "see" its action take effect immediately in the phase integer, confusing the learning process and making the switch penalty logic (`action != prev_phase`) overly trigger if the agent repeats the action while waiting for the clearance.
   - **Observed effect:** RL agent training converges slowly and performs redundant actions.
   - **Recommended fix:** Update `TrafficEnv._get_obs` to include the `_pending_phase` or accurately reflect the target phase, and ensure switch penalty applies only once per transition.

5. **Medium: Replay Buffer done flag logic violates Bellman equation for truncated episodes**
   - **Layer:** RL Engine
   - **File:line references:** `server/app/simulation/environment.py:59`, `server/app/rl/trainer.py:66`
   - **Root cause explanation:** `TrafficEnv` incorrectly sets `terminated = True` when the max timestep limit is reached, instead of `truncated = True`. `Trainer` then pushes `done = terminated or truncated` into the replay buffer. Setting `done = True` due to an arbitrary time limit forces the Q-value target to only equal the immediate reward, destroying the agent's value estimation for states near the end of the episode.
   - **Observed effect:** The agent's value estimation becomes corrupt near the end of training episodes.
   - **Recommended fix:** In `environment.py`, return `terminated = False` and `truncated = self.intersection.timestep >= MAX_STEPS_PER_EPISODE`. In `trainer.py`, the replay buffer should only receive `done = terminated`.

### Backend API / WebSocket Protocol
6. **High: Training WebSocket missing cleanup on disconnect**
   - **Layer:** WebSocket Protocol
   - **File:line references:** `server/app/websockets/training_ws.py:68-70`
   - **Root cause explanation:** Disconnecting from the training WebSocket does NOT stop the training loop; `app_state["trainer"].stop()` is never called in the `except WebSocketDisconnect:` block.
   - **Observed effect:** If a user closes the browser during training, the background task continues consuming server resources indefinitely.
   - **Recommended fix:** In `training_socket`'s `WebSocketDisconnect` handler, call `app_state["trainer"].stop()`.

7. **Medium: Signal lacks Red clearance duration**
   - **Layer:** Sim Engine
   - **File:line references:** `server/app/simulation/traffic_signal.py:68-74`
   - **Root cause explanation:** When the yellow phase completes, the signal transitions to `SignalColor.RED`. However, on the very next tick, the `if self.color == SignalColor.RED:` block immediately resolves the pending phase and switches to `GREEN`. This results in a 0.1s red clearance, which is insufficient for vehicles to clear the intersection.
   - **Observed effect:** Opposing traffic gets a green light instantly after yellow ends.
   - **Recommended fix:** Introduce a `red_duration` (e.g., 1.0s or 2.0s) and only resolve the pending phase after `time_in_phase >= self.red_duration`.

### Frontend / 3D Rendering
8. **High: Frontend Traffic Lights render left-turn phases identically to straight phases**
   - **Layer:** 3D Rendering
   - **File:line references:** `client/src/components/simulation/IntersectionScene.tsx:26-32`
   - **Root cause explanation:** The `resolveLightColor` function groups phases `0` and `2` into `isNS`. When the backend switches to `NS_LEFT` (phase 2), the frontend traffic light components for North and South simply show a solid green light. Visually, this incorrectly signals that straight movements are allowed.
   - **Observed effect:** Users misinterpret the active phase because left-turn signals look like straight green signals.
   - **Recommended fix:** Distinguish between phase 0 and phase 2 in the frontend. Render a specific color hue for left-turn phases or use a separate mesh for left arrows.

9. **Medium: Vehicle visual interpolation extrapolates past destination when stopped**
   - **Layer:** 3D Rendering
   - **File:line references:** `client/src/components/simulation/Vehicle.tsx:300-316`
   - **Root cause explanation:** The vehicle interpolation loop in the frontend caps progress at `1.0`, but relies on `vehicle.position` over time. Due to network latency, rapid back-to-back frames during stop-and-go behavior can cause slight jittering or interpolation overshoots.
   - **Observed effect:** Vehicles appear to jitter or slightly teleport when stopping and starting at the intersection line.
   - **Recommended fix:** Improve the interpolation clamp logic to respect stop lines and halt purely when `vehicle.state === "waiting"`.

### Frontend Store
10. **Low: Training state persistence assumes single client**
    - **Layer:** Frontend Store
    - **File:line references:** `client/src/store/simulationStore.ts:38-46`
    - **Root cause explanation:** The Zustand store initializes `isTraining` to `false`. When a page reloads, it connects to the WebSocket but doesn't immediately pull the live training status until the next metric payload arrives.
    - **Observed effect:** Reloading the browser during an active AI training session shows the training UI in a stopped state for up to several seconds.
    - **Recommended fix:** Upon WebSocket connection, send an initial "status_request" message to the backend to sync state immediately.

### Config / Mechanics
11. **Low: Misnamed Wait Time Penalty Variable**
    - **Layer:** Config / Sim Engine
    - **File:line references:** `server/app/simulation/environment.py:44`, `server/app/simulation/intersection.py:140-141`
    - **Root cause explanation:** `intersection.get_total_waiting()` returns the sum of queue *lengths* (`sum(len(queue))`), not the sum of wait *times* (`sum(vehicle.wait_time)`). The agent's reward function penalizes this value as `wait_penalty = -0.1 * total_waiting`, meaning it penalizes queue length instead of actual wait time accumulation.
    - **Observed effect:** The agent prioritizes clearing long lines of new cars rather than prioritizing cars that have been waiting the longest.
    - **Recommended fix:** Rename `get_total_waiting` to `get_total_queue_length` or change it to return actual wait times.

# FlowSync — Full-Stack Audit Report

> **Read-only audit.** No fixes applied. Bugs organized by layer, ordered by severity within each layer.

---

## Layer 1: Simulation Engine

### 1.1 [CRITICAL] AI signal control overridden by fixed-timer rollover

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/traffic_signal.py:76-121` |
| **Type** | Definite bug |

**Root cause:** When the AI requests a phase that matches the current phase (i.e. it wants to maintain the current green), the early-return guard at lines 77–83 is skipped:

```python
if (
    requested_phase is not None
    and requested_phase != self.current_phase      # ← False when same phase
    and self.time_in_phase >= self.min_green_duration
):
    self.set_phase(requested_phase)
    return
```

Execution falls through to the fixed-timer logic at lines 86–121. After `fixed_duration` (8 s) the signal auto-switches to the phase with the highest queue count — regardless of what the AI wanted.

**Observed effect:** The AI cannot hold a green phase for longer than 8 s. This is the primary cause of the symptom _"traffic lights are not controlled correctly — phases appear to switch with no real relationship to traffic demand"_. The AI is nominally "in control" but the signal overrides it every 8 s with fixed-timer logic.

**Fix:** In AI mode, after satisfying `min_green_duration`, skip the fixed-timer rollover block entirely. The signal should only change when the AI requests a different phase (after minimum green + yellow clearance).

---

### 1.2 [CRITICAL] Phase reservation fails for same-direction-group transitions

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/intersection.py:100-104` |
| **Type** | Definite bug |

**Root cause:** The intersection reservation system uses `signal.current_phase` as the lock key:

```python
if (self.intersection_reserved_phase is None or 
    self.intersection_reserved_phase == self.signal.current_phase):
    self.vehicles_in_intersection.add(vehicle.id)
    self.intersection_reserved_phase = self.signal.current_phase
else:
    vehicle.position = STOP_LINE
    can_move = False
```

The four phases are:
- 0 = NS_GREEN
- 1 = EW_GREEN
- 2 = NS_LEFT
- 3 = EW_LEFT

When phase 0 (NS_GREEN) reserves the intersection (`reserved=0`), and the signal transitions through yellow→red→green to phase 2 (NS_LEFT), NS_LEFT vehicles check `reserved(0) == current(2)` → **False** → they are blocked despite being in the same direction group.

**Observed effect:** After NS_GREEN switches to NS_LEFT (or EW_GREEN to EW_LEFT), no left-turn vehicles from that direction group can enter the intersection until all previously-entered vehicles clear the intersection _and_ the reservation releases. This starves left-turn traffic and wastes green time.

Furthermore, when the opposite pattern happens (NS_LEFT → NS_GREEN at next cycle), `reserved(2) != current(0)` blocks straight-through traffic too.

**Fix:** The reservation should be keyed by direction group (NS=0,2 vs EW=1,3), not by individual phase number. Add a helper that maps phase → group and compare groups instead of raw phase values.

---

### 1.3 [HIGH] `_spawned_this_interval` and `_passed_this_interval` attributes do not exist on Intersection

| Field | Value |
|---|---|
| **Files** | `server/app/websockets/simulation_ws.py:82-83` |
| **Type** | Definite bug |

**Root cause:** The telemetry buffer reads counters that are never set:

```python
"vehiclesSpawned": getattr(intersection, "_spawned_this_interval", 0),
"vehiclesPassed": getattr(intersection, "_passed_this_interval", 0),
```

Neither `_spawned_this_interval` nor `_passed_this_interval` is ever assigned on the `Intersection` object. `getattr` falls back to `0` unconditionally.

**Observed effect:** Every `traffic_logs` row in the database has `vehiclesSpawned=0` and `vehiclesPassed=0`. The analytics dashboard cannot display per-interval spawn/throughput data.

**Fix:** Either add these counters to `Intersection` (increment `_spawned_this_interval` in `PoissonSpawner.spawn()` and `_passed_this_interval` in the cleanup section of `Intersection.tick()`, resetting them on each log sample), or compute them from the available data in the `_SimBuffer.add()` method.

---

### 1.4 [HIGH] All-red clearance time is only one tick (0.1 s)

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/traffic_signal.py:68-74` |
| **Type** | Definite bug |

**Root cause:** The red→green transition happens in a single tick:

```python
# Red -> resolve pending phase
if self.color == SignalColor.RED:
    if self._pending_phase is not None:
        self.current_phase = self._pending_phase
        self._pending_phase = None
    self.color = SignalColor.GREEN
    self.time_in_phase = 0.0
    return
```

The cycle is: GREEN → YELLOW (2 s) → RED (0.1 s) → GREEN (new phase). Real traffic signals maintain all-red for 1–2 s to allow vehicles already in the intersection to clear.

**Observed effect:** Vehicles from the previous phase still occupy the intersection when the new phase turns green. The intersection reservation system partially mitigates this (by blocking new vehicles from entering when the previous phase still has vehicles in the intersection), but any gap in the set (e.g. all previous vehicles happened to clear early) allows immediate cross-traffic entry.

**Fix:** Add an explicit `all_red_duration` parameter (1–2 s). After yellow transitions to red, wait for this duration before transitioning to green. Do not respond to phase requests during all-red.

---

### 1.5 [HIGH] No same-direction conflict detection within a phase group

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/intersection.py:83-109` |
| **Type** | Design flaw (strongly suspected contributor to collision symptom) |

**Root cause:** The intersection reservation system only tracks which phase has the intersection, not which specific lanes or paths are occupied. During NS_GREEN (phase 0), vehicles from both north (southbound) and south (northbound) lanes can enter the intersection simultaneously:

```
southbound vehicle (north lane, straight)  → travels -Z direction
northbound vehicle (south lane, left turn)  → crosses -Z path to go +X direction
                                                     ↕ COLLISION
```

Both vehicles check the reservation and see `reserved_phase == current_phase`, so both enter.

During EW_GREEN (phase 1), the same conflict exists between eastbound and westbound traffic: a westbound through vehicle and an eastbound left-turn vehicle would cross paths.

**Observed effect:** Vehicles from opposite approaches within the same direction group can simultaneously occupy the intersection with conflicting paths. This is one source of the _"vehicles from perpendicular approaches appear to occupy the intersection at the same time"_ symptom.

**Fix:** This is a complex problem. Options include:
- (Simple) Model only one lane per approach and prohibit opposing left-turns during the same phase
- (Complex) Implement per-path conflict tracking: maintain a set of occupied paths and check new vehicle trajectories against it

---

### 1.6 [MEDIUM] REST API `/simulation/start` does not enable the spawner

| Field | Value |
|---|---|
| **Files** | `server/app/routers/simulation.py:34-48` |
| **Type** | Definite bug |

**Root cause:** `POST /simulation/start` resets the intersection and creates a database simulation record but never calls `spawner.set_enabled(True)`:

```python
@router.post("/start")
async def start_simulation(request: Request) -> dict:
    app_state = request.app.state.app_state
    intersection = app_state["intersection"]
    intersection.reset()
    if not app_state.get("sim_running"):
        app_state["sim_running"] = True
    simulation_id = await asyncio.to_thread(
        supabase_service.create_simulation, app_state["mode"]
    )
    app_state["current_simulation_id"] = simulation_id
    return {"simulation_id": simulation_id}
```

Contrast with the WebSocket `start` command in `simulation_ws.py:178-182` which correctly calls `intersection.spawner.set_enabled(True)`.

**Observed effect:** If any client calls `POST /simulation/start` (rather than using the WebSocket), `sim_running` is true and a DB record is created, but `intersection.tick()` → `spawner.spawn()` does nothing because the spawner is disabled. No vehicles appear. The REST endpoint is broken for its nominal purpose.

**Fix:** Add `app_state["intersection"].spawner.set_enabled(True)` to the REST start handler, or remove the unimplemented REST path if it is not intended for use.

---

### 1.7 [LOW] `MetricsTracker` class defined but never used

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/metrics.py:6`, whole file |
| **Type** | Dead code |

**Root cause:** The `MetricsTracker` class is never imported or instantiated anywhere in the codebase. All metrics are computed inline in the WebSocket simulation loop directly from `Intersection` state.

**Fix:** Remove the file or integrate it into the simulation flow if the rolling-average snapshot logic is needed.

---

## Layer 2: RL Engine

### 2.1 [CRITICAL] Training and AI-mode simulation share the same environment / intersection instance

| Field | Value |
|---|---|
| **Files** | `server/app/main.py:33-48`, `server/app/rl/trainer.py:52` |
| **Type** | Definite bug |

**Root cause:** In `main.py`, a single `TrafficEnv` is created at startup and shared between the WebSocket simulation loop and the Trainer:

```python
env = TrafficEnv()
agent = DQNAgent()
trainer = Trainer(env, agent, ...)   # trainer holds same env reference
app_state["env"] = env               # sim loop uses same env reference
app_state["intersection"] = env.intersection  # sim loop uses same intersection
```

When training starts, `trainer.train()` calls `self.env.reset()` (`trainer.py:52`), which calls `self.intersection.reset()` (`environment.py:31`), which clears ALL vehicles and resets the signal to phase 0.

**Observed effect:** If AI-mode simulation is running when training starts, the intersection is forcibly reset — all vehicles disappear, the timestep resets to 0, and the 3D scene shows an empty intersection mid-session.

**Fix:** The Trainer should use a **copy** of the environment or create its own independent instance. Since the environment contains mutable state (vehicle lists, signal state), a shallow copy is insufficient. The Trainer or the `app_state` should maintain separate environment instances.

---

### 2.2 [MEDIUM] No all-red action in the available action space

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/environment.py:21` |
| **Type** | Design smell |

**Root cause:** The action space is `Discrete(4)` — one action per signal phase. There is no "all-red / clear intersection" action. The agent cannot intentionally flush the intersection.

Combined with the 1-tick all-red in `TrafficSignal` (issue 1.4), the system lacks a mechanism to safely clear the intersection before switching direction groups.

**Fix:** Add a 5th action for all-red (0.5–1 s all directions red). Remove it from the one-hot or use it sparingly. Alternatively, make the all-red mandatory and implicit in the transition logic (not a separate action) — this is the more standard approach.

---

### 2.3 [LOW] `_get_obs` includes `time_in_phase` without accounting for yellow/red intervals

| Field | Value |
|---|---|
| **Files** | `server/app/simulation/environment.py:80` |
| **Type** | Design smell |

**Root cause:** The observation includes `self.intersection.signal.time_in_phase`. During yellow (2 s) and red (1 tick), `time_in_phase` continues to increment. It is only reset when entering a new color state:

```python
# Yellow: resets at line 49 (when set_phase is called)
# Red: resets when transitioning from yellow→red (line 64)
# Green: resets when transitioning from red→green (line 73)
```

The same phase number + color combination can therefore appear with different `time_in_phase` values, because the counter includes time spent in the previous color during that phase.

**Observed effect:** The agent sees ambiguous signal timing — the `time_in_phase` feature does not reliably indicate "how long the current color has been displayed."

**Fix:** Reset `time_in_phase` to 0 at every color transition, not just at phase changes. The current code does this for most transitions but redundantly increments it during yellow before resetting at red.

---

## Layer 3: WebSocket Protocol

### 3.1 [HIGH] `checkpoint_saved` message parsed as `TrainingMetric` (silent data corruption)

| Field | Value |
|---|---|
| **Files** | `server/app/rl/trainer.py:165-171` → `client/src/hooks/useTrainingSocket.ts:43-52` |
| **Type** | Definite bug |

**Root cause (server):** After saving a checkpoint, `trainer.py` broadcasts a message with a `type` field over the training WebSocket:

```python
await self.ws_broadcast_fn({
    "type": "checkpoint_saved",
    "model_id": simulation_id,
    "episode": episode_num,
})
```

**Root cause (client):** The training WebSocket handler casts every incoming message to `TrainingMetric`:

```typescript
const payload = JSON.parse(event.data) as TrainingMetric;
addTrainingMetric(payload);
```

`addTrainingMetric` at `simulationStore.ts:44-52` appends the message to the `trainingMetrics` array:

```typescript
addTrainingMetric: (metric) => set((state) => {
    const next = [...state.trainingMetrics, metric];
    const trimmed = next.length > MAX_TRAINING_METRICS ? next.slice(-MAX_TRAINING_METRICS) : next;
    return { trainingMetrics: trimmed, isTraining: metric.is_training };
})
```

The `checkpoint_saved` message has `total_reward=undefined`, `avg_wait_time=undefined`, `throughput=undefined`, `epsilon=undefined`, `loss=undefined`, `is_training=undefined`. These undefined values pollute the metrics array.

**Observed effect:** The training metrics array contains corrupted entries. The `AgentPhaseDescription` component at `TrainingControls.tsx:338-340` reads `latest.epsilon` which is `undefined` for checkpoint messages. However, the component guards with `"epsilon" in latest` which should filter them out. Still, `is_training` is `undefined` which is falsy, so the `isTraining` store field gets set to `false` when a checkpoint is saved during active training — potentially causing the UI to briefly show "Training Complete" between checkpoints.

**Fix:** On the client side, filter messages by checking for a `type` field before casting:

```typescript
socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "checkpoint_saved") {
        // handle checkpoint notification (e.g. invalidate query)
        return;
    }
    addTrainingMetric(payload as TrainingMetric);
};
```

---

### 3.2 [MEDIUM] Frontend `turn` field typed as optional, backend sends it as required

| Field | Value |
|---|---|
| **Files** | `client/src/types/simulation.ts:7` vs `server/app/schemas/simulation_schema.py:11` |
| **Type** | Type mismatch (latent bug) |

**Root cause:** The backend Pydantic schema declares `turn: str` (required, non-optional). The frontend TypeScript declares `turn?: "straight" | "left" | "right"` (optional). The backend always sends `turn`, so the optional type works in practice — but it creates a maintenance hazard.

**Observed effect:** A future change that makes `turn` nullable on the backend would silently propagate `undefined` to the frontend. The Vehicle component at `Vehicle.tsx:275` does `const turn = (vehicle.turn ?? "straight") as Turn;` which would default to "straight" — silently hiding the null case.

**Fix:** Make `turn` required on the frontend:
```typescript
turn: "straight" | "left" | "right";
```

---

## Layer 4: 3D Rendering

### 4.1 [HIGH] Bezier curve parameter `t` is not arclength-parameterized

| Field | Value |
|---|---|
| **Files** | `client/src/components/simulation/Vehicle.tsx:329` |
| **Type** | Design flaw (strongly suspected root cause of position/teleportation bugs) |

**Root cause:** The backend tracks vehicle positions as a unitless value in `[0, 1]`, where `0` = spawn point, `0.42` = stop line, `1.0` = passed intersection. The frontend maps this directly to the Bezier curve parameter `t` via `curve.getPointAt(t)`.

Cubic Bezier `t` is **not** proportional to arclength. The mapping between parameter `t` and distance along the curve is non-linear:

| Backend position | Visual `t` | Actual distance from spawn | Expected visual position |
|---|---|---|---|
| `0.42` (stop line) | `0.42` | z ≈ -1.51 on north curve | stop bar at z = -1.6 |
| `0.50` (mid-intersection) | `0.50` | z = 0.0 | actual center of intersection |
| `0.71` (exit) | `0.71` | z ≈ 4.06 (past the intersection) | end of intersection ~ z=1.5 |

The non-linearity means:
- At the stop line: vehicle appears 0.09 units BEFORE the visual stop bar (close but not exact)
- Past the center: positions are stretched toward the exit, causing vehicles to accelerate visually faster than the backend physics

**Observed effect:** "Vehicles either don't render, render at wrong positions, jump/teleport, or follow incorrect paths through the intersection." The non-linear mapping causes vehicles to appear at inconsistent positions relative to the 3D road geometry — especially noticeable when vehicles stop at the red light (position ≠ stop bar location).

**Fix:** Replace the simple `t = position` mapping with arclength parameterization. Options:
1. Pre-compute a lookup table: sample the curve at many `t` values, measure cumulative arclength, then map backend position → arclength fraction → `t` via binary search
2. Use a spline with uniform parameterization (e.g., Catmull-Rom with chord-length parameterization)
3. Simplify: use a straight-line path with simple linear interpolation and animate turns at fixed positions

---

### 4.2 [HIGH] Traffic light color incorrect for straight-through vehicles during left-turn phases

| Field | Value |
|---|---|
| **Files** | `client/src/components/simulation/IntersectionScene.tsx:26-32` |
| **Type** | Definite bug |

**Root cause:** `resolveLightColor` maps phase numbers to colors based solely on direction group:

```typescript
function resolveLightColor(phase, signalColor, direction) {
  const isNS = phase === 0 || phase === 2;
  const isEW = phase === 1 || phase === 3;
  const active = direction === "north" || direction === "south" ? isNS : isEW;
  if (active && (signalColor === "green" || signalColor === "yellow")) {
    return signalColor;
  }
  return "red";
}
```

During phase 2 (NS_LEFT), `resolveLightColor(2, "green", "north")` returns `"green"`. But in the backend, `is_green_for("north", "straight")` during phase 2 returns `False` because `PHASE_ALLOWED_TURNS[2] = {"left"}`.

**Observed effect:** Vehicles on the north approach see a green traffic light but cannot move forward (the backend correctly blocks them). This is the visual manifestation of the symptom _"during multi-phase transitions conflicting movements are permitted"_ — the light shows green for all movements during left-turn phases, misleading the user.

**Fix:** The traffic light visual needs to distinguish protected left-turn phases from through-traffic phases. Options:
1. Show separate left-turn arrows on the traffic light model (requires model change)
2. Show a yellow/amber for straight movements during left-turn-only phases
3. Show a dedicated "left arrow" indicator (requires new 3D geometry)

---

### 4.3 [MEDIUM] Vehicle interpolation skips one frame at every WebSocket update

| Field | Value |
|---|---|
| **Files** | `client/src/components/simulation/Vehicle.tsx:312-326` |
| **Type** | Definite bug |

**Root cause:** When a new position arrives from the WebSocket, the interpolation start time is set to `now`. The elapsed time is then computed as `now - now = 0`, giving `progress = 0`:

```typescript
if (vehicle.position !== lastTargetPosRef.current) {
    const actualInterval = time - lastUpdateTimeRef.current;
    lastUpdateIntervalRef.current = Math.min(Math.max(actualInterval, 0.05), 0.5);
    startPosRef.current = lastVisualTRef.current;
    lastTargetPosRef.current = vehicle.position;
    lastUpdateTimeRef.current = time;   // ← set to now
}
const elapsed = time - lastUpdateTimeRef.current;  // ← 0 on this frame
const duration = lastUpdateIntervalRef.current;
const progress = Math.min(1.0, elapsed / duration);
let t = startPosRef.current + (vehicle.position - startPosRef.current) * progress;
// t = startPosRef.current (no change this frame)
```

**Observed effect:** Every 100 ms (10 Hz WS update), the vehicle's visual position does not change for one render frame (16 ms at 60 fps). This produces a subtle but perceptible stutter at the start of each interpolation cycle.

**Fix:** When a new position is detected, compute `progress` from the time delta directly (don't set `lastUpdateTimeRef.current = time` before computing `elapsed`). Restructure so that `lastUpdateTimeRef.current` represents the time when the PREVIOUS update arrived, not the current render frame:

```typescript
if (vehicle.position !== lastTargetPosRef.current) {
    startPosRef.current = lastVisualTRef.current;
    lastTargetPosRef.current = vehicle.position;
    lastUpdateTimeRef.current = time;  // this is when the new target was set
}
const elapsed = time - lastUpdateTimeRef.current;
// On the very first frame, elapsed ≈ 0 → progress ≈ 0 → no movement
// Better: set lastUpdateTimeRef to slightly in the past
```

Or, simpler: set `lastUpdateTimeRef.current = time - actualInterval` so that `elapsed = actualInterval` on the first frame, giving immediate progress.

---

## Layer 5: Frontend Store / Hooks

### 5.1 [MEDIUM] `setFrame` does not update `isRunning` — Start button sends "start" command on every re-render

| Field | Value |
|---|---|
| **Files** | `client/src/store/simulationStore.ts:37-43`, `client/src/components/controls/SimulationControls.tsx:36-39` |
| **Type** | Definite bug |

**Root cause (store):** `setFrame` updates `mode` from frame data but never derives `isRunning`:

```typescript
setFrame: (frame) => set((state) => ({
    currentFrame: frame,
    lastFrameAt: Date.now(),
    mode: frame.mode === "fixed" || frame.mode === "ai" ? frame.mode : state.mode,
    // isRunning: true  ← never set
})),
```

**Root cause (SimulationControls):** The `useEffect` sends a "start" command every time `isRunning` is true AND `isConnected` is true AND the component re-renders:

```typescript
useEffect(() => {
    if (isConnected && isRunning) {
        sendCommand({ command: "start" });
    }
}, [isConnected, isRunning, sendCommand]);
```

Since `isRunning` is set independently by `handleStart` (sets `true`) and never synced from the frame data, this effect fires once when the user clicks Start. But if any dependency changes (e.g. `sendCommand` identity), it fires again, sending duplicate "start" commands to the backend.

**Observed effect:** Duplicate "start" commands are sent to the backend WebSocket on re-renders. The backend's start handler is mostly idempotent (`sim_running` is already True, spawner is already enabled), but duplicate `create_simulation` calls create orphan simulation records with no matching stop.

**Fix:** Remove the effect entirely — the `handleStart` function already calls `sendCommand({ command: "start" })`. The effect is redundant.

---

### 5.2 [MEDIUM] Simulation state is not reset when all clients disconnect

| Field | Value |
|---|---|
| **Files** | `server/app/websockets/simulation_ws.py:269-275` |
| **Type** | Design smell |

**Root cause:** When all WebSocket clients disconnect, the handler stops the simulation and cancels the task:

```python
except WebSocketDisconnect:
    manager.disconnect(websocket)
    if not manager.active_connections:
        app_state["sim_running"] = False
        task = app_state.get("sim_task")
        if task and not task.done():
            task.cancel()
```

But `app_state["current_simulation_id"]` is not cleared, `_buffer` is not flushed, and the simulation record is never updated to "stopped". The simulation hangs in "running" state in the database forever.

**Observed effect:** Orphaned simulation records with `status = "running"` that never complete. Over time this accumulates in the database.

**Fix:** In the disconnect handler, if no clients remain: flush the buffer, update the simulation record to `status = "stopped"`, and clear `current_simulation_id`.

---

## Layer 6: Config / Infrastructure

### 6.1 [MEDIUM] No database indexes on foreign key columns

| Field | Value |
|---|---|
| **Files** | `client/prisma/schema.prisma` |
| **Type** | Performance issue |

**Root cause:** The four tables with `simulationId` foreign keys (`Episode`, `PerformanceMetric`, `TrafficLog`, `SignalState`) have no indexes on those columns. All queries filtering by simulation ID will perform sequential scans.

The `RLModel` table likewise has no indexes on `isActive` or `createdAt`.

**Fix:** Add indexes:
```prisma
@@index([simulationId])
@@index([isActive])
@@index([createdAt])
```

---

### 6.2 [LOW] Hardcoded production backend URL

| Field | Value |
|---|---|
| **Files** | `client/src/lib/utils.ts:29,32` |
| **Type** | Fragile config |

**Root cause:** `getFastApiUrls()` hardcodes the Render backend URL:

```typescript
if (!httpUrl || httpUrl.includes("localhost") || httpUrl.includes("127.0.0.1")) {
    httpUrl = "https://flowsync-gelt.onrender.com";
}
if (!wsUrl || wsUrl.includes("localhost") || wsUrl.includes("127.0.0.1")) {
    wsUrl = "wss://flowsync-gelt.onrender.com";
}
```

This value is also duplicated in `next.config.ts:12-13`.

**Observed effect:** If the Render service URL changes (e.g. project rename, redeployment to a different region), both files must be updated. The URL appears in client-side code and cannot be overridden per-environment without a deploy.

**Fix:** Use environment variables exclusively. Remove hardcoded fallbacks from `utils.ts` (they are already provided by `next.config.ts` in production).

---

## Layer 7: Tests

### 7.1 [MEDIUM] Tests patch `supabase_client` but do not mock `create_client`

| Field | Value |
|---|---|
| **Files** | `server/tests/conftest.py:7-9` |
| **Type** | Fragile test setup |

**Root cause:** The `mock_supabase` fixture patches `app.services.supabase_service.supabase_client`:

```python
@patch("app.services.supabase_service.supabase_client")
```

But `supabase_client` at `supabase_service.py:20-23` is created at module import level by `create_client()`. The patch only takes effect AFTER the module is already imported. If the `Settings` validation raises an error during import (e.g. missing env vars), the test suite fails before any test runs.

**Observed effect:** Tests require a real `.env` file with valid Supabase credentials. CI/CD pipelines without secrets will fail.

**Fix:** Lazily initialize `supabase_client` (e.g. in a function, not at module level), or configure the test runner to set dummy env vars before importing the app.

---

## Summary by Severity

| Severity | Count | Key |
|---|---|---|
| **Critical** | 3 | AI control overridden by fixed timer, reservation fails on same-group phase transition, training/simulation share environment |
| **High** | 4 | Missing spawn/passed counters, 1-tick all-red, no same-direction conflict detection, Bezier non-linear mapping, checkpoint message pollutes training metrics, incorrect traffic light color for straight traffic during left-turn phases |
| **Medium** | 7 | REST API spawner not enabled, optional `turn` type, one-frame interpolation skip, `setFrame` doesn't update `isRunning`, reconnection state leak, no indexes, hardcoded URL, no all-red action |
| **Low** | 3 | Dead `MetricsTracker`, `time_in_phase` in obs, fragile test setup |

**Root cause chains (single underlying cause → multiple symptoms):**

1. **Fixed-timer overrides AI** (`traffic_signal.py:76-121`) → phases not responsive to traffic, AI appears ineffective
2. **Phase reservation keyed by phase number, not group** (`intersection.py:100-104`) → left-turn phases cannot follow through phases in same direction, vehicles appear stuck at green lights
3. **Shared environment instance** (`main.py:33-48`) → training resets active simulation, vehicles disappear mid-session
4. **Bezier non-linear parameterization** (`Vehicle.tsx:329`) → vehicles appear at wrong positions, stop short of / past visual stop bar, teleport-like acceleration/deceleration
5. **Traffic light color ignores turn restrictions** (`IntersectionScene.tsx:26-32`) → green light shows during left-turn phase but straight vehicles don't move, contradictory UX

These 5 root causes explain every symptom described in the bug report.

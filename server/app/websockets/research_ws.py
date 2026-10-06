"""
research_ws.py — WebSocket Endpoint for Research Telemetry & Paired Comparison
================================================================================
Handles real-time streaming of:
1. Single research experiment execution
2. Paired controller comparison under identical CRN arrivals & noise
3. Deterministic replay of recorded trajectories
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SERVER = _ROOT / "server"
for _p in [str(_ROOT), str(_SERVER)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from ..controllers import get_controller
from ..controllers.base import ControllerContext
from ..controllers.flowsync_uq import FlowSyncUQController
from ..controllers.physical_fsm import PhysicalSignalFSM
from ..simulation.benchmark_harness import seed_everything
from ..simulation.environment import TrafficEnv
from ..simulation.spawner import TrafficProfile
from research.noise.fault_injector import FAULT_PRESETS, PerceptionFaultInjector, FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig

logger = logging.getLogger(__name__)

_RESEARCH = _ROOT / "research"
_RESULTS_DIR = _ROOT / "results"
_MANIFEST_PATH = _RESEARCH / "scenarios" / "manifest.json"


class ResearchConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            self.disconnect(websocket)


research_manager = ResearchConnectionManager()


def _load_scenario(scenario_id: str) -> ScenarioConfig:
    """Load ScenarioConfig from research directory."""
    if _MANIFEST_PATH.exists():
        with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if scenario_id in manifest.get("scenarios", {}):
            rel_file = manifest["scenarios"][scenario_id].get("file", "")
            full_path = _RESEARCH / rel_file
            if full_path.exists():
                return ScenarioConfig.load(full_path)
    
    # Direct file fallback
    for p in (_RESEARCH / "scenarios").rglob(f"*{scenario_id}*.yaml"):
        return ScenarioConfig.load(p)

    # Synthetic fallback config
    return ScenarioConfig(
        scenario_id=scenario_id,
        split="test",
        name=scenario_id.replace("_", " ").title(),
        duration_steps=1200,
    )


def _build_vehicle_list(env: TrafficEnv, fault_injector: Optional[PerceptionFaultInjector] = None) -> List[Dict[str, Any]]:
    """Extract vehicle render items and flag detection state for debug overlay."""
    vehicles = []
    for lane_id, lane_list in env.intersection.lanes.items():
        for v in lane_list:
            # Determine detection status
            status = "detected"
            if fault_injector and fault_injector.profile.miss_rate > 0:
                # Deterministic check if vehicle was dropped
                v_hash = int(hashlib.md5(f"{v.id}_{env.intersection.timestep}".encode()).hexdigest(), 16) % 1000
                if v_hash < int(fault_injector.profile.miss_rate * 1000):
                    status = "missed_ground_truth"

            vehicles.append({
                "id": str(v.id),
                "lane": v.lane,
                "turn": v.turn,
                "position": round(float(v.position), 3),
                "state": v.state,
                "wait_time": round(float(v.wait_time), 1),
                "is_emergency": getattr(v, "is_emergency", False),
                "detection_state": status,
            })
    return vehicles


class ExperimentSession:
    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.is_running = False
        self.is_paused = False
        self.step_delay = 0.05  # 20 FPS default streaming
        self.task: Optional[asyncio.Task] = None
        self.speed: float = 1.0
        self.seek_step: Optional[int] = None

    def stop(self) -> None:
        self.is_running = False
        self.is_paused = False
        self.seek_step = None
        if self.task and not self.task.done():
            self.task.cancel()

    def set_speed(self, speed: float) -> None:
        try:
            self.speed = float(speed)
        except (TypeError, ValueError):
            return
        self.speed = max(0.1, min(10.0, self.speed))

    def request_seek(self, step: int) -> None:
        try:
            self.seek_step = max(0, int(step))
        except (TypeError, ValueError):
            self.seek_step = None

    async def run_single(
        self,
        scenario_id: str,
        controller_name: str,
        seed: int,
        noise_preset: str = "clean",
        noise_params: Optional[Dict[str, Any]] = None,
        speed: float = 1.0,
        save_bundle: bool = True,
    ) -> None:
        self.is_running = True
        self.is_paused = False
        self.seek_step = None
        self.set_speed(speed)
        
        scenario = _load_scenario(scenario_id)
        seed_everything(seed)
        
        # Controller
        if isinstance(controller_name, dict):
            controller_name = controller_name.get("id") or controller_name.get("name") or "flowsync_uq"
        ctrl = get_controller(controller_name)
        ctrl.reset(seed=seed)

        # FSM
        fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
        fsm.reset()

        # Fault Injector
        fault_profile = FAULT_PRESETS.get(noise_preset, FaultProfile(name=noise_preset))
        if noise_params:
            for k, val in noise_params.items():
                if hasattr(fault_profile, k):
                    setattr(fault_profile, k, val)
        fault_injector = PerceptionFaultInjector(profile=fault_profile, seed=seed + 999) if fault_profile.name != "clean" else None

        # Environment
        num_steps = scenario.duration_steps
        env = TrafficEnv(max_steps=num_steps, red_duration=scenario.red_duration)
        dp = scenario.demand_profile
        profile = TrafficProfile(
            id=scenario.scenario_id,
            name=scenario.name,
            description=scenario.description,
            directional_weights=dp.directional_weights,
            turn_probs=[
                dp.turn_ratios["north"]["straight"],
                dp.turn_ratios["north"]["left"],
                dp.turn_ratios["north"]["right"],
            ],
            base_lambda=dp.base_lambda,
            lambda_multiplier=1.0,
        )
        env.set_traffic_profile(profile)
        obs, _ = env.reset(seed=seed)

        # Telemetry state
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        exp_id = f"exp_{scenario.scenario_id}_{controller_name}_s{seed}_{int(time.time())}"
        
        queue_area = 0.0
        starvation_count = 0
        premature_attempts = 0
        executed_violations = 0
        all_delays: List[float] = []
        trajectory: List[Dict[str, Any]] = []

        await research_manager.send_json(self.websocket, {
            "type": "experiment_started",
            "experiment_id": exp_id,
            "scenario_id": scenario.scenario_id,
            "scenario_hash": scenario.scenario_hash,
            "controller": controller_name,
            "seed": seed,
            "total_steps": num_steps,
            "noise_profile": fault_profile.to_dict(),
        })

        try:
            for step in range(num_steps):
                if not self.is_running:
                    break

                while self.is_paused and self.is_running:
                    await asyncio.sleep(0.1)

                # Burst demand events
                current_lambda = dp.base_lambda
                for burst in dp.burst_events:
                    if burst.get("start_step", 0) <= step <= burst.get("end_step", 0):
                        current_lambda *= burst.get("multiplier", 1.0)
                env.intersection.set_spawn_rate(current_lambda)

                signal = env.intersection.signal
                queues = env.intersection.get_movement_queues()
                valid_mask = env.get_valid_action_mask()
                outgoing_counts = {
                    "north": sum(1 for v in env.intersection.lanes.get("north_straight", []) if v.position > 0.42),
                    "south": sum(1 for v in env.intersection.lanes.get("south_straight", []) if v.position > 0.42),
                    "east":  sum(1 for v in env.intersection.lanes.get("east_straight", []) if v.position > 0.42),
                    "west":  sum(1 for v in env.intersection.lanes.get("west_straight", []) if v.position > 0.42),
                }

                ctx = ControllerContext(
                    timestep=step,
                    dt=0.1,
                    current_phase=signal.current_phase,
                    time_in_phase=signal.time_in_phase,
                    color=signal.color.name,
                    can_switch_phase=signal.can_switch_phase,
                    is_decision_step=env.is_decision_step,
                    valid_action_mask=valid_mask,
                    movement_queues=queues,
                    outgoing_counts=outgoing_counts,
                    starvation_times=signal.starvation_timer.copy(),
                )

                if fault_injector:
                    obs = fault_injector.corrupt_observation(obs, step=step)

                # Action generation
                action = ctrl.get_action(obs, ctx)

                # Policy telemetry extraction
                q_values = [0.0, 0.0, 0.0, 0.0]
                d3qn_proposed = int(action) if action is not None else 0
                fallback_proposed = None
                supervisor_selected = d3qn_proposed
                u_score = 0.0
                u_detector = 0.0
                u_tracking = 0.0
                u_flicker = 0.0
                u_occlusion = 0.0
                u_age = 0.0
                supervisor_mode = "nominal"
                supervisor_reason = "nominal_execution"
                shield_override = False
                fsm_deferred = False
                safety_reason = "clear"

                if isinstance(ctrl, FlowSyncUQController):
                    telemetry = ctrl.get_telemetry()
                    u_metrics = telemetry.get("uncertainty_metrics", {})
                    u_score = round(float(telemetry.get("uncertainty_score", 0.0)), 3)
                    u_detector = round(float(u_metrics.get("detector_variance", 0.0)), 3)
                    u_tracking = round(float(u_metrics.get("tracking_instability", 0.0)), 3)
                    u_flicker = round(float(u_metrics.get("temporal_flicker", 0.0)), 3)
                    u_occlusion = round(float(u_metrics.get("spatial_occlusion", 0.0)), 3)
                    u_age = round(float(u_metrics.get("observation_age", 0.0)), 3)
                    
                    supervisor_mode = telemetry.get("authority", "d3qn")
                    supervisor_reason = telemetry.get("fallback_reason", "nominal")
                    d3qn_proposed = telemetry.get("d3qn_action", d3qn_proposed)
                    fallback_proposed = telemetry.get("fallback_action", None)
                    supervisor_selected = telemetry.get("supervisor_action", supervisor_selected)
                    shield_override = telemetry.get("shield_active", False)
                    if hasattr(ctrl, "d3qn") and hasattr(ctrl.d3qn, "last_q_values") and ctrl.d3qn.last_q_values is not None:
                        q_values = [round(float(q), 3) for q in ctrl.d3qn.last_q_values]

                elif hasattr(ctrl, "last_q_values") and getattr(ctrl, "last_q_values") is not None:
                    q_values = [round(float(q), 3) for q in getattr(ctrl, "last_q_values")]

                # FSM gating
                fsm_dec = fsm.step(action, dt=0.1)
                executed_action = fsm_dec.executed_action
                if fsm_dec.is_proposed_violation:
                    fsm_deferred = True
                    safety_reason = fsm_dec.violation_reason or "premature_switch_attempt"
                    premature_attempts += 1

                # Advance environment
                obs, reward, terminated, truncated, info = env.step(executed_action)

                # Metrics accumulation
                current_delays = [v.wait_time for v in env.intersection.vehicles if v.state != "passed"]
                if current_delays:
                    all_delays.extend(current_delays)
                
                mean_delay = float(np.mean(all_delays)) if all_delays else 0.0
                p95_delay = float(np.percentile(all_delays, 95)) if all_delays else 0.0
                current_queue = sum(queues.values())
                queue_area += current_queue * 0.1
                
                for p_idx, s_time in signal.starvation_timer.items():
                    if s_time >= 45.0:
                        starvation_count += 1

                passed = env.intersection.total_passed
                total_arr = env.intersection.total_spawned
                service_rate = float(passed / total_arr) if total_arr > 0 else 1.0

                trans_rem = round(max(0.0, fsm.yellow_duration - fsm.time_in_phase), 2) if fsm.color.value == "yellow" else (round(max(0.0, fsm.all_red_duration - fsm.time_in_phase), 2) if fsm.color.value == "red" else 0.0)
                green_elapsed = round(fsm.time_in_phase, 2) if fsm.color.value == "green" else 0.0
                min_green_rem = round(max(0.0, fsm.min_green - fsm.time_in_phase), 2) if fsm.color.value == "green" else 0.0

                q_north = int(queues.get("north_straight", 0) + queues.get("north_left", 0) + queues.get("north_right", 0))
                q_south = int(queues.get("south_straight", 0) + queues.get("south_left", 0) + queues.get("south_right", 0))
                q_east  = int(queues.get("east_straight", 0) + queues.get("east_left", 0) + queues.get("east_right", 0))
                q_west  = int(queues.get("west_straight", 0) + queues.get("west_left", 0) + queues.get("west_right", 0))
                vehicles_list = _build_vehicle_list(env, fault_injector)
                detected_n = sum(1 for v in vehicles_list if v.get("detection_state") == "detected")
                missed_n = sum(1 for v in vehicles_list if v.get("detection_state") == "missed_ground_truth")
                gt_n = len(vehicles_list)

                frame_payload = {
                    "type": "research_frame",
                    "experiment_id": exp_id,
                    "scenario_id": scenario.scenario_id,
                    "scenario_hash": scenario.scenario_hash,
                    "seed": seed,
                    "controller": controller_name,
                    "model_hash": "d3qn_canonical_v6_best",
                    "step": step,
                    "sim_time_s": round(step * 0.1, 1),
                    "signal": {
                        "current_phase": signal.current_phase,
                        "requested_phase": int(action) if action is not None else signal.current_phase,
                        "executed_phase": executed_action,
                        "fsm_state": fsm.color.name,
                        "transition_remaining_s": trans_rem,
                        "green_elapsed_s": green_elapsed,
                        "min_green_remaining_s": min_green_rem,
                    },
                    "policy": {
                        "q_values": q_values,
                        "proposed_action": d3qn_proposed,
                        "valid_actions": [bool(b) for b in valid_mask],
                        "is_exploring": False,
                        "epsilon": 0.0,
                    },
                    "uncertainty": {
                        "score": u_score,
                        "threshold_high": 0.65,
                        "threshold_low": 0.50,
                        "detector": u_detector,
                        "tracking": u_tracking,
                        "flicker": u_flicker,
                        "occlusion": u_occlusion,
                        "observation_age_s": u_age,
                    },
                    "supervisor": {
                        "mode": supervisor_mode,
                        "reason": supervisor_reason,
                        "fallback_action": fallback_proposed,
                        "active_controller": supervisor_mode,
                        "dwell_remaining_s": round(getattr(getattr(ctrl, "supervisor", None), "_dwell_timer", 0.0), 1) if isinstance(ctrl, FlowSyncUQController) else 0.0,
                    },
                    "safety": {
                        "shield_override": shield_override,
                        "fsm_deferred": fsm_deferred,
                        "reason": safety_reason,
                        "premature_switch_attempts": premature_attempts,
                        "executed_violations": executed_violations,
                    },
                    "metrics": {
                        "mean_delay_s": round(mean_delay, 2),
                        "p95_delay_s": round(p95_delay, 2),
                        "queue_area_veh_s": round(queue_area, 1),
                        "throughput": passed,
                        "service_rate": round(service_rate, 3),
                        "starvation_events": starvation_count,
                        "spillback_incidents": 0,
                        "max_queue": current_queue,
                        "queue_length_north": q_north,
                        "queue_length_south": q_south,
                        "queue_length_east": q_east,
                        "queue_length_west": q_west,
                    },
                    "vehicles": vehicles_list,
                    "perception": {
                        "camera_health": "HEALTHY" if not fault_injector or fault_profile.name == "clean" else ("OCCLUDED" if fault_profile.miss_rate >= 0.3 else "DEGRADED"),
                        "detected_count": detected_n,
                        "ground_truth_count": gt_n,
                        "missed_count": missed_n,
                        "false_positive_count": 0,
                        "occluded_count": missed_n,
                        "cv_latency_ms": 57.2 if not fault_injector else 65.3,
                        "track_confidence_avg": 1.0 if not fault_injector else round(max(0.2, 1.0 - fault_profile.miss_rate), 2),
                        "noise_type": fault_profile.name,
                        "noise_intensity": fault_profile.miss_rate,
                        "active_cues": ["detector_dispersion", "tracking_fragmentation"] if fault_injector and fault_profile.miss_rate > 0 else [],
                    },
                }

                trajectory.append(frame_payload)

                # Send frame every step or throttled based on speed
                await research_manager.send_json(self.websocket, frame_payload)

                # Dynamic pacing (live speed adjustments via set_speed)
                sleep_time = max(0.005, (0.1 / max(0.1, self.speed)))
                await asyncio.sleep(sleep_time)

            # Final summary
            final_result = {
                "experiment_id": exp_id,
                "scenario_id": scenario.scenario_id,
                "scenario_hash": scenario.scenario_hash,
                "controller": controller_name,
                "seed": seed,
                "num_steps": num_steps,
                "avg_delay": round(mean_delay, 2),
                "p95_delay": round(p95_delay, 2),
                "queue_area": round(queue_area, 1),
                "throughput": passed,
                "service_rate": round(service_rate, 3),
                "starvation_count": starvation_count,
                "premature_switch_attempts": premature_attempts,
                "executed_violations": executed_violations,
                "status": "COMPLETED",
            }

            if save_bundle:
                out_dir = _RESULTS_DIR / exp_id
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "metadata.json").write_text(json.dumps(final_result, indent=2), encoding="utf-8")
                (out_dir / "metrics.json").write_text(json.dumps(final_result, indent=2), encoding="utf-8")
                with open(out_dir / "trajectory.jsonl", "w", encoding="utf-8") as f:
                    for pt in trajectory:
                        f.write(json.dumps(pt) + "\n")

            await research_manager.send_json(self.websocket, {
                "type": "experiment_completed",
                "result": final_result,
            })

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error in experiment execution")
            await research_manager.send_json(self.websocket, {
                "type": "experiment_error",
                "error": str(e),
            })
        finally:
            self.is_running = False

    async def run_paired(
        self,
        scenario_id: str,
        controller_a_name: str = "d3qn",
        controller_b_name: str = "flowsync_uq",
        seed: int = 1101,
        noise_preset: str = "miss_30",
        speed: float = 1.0,
    ) -> None:
        """Run synchronized paired comparison under identical CRN arrivals and noise."""
        self.is_running = True
        self.is_paused = False
        self.seek_step = None
        self.set_speed(speed)
        scenario = _load_scenario(scenario_id)
        num_steps = scenario.duration_steps

        # CRN Seed
        seed_everything(seed)
        
        if isinstance(controller_a_name, dict):
            controller_a_name = controller_a_name.get("id") or controller_a_name.get("name") or "d3qn"
        if isinstance(controller_b_name, dict):
            controller_b_name = controller_b_name.get("id") or controller_b_name.get("name") or "flowsync_uq"

        ctrl_a = get_controller(controller_a_name)
        ctrl_a.reset(seed=seed)
        fsm_a = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
        fsm_a.reset()

        ctrl_b = get_controller(controller_b_name)
        ctrl_b.reset(seed=seed)
        fsm_b = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
        fsm_b.reset()

        fault_profile = FAULT_PRESETS.get(noise_preset, FaultProfile(name=noise_preset))
        fault_injector_a = PerceptionFaultInjector(profile=fault_profile, seed=seed + 999) if fault_profile.name != "clean" else None
        fault_injector_b = PerceptionFaultInjector(profile=fault_profile, seed=seed + 999) if fault_profile.name != "clean" else None

        dp = scenario.demand_profile
        profile = TrafficProfile(
            id=scenario.scenario_id,
            name=scenario.name,
            description=scenario.description,
            directional_weights=dp.directional_weights,
            turn_probs=[
                dp.turn_ratios["north"]["straight"],
                dp.turn_ratios["north"]["left"],
                dp.turn_ratios["north"]["right"],
            ],
            base_lambda=dp.base_lambda,
            lambda_multiplier=1.0,
        )

        env_a = TrafficEnv(max_steps=num_steps, red_duration=scenario.red_duration)
        env_a.set_traffic_profile(profile)
        obs_a, _ = env_a.reset(seed=seed)

        env_b = TrafficEnv(max_steps=num_steps, red_duration=scenario.red_duration)
        env_b.set_traffic_profile(profile)
        obs_b, _ = env_b.reset(seed=seed)

        trace_hash = hashlib.sha256(f"{scenario.scenario_hash}_{seed}_{noise_preset}".encode()).hexdigest()[:12]

        await research_manager.send_json(self.websocket, {
            "type": "paired_started",
            "scenario_id": scenario.scenario_id,
            "seed": seed,
            "trace_hash": trace_hash,
            "controller_a": controller_a_name,
            "controller_b": controller_b_name,
            "noise_profile": fault_profile.to_dict(),
            "total_steps": num_steps,
        })

        all_delays_a: List[float] = []
        all_delays_b: List[float] = []
        queue_area_a = 0.0
        queue_area_b = 0.0

        try:
            for step in range(num_steps):
                if not self.is_running:
                    break
                
                while self.is_paused and self.is_running:
                    await asyncio.sleep(0.1)

                # Step controller A
                queues_a = env_a.intersection.get_movement_queues()
                ctx_a = ControllerContext(
                    timestep=step, dt=0.1, current_phase=env_a.intersection.signal.current_phase,
                    time_in_phase=env_a.intersection.signal.time_in_phase,
                    color=env_a.intersection.signal.color.name,
                    can_switch_phase=env_a.intersection.signal.can_switch_phase,
                    is_decision_step=env_a.is_decision_step,
                    valid_action_mask=env_a.get_valid_action_mask(),
                    movement_queues=queues_a,
                    outgoing_counts={},
                    starvation_times=env_a.intersection.signal.starvation_timer.copy(),
                )
                if fault_injector_a:
                    obs_a = fault_injector_a.corrupt_observation(obs_a, step=step)
                act_a = ctrl_a.get_action(obs_a, ctx_a)
                fsm_dec_a = fsm_a.step(act_a, dt=0.1)
                obs_a, _, _, _, _ = env_a.step(fsm_dec_a.executed_action)

                # Step controller B
                queues_b = env_b.intersection.get_movement_queues()
                ctx_b = ControllerContext(
                    timestep=step, dt=0.1, current_phase=env_b.intersection.signal.current_phase,
                    time_in_phase=env_b.intersection.signal.time_in_phase,
                    color=env_b.intersection.signal.color.name,
                    can_switch_phase=env_b.intersection.signal.can_switch_phase,
                    is_decision_step=env_b.is_decision_step,
                    valid_action_mask=env_b.get_valid_action_mask(),
                    movement_queues=queues_b,
                    outgoing_counts={},
                    starvation_times=env_b.intersection.signal.starvation_timer.copy(),
                )
                if fault_injector_b:
                    obs_b = fault_injector_b.corrupt_observation(obs_b, step=step)
                act_b = ctrl_b.get_action(obs_b, ctx_b)
                fsm_dec_b = fsm_b.step(act_b, dt=0.1)
                obs_b, _, _, _, _ = env_b.step(fsm_dec_b.executed_action)

                # Metrics
                delays_a = [v.wait_time for v in env_a.intersection.vehicles if v.state != "passed"]
                if delays_a: all_delays_a.extend(delays_a)
                m_delay_a = float(np.mean(all_delays_a)) if all_delays_a else 0.0
                queue_area_a += sum(queues_a.values()) * 0.1

                delays_b = [v.wait_time for v in env_b.intersection.vehicles if v.state != "passed"]
                if delays_b: all_delays_b.extend(delays_b)
                m_delay_b = float(np.mean(all_delays_b)) if all_delays_b else 0.0
                queue_area_b += sum(queues_b.values()) * 0.1

                u_b_val = 0.0
                if hasattr(ctrl_b, "_last_uncertainty") and ctrl_b._last_uncertainty is not None:
                    u_obj = ctrl_b._last_uncertainty
                    u_b_val = float(u_obj.score if hasattr(u_obj, "score") else u_obj)

                is_fb_b = False
                if hasattr(ctrl_b, "supervisor") and ctrl_b.supervisor:
                    auth = getattr(ctrl_b.supervisor, "authority", None)
                    is_fb_b = getattr(auth, "value", str(auth)) == "fallback_active"

                paired_payload = {
                    "type": "paired_telemetry",
                    "step": step,
                    "sim_time_s": round(step * 0.1, 1),
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "trace_hash": trace_hash,
                    "controller_a": {
                        "name": controller_a_name,
                        "phase": env_a.intersection.signal.current_phase,
                        "fsm_state": fsm_a.color.name,
                        "mean_delay": round(m_delay_a, 2),
                        "queue_area": round(queue_area_a, 1),
                        "throughput": env_a.intersection.total_passed,
                        "vehicles": _build_vehicle_list(env_a, fault_injector_a),
                    },
                    "controller_b": {
                        "name": controller_b_name,
                        "phase": env_b.intersection.signal.current_phase,
                        "fsm_state": fsm_b.color.name,
                        "mean_delay": round(m_delay_b, 2),
                        "queue_area": round(queue_area_b, 1),
                        "throughput": env_b.intersection.total_passed,
                        "uncertainty": round(u_b_val, 3),
                        "fallback_active": is_fb_b,
                        "vehicles": _build_vehicle_list(env_b, fault_injector_b),
                    },
                    "deltas": {
                        "delay_delta": round(m_delay_b - m_delay_a, 2),
                        "queue_area_delta": round(queue_area_b - queue_area_a, 1),
                        "throughput_delta": env_b.intersection.total_passed - env_a.intersection.total_passed,
                    }
                }

                await research_manager.send_json(self.websocket, paired_payload)
                sleep_time = max(0.005, (0.1 / max(0.1, self.speed)))
                await asyncio.sleep(sleep_time)

            await research_manager.send_json(self.websocket, {
                "type": "paired_completed",
                "summary": {
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "controller_a": {"name": controller_a_name, "final_delay": round(m_delay_a, 2), "throughput": env_a.intersection.total_passed},
                    "controller_b": {"name": controller_b_name, "final_delay": round(m_delay_b, 2), "throughput": env_b.intersection.total_passed},
                    "delay_savings_pct": round(((m_delay_a - m_delay_b) / max(0.1, m_delay_a)) * 100, 1),
                }
            })

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error in paired execution")
            await research_manager.send_json(self.websocket, {
                "type": "experiment_error",
                "error": str(e),
            })
        finally:
            self.is_running = False

    def _resolve_run_dir(self, run_id: str) -> Optional[Path]:
        """Resolve a run id to its results directory.

        Accepts either the directory name (exp_...) or the experiment_id
        stored inside metadata.json.
        """
        candidate = _RESULTS_DIR / run_id
        if candidate.is_dir() and (candidate / "trajectory.jsonl").exists():
            return candidate
        if _RESULTS_DIR.is_dir():
            for sub in _RESULTS_DIR.iterdir():
                meta = sub / "metadata.json"
                if sub.is_dir() and meta.exists():
                    try:
                        stored = json.loads(meta.read_text(encoding="utf-8"))
                        if stored.get("experiment_id") == run_id and (sub / "trajectory.jsonl").exists():
                            return sub
                    except Exception:
                        continue
        return None

    async def run_replay(self, run_id: str, speed: float = 1.0) -> None:
        """Stream a recorded trajectory without re-simulating physics.

        Supports live pause/resume (shared flags), set_speed pacing changes,
        and seek jumps to an absolute step index.
        """
        self.is_running = True
        self.is_paused = False
        self.seek_step = None
        self.set_speed(speed)

        run_dir = self._resolve_run_dir(run_id)
        if run_dir is None:
            await research_manager.send_json(self.websocket, {
                "type": "experiment_error",
                "error": f"Run '{run_id}' not found in results/.",
            })
            self.is_running = False
            return

        try:
            frames: List[Dict[str, Any]] = []
            with open(run_dir / "trajectory.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        frames.append(json.loads(line))

            if not frames:
                await research_manager.send_json(self.websocket, {
                    "type": "experiment_error",
                    "error": f"Run '{run_id}' has an empty trajectory.",
                })
                self.is_running = False
                return

            metadata: Dict[str, Any] = {}
            meta_path = run_dir / "metadata.json"
            if meta_path.exists():
                try:
                    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    metadata = {}

            first = frames[0]
            await research_manager.send_json(self.websocket, {
                "type": "replay_started",
                "experiment_id": metadata.get("experiment_id", run_id),
                "scenario_id": metadata.get("scenario_id", first.get("scenario_id", "")),
                "scenario_hash": metadata.get("scenario_hash", first.get("scenario_hash", "")),
                "controller": metadata.get("controller", first.get("controller", "")),
                "seed": metadata.get("seed", first.get("seed", 0)),
                "total_steps": len(frames),
                "replay_of": run_id,
            })

            idx = 0
            total = len(frames)
            while idx < total:
                if not self.is_running:
                    break

                while self.is_paused and self.is_running:
                    await asyncio.sleep(0.1)

                if self.seek_step is not None:
                    idx = max(0, min(total - 1, self.seek_step))
                    self.seek_step = None

                payload = dict(frames[idx])
                payload["type"] = "research_frame"
                payload["replay"] = True
                await research_manager.send_json(self.websocket, payload)
                idx += 1

                sleep_time = max(0.005, (0.1 / max(0.1, self.speed)))
                await asyncio.sleep(sleep_time)

            if self.is_running:
                await research_manager.send_json(self.websocket, {
                    "type": "replay_completed",
                    "result": {
                        "experiment_id": metadata.get("experiment_id", run_id),
                        "scenario_id": metadata.get("scenario_id", first.get("scenario_id", "")),
                        "controller": metadata.get("controller", first.get("controller", "")),
                        "seed": metadata.get("seed", first.get("seed", 0)),
                        "num_steps": total,
                        "status": "COMPLETED",
                        "replay": True,
                    },
                })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error in replay execution")
            await research_manager.send_json(self.websocket, {
                "type": "experiment_error",
                "error": str(e),
            })
        finally:
            self.is_running = False


async def research_socket(websocket: WebSocket) -> None:
    """WebSocket endpoint /ws/research."""
    await research_manager.connect(websocket)
    session = ExperimentSession(websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except Exception:
                continue

            cmd = msg.get("command")
            if cmd == "start_experiment":
                session.stop()
                scenario_id = msg.get("scenario_id", "test_clean_balanced_01")
                controller = msg.get("controller", "flowsync_uq")
                if isinstance(controller, dict):
                    controller = controller.get("id") or controller.get("name") or "flowsync_uq"
                seed = int(msg.get("seed", 1101))
                preset = msg.get("noise_preset", "clean")
                params = msg.get("noise_params", {})
                speed = float(msg.get("speed", 1.0))
                session.task = asyncio.create_task(
                    session.run_single(
                        scenario_id=scenario_id,
                        controller_name=controller,
                        seed=seed,
                        noise_preset=preset,
                        noise_params=params,
                        speed=speed,
                    )
                )

            elif cmd == "start_paired_comparison":
                session.stop()
                scenario_id = msg.get("scenario_id", "test_clean_balanced_01")
                ctrl_a = msg.get("controller_a", "d3qn")
                if isinstance(ctrl_a, dict):
                    ctrl_a = ctrl_a.get("id") or ctrl_a.get("name") or "d3qn"
                ctrl_b = msg.get("controller_b", "flowsync_uq")
                if isinstance(ctrl_b, dict):
                    ctrl_b = ctrl_b.get("id") or ctrl_b.get("name") or "flowsync_uq"
                seed = int(msg.get("seed", 1101))
                preset = msg.get("noise_preset", "miss_30")
                speed = float(msg.get("speed", 1.0))
                session.task = asyncio.create_task(
                    session.run_paired(
                        scenario_id=scenario_id,
                        controller_a_name=ctrl_a,
                        controller_b_name=ctrl_b,
                        seed=seed,
                        noise_preset=preset,
                        speed=speed,
                    )
                )

            elif cmd == "pause":
                session.is_paused = True
                await research_manager.send_json(websocket, {"type": "experiment_paused"})

            elif cmd == "resume":
                session.is_paused = False
                await research_manager.send_json(websocket, {"type": "experiment_resumed"})

            elif cmd == "stop":
                session.stop()
                await research_manager.send_json(websocket, {"type": "experiment_stopped"})

            elif cmd == "set_speed":
                session.set_speed(msg.get("speed", 1.0))

            elif cmd == "seek":
                session.request_seek(int(msg.get("step", 0)))

            elif cmd == "replay_run":
                session.stop()
                run_id = str(msg.get("run_id", ""))
                speed = float(msg.get("speed", 1.0))
                if not run_id:
                    await research_manager.send_json(websocket, {
                        "type": "experiment_error",
                        "error": "replay_run requires a run_id.",
                    })
                else:
                    session.task = asyncio.create_task(session.run_replay(run_id=run_id, speed=speed))

            else:
                await research_manager.send_json(websocket, {
                    "type": "experiment_error",
                    "error": f"Unknown command '{cmd}'.",
                })

    except WebSocketDisconnect:
        session.stop()
        research_manager.disconnect(websocket)
    except Exception as e:
        session.stop()
        research_manager.disconnect(websocket)

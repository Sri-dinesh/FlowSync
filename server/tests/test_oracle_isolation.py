"""
test_oracle_isolation.py — Oracle Ground-Truth vs Camera-Observable State Isolation Tests
========================================================================================
Task 1A.2 Acceptance Criteria:
- Policy can run entirely on camera-observable state.
- Hidden simulator truth (spawner backlog, unobserved upstream vehicles) is inaccessible.
- A test fails if forbidden oracle fields enter the policy observation.
"""
import numpy as np
import pytest

from server.app.simulation.intersection import Intersection
from server.app.simulation.vehicle import Vehicle
from research.observation.ground_truth_builder import GroundTruthStateBuilder
from research.observation.camera_observable_builder import CameraObservableStateBuilder


def test_oracle_vs_camera_observable_isolation():
    """Vehicles far upstream (> 0.45) must be visible to GroundTruth but hidden from CameraObservable."""
    intersection = Intersection(spawn_lambda=0.0)
    gt_builder = GroundTruthStateBuilder()
    cam_builder = CameraObservableStateBuilder(fov_max_distance=0.45)

    # 1. Place a vehicle near stop-line (position = 0.20, inside FOV)
    v_near = Vehicle(
        id="v-near", lane="north", turn="straight", position=0.20,
        wait_time=5.0, speed=0.0, state="waiting"
    )
    intersection.lanes["north_straight"].append(v_near)

    # 2. Place a vehicle far upstream (position = 0.85, outside camera FOV)
    v_far = Vehicle(
        id="v-far", lane="north", turn="straight", position=0.85,
        wait_time=2.0, speed=0.1, state="approaching"
    )
    intersection.lanes["north_straight"].append(v_far)

    # Ground truth must see both vehicles (count = 2)
    gt_obs = gt_builder.build_oracle_state(intersection)
    # Camera observable must see ONLY the near vehicle (count = 1)
    cam_obs = cam_builder.build_observation(intersection)

    # Dim 0 is north_straight queue
    gt_north_queue = gt_obs[0]
    cam_north_queue = cam_obs[0]

    assert gt_north_queue == pytest.approx(float(np.tanh(2.0 / 15.0)), rel=1e-3)
    assert cam_north_queue == pytest.approx(float(np.tanh(1.0 / 15.0)), rel=1e-3)
    assert gt_north_queue > cam_north_queue  # Demonstrates oracle isolation!


def test_spawner_backlog_leakage_protection():
    """Spawner backlogs (vehicles queued outside the simulated grid) must NEVER enter camera obs."""
    intersection = Intersection(spawn_lambda=0.0)
    cam_builder = CameraObservableStateBuilder()

    # Manually inject backlog into spawner
    intersection.spawner._pending["north_straight"].append(10.0)
    intersection.spawner._pending["north_straight"].append(12.0)

    cam_obs = cam_builder.build_observation(intersection)

    # Dim 0 (north_straight) should be 0 because lanes on physical canvas are empty
    assert cam_obs[0] == 0.0
    assert len(cam_obs) == 28
    assert cam_obs.dtype == np.float32

"""Explicit, observed-only spatial baseline; never changes historical Max-Pressure."""
from dataclasses import replace
import numpy as np

from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.observations import SPATIAL_KEY
from server.app.simulation.traffic_math import MOVEMENT_KEYS


class UpstreamMaxPressureController(MaxPressureController):
    requires_spatial_observation = True

    def __init__(self):
        super().__init__()
        self.name = "max_pressure_upstream"

    def act(self, observation, context):
        spatial = np.asarray(context.extra_telemetry.get(SPATIAL_KEY), dtype=float)
        if (spatial.shape != (12,) or not np.isfinite(spatial).all() or (spatial < 0).any()
                or (spatial > np.asarray(observation[:12]) + 1e-7).any()):
            raise ValueError("Upstream baseline requires delivered spatial counts")
        counts = np.rint(15 * np.arctanh(np.clip(spatial, 0, .999999))).astype(int)
        return super().act(observation, replace(context, movement_queues=dict(zip(MOVEMENT_KEYS, counts.tolist()))))

    def get_capabilities(self):
        return replace(super().get_capabilities(), name=self.name, version="1.0.0",
                       description="Max-Pressure on delivered upstream-only counts; explicit spatial baseline")

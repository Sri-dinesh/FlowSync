"""Versioned, sensor-only policy features; never reads the simulator."""
import numpy as np

LEGACY_VERSION = "v6_28dim_smdp"
OBSERVED_VERSION = "v7_36dim_observed"
TEMPORAL_VERSION = "v8_64dim_temporal"
TEMPORAL_CONTROL_VERSION = "v8_64dim_zero_history"
TEMPORAL_VERSIONS = (TEMPORAL_CONTROL_VERSION, TEMPORAL_VERSION)
TEMPORAL_KEY = "policy_temporal_features_v8"
SPATIAL_VERSION = "v9_48dim_spatial"
SPATIAL_CONTROL_VERSION = "v9_48dim_zero_spatial"
SPATIAL_VERSIONS = (SPATIAL_CONTROL_VERSION, SPATIAL_VERSION)
SPATIAL_KEY = "policy_spatial_features_v9"
SPATIAL_SCHEMA = {
    "current_v7_slice": [0, 36], "delivered_upstream_counts_slice": [36, 48],
    "count_encoding": "tanh(delivered upstream count / 15), canonical movement order",
    "boundary": "non-passed vehicles at/before stop line; same backlog assumption as legacy",
    "saturation": "upstream count bounded by reconstructed legacy movement count",
    "faults": "joint count partition; shared packet latency/drop, burst and lane swap",
    "ghost_and_positive_jitter_location": "independent Bernoulli(0.5) upstream assignment",
    "control_arm": "indices 36:48 forced to zero; identical architecture and sensor pipeline",
    "mask_and_shield": "unchanged legacy delivered demand; spatial extension is additional information only",
}
TEMPORAL_SCHEMA = {
    "tick_seconds": .1, "current_v7_slice": [0, 36],
    "delivered_count_lags": {"10_ticks": [36, 48], "30_ticks": [48, 60]},
    "count_encoding": "unchanged tanh(count / 15) from delivered packet",
    "age_index": 60, "age_encoding": "min(age_ms / 5000, 1); unknown -> 0 plus false known flag",
    "lag_available_indices": [61, 62], "age_known_index": 63,
    "control_arm": "indices 36:64 forced to zero; identical architecture",
    "history_boundary": "post-fault packets at every tick, reset each episode; no interpolation",
}
OBSERVATION_DIMS = {LEGACY_VERSION: 28, OBSERVED_VERSION: 36,
                    TEMPORAL_VERSION: 64, TEMPORAL_CONTROL_VERSION: 64,
                    SPATIAL_VERSION: 48, SPATIAL_CONTROL_VERSION: 48}


class DeliveredHistory:
    """One episode of post-fault packets at 10 Hz; no simulator access.

    Extension order: lag-10 counts (12), lag-30 counts (12), age/5000,
    lag-10 available, lag-30 available, age known. Missing samples are not
    interpolated. A repeated camera frame is still delivered at a new tick.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self._counts = {}
        self._last_step = None

    def update(self, observation, context):
        step = context.timestep
        if (not isinstance(step, (int, np.integer)) or step < 0
                or not np.isclose(context.dt, .1, rtol=0, atol=1e-9)):
            raise ValueError("Temporal observations require integer 10 Hz ticks")
        if self._last_step is not None and step <= self._last_step:
            raise ValueError("Temporal ticks must increase; reset history between episodes")
        counts = np.asarray(observation, dtype=np.float32)[:12]
        if counts.shape != (12,) or not np.isfinite(counts).all():
            raise ValueError("Temporal history requires twelve finite delivered counts")
        self._counts = {t: x for t, x in self._counts.items() if t >= step - 30}
        self._counts[step] = counts.copy()
        self._last_step = step
        available = [float(step - lag in self._counts) for lag in (10, 30)]
        lags = [self._counts.get(step - lag, np.zeros(12, dtype=np.float32)) for lag in (10, 30)]
        age = context.extra_telemetry.get("observation_age_ms")
        known = isinstance(age, (int, float, np.integer, np.floating)) and np.isfinite(age) and age >= 0
        tail = [min(float(age) / 5000., 1.) if known else 0., *available, float(known)]
        return np.concatenate((*lags, tail)).astype(np.float32)


def encode_policy_observation(observation, context, version=LEGACY_VERSION):
    if version == LEGACY_VERSION:
        return np.asarray(observation, dtype=np.float32)
    if version not in (OBSERVED_VERSION, *TEMPORAL_VERSIONS, *SPATIAL_VERSIONS):
        raise ValueError(f"Unsupported policy observation version: {version}")
    if len(observation) != 28:
        raise ValueError("v7 requires the shared 28-dimensional sensor observation")
    outgoing = context.outgoing_counts or {}
    waits = context.phase_starvation_times or {}
    extra = [np.tanh(max(0, outgoing.get(d, 0)) / 15.)
             for d in ("north", "south", "east", "west")]
    extra += [min(1., max(0., waits.get(p, 0)) / 45.) for p in range(4)]
    current = np.concatenate((observation, extra)).astype(np.float32)
    if version == OBSERVED_VERSION:
        return current
    if version in SPATIAL_VERSIONS:
        spatial = np.asarray(context.extra_telemetry.get(SPATIAL_KEY), dtype=np.float32)
        if (spatial.shape != (12,) or not np.isfinite(spatial).all() or (spatial < 0).any()
                or (spatial > np.asarray(observation[:12]) + 1e-7).any()):
            raise ValueError("v9 requires delivered spatial counts from the shared spatial sensor boundary")
        if version == SPATIAL_CONTROL_VERSION:
            spatial = np.zeros(12, dtype=np.float32)
        return np.concatenate((current, spatial))
    temporal = np.asarray(context.extra_telemetry.get(TEMPORAL_KEY), dtype=np.float32)
    if temporal.shape != (28,) or not np.isfinite(temporal).all():
        raise ValueError("v8 requires the research delivered-history builder on every tick")
    if version == TEMPORAL_CONTROL_VERSION:
        temporal = np.zeros(28, dtype=np.float32)
    return np.concatenate((current, temporal))

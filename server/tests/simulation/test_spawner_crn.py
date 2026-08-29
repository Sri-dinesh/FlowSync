"""
Tests for PoissonSpawner and CitySpawner Common Random Numbers (CRN) seeding.
Verifies that:
  1. Identical seeds yield identical vehicle counts, lanes, and turns across runs (fair benchmarking).
  2. Unseeded (seed=None) spawners yield stochastic, non-identical arrivals for manual simulations.
"""
import pytest
from app.simulation.spawner import PoissonSpawner
from app.simulation.city_spawner import CitySpawner
from app.simulation.city_network import CityNetwork


def test_poisson_spawner_crn_determinism():
    """Identical seeds must produce the exact same vehicle sequence."""
    SEED = 12345
    spawner = PoissonSpawner(lambda_rate=1.0)
    spawner.set_enabled(True)

    # Run 1
    spawner.set_seed(SEED)
    lanes_run1 = {
        f"{d}_{t}": []
        for d in ["north", "south", "east", "west"]
        for t in ["straight", "left", "right"]
    }
    trace1 = []
    for _ in range(50):
        spawned = spawner.spawn(dt=0.1, lanes=lanes_run1)
        for v in spawned:
            trace1.append((v.lane, v.turn))

    # Run 2 (reseeded with exact same seed)
    spawner.set_seed(SEED)
    lanes_run2 = {
        f"{d}_{t}": []
        for d in ["north", "south", "east", "west"]
        for t in ["straight", "left", "right"]
    }
    trace2 = []
    for _ in range(50):
        spawned = spawner.spawn(dt=0.1, lanes=lanes_run2)
        for v in spawned:
            trace2.append((v.lane, v.turn))

    assert len(trace1) > 0, "Spawner should have generated vehicles"
    assert len(trace1) == len(trace2), f"CRN runs must generate identical count: {len(trace1)} vs {len(trace2)}"
    assert trace1 == trace2, "CRN runs must generate identical lane and turn sequence"


def test_poisson_spawner_unseeded_randomness():
    """Unseeded spawner (seed=None) must restore stochastic behavior."""
    spawner = PoissonSpawner(lambda_rate=1.0)
    spawner.set_enabled(True)
    spawner.set_seed(None)

    lanes_a = {f"{d}_{t}": [] for d in ["north", "south", "east", "west"] for t in ["straight", "left", "right"]}
    trace_a = []
    for _ in range(100):
        spawned = spawner.spawn(dt=0.1, lanes=lanes_a)
        for v in spawned:
            trace_a.append((v.lane, v.turn))

    spawner.set_seed(None)
    lanes_b = {f"{d}_{t}": [] for d in ["north", "south", "east", "west"] for t in ["straight", "left", "right"]}
    trace_b = []
    for _ in range(100):
        spawned = spawner.spawn(dt=0.1, lanes=lanes_b)
        for v in spawned:
            trace_b.append((v.lane, v.turn))

    # In 100 ticks with high lambda, stochastic traces should not be identical
    assert trace_a != trace_b, "Unseeded spawner must produce non-identical stochastic sequences"


def test_city_spawner_crn_determinism():
    """CitySpawner must produce identical arrivals across city network when seeded."""
    SEED = 99999
    city_net1 = CityNetwork()
    city_spawner1 = CitySpawner(lambda_rate=1.5)
    city_spawner1.set_enabled(True)
    city_spawner1.set_seed(SEED)

    counts1 = []
    for _ in range(50):
        n = city_spawner1.spawn(dt=0.1, intersections=city_net1.intersections)
        counts1.append(n)

    city_net2 = CityNetwork()
    city_spawner2 = CitySpawner(lambda_rate=1.5)
    city_spawner2.set_enabled(True)
    city_spawner2.set_seed(SEED)

    counts2 = []
    for _ in range(50):
        n = city_spawner2.spawn(dt=0.1, intersections=city_net2.intersections)
        counts2.append(n)

    assert sum(counts1) > 0, "City spawner should spawn vehicles"
    assert counts1 == counts2, f"CitySpawner CRN must produce identical tick-by-tick counts: {counts1} vs {counts2}"
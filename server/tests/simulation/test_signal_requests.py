"""Signal requests, zero demand and scenario identity regressions."""
from copy import deepcopy
import pytest
from app.simulation.intersection import Intersection
from app.simulation.spawner import PoissonSpawner, TrafficProfile
from app.simulation.traffic_signal import TrafficSignal, SignalColor
from research.scenarios.scenario_schema import ScenarioConfig


def test_manual_request_waits_for_minimum_and_cannot_retarget_clearance():
    signal = TrafficSignal()
    signal.request_phase(1)
    signal.tick(.1,is_manual=True)
    assert signal.current_phase == 0 and signal.color == SignalColor.GREEN
    signal.tick(7.9,is_manual=True)
    assert signal.color == SignalColor.YELLOW and signal.pending_phase == 1
    signal.request_phase(2)
    signal.tick(2.,is_manual=True)
    assert signal.color == SignalColor.RED and signal.pending_phase == 1
    signal.tick(3.,is_manual=True)
    assert signal.color == SignalColor.GREEN and signal.current_phase == 1
    signal.tick(8.,is_manual=True)
    assert signal.color == SignalColor.YELLOW and signal.pending_phase == 2
    signal.MIN_GREEN_TIME = 9.
    assert signal.min_green_duration == 9.
    signal.min_green_duration = 10.
    assert signal.MIN_GREEN_TIME == 10.



@pytest.mark.parametrize("phase", [True,-1,4,1.5,float("nan")])
def test_invalid_signal_request_does_not_mutate_signal(phase):
    signal = TrafficSignal()
    state = deepcopy(vars(signal))
    with pytest.raises(ValueError):
        signal.request_phase(phase)
    assert vars(signal) == state



@pytest.mark.parametrize("stage", [SignalColor.GREEN,SignalColor.YELLOW,SignalColor.RED])
def test_emergency_uses_physical_clearance_without_stale_targets(stage):
    intersection = Intersection()
    intersection.spawner.set_enabled(False)
    signal = intersection.signal
    signal.color,signal.pending_phase,signal.time_in_phase = stage,2 if stage != SignalColor.GREEN else None,.2
    intersection.trigger_emergency_override("east")
    intersection.tick(.1,is_manual=True)
    assert signal.color == stage and signal.current_phase == 0
    assert signal.time_in_phase == pytest.approx(.3)
    assert signal.pending_phase == (2 if stage != SignalColor.GREEN else None)
    assert not hasattr(signal,"_pending_phase")



def test_zero_demand_profile_replaces_positive_demand_and_stale_hash_rejects():
    spawner = PoissonSpawner(lambda_rate=.8)
    spawner.set_profile(TrafficProfile(id="zero",name="Zero",description="Zero demand",base_lambda=0.))
    assert spawner.lambda_rate == 0.
    assert spawner.spawn(.1,{}) == [] and spawner.generated_last_tick == 0
    scenario = ScenarioConfig("train_contract","train","Contract")
    altered = {**scenario.to_dict(),"duration_steps":scenario.duration_steps+1}
    with pytest.raises(ValueError,match="scenario_hash"):
        ScenarioConfig.from_dict(altered)
    scenario.duration_steps += 1
    with pytest.raises(ValueError,match="mutated"):
        scenario.to_dict()

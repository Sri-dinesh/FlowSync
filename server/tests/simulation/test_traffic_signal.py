import pytest
from app.simulation.traffic_signal import TrafficSignal, SignalPhase, SignalColor

def test_signal_initialization():
    ts = TrafficSignal()
    assert ts.current_phase == SignalPhase.NS_GREEN.value
    assert ts.color == SignalColor.GREEN
    assert ts.time_in_phase == 0.0

def test_signal_set_phase():
    ts = TrafficSignal()
    ts.set_phase(SignalPhase.EW_GREEN.value)
    assert ts.color == SignalColor.YELLOW
    assert ts._pending_phase == SignalPhase.EW_GREEN.value
    assert ts.time_in_phase == 0.0

def test_signal_tick_yellow_to_red():
    ts = TrafficSignal()
    ts.set_phase(SignalPhase.EW_GREEN.value)
    ts.tick(dt=ts.yellow_duration)
    assert ts.color == SignalColor.RED
    assert ts.time_in_phase == 0.0

def test_signal_tick_red_to_green():
    ts = TrafficSignal()
    ts.set_phase(SignalPhase.EW_GREEN.value)
    ts.tick(dt=ts.yellow_duration) # to Red
    ts.tick(dt=1.0) # Red to Green
    assert ts.color == SignalColor.GREEN
    assert ts.current_phase == SignalPhase.EW_GREEN.value
    assert ts.time_in_phase == 0.0

def test_signal_fixed_duration_rollover():
    ts = TrafficSignal()
    ts.tick(dt=ts.fixed_duration)
    assert ts.color == SignalColor.YELLOW
    assert ts._pending_phase == (SignalPhase.NS_GREEN.value + 1) % 4

def test_is_green_for():
    ts = TrafficSignal()
    # NS_GREEN is phase 0
    assert ts.is_green_for("north", "straight") is True
    assert ts.is_green_for("east", "straight") is False
    
    ts.set_phase(SignalPhase.EW_GREEN.value)
    assert ts.is_green_for("north") is False # It's yellow

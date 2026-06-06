import pytest
from app.simulation.vehicle import Vehicle, DEFAULT_SPEED

def test_vehicle_initialization():
    v = Vehicle(id="v1", lane="north", turn="straight", position=0.0, wait_time=0.0, speed=0.0, state="waiting")
    assert v.id == "v1"
    assert v.lane == "north"
    assert v.position == 0.0
    assert v.state == "waiting"

def test_vehicle_movement():
    v = Vehicle(id="v1", lane="north", turn="straight", position=0.0, wait_time=0.0, speed=0.0, state="waiting")
    v.tick(dt=1.0, can_move=True)
    assert v.position == DEFAULT_SPEED
    assert v.state == "moving"
    assert v.speed == DEFAULT_SPEED

def test_vehicle_waiting():
    v = Vehicle(id="v1", lane="north", turn="straight", position=0.0, wait_time=0.0, speed=0.0, state="waiting")
    v.tick(dt=1.0, can_move=False)
    assert v.position == 0.0
    assert v.state == "waiting"
    assert v.wait_time == 1.0
    assert v.speed == 0.0

def test_vehicle_passed():
    v = Vehicle(id="v1", lane="north", turn="straight", position=0.95, wait_time=0.0, speed=DEFAULT_SPEED, state="moving")
    v.tick(dt=1.0, can_move=True)
    assert v.position >= 1.0
    assert v.state == "passed"

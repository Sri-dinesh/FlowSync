"""Declared pressure comparator with an observed-demand phase-service watchdog.

This is a conventional engineering control, not a new fairness algorithm. Ages
refer to observed phase demand without executed green, not vehicle waiting.
"""
from research.policies.sumo_classical import Clock, Counts, choose_action

VERSION = "sumo_service_watchdog_v1"
WATCHDOG_TICKS = 240


def _validate(counts, clock, ages):
    if (not isinstance(counts, Counts) or not isinstance(clock, Clock)
            or not isinstance(ages, tuple) or len(ages) != 2
            or any(type(value) is not int or value < 0 for value in ages)):
        raise ValueError("Watchdog requires delivered counts, a physical clock and two nonnegative integer ages")


def propose(counts, clock, ages):
    _validate(counts, clock, ages)
    reference = choose_action("max_pressure", counts, clock)
    other = 1-clock.phase
    demanded = sum(counts.incoming[2*other:2*other+2]) > 0
    override = clock.stage == "green" and clock.age >= 80 and demanded and ages[other] >= WATCHDOG_TICKS
    return dict(reference=reference, proposal=other if override else reference,
                watchdog_due=override, ages=list(ages))


def after_execution(counts, executed, ages):
    _validate(counts, executed, ages)
    return tuple(0 if (executed.stage == "green" and executed.phase == phase
                       or not any(counts.incoming[2*phase:2*phase+2])) else ages[phase]+1
                 for phase in (0, 1))

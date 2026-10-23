"""Untuned total incoming count ablation of the frozen SUMO classical policies."""
from research.policies.sumo_classical import Clock, Counts, choose_action


def choose_total_count(packet: Counts, clock: Clock) -> int:
    if not isinstance(packet, Counts) or not isinstance(clock, Clock):
        raise ValueError("Delivered count packet and physical clock required")
    if clock.stage != "green" or clock.age < 80:
        return clock.phase
    ns, ew = sum(packet.incoming[:2]), sum(packet.incoming[2:])
    return clock.phase if ns == ew else int(ew > ns)


def policy_for(controller):
    if controller == "total_incoming":
        return choose_total_count
    if controller in ("halted", "fixed", "max_pressure"):
        return lambda packet, clock: choose_action(controller, packet, clock)
    raise ValueError("Unknown observed-count policy")

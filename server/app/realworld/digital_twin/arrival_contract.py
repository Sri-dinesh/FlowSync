"""Reject incomplete replay inputs instead of inventing movements or timing."""
import math


def replay_input_error(arrivals):
    if not isinstance(arrivals, list) or not arrivals:
        return "Replay requires a nonempty recorded arrival list."
    seen = set()
    for row in arrivals:
        if not isinstance(row, dict):
            return "Each replay arrival must be an object."
        if row.get("event_semantics") == "first_track_sighting_not_stop_line_arrival":
            return "Camera track sightings lack measured movement and arrival timing; calibrated replay is unavailable."
        if row.get("lane") not in ("north", "south", "east", "west") or row.get("turn") not in ("straight", "left", "right"):
            return "Replay requires an explicit approach and turning movement for every arrival."
        t = row.get("time_s")
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
            return "Replay requires finite nonnegative arrival timestamps."
        identifier = row.get("vehicle_id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            return "Replay requires unique vehicle identifiers."
        seen.add(identifier)
    return None

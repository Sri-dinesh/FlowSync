"""Estimate provided upstream-event rates; occupancy exposure is not arrivals."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from .arrival_contract import replay_input_error
from ..models.config import LANE_KEYS, VEHICLE_QUEUE_WEIGHTS
from ..models.schemas import FlowCalibrationProvenance, TrafficFlowParams


class FlowCalibrator:
    """Count unique declared arrivals over an explicit source-clock interval.

    Accepted syntax does not validate camera accuracy, movement labels or
    coverage. Occupancies, first sightings and discharges are not demand.
    """

    def calibrate_from_session(self, session_path: str) -> TrafficFlowParams:
        raw = Path(session_path).read_bytes()
        data = json.loads(raw)
        if not isinstance(data,dict) or not isinstance(data.get("session_id"),str) or not data["session_id"].strip():
            raise ValueError("Event calibration requires a session_id")
        window,events = data.get("observation_window"),data.get("arrivals")
        if not isinstance(window,dict) or set(window) != {"start_s","end_s","timebase"}:
            raise ValueError("Calibration requires an explicit observation_window and upstream arrivals; occupancy frames are insufficient")
        start,end = window["start_s"],window["end_s"]
        if (any(type(t) not in (int,float) or not math.isfinite(t) for t in (start,end))
                or not 0 <= start < end):
            raise ValueError("Observation interval requires finite 0 <= start_s < end_s")
        error = replay_input_error(events)
        if error:
            raise ValueError(error)
        if any(event.get("event_semantics") != "upstream_demand_arrival" for event in events):
            raise ValueError("Every event must explicitly declare upstream_demand_arrival semantics")
        if any(not start <= event["time_s"] < end for event in events):
            raise ValueError("Arrival timestamps must lie in the half-open observation interval [start_s,end_s)")
        if any(e.get("vehicle_type") is not None and e["vehicle_type"] not in VEHICLE_QUEUE_WEIGHTS for e in events):
            raise ValueError("Unknown declared vehicle type")
        provenance = FlowCalibrationProvenance(timebase=window["timebase"],start_s=start,end_s=end,
            source_file_sha256=hashlib.sha256(raw).hexdigest())
        duration_minutes = (end-start)/60.
        counts = Counter(f"{e['lane']}_{e['turn']}" for e in events)
        rates = {lane:counts[lane]/duration_minutes for lane in LANE_KEYS}
        ratios = {}
        for direction in ("north","south","east","west"):
            total = sum(counts[f"{direction}_{turn}"] for turn in ("straight","left","right"))
            if total:
                ratios[direction] = {turn:counts[f"{direction}_{turn}"]/total for turn in ("straight","left","right")}
        types = Counter(e["vehicle_type"] for e in events) if all(e.get("vehicle_type") for e in events) else {}
        return TrafficFlowParams(intersection_id=data["session_id"],spawn_rates=rates,turn_ratios=ratios,
            vehicle_type_distribution={key:value/len(events) for key,value in types.items()},peak_hours=[],
            avg_vehicles_per_minute=len(events)/duration_minutes,calibration_provenance=provenance)

    def calibrate_from_directory(self, sessions_dir: str) -> TrafficFlowParams:
        raise ValueError("Calibrate one event session at a time; directory files do not establish shared clocks, coverage or nonoverlapping vehicles")

    def export_as_simulation_config(self, params: TrafficFlowParams) -> dict:
        if params.calibration_provenance is None:
            raise ValueError("Event-calibration export requires input provenance")
        return params.model_dump(mode="json")
